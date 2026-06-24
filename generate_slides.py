"""Génère les slides de soutenance pour le Projet Thumalien."""

from pptx import Presentation
from pptx.util import Inches, Pt, Emu
from pptx.dml.color import RGBColor
from pptx.enum.text import PP_ALIGN
from pptx.oxml.ns import qn
from pptx.util import Inches, Pt
import copy
from lxml import etree

# ---------------------------------------------------------------------------
# Palette
# ---------------------------------------------------------------------------
NAVY      = RGBColor(0x0D, 0x1B, 0x2A)
BLUE      = RGBColor(0x1B, 0x4F, 0x72)
ACCENT    = RGBColor(0xE8, 0x4A, 0x5F)   # rouge-corail
GOLD      = RGBColor(0xF5, 0xA6, 0x23)
WHITE     = RGBColor(0xFF, 0xFF, 0xFF)
LGRAY     = RGBColor(0xF0, 0xF4, 0xF8)
DGRAY     = RGBColor(0x55, 0x65, 0x73)
GREEN     = RGBColor(0x27, 0xAE, 0x60)
ORANGE    = RGBColor(0xE6, 0x7E, 0x22)

W, H = Inches(13.33), Inches(7.5)   # 16:9

prs = Presentation()
prs.slide_width  = W
prs.slide_height = H

BLANK = prs.slide_layouts[6]   # layout vide

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def add_rect(slide, x, y, w, h, fill_rgb, alpha=None):
    shape = slide.shapes.add_shape(1, x, y, w, h)
    shape.line.fill.background()
    shape.fill.solid()
    shape.fill.fore_color.rgb = fill_rgb
    return shape


def txb(slide, text, x, y, w, h,
        size=24, bold=False, color=WHITE, align=PP_ALIGN.LEFT,
        italic=False, wrap=True):
    box = slide.shapes.add_textbox(x, y, w, h)
    box.word_wrap = wrap
    tf = box.text_frame
    tf.word_wrap = wrap
    p = tf.paragraphs[0]
    p.alignment = align
    run = p.add_run()
    run.text = text
    run.font.size = Pt(size)
    run.font.bold = bold
    run.font.italic = italic
    run.font.color.rgb = color
    return box


def bullet_box(slide, items, x, y, w, h,
               size=20, color=WHITE, indent=False, spacing=1.15):
    box = slide.shapes.add_textbox(x, y, w, h)
    box.word_wrap = True
    tf = box.text_frame
    tf.word_wrap = True
    for i, item in enumerate(items):
        p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
        p.space_before = Pt(4)
        p.space_after  = Pt(2)
        run = p.add_run()
        run.text = item
        run.font.size = Pt(size)
        run.font.color.rgb = color
    return box


def divider(slide, y, color=ACCENT):
    add_rect(slide, Inches(0.6), y, Inches(12.1), Pt(3), color)


# ---------------------------------------------------------------------------
# Slide helpers
# ---------------------------------------------------------------------------

def dark_slide(title_text, subtitle_text="", tag_text=""):
    """Fond sombre — pour titres de section."""
    slide = prs.slides.add_slide(BLANK)
    add_rect(slide, 0, 0, W, H, NAVY)
    # bande gauche décorative
    add_rect(slide, 0, 0, Inches(0.45), H, ACCENT)
    # grand titre
    txb(slide, title_text,
        Inches(0.7), Inches(2.5), Inches(12), Inches(1.8),
        size=44, bold=True, color=WHITE)
    if subtitle_text:
        txb(slide, subtitle_text,
            Inches(0.7), Inches(4.2), Inches(11), Inches(1),
            size=22, color=GOLD)
    if tag_text:
        txb(slide, tag_text,
            Inches(0.7), Inches(6.5), Inches(8), Inches(0.6),
            size=14, color=DGRAY)
    return slide


def content_slide(title_text):
    """Fond clair — pour contenu."""
    slide = prs.slides.add_slide(BLANK)
    add_rect(slide, 0, 0, W, H, LGRAY)
    # header
    add_rect(slide, 0, 0, W, Inches(1.1), NAVY)
    add_rect(slide, 0, 0, Inches(0.35), H, BLUE)
    txb(slide, title_text,
        Inches(0.55), Inches(0.15), Inches(11.5), Inches(0.85),
        size=28, bold=True, color=WHITE)
    # numéro de slide (placeholder)
    return slide


def section_divider(number, title):
    slide = prs.slides.add_slide(BLANK)
    add_rect(slide, 0, 0, W, H, BLUE)
    add_rect(slide, 0, 0, Inches(0.45), H, ACCENT)
    txb(slide, f"0{number}", Inches(0.7), Inches(1.8), Inches(3), Inches(2),
        size=96, bold=True, color=RGBColor(0xFF,0xFF,0xFF) )
    # ligne
    add_rect(slide, Inches(0.7), Inches(4.0), Inches(5), Pt(3), GOLD)
    txb(slide, title, Inches(0.7), Inches(4.2), Inches(11.5), Inches(1.5),
        size=34, bold=True, color=WHITE)
    return slide


# ===========================================================================
# SLIDE 1 — Titre principal
# ===========================================================================
slide = prs.slides.add_slide(BLANK)
add_rect(slide, 0, 0, W, H, NAVY)
add_rect(slide, 0, 0, Inches(0.45), H, ACCENT)

# bloc blanc gauche / visuel
add_rect(slide, Inches(8.3), Inches(1.2), Inches(4.7), Inches(5.2), BLUE)
txb(slide, "🔍", Inches(9.6), Inches(2.2), Inches(2), Inches(2),
    size=80, color=WHITE, align=PP_ALIGN.CENTER)
txb(slide, "NLP & IA", Inches(8.5), Inches(4.1), Inches(4.2), Inches(0.8),
    size=22, bold=True, color=GOLD, align=PP_ALIGN.CENTER)

txb(slide, "PROJET THUMALIEN",
    Inches(0.7), Inches(1.2), Inches(7.5), Inches(0.8),
    size=16, bold=True, color=ACCENT)

txb(slide, "Détection de\nFake News\nsur Bluesky",
    Inches(0.7), Inches(1.9), Inches(7.4), Inches(2.8),
    size=46, bold=True, color=WHITE)

add_rect(slide, Inches(0.7), Inches(4.7), Inches(3), Pt(3), GOLD)

txb(slide, "Pipeline NLP · Analyse émotionnelle · Score de crédibilité · Dashboard IA",
    Inches(0.7), Inches(4.9), Inches(7.4), Inches(0.6),
    size=14, color=GOLD, italic=True)

txb(slide, "Master 1 Big Data & IA  ·  SUP DE VINCI  ·  Juin 2026",
    Inches(0.7), Inches(6.5), Inches(7), Inches(0.5),
    size=13, color=DGRAY)

# ===========================================================================
# SLIDE 2 — Sommaire
# ===========================================================================
slide = content_slide("Sommaire")
items = [
    ("01", "Contexte et problématique"),
    ("02", "Objectifs et architecture"),
    ("03", "Pipeline technique — 5 étapes"),
    ("04", "Résultats obtenus"),
    ("05", "Dashboard et démonstration"),
    ("06", "Perspectives d'amélioration"),
]
x_start = Inches(0.7)
y_start = Inches(1.35)
col_w   = Inches(5.9)
row_h   = Inches(0.85)

for i, (num, label) in enumerate(items):
    col = i % 2
    row = i // 2
    x = x_start + col * col_w
    y = y_start + row * (row_h + Inches(0.1))
    bg = NAVY if col == 0 else BLUE
    add_rect(slide, x, y, Inches(0.55), row_h, ACCENT)
    add_rect(slide, x + Inches(0.55), y, col_w - Inches(0.6), row_h, bg)
    txb(slide, num, x + Inches(0.05), y + Inches(0.2), Inches(0.45), Inches(0.5),
        size=18, bold=True, color=WHITE, align=PP_ALIGN.CENTER)
    txb(slide, label, x + Inches(0.65), y + Inches(0.22), col_w - Inches(0.75), Inches(0.5),
        size=17, bold=True, color=WHITE)

# ===========================================================================
# SLIDE 3 — Section : Contexte
# ===========================================================================
section_divider(1, "Contexte et problématique")

# ===========================================================================
# SLIDE 4 — Contexte
# ===========================================================================
slide = content_slide("Contexte — Un défi mondial")

facts = [
    ("500 M+", "messages publiés/jour sur les réseaux sociaux"),
    ("6×",     "les fake news se propagent 6× plus vite que les vraies informations"),
    ("70%",    "des internautes ont déjà partagé une information fausse sans le savoir"),
    ("Bluesky","réseau décentralisé en forte croissance, peu couvert par les outils existants"),
]
for i, (stat, desc) in enumerate(facts):
    y = Inches(1.35) + i * Inches(1.4)
    add_rect(slide, Inches(0.6), y, Inches(1.6), Inches(1.15), ACCENT)
    txb(slide, stat, Inches(0.62), y + Inches(0.2), Inches(1.55), Inches(0.75),
        size=26, bold=True, color=WHITE, align=PP_ALIGN.CENTER)
    add_rect(slide, Inches(2.25), y, Inches(10.5), Inches(1.15), NAVY)
    txb(slide, desc, Inches(2.4), y + Inches(0.28), Inches(10.2), Inches(0.7),
        size=17, color=WHITE)

# ===========================================================================
# SLIDE 5 — Problématique
# ===========================================================================
slide = content_slide("Problématique identifiée")

problems = [
    ("📊", "Volume impossible à modérer manuellement",
           "Des milliers de posts par heure, impossible pour une équipe humaine."),
    ("⚡", "Propagation plus rapide que les démentis",
           "Une fake news virale avant même d'être vérifiée."),
    ("🌍", "Outils limités à l'anglais",
           "Peu de solutions couvrent le français sur les nouveaux réseaux."),
    ("💭", "Impact émotionnel ignoré",
           "La colère et la peur amplifient la viralité — aucun outil ne le mesure."),
]

for i, (icon, title, desc) in enumerate(problems):
    col = i % 2
    row = i // 2
    x = Inches(0.6) + col * Inches(6.35)
    y = Inches(1.35) + row * Inches(2.65)
    add_rect(slide, x, y, Inches(6.1), Inches(2.45), WHITE)
    add_rect(slide, x, y, Inches(0.55), Inches(2.45), ACCENT)
    txb(slide, icon, x + Inches(0.65), y + Inches(0.15), Inches(1), Inches(0.8),
        size=28, color=NAVY)
    txb(slide, title, x + Inches(0.65), y + Inches(0.15), Inches(5.3), Inches(0.7),
        size=16, bold=True, color=NAVY)
    txb(slide, desc, x + Inches(0.65), y + Inches(0.85), Inches(5.3), Inches(1.3),
        size=14, color=DGRAY)

# ===========================================================================
# SLIDE 6 — Section : Objectifs
# ===========================================================================
section_divider(2, "Objectifs et architecture")

# ===========================================================================
# SLIDE 7 — Objectifs
# ===========================================================================
slide = content_slide("Objectifs du projet Thumalien")

objectives = [
    ("🔗", "Collecter", "Posts Bluesky FR/EN via API officielle"),
    ("🤖", "Classifier", "Fake vs. real par apprentissage automatique"),
    ("💬", "Analyser", "Impact émotionnel (colère, peur, joie...)"),
    ("📊", "Scorer", "Score de crédibilité explicable 0→1"),
    ("🖥️", "Visualiser", "Dashboard interactif + agent IA conversationnel"),
    ("🌱", "Mesurer", "Empreinte carbone du pipeline (Green IT)"),
]

for i, (icon, title, desc) in enumerate(objectives):
    col = i % 3
    row = i // 3
    x = Inches(0.6) + col * Inches(4.2)
    y = Inches(1.35) + row * Inches(2.7)
    add_rect(slide, x, y, Inches(4.0), Inches(2.5), NAVY)
    add_rect(slide, x, y, Inches(4.0), Inches(0.65), BLUE)
    txb(slide, icon + "  " + title,
        x + Inches(0.15), y + Inches(0.1), Inches(3.7), Inches(0.5),
        size=17, bold=True, color=WHITE)
    txb(slide, desc,
        x + Inches(0.15), y + Inches(0.85), Inches(3.7), Inches(1.4),
        size=15, color=LGRAY)

# ===========================================================================
# SLIDE 8 — Architecture (pipeline)
# ===========================================================================
slide = content_slide("Architecture — Pipeline en 5 étapes")

steps = [
    ("Bluesky\nAPI", ACCENT),
    ("NLP\nCleaning", BLUE),
    ("ML\nScoring", RGBColor(0x6C, 0x3A, 0x83)),
    ("Emotion\nAnalysis", ORANGE),
    ("Final\nScore", GREEN),
]

arrow_y = Inches(3.3)
box_w   = Inches(2.0)
box_h   = Inches(1.5)
gap     = Inches(0.45)
start_x = Inches(0.5)

for i, (label, color) in enumerate(steps):
    x = start_x + i * (box_w + gap)
    add_rect(slide, x, arrow_y, box_w, box_h, color)
    txb(slide, label, x, arrow_y + Inches(0.25), box_w, box_h - Inches(0.3),
        size=16, bold=True, color=WHITE, align=PP_ALIGN.CENTER)
    if i < len(steps) - 1:
        txb(slide, "→", x + box_w + Inches(0.05), arrow_y + Inches(0.45),
            gap, Inches(0.6), size=22, bold=True, color=NAVY, align=PP_ALIGN.CENTER)

# Stockages
stores = ["MongoDB\nraw", "MongoDB\nclean", "models/\n.joblib", "posts_clean\n(emotions)", "posts_clean\n(final_score)"]
for i, label in enumerate(stores):
    x = start_x + i * (box_w + gap)
    add_rect(slide, x + Inches(0.4), arrow_y + box_h + Inches(0.15),
             Inches(1.2), Inches(0.9), LGRAY)
    txb(slide, label,
        x + Inches(0.4), arrow_y + box_h + Inches(0.2),
        Inches(1.2), Inches(0.8), size=11, color=NAVY, align=PP_ALIGN.CENTER)

# Dashboard
db_x = Inches(10.7)
add_rect(slide, db_x, Inches(1.5), Inches(2.2), Inches(4.5), NAVY)
txb(slide, "🖥️\nDashboard\nStreamlit\n+\nAgent IA\n(Groq)",
    db_x + Inches(0.1), Inches(1.7), Inches(2.0), Inches(4.0),
    size=16, bold=True, color=WHITE, align=PP_ALIGN.CENTER)

txb(slide, "→", Inches(10.3), Inches(3.2), Inches(0.45), Inches(0.5),
    size=22, bold=True, color=NAVY, align=PP_ALIGN.CENTER)

# MongoDB
add_rect(slide, Inches(0.4), Inches(1.3), Inches(2.3), Inches(0.9), RGBColor(0x4A,0x90,0xD9))
txb(slide, "🗄️  MongoDB 7 (Docker)",
    Inches(0.5), Inches(1.45), Inches(2.2), Inches(0.6),
    size=12, bold=True, color=WHITE)

# ===========================================================================
# SLIDE 9 — Section : Pipeline
# ===========================================================================
section_divider(3, "Pipeline technique — 5 étapes")

# ===========================================================================
# SLIDE 10 — Étape 1 : Collecte
# ===========================================================================
slide = content_slide("Étape 1 — Collecte Bluesky")

add_rect(slide, Inches(0.6), Inches(1.3), Inches(5.8), Inches(5.6), NAVY)
txb(slide, "API Bluesky", Inches(0.75), Inches(1.45), Inches(3.5), Inches(0.6),
    size=20, bold=True, color=ACCENT)
items_left = [
    "• API officielle app.bsky.feed.searchPosts",
    "• Authentification par App Password",
    "• Pagination automatique des résultats",
    "• Retry HTTP avec backoff exponentiel",
    "• Déduplication par URI unique",
    "• Mots-clés FR/EN :",
    "  fake news · désinformation · complot",
    "  hoax · manipulation · intox",
]
bullet_box(slide, items_left, Inches(0.75), Inches(2.1), Inches(5.5), Inches(4.5),
           size=15, color=LGRAY)

# Stats
stats = [("4 729", "posts collectés"), ("4 667", "posts uniques"), ("2", "langues (FR/EN)")]
for i, (val, lbl) in enumerate(stats):
    x = Inches(7.0) + i * Inches(2.05)
    add_rect(slide, x, Inches(1.3), Inches(1.9), Inches(1.6), ACCENT)
    txb(slide, val, x, Inches(1.4), Inches(1.9), Inches(0.9),
        size=30, bold=True, color=WHITE, align=PP_ALIGN.CENTER)
    txb(slide, lbl, x, Inches(2.2), Inches(1.9), Inches(0.5),
        size=12, color=WHITE, align=PP_ALIGN.CENTER)

add_rect(slide, Inches(7.0), Inches(3.1), Inches(6.0), Inches(3.8), WHITE)
txb(slide, "Structure MongoDB posts_raw :",
    Inches(7.15), Inches(3.2), Inches(5.7), Inches(0.5),
    size=14, bold=True, color=NAVY)
code = ('{\n'
        '  "uri": "at://did.../post/xyz",\n'
        '  "text": "Contenu brut du post...",\n'
        '  "author": "handle.bsky.social",\n'
        '  "createdAt": "2025-12-01T...",\n'
        '  "lang": ["fr"],\n'
        '  "collected_at": "2025-12-01T..."\n'
        '}')
txb(slide, code, Inches(7.15), Inches(3.75), Inches(5.8), Inches(2.9),
    size=12, color=DGRAY)

# ===========================================================================
# SLIDE 11 — Étape 2 : NLP Cleaning
# ===========================================================================
slide = content_slide("Étape 2 — Prétraitement NLP")

before_after = [
    ("Texte brut", "🔴 Avant",
     '"CHOC !! Les @journalistes mentent encore 😱\nhttps://t.co/fake #DesinfoAlerte\nC\'est PROUVÉ par des EXPERTS 🤡"'),
    ("Texte nettoyé", "🟢 Après",
     '"choc les journalistes mentent encore\nc\'est prouvé par des experts"'),
]
for i, (title, badge, text) in enumerate(before_after):
    y = Inches(1.35) + i * Inches(2.3)
    col = NAVY if i == 0 else BLUE
    add_rect(slide, Inches(0.6), y, Inches(7.5), Inches(2.1), col)
    txb(slide, badge, Inches(0.75), y + Inches(0.1), Inches(2), Inches(0.5),
        size=14, bold=True, color=WHITE)
    txb(slide, text, Inches(0.75), y + Inches(0.55), Inches(7.2), Inches(1.4),
        size=14, italic=(i==0), color=LGRAY)

steps_nlp = [
    "🔗 Suppression des URLs",
    "👤 Suppression des mentions @",
    "# Suppression des hashtags",
    "🔡 Conversion minuscules",
    "😀 Retrait des emojis",
    "🌍 Détection de langue auto",
    "✅ Tokenisation et comptage",
]
add_rect(slide, Inches(8.5), Inches(1.35), Inches(4.5), Inches(5.5), WHITE)
txb(slide, "Étapes de nettoyage :", Inches(8.65), Inches(1.5), Inches(4.2), Inches(0.5),
    size=16, bold=True, color=NAVY)
bullet_box(slide, steps_nlp, Inches(8.65), Inches(2.1), Inches(4.2), Inches(4.5),
           size=15, color=DGRAY)

add_rect(slide, Inches(0.6), Inches(6.0), Inches(7.5), Inches(0.85), GREEN)
txb(slide, "✅  4 618 posts nettoyés → prêts pour l'analyse ML",
    Inches(0.75), Inches(6.1), Inches(7.2), Inches(0.65),
    size=16, bold=True, color=WHITE)

# ===========================================================================
# SLIDE 12 — Étape 3 : Classification Fake News
# ===========================================================================
slide = content_slide("Étape 3 — Classification Fake News (ML Baseline)")

# Gauche : pipeline
add_rect(slide, Inches(0.6), Inches(1.35), Inches(5.8), Inches(5.5), NAVY)
txb(slide, "Pipeline scikit-learn", Inches(0.75), Inches(1.5), Inches(5.5), Inches(0.5),
    size=18, bold=True, color=ACCENT)

pipeline_steps = [
    ("Dataset", "GonzaloA/fake_news (HuggingFace)\n40 000 articles labellisés fake/real"),
    ("TF-IDF", "Unigrams + bigrams · 50 000 features\nsublinear_tf=True · min_df=2"),
    ("LogReg", "Logistic Regression · C=1.0\nclass_weight='balanced' · max_iter=1000"),
    ("Split", "80% entraînement / 20% test · stratifié"),
]
for i, (tag, desc) in enumerate(pipeline_steps):
    y = Inches(2.1) + i * Inches(1.1)
    add_rect(slide, Inches(0.75), y, Inches(1.0), Inches(0.85), ACCENT)
    txb(slide, tag, Inches(0.75), y + Inches(0.15), Inches(1.0), Inches(0.6),
        size=13, bold=True, color=WHITE, align=PP_ALIGN.CENTER)
    txb(slide, desc, Inches(1.85), y + Inches(0.08), Inches(4.4), Inches(0.8),
        size=13, color=LGRAY)

# Droite : métriques
metrics = [
    ("97.7%", "F1-score\n(weighted)", ACCENT),
    ("98.1%", "Précision", BLUE),
    ("97.4%", "Rappel", GREEN),
]
for i, (val, lbl, col) in enumerate(metrics):
    x = Inches(6.8) + i * Inches(2.1)
    add_rect(slide, x, Inches(1.35), Inches(1.95), Inches(2.3), col)
    txb(slide, val, x, Inches(1.55), Inches(1.95), Inches(1.1),
        size=34, bold=True, color=WHITE, align=PP_ALIGN.CENTER)
    txb(slide, lbl, x, Inches(2.65), Inches(1.95), Inches(0.8),
        size=13, color=WHITE, align=PP_ALIGN.CENTER)

# Répartition alertes
alert_data = [("1 109", "Alertes HAUTES", ACCENT, "24%"),
              ("3 194", "Alertes MOYENNES", ORANGE, "69%"),
              ("315",   "Alertes BASSES", GREEN, "7%")]
for i, (n, lbl, col, pct) in enumerate(alert_data):
    x = Inches(6.8) + i * Inches(2.1)
    add_rect(slide, x, Inches(3.9), Inches(1.95), Inches(2.5), LGRAY)
    add_rect(slide, x, Inches(3.9), Inches(1.95), Inches(0.45), col)
    txb(slide, lbl, x + Inches(0.05), Inches(3.95), Inches(1.85), Inches(0.4),
        size=11, bold=True, color=WHITE, align=PP_ALIGN.CENTER)
    txb(slide, n, x + Inches(0.05), Inches(4.45), Inches(1.85), Inches(0.9),
        size=28, bold=True, color=NAVY, align=PP_ALIGN.CENTER)
    txb(slide, pct, x + Inches(0.05), Inches(5.35), Inches(1.85), Inches(0.6),
        size=20, bold=True, color=col, align=PP_ALIGN.CENTER)
    txb(slide, "des posts", x + Inches(0.05), Inches(5.9), Inches(1.85), Inches(0.4),
        size=11, color=DGRAY, align=PP_ALIGN.CENTER)

# ===========================================================================
# SLIDE 13 — Étape 4 : Analyse Émotionnelle
# ===========================================================================
slide = content_slide("Étape 4 — Analyse Émotionnelle")

# Méthode
add_rect(slide, Inches(0.6), Inches(1.35), Inches(6.2), Inches(2.2), NAVY)
txb(slide, "Méthode hybride", Inches(0.75), Inches(1.45), Inches(6.0), Inches(0.5),
    size=16, bold=True, color=ACCENT)
bullet_box(slide,
           ["🔢  VADER Sentiment Analysis → score compound (-1 à +1)",
            "📖  Lexiques bilingues custom FR/EN → 6 émotions",
            "🌍  Bilingue : gestion des posts en français ET anglais"],
           Inches(0.75), Inches(2.0), Inches(5.9), Inches(1.4), size=14, color=LGRAY)

# Émotions
emotions = [("😡 Colère", ACCENT), ("😨 Peur", RGBColor(0x8E,0x44,0xAD)),
            ("😢 Tristesse", BLUE), ("😊 Joie", GREEN),
            ("😲 Surprise", GOLD), ("😄 Humour", ORANGE)]
for i, (em, col) in enumerate(emotions):
    col_i = i % 3
    row_i = i // 3
    x = Inches(0.6) + col_i * Inches(2.05)
    y = Inches(3.7) + row_i * Inches(0.9)
    add_rect(slide, x, y, Inches(1.9), Inches(0.75), col)
    txb(slide, em, x + Inches(0.08), y + Inches(0.15), Inches(1.75), Inches(0.5),
        size=14, bold=True, color=WHITE)

# Résultats sentiment
add_rect(slide, Inches(6.9), Inches(1.35), Inches(6.1), Inches(5.5), WHITE)
txb(slide, "Résultats sur 4 618 posts",
    Inches(7.05), Inches(1.5), Inches(5.8), Inches(0.5),
    size=16, bold=True, color=NAVY)

sentiment_data = [
    ("Négatif", 1946, 4618, ACCENT),
    ("Positif", 1439, 4618, GREEN),
    ("Neutre",  1233, 4618, BLUE),
]
for i, (label, n, total, col) in enumerate(sentiment_data):
    y = Inches(2.2) + i * Inches(1.3)
    pct = n / total
    bar_w = Inches(4.5) * pct
    txb(slide, label, Inches(7.05), y, Inches(1.4), Inches(0.4),
        size=14, bold=True, color=NAVY)
    add_rect(slide, Inches(7.05), y + Inches(0.45), Inches(4.5), Inches(0.45), LGRAY)
    if bar_w > 0:
        add_rect(slide, Inches(7.05), y + Inches(0.45), bar_w, Inches(0.45), col)
    txb(slide, f"{n} ({pct*100:.0f}%)", Inches(11.65), y + Inches(0.45),
        Inches(1.2), Inches(0.45), size=13, bold=True, color=col)

txb(slide, "Émotion dominante la plus fréquente : 😡 Colère",
    Inches(7.05), Inches(6.1), Inches(5.8), Inches(0.5),
    size=14, italic=True, color=ACCENT)

# ===========================================================================
# SLIDE 14 — Étape 5 : Score Final
# ===========================================================================
slide = content_slide("Étape 5 — Score de Crédibilité Final")

# Formule
add_rect(slide, Inches(0.6), Inches(1.35), Inches(12.5), Inches(1.5), NAVY)
txb(slide, "Score Final  =  70% × Risque Fake  +  20% × Risque Sentiment  +  10% × Risque Émotionnel",
    Inches(0.75), Inches(1.55), Inches(12.2), Inches(1.1),
    size=20, bold=True, color=WHITE, align=PP_ALIGN.CENTER)

# 3 composantes
components = [
    ("70%", "Risque Fake News", "1 - credibility_score\nIssu du modèle TF-IDF + LogReg", ACCENT),
    ("20%", "Risque Sentiment", "Sentiment VADER négatif\n→ amplifie le risque", ORANGE),
    ("10%", "Risque Émotionnel", "Colère/Peur → +risque\nJoie → -risque", BLUE),
]
for i, (pct, title, desc, col) in enumerate(components):
    x = Inches(0.6) + i * Inches(4.2)
    add_rect(slide, x, Inches(3.0), Inches(4.0), Inches(3.0), col)
    txb(slide, pct, x + Inches(0.1), Inches(3.05), Inches(3.8), Inches(1.1),
        size=52, bold=True, color=WHITE, align=PP_ALIGN.CENTER)
    txb(slide, title, x + Inches(0.1), Inches(4.1), Inches(3.8), Inches(0.5),
        size=16, bold=True, color=WHITE, align=PP_ALIGN.CENTER)
    txb(slide, desc, x + Inches(0.1), Inches(4.65), Inches(3.8), Inches(1.2),
        size=13, color=LGRAY, align=PP_ALIGN.CENTER)

# Niveaux d'alerte
levels = [("< 0.35 → 🔴 ALERTE HAUTE", ACCENT),
          ("0.35–0.60 → 🟠 ALERTE MOYENNE", ORANGE),
          ("> 0.60 → 🟢 ALERTE BASSE", GREEN)]
add_rect(slide, Inches(0.6), Inches(6.15), Inches(12.5), Inches(1.1), LGRAY)
for i, (label, col) in enumerate(levels):
    x = Inches(0.8) + i * Inches(4.2)
    txb(slide, label, x, Inches(6.35), Inches(4.0), Inches(0.6),
        size=15, bold=True, color=col)

# ===========================================================================
# SLIDE 15 — Section : Résultats
# ===========================================================================
section_divider(4, "Résultats obtenus")

# ===========================================================================
# SLIDE 16 — Résultats globaux
# ===========================================================================
slide = content_slide("Résultats globaux du pipeline")

kpis = [
    ("4 618", "posts\nanalysés", ACCENT),
    ("97.7%", "F1-score\nbaseline", GREEN),
    ("0.44", "score moyen\nde crédibilité", ORANGE),
    ("24%", "posts en\nalerte haute", RGBColor(0x8E,0x44,0xAD)),
    ("< 5 min", "pipeline\ncomplete", BLUE),
    ("3", "langues\n(FR/EN/mixte)", NAVY),
]
for i, (val, lbl, col) in enumerate(kpis):
    col_i = i % 3
    row_i = i // 3
    x = Inches(0.6) + col_i * Inches(4.2)
    y = Inches(1.35) + row_i * Inches(2.7)
    add_rect(slide, x, y, Inches(4.0), Inches(2.5), col)
    txb(slide, val, x + Inches(0.1), y + Inches(0.2), Inches(3.8), Inches(1.2),
        size=40, bold=True, color=WHITE, align=PP_ALIGN.CENTER)
    txb(slide, lbl, x + Inches(0.1), y + Inches(1.45), Inches(3.8), Inches(0.9),
        size=15, color=LGRAY, align=PP_ALIGN.CENTER)

# ===========================================================================
# SLIDE 17 — Section : Dashboard
# ===========================================================================
section_divider(5, "Dashboard et démonstration")

# ===========================================================================
# SLIDE 18 — Dashboard Streamlit
# ===========================================================================
slide = content_slide("Dashboard Streamlit — Vue d'ensemble")

features = [
    ("📊 Vue Synthèse", ["KPIs : total posts, alertes H/M/B", "Graphique distribution des alertes", "Répartition des émotions (pie chart)", "Timeline des publications"]),
    ("🔍 Filtres avancés", ["Langue (FR / EN)", "Niveau d'alerte (high / medium / low)", "Émotion dominante", "Plage de dates + recherche texte"]),
    ("📄 Détail par post", ["Texte brut et texte nettoyé", "Breakdown 70/20/10 du score", "Justification textuelle lisible", "Niveau d'alerte coloré"]),
    ("🤖 Agent IA (Groq)", ["Chat en français sur les données", "Llama 3.1 8B Instant (gratuit)", "Contexte : résumé MongoDB live", 'Ex: "Quelle émotion domine ?"']),
]

for i, (title, items) in enumerate(features):
    col = i % 2
    row = i // 2
    x = Inches(0.6) + col * Inches(6.35)
    y = Inches(1.35) + row * Inches(2.8)
    add_rect(slide, x, y, Inches(6.1), Inches(2.6), WHITE)
    add_rect(slide, x, y, Inches(6.1), Inches(0.6), NAVY)
    txb(slide, title, x + Inches(0.15), y + Inches(0.1), Inches(5.8), Inches(0.45),
        size=16, bold=True, color=WHITE)
    bullet_box(slide, ["• " + it for it in items],
               x + Inches(0.15), y + Inches(0.7), Inches(5.8), Inches(1.8),
               size=13, color=DGRAY)

# ===========================================================================
# SLIDE 19 — Monitoring Green IT
# ===========================================================================
slide = content_slide("Monitoring énergétique — Green IT (CodeCarbon)")

add_rect(slide, Inches(0.6), Inches(1.35), Inches(5.8), Inches(5.5), NAVY)
txb(slide, "🌱  Objectif Green IT", Inches(0.75), Inches(1.45), Inches(5.5), Inches(0.55),
    size=18, bold=True, color=GREEN)
items_left = [
    "• Mesure de l'empreinte carbone",
    "  du pipeline ML de bout en bout",
    "",
    "• CodeCarbon intégré sur :",
    "  → Entraînement TF-IDF + LogReg",
    "  → Analyse émotionnelle (batch)",
    "",
    "• Sortie : models/emissions.csv",
    "  (kgCO2eq par run)",
    "",
    "• Permet de comparer",
    "  différentes configurations",
]
bullet_box(slide, items_left, Inches(0.75), Inches(2.1), Inches(5.5), Inches(4.5),
           size=14, color=LGRAY)

# Droite : KPIs écolo
add_rect(slide, Inches(6.9), Inches(1.35), Inches(6.0), Inches(5.5), WHITE)
txb(slide, "Données mesurées par run :", Inches(7.05), Inches(1.5), Inches(5.7), Inches(0.5),
    size=16, bold=True, color=NAVY)

eco_items = [
    ("⚡", "Énergie consommée (kWh)"),
    ("🌡️", "CO2 équivalent (kgCO2eq)"),
    ("🖥️", "CPU/GPU utilisés"),
    ("⏱️", "Durée d'exécution"),
    ("🌍", "Pays / mix énergétique"),
]
for i, (icon, desc) in enumerate(eco_items):
    y = Inches(2.15) + i * Inches(0.9)
    add_rect(slide, Inches(7.05), y, Inches(0.65), Inches(0.7), GREEN)
    txb(slide, icon, Inches(7.05), y + Inches(0.1), Inches(0.65), Inches(0.5),
        size=18, align=PP_ALIGN.CENTER, color=WHITE)
    txb(slide, desc, Inches(7.8), y + Inches(0.15), Inches(4.9), Inches(0.5),
        size=15, color=NAVY)

txb(slide, "Recommandation : batch processing nocturne\n→ réduction jusqu'à 40% CO2 (mix énergétique off-peak)",
    Inches(7.05), Inches(6.1), Inches(5.8), Inches(0.75),
    size=13, italic=True, color=GREEN)

# ===========================================================================
# SLIDE 20 — Section : Perspectives
# ===========================================================================
section_divider(6, "Perspectives d'amélioration")

# ===========================================================================
# SLIDE 21 — Perspectives
# ===========================================================================
slide = content_slide("Perspectives d'amélioration")

perspectives = [
    ("🧠 Modèle avancé",
     "Remplacer TF-IDF + LogReg par CamemBERT\n(BERT francophone) pour améliorer la précision\nsur les posts en français."),
    ("🌐 Multi-sources",
     "Étendre la collecte à d'autres plateformes\n(Reddit, Mastodon) pour élargir\nla couverture."),
    ("🔍 Explicabilité avancée",
     "Intégrer SHAP pour identifier les mots\nqui influencent la prédiction fake news\n(features TF-IDF dominantes)."),
    ("⚡ Temps réel",
     "Pipeline en streaming avec Kafka\npour analyser les posts au fil\nde leur publication."),
    ("☁️ Déploiement cloud",
     "Docker Compose complet + Streamlit Cloud\npour un accès partagé sans installation\nlocale."),
    ("✅ Tests automatisés",
     "Tests unitaires sur chaque module\n+ CI/CD GitHub Actions pour garantir\nla non-régression."),
]

for i, (title, desc) in enumerate(perspectives):
    col = i % 3
    row = i // 3
    x = Inches(0.6) + col * Inches(4.2)
    y = Inches(1.35) + row * Inches(2.7)
    add_rect(slide, x, y, Inches(4.0), Inches(2.5), WHITE)
    add_rect(slide, x, y, Inches(4.0), Inches(0.6), NAVY)
    txb(slide, title, x + Inches(0.12), y + Inches(0.1), Inches(3.76), Inches(0.45),
        size=14, bold=True, color=WHITE)
    txb(slide, desc, x + Inches(0.12), y + Inches(0.7), Inches(3.76), Inches(1.7),
        size=12, color=DGRAY)

# ===========================================================================
# SLIDE 22 — Conclusion
# ===========================================================================
slide = prs.slides.add_slide(BLANK)
add_rect(slide, 0, 0, W, H, NAVY)
add_rect(slide, 0, 0, Inches(0.45), H, ACCENT)
add_rect(slide, Inches(8.5), 0, Inches(4.83), H, BLUE)

txb(slide, "Conclusion",
    Inches(0.7), Inches(1.0), Inches(7.5), Inches(0.7),
    size=36, bold=True, color=WHITE)
add_rect(slide, Inches(0.7), Inches(1.8), Inches(4), Pt(3), GOLD)

summary = [
    "✅  Pipeline NLP complet de bout en bout",
    "✅  4 618 posts analysés — F1-score 97.7%",
    "✅  Score explicable (70/20/10) + texte justificatif",
    "✅  Dashboard Streamlit + Agent IA conversationnel",
    "✅  Monitoring Green IT (CodeCarbon)",
    "✅  Bilingue FR/EN — open-source et reproductible",
]
bullet_box(slide, summary, Inches(0.7), Inches(2.0), Inches(7.5), Inches(4.5),
           size=17, color=WHITE)

txb(slide, "Merci pour votre attention",
    Inches(8.7), Inches(2.0), Inches(4.4), Inches(0.7),
    size=22, bold=True, color=WHITE, align=PP_ALIGN.CENTER)

add_rect(slide, Inches(8.7), Inches(2.8), Inches(4.2), Pt(2), GOLD)

txb(slide, "🙋 Questions ?",
    Inches(8.7), Inches(3.0), Inches(4.4), Inches(1.0),
    size=32, bold=True, color=GOLD, align=PP_ALIGN.CENTER)

txb(slide, "Démonstration disponible\n↓\npython run_all.py --dashboard",
    Inches(8.7), Inches(4.2), Inches(4.4), Inches(1.5),
    size=14, color=LGRAY, align=PP_ALIGN.CENTER)

txb(slide, "Master 1 Big Data & IA  ·  SUP DE VINCI  ·  Juin 2026",
    Inches(0.7), Inches(6.7), Inches(7.5), Inches(0.45),
    size=12, color=DGRAY)

# ===========================================================================
# Sauvegarde
# ===========================================================================
output = r"C:\Users\utilisateur\Documents\M1-BigDATA&IA\00-Projet\Projet_Etude_M1_SDV\Soutenance_Projet_Thumalien.pptx"
prs.save(output)
print("Fichier cree : " + output)
print("Nombre de slides : " + str(len(prs.slides)))
