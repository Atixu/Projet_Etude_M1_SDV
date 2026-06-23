"""Partie 7 - Monitoring energetique (Green IT).

Petit utilitaire qui mesure la consommation energetique et les emissions CO2
d'un bloc de code (entrainement, inference...) via CodeCarbon.

Utilisation:

    from energy_monitoring import track_energy

    with track_energy("baseline_training", n_samples=40000):
        ...  # code a mesurer

Chaque mesure est :
- loggee dans la console (energie Wh, CO2 g, duree s),
- ajoutee a reports/energy_summary.csv (1 ligne par run).

Si CodeCarbon n'est pas installe, le bloc s'execute normalement mais sans
mesure (avertissement dans les logs). Installation : pip install codecarbon
"""

from __future__ import annotations

import csv
import logging
import time
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path

# Grille electrique France (gCO2eq / kWh) - utilisee comme repere d'affichage.
FRANCE_GRID_GCO2_PER_KWH = 56.0


def _summary_path(output_dir: str | Path) -> Path:
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    return out / "energy_summary.csv"


def _append_summary(row: dict, output_dir: str | Path) -> None:
    path = _summary_path(output_dir)
    fields = [
        "timestamp", "task", "duration_s",
        "energy_kwh", "energy_wh", "emissions_gco2", "n_samples",
    ]
    write_header = not path.exists()
    with open(path, "a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        if write_header:
            writer.writeheader()
        writer.writerow({k: row.get(k, "") for k in fields})


@contextmanager
def track_energy(task: str, output_dir: str | Path = "reports", n_samples=None):
    """Mesure l'energie/CO2 du bloc englobe et l'enregistre.

    Args:
        task: nom de l'etape mesuree (ex: "baseline_training").
        output_dir: dossier ou ecrire energy_summary.csv (defaut: reports/).
        n_samples: nombre d'echantillons traites (optionnel, pour info).
    """
    tracker = None
    try:
        from codecarbon import EmissionsTracker

        tracker = EmissionsTracker(
            project_name=f"thumalien_{task}",
            output_dir=str(output_dir),
            output_file="emissions_raw.csv",
            country_iso_code="FRA",
            log_level="error",
            measure_power_secs=2,
            save_to_file=True,
        )
        tracker.start()
    except ImportError:
        logging.warning(
            "[energy] CodeCarbon non installe : bloc '%s' execute sans mesure "
            "(pip install codecarbon).", task,
        )
    except Exception as exc:  # configuration / hardware non supporte
        logging.warning("[energy] Tracker indisponible pour '%s' : %s", task, exc)
        tracker = None

    start = time.perf_counter()
    try:
        yield
    finally:
        duration_s = time.perf_counter() - start
        energy_kwh = None
        emissions_g = None

        if tracker is not None:
            try:
                emissions_kg = tracker.stop()  # kg CO2eq
                data = getattr(tracker, "final_emissions_data", None)
                if data is not None:
                    energy_kwh = getattr(data, "energy_consumed", None)
                    duration_s = getattr(data, "duration", duration_s) or duration_s
                if emissions_kg is not None:
                    emissions_g = float(emissions_kg) * 1000.0
            except Exception as exc:
                logging.warning("[energy] Echec arret tracker '%s' : %s", task, exc)

        energy_wh = energy_kwh * 1000.0 if energy_kwh is not None else None

        if energy_kwh is not None:
            logging.info(
                "[energy] %s | duree=%.1fs | energie=%.4f Wh | CO2=%.4f g%s",
                task, duration_s, energy_wh, emissions_g if emissions_g is not None else 0.0,
                f" | n={n_samples}" if n_samples is not None else "",
            )
        else:
            logging.info(
                "[energy] %s | duree=%.1fs | (energie non mesuree)", task, duration_s,
            )

        _append_summary(
            {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "task": task,
                "duration_s": round(duration_s, 2),
                "energy_kwh": round(energy_kwh, 8) if energy_kwh is not None else "",
                "energy_wh": round(energy_wh, 4) if energy_wh is not None else "",
                "emissions_gco2": round(emissions_g, 4) if emissions_g is not None else "",
                "n_samples": n_samples if n_samples is not None else "",
            },
            output_dir,
        )
