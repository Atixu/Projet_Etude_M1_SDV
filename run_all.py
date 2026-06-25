"""
run_all.py — Lanceur unique du pipeline Thumalien
Usage:
    python run_all.py              # pipeline complet sans dashboard
    python run_all.py --dashboard  # pipeline + lance le dashboard à la fin
    python run_all.py --skip-collect  # saute la collecte (données déjà en base)
"""

import argparse
import subprocess
import sys
import os
import time
from pathlib import Path

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

ROOT = Path(__file__).parent
SRC = ROOT / "src"
ETL = ROOT / "etl-bluesky"

STEPS = [
    {
        "id": "collect",
        "label": "Collecte Bluesky → MongoDB (posts_raw)",
        "script": SRC / "getapi.py",
        "skip_flag": "skip_collect",
    },
    {
        "id": "clean",
        "label": "Nettoyage NLP → MongoDB (posts_clean_kedro) — Kedro pipeline",
        "cmd": ["kedro", "run", "--pipeline", "nlp_cleaning"],
        "cwd": ETL,
        "env_extra": {"PYTHONUTF8": "1"},
        "skip_flag": None,
    },
    {
        "id": "claim",
        "label": "Filtre affirmations factuelles (claim detection)",
        "script": SRC / "run_claim_filter.py",
        "skip_flag": None,
    },
    {
        "id": "baseline",
        "label": "Modèle baseline TF-IDF + LogReg (fake news scoring)",
        "script": SRC / "run_baseline.py",
        "skip_flag": None,
    },
    {
        "id": "emotion",
        "label": "Analyse émotionnelle VADER + lexique",
        "script": SRC / "run_emotion_analysis.py",
        "skip_flag": None,
    },
    {
        "id": "scoring",
        "label": "Score final combiné + explainabilité",
        "script": SRC / "run_final_scoring.py",
        "skip_flag": None,
    },
]

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

GREEN  = "\033[92m"
YELLOW = "\033[93m"
RED    = "\033[91m"
CYAN   = "\033[96m"
BOLD   = "\033[1m"
RESET  = "\033[0m"

def banner(text: str) -> None:
    print(f"\n{BOLD}{CYAN}{'='*60}{RESET}")
    print(f"{BOLD}{CYAN}  {text}{RESET}")
    print(f"{BOLD}{CYAN}{'='*60}{RESET}\n")

def ok(text: str) -> None:
    print(f"{GREEN}✔  {text}{RESET}")

def warn(text: str) -> None:
    print(f"{YELLOW}⚠  {text}{RESET}")

def err(text: str) -> None:
    print(f"{RED}✖  {text}{RESET}")

def check_env() -> bool:
    env_file = ROOT / ".env"
    if not env_file.exists():
        err(".env introuvable. Lance : cp .env.example .env  puis remplis les variables.")
        return False
    ok(".env présent")
    return True

def check_mongo() -> bool:
    try:
        import pymongo
        client = pymongo.MongoClient("mongodb://localhost:27017", serverSelectionTimeoutMS=3000)
        client.server_info()
        client.close()
        ok("MongoDB accessible sur localhost:27017")
        return True
    except Exception as e:
        err(f"MongoDB inaccessible : {e}")
        print(f"  → Lance : {YELLOW}docker run -d --name m1-mongo -p 27017:27017 mongo:7{RESET}")
        return False

def run_step(step: dict) -> bool:
    label = step["label"]
    print(f"\n{BOLD}▶  {label}{RESET}")
    t0 = time.time()

    if "cmd" in step:
        env = os.environ.copy()
        env.update(step.get("env_extra", {}))
        result = subprocess.run(
            step["cmd"],
            cwd=str(step.get("cwd", ROOT)),
            env=env,
        )
    else:
        result = subprocess.run(
            [sys.executable, str(step["script"])],
            cwd=str(ROOT),
        )

    elapsed = time.time() - t0
    if result.returncode == 0:
        ok(f"Terminé en {elapsed:.1f}s")
        return True
    else:
        err(f"Échec (code {result.returncode}) après {elapsed:.1f}s")
        return False

# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(description="Pipeline Thumalien — lanceur unique")
    parser.add_argument("--dashboard", action="store_true", help="Lance le dashboard Streamlit après le pipeline")
    parser.add_argument("--skip-collect", dest="skip_collect", action="store_true", help="Saute la collecte Bluesky")
    parser.add_argument("--only", metavar="STEP_ID", help="Exécute uniquement une étape (collect/clean/baseline/emotion/scoring)")
    args = parser.parse_args()

    banner("Pipeline Thumalien — Fake News Detection on Bluesky")

    # --- Pré-requis ---
    print(f"{BOLD}Vérification des prérequis...{RESET}")
    if not check_env():
        sys.exit(1)
    if not check_mongo():
        sys.exit(1)

    # --- Étapes ---
    failures = []

    for step in STEPS:
        # Filtre --only
        if args.only and step["id"] != args.only:
            continue
        # Filtre --skip-collect
        if step["skip_flag"] == "skip_collect" and args.skip_collect:
            warn(f"Étape ignorée (--skip-collect) : {step['label']}")
            continue

        success = run_step(step)
        if not success:
            failures.append(step["label"])
            err("Pipeline interrompu.")
            sys.exit(1)

    # --- Résumé ---
    banner("Pipeline terminé avec succès ✔")
    if not failures:
        print(f"Toutes les étapes ont réussi.")

    # --- Dashboard ---
    if args.dashboard:
        dashboard = SRC / "dashboard_app.py"
        print(f"\n{BOLD}Lancement du dashboard Streamlit...{RESET}")
        print(f"  → Ouvre {CYAN}http://localhost:8501{RESET} dans ton navigateur.")
        print(f"  → Ctrl+C pour arrêter.\n")
        subprocess.run([sys.executable, "-m", "streamlit", "run", str(dashboard)], cwd=str(ROOT))


if __name__ == "__main__":
    main()
