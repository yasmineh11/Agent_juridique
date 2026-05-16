# src/tools.py
# ═══════════════════════════════════════════════════════════════════
# Agent IA Juridique Tunisien — Guide Juridique Tunisien
# Fichier : tools.py
# Rôle    : Définition des 4 outils utilisés par l'agent ReAct
# ═══════════════════════════════════════════════════════════════════

import chromadb
from langchain_core.tools import tool
from chromadb.utils.embedding_functions import SentenceTransformerEmbeddingFunction
from dotenv import load_dotenv
from scraper import fetch_9anoun_code, fetch_9anoun_jort

load_dotenv()

from config import CHROMA_DB_PATH, COLLECTION_NAME, EMBEDDING_MODEL

# ── Initialisation globale (une seule fois au démarrage) ──────────
# FIX: use SentenceTransformerEmbeddingFunction (same as ingest.py) so that
# query vectors use the exact same normalisation as the stored vectors.
# The previous code used a bare SentenceTransformer + manual .encode(),
# which produced different vector scales → wrong similarity scores.
embedding_fn = SentenceTransformerEmbeddingFunction(model_name=EMBEDDING_MODEL)

chroma_client = chromadb.PersistentClient(path=CHROMA_DB_PATH)
# FIX: pass embedding_function when opening the collection so ChromaDB uses
# our model at query time instead of its own default embedder.
collection = chroma_client.get_or_create_collection(
    COLLECTION_NAME,
    embedding_function=embedding_fn
)

# ── Translation pipeline cache (loaded once, not on every call) ───
_translation_pipelines: dict = {}


def _get_translation_pipeline(model_name: str):
    """Lazy-load and cache HuggingFace translation pipelines."""
    if model_name not in _translation_pipelines:
        from transformers import pipeline as hf_pipeline
        _translation_pipelines[model_name] = hf_pipeline("translation", model=model_name)
    return _translation_pipelines[model_name]


# ═══════════════════════════════════════════════════════════════════
# OUTIL 1 — Recherche locale dans ChromaDB
# ═══════════════════════════════════════════════════════════════════
@tool
def search_legal_docs(query: str) -> str:
    """
    Recherche sémantique dans les lois tunisiennes stockées localement
    dans ChromaDB : Code du Travail, Code Pénal, Code de procédure
    civile, Code des obligations et contrats, Constitution 2022.

    Retourne les articles les plus pertinents avec :
      - La source exacte (nom du fichier PDF)
      - Le score de confiance (0 à 100%)
      - Le texte de l'article

    RÈGLE IMPORTANTE :
      - Toujours appeler CET outil EN PREMIER avant tout autre outil.
      - Si le score retourné est < 40% → retourne le signal
        CONFIANCE_FAIBLE qui déclenchera web_search_jort.
    """
    try:
        # FIX: use query_texts instead of manually encoding with a separate
        # SentenceTransformer instance. The collection's own embedding_function
        # (set at init above) handles vectorisation, guaranteeing consistency
        # with the vectors stored during ingest.py.
        results = collection.query(
            query_texts=[query],
            n_results=4,
            include=["documents", "metadatas", "distances"]
        )

        if not results["documents"] or not results["documents"][0]:
            return (
                "CONFIANCE_FAIBLE (0%) — "
                "La base locale est vide. Lance ingest.py d'abord. "
                "Utiliser web_search_jort."
            )

        best_distance = results["distances"][0][0]
        # FIX: cosine distance from sentence-transformers is in [0, 1] for
        # normalised vectors. Correct formula is (1 - distance), not
        # (1 - distance/2) which capped the maximum confidence at 50%.
        confidence = round((1 - best_distance) * 100)

        if confidence < 40:
            return (
                f"CONFIANCE_FAIBLE ({confidence}%) — "
                f"Résultats insuffisants dans la base locale. "
                f"Utiliser web_search_jort pour chercher en ligne."
            )

        output = []
        for doc, meta, dist in zip(
            results["documents"][0],
            results["metadatas"][0],
            results["distances"][0]
        ):
            score = round((1 - dist) * 100)  # FIX: same corrected formula
            source = meta.get("source", "Source inconnue")
            article = meta.get("article", "")
            ref = f"{source}" + (f" — {article}" if article else "")
            output.append(f"[{ref} | Confiance : {score}%]\n{doc}")

        return "\n\n---\n\n".join(output)

    except Exception as e:
        return f"ERREUR search_legal_docs : {str(e)}"


# ═══════════════════════════════════════════════════════════════════
# OUTIL 2 — Recherche web : JORT + 9anoun.tn
# ═══════════════════════════════════════════════════════════════════
@tool
def web_search_jort(keywords: str) -> str:
    """
    Recherche les lois et décrets tunisiens récents sur 9anoun.tn,
    qui héberge à la fois les codes juridiques ET toutes les éditions
    du Journal Officiel de la République Tunisienne (JORT).

    Sources utilisées (toutes via 9anoun.tn, HTML statique, sans JS) :
      1. https://9anoun.tn/kb/codes/{slug}  — code juridique correspondant
         aux mots-clés (code du travail, code pénal, COC, etc.)
      2. https://9anoun.tn/kb/jorts         — dernières éditions du JORT

    Note : iort.gov.tn utilise une application WinDev avec navigation
    en javascript:{} et tokens de session — impossible à interroger
    automatiquement. 9anoun.tn est le miroir officiel utilisé à la place.

    RÈGLE D'UTILISATION :
      - Appeler UNIQUEMENT si search_legal_docs retourne CONFIANCE_FAIBLE
      - Ou si la question porte sur une loi très récente
      - Ne JAMAIS appeler avant search_legal_docs
    """
    results = []

    # ── SOURCE 1 : Code juridique sur 9anoun.tn ───────────────────
    code_content, code_url = fetch_9anoun_code(keywords)
    if code_content:
        results.append(
            f"[Source : 9anoun.tn — Codes | {code_url}]\n{code_content}"
        )
    else:
        results.append("[9anoun.tn codes : aucun contenu trouvé]")

    # ── SOURCE 2 : JORT sur 9anoun.tn ────────────────────────────
    jort_content, jort_url = fetch_9anoun_jort(keywords)
    if jort_content:
        results.append(
            f"[Source : 9anoun.tn — JORT | {jort_url}]\n{jort_content}"
        )
    else:
        results.append("[9anoun.tn JORT : aucun contenu trouvé]")

    separator = "\n\n" + "═" * 50 + "\n\n"
    return separator.join(results)


# ═══════════════════════════════════════════════════════════════════
# OUTIL 3 — Traduction arabe ↔ français
# ═══════════════════════════════════════════════════════════════════
@tool
def translate_legal_text(input_text: str) -> str:
    """
    Traduit un texte juridique tunisien entre l'arabe et le français.

    Format d'entrée OBLIGATOIRE : "direction|texte"
      - "fr|النص العربي"    → traduit de l'arabe vers le français
      - "ar|texte français" → traduit du français vers l'arabe

    Exemples :
      - "fr|الفصل 14 من مجلة الشغل"
      - "ar|Article 14 du Code du Travail"

    Utiliser cet outil quand :
      - L'utilisateur écrit sa question en arabe
      - Un article trouvé est en arabe et l'utilisateur veut le français
      - L'utilisateur demande explicitement une traduction
    """
    try:
        if "|" not in input_text:
            return (
                "Format invalide. Utiliser : 'fr|texte arabe' ou 'ar|texte français'.\n"
                "Exemple : 'fr|الفصل 14 من مجلة الشغل'"
            )

        target_lang, text = input_text.split("|", 1)
        target_lang = target_lang.strip().lower()
        text = text.strip()

        if target_lang == "fr":
            model_name = "Helsinki-NLP/opus-mt-ar-fr"
            direction = "Arabe → Français"
        elif target_lang == "ar":
            model_name = "Helsinki-NLP/opus-mt-fr-ar"
            direction = "Français → Arabe"
        else:
            return f"Direction invalide : '{target_lang}'. Utiliser 'fr' ou 'ar'."

        # FIX: use cached pipeline — no more per-call model download.
        pipe = _get_translation_pipeline(model_name)
        text_truncated = text[:512]
        result = pipe(text_truncated)[0]["translation_text"]

        return (
            f"[Traduction {direction}]\n"
            f"Texte original : {text_truncated}\n\n"
            f"Traduction : {result}"
        )

    except ImportError:
        return "Librairie 'transformers' manquante. Lance : pip install transformers"
    except Exception as e:
        return f"Erreur de traduction : {str(e)}"


# ═══════════════════════════════════════════════════════════════════
# OUTIL 4 — Analyse de document uploadé par l'utilisateur
# ═══════════════════════════════════════════════════════════════════
@tool
def analyze_document(text_content: str) -> str:
    """
    Extrait et structure les informations juridiques clés d'un document
    fourni par l'utilisateur.

    Documents supportés :
      - Contrat de travail
      - Mise en demeure
      - Jugement ou décision de tribunal
      - Bail / contrat de location
      - Tout autre document juridique tunisien

    Identifie :
      - Les parties impliquées (employeur/employé, bailleur/locataire...)
      - Les clauses importantes et obligations de chaque partie
      - Les dates et délais mentionnés
      - Les points de risque juridique potentiels
      - Les articles de loi tunisienne éventuellement cités

    Utiliser cet outil quand :
      - L'utilisateur uploade un fichier PDF et demande une analyse
      - L'utilisateur demande si une clause spécifique est légale
      - L'utilisateur veut comprendre un document juridique reçu
    """
    try:
        if not text_content or len(text_content.strip()) < 20:
            return "Document vide ou trop court pour être analysé."

        import re

        lines = [
            l.strip()
            for l in text_content.split("\n")
            if len(l.strip()) > 20
        ]

        total_lines = len(lines)
        word_count = len(text_content.split())

        # ── Pre-processing: lightweight structural extraction ──────
        # Detect party lines (employer, employee, lessor, tenant, company...)
        party_pattern = re.compile(
            r"(entre\s*:?|parties?\s*:?|employeur\s*:?|employ[eé]\s*:?|"
            r"bailleur\s*:?|locataire\s*:?|soci[eé]t[eé]\s*:?|m\.\s|mme\.?\s)",
            re.IGNORECASE
        )
        parties = [l for l in lines if party_pattern.search(l)][:5]

        # Detect article/clause headings
        clause_pattern = re.compile(
            r"^(article|clause|chapitre|section|titre|فصل|مادة)\s*\d*",
            re.IGNORECASE
        )
        clauses = [l for l in lines if clause_pattern.match(l)][:15]

        # Flag high-risk legal keywords for the LLM to scrutinise
        risk_keywords = [
            "non-concurrence", "non concurrence", "clause pénale", "clause penale",
            "résiliation", "resiliation", "indemnité", "indemnite",
            "exclusivité", "exclusivite", "période d'essai", "periode d'essai",
            "nullité", "nullite", "abusif", "irrégulier", "irregulier",
            "dommages-intérêts", "dommages interets",
        ]
        risk_lines = [
            l for l in lines
            if any(kw.lower() in l.lower() for kw in risk_keywords)
        ][:10]

        # ── Build structured output for the LLM ───────────────────
        sections = [
            f"[Document reçu — {total_lines} lignes utiles, ~{word_count} mots]",
        ]

        if parties:
            sections.append(
                "PARTIES DÉTECTÉES :\n" + "\n".join(f"  • {p}" for p in parties)
            )
        if clauses:
            sections.append(
                "CLAUSES / ARTICLES IDENTIFIÉS :\n" + "\n".join(f"  • {c}" for c in clauses)
            )
        if risk_lines:
            sections.append(
                "⚠️  POINTS DE RISQUE POTENTIELS (à vérifier au regard du droit tunisien) :\n"
                + "\n".join(f"  • {r}" for r in risk_lines)
            )

        # FIX: increased from 80 lines to 200 lines so the LLM sees the bulk
        # of a real contract (gradio_app.py also sends 8000 chars now).
        preview = "\n".join(lines[:200])
        sections.append(
            f"TEXTE COMPLET POUR ANALYSE :\n{'─' * 40}\n{preview}\n{'─' * 40}"
            + ("\n[...document tronqué — 200 premières lignes]" if total_lines > 200 else "")
        )

        return "\n\n".join(sections)

    except Exception as e:
        return f"Erreur lors de l'analyse du document : {str(e)}"
