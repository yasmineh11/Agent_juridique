# src/tools.py
# ═══════════════════════════════════════════════════════════════════
# Agent IA Juridique Tunisien — Guide Juridique Tunisien
# Fichier : tools.py
# Rôle    : Définition des 4 outils utilisés par l'agent ReAct
# ═══════════════════════════════════════════════════════════════════

import chromadb
import requests
from bs4 import BeautifulSoup
from datetime import datetime, timedelta
from langchain_core.tools import tool
from sentence_transformers import SentenceTransformer
from dotenv import load_dotenv

load_dotenv()

# ── Initialisation globale (une seule fois au démarrage) ──────────
model = SentenceTransformer(
    "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
)
from config import CHROMA_DB_PATH, COLLECTION_NAME

chroma_client = chromadb.PersistentClient(path=CHROMA_DB_PATH)
collection = chroma_client.get_or_create_collection(COLLECTION_NAME)
collection = chroma_client.get_or_create_collection("lois_tunisiennes")

HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; AgentJuridiqueTN/1.0)"}

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
        # Vectoriser la question
        emb = model.encode(query).tolist()

        # Recherche dans ChromaDB
        results = collection.query(
            query_embeddings=[emb],
            n_results=4,
            include=["documents", "metadatas", "distances"]
        )

        # Vérifier si des résultats existent
        if not results["documents"] or not results["documents"][0]:
            return (
                "CONFIANCE_FAIBLE (0%) — "
                "La base locale est vide. Lance ingest.py d'abord. "
                "Utiliser web_search_jort."
            )

        # Calculer le score de confiance du meilleur résultat
        # ChromaDB retourne une distance (0=identique, 2=opposé)
        # On la convertit en pourcentage de confiance
        best_distance = results["distances"][0][0]
        confidence = round((1 - best_distance / 2) * 100)

        # Seuil de confiance : si < 40% → signal fallback
        if confidence < 40:
            return (
                f"CONFIANCE_FAIBLE ({confidence}%) — "
                f"Résultats insuffisants dans la base locale. "
                f"Utiliser web_search_jort pour chercher en ligne."
            )

        # Formater les résultats avec sources et scores
        output = []
        for doc, meta, dist in zip(
            results["documents"][0],
            results["metadatas"][0],
            results["distances"][0]
        ):
            score = round((1 - dist / 2) * 100)
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
    Recherche les lois et décrets tunisiens récents sur deux sources :

      1. iort.gov.tn  — Journal Officiel de la République Tunisienne
                        Source officielle de toutes les lois promulguées.

      2. 9anoun.tn    — Codes juridiques tunisiens en arabe, mis à jour
                        Contient : Code du Travail, Code Pénal, Code des
                        Obligations, Code de Commerce, Code Fiscal,
                        Code de Procédure Civile, Code des Douanes,
                        Code des Droits Réels, Code Maritime, JORT.

    RÈGLE D'UTILISATION :
      - Appeler UNIQUEMENT si search_legal_docs retourne CONFIANCE_FAIBLE
      - Ou si la question porte sur une loi très récente (2024-2025)
      - Ne JAMAIS appeler avant search_legal_docs
    """

    results = []

    # ── SOURCE 1 : JORT officiel (iort.gov.tn) ───────────────────
    try:
        jort_url = (
            f"https://www.google.com/search"
            f"?q={requests.utils.quote(keywords)}+site:iort.gov.tn"
        )
        resp = requests.get(jort_url, headers=HEADERS, timeout=8)
        soup = BeautifulSoup(resp.text, "html.parser")

        # Extraire les snippets Google
        snippets = [
            g.get_text()
            for g in soup.find_all("div", class_="BNeawe")[:4]
            if len(g.get_text()) > 40
        ]

        if snippets:
            results.append(
                "[Source : JORT — iort.gov.tn]\n" +
                "\n\n".join(snippets)
            )
        else:
            # Tentative directe sur le site JORT
            direct = requests.get(
                f"https://www.iort.gov.tn/SITEIORT_WEB/",
                headers=HEADERS, timeout=6
            )
            soup_d = BeautifulSoup(direct.text, "html.parser")
            paras = [
                p.get_text().strip()
                for p in soup_d.find_all("p")
                if len(p.get_text().strip()) > 50
            ][:4]
            if paras:
                results.append(
                    "[Source : JORT — iort.gov.tn]\n" +
                    "\n".join(paras)
                )
            else:
                results.append("[JORT : aucun résultat trouvé]")

    except Exception as e:
        results.append(f"[JORT inaccessible : {str(e)}]")

    # ── SOURCE 2 : 9anoun.tn ─────────────────────────────────────
    # Mapping complet mots-clés → slug du code sur 9anoun.tn
    CODE_MAP = {
        # ── Code du Travail ──
        "شغل":              "code-travail-proposition-amendements-2025",
        "travail":           "code-travail-proposition-amendements-2025",
        "licenciement":      "code-travail-proposition-amendements-2025",
        "preavis":           "code-travail-proposition-amendements-2025",
        "préavis":           "code-travail-proposition-amendements-2025",
        "salaire":           "code-travail-proposition-amendements-2025",
        "conge":             "code-travail-proposition-amendements-2025",
        "congé":             "code-travail-proposition-amendements-2025",
        "contrat travail":   "code-travail-proposition-amendements-2025",
        "heures travail":    "code-travail-proposition-amendements-2025",
        "syndicat":          "code-travail-proposition-amendements-2025",
        "greve":             "code-travail-proposition-amendements-2025",
        "grève":             "code-travail-proposition-amendements-2025",
        "indemnite":         "code-travail-proposition-amendements-2025",
        "indemnité":         "code-travail-proposition-amendements-2025",

        # ── Code des Obligations et Contrats ──
        "عقود":              "code-obligations-contrats",
        "التزامات":          "code-obligations-contrats",
        "obligations":       "code-obligations-contrats",
        "contrat":           "code-obligations-contrats",
        "loyer":             "code-obligations-contrats",
        "bail":              "code-obligations-contrats",
        "responsabilite":    "code-obligations-contrats",
        "responsabilité":    "code-obligations-contrats",
        "dommages":          "code-obligations-contrats",
        "vente":             "code-obligations-contrats",

        # ── Code de Commerce ──
        "تجاري":             "code-commerce",
        "commerce":          "code-commerce",
        "societe":           "code-commerce",
        "société":           "code-commerce",
        "faillite":          "code-commerce",
        "liquidation":       "code-commerce",
        "cheque":            "code-commerce",
        "chèque":            "code-commerce",
        "facture":           "code-commerce",

        # ── Code Fiscal / Impôts ──
        "ضريبة":             "code-impot-sur-revenu-personnes-physiques-impot-sur-les-societes",
        "جباية":             "code-impot-sur-revenu-personnes-physiques-impot-sur-les-societes",
        "impot":             "code-impot-sur-revenu-personnes-physiques-impot-sur-les-societes",
        "impôt":             "code-impot-sur-revenu-personnes-physiques-impot-sur-les-societes",
        "fiscal":            "code-impot-sur-revenu-personnes-physiques-impot-sur-les-societes",
        "taxe":              "code-impot-sur-revenu-personnes-physiques-impot-sur-les-societes",
        "tva":               "code-impot-sur-revenu-personnes-physiques-impot-sur-les-societes",
        "declaration":       "code-impot-sur-revenu-personnes-physiques-impot-sur-les-societes",
        "déclaration":       "code-impot-sur-revenu-personnes-physiques-impot-sur-les-societes",

        # ── Code de Procédure Civile ──
        "مرافعات":           "code-procedure-civile-commerciale",
        "procedure":         "code-procedure-civile-commerciale",
        "procédure":         "code-procedure-civile-commerciale",
        "delai":             "code-procedure-civile-commerciale",
        "délai":             "code-procedure-civile-commerciale",
        "recours":           "code-procedure-civile-commerciale",
        "tribunal":          "code-procedure-civile-commerciale",
        "jugement":          "code-procedure-civile-commerciale",
        "appel":             "code-procedure-civile-commerciale",
        "cassation":         "code-procedure-civile-commerciale",
        "execution":         "code-procedure-civile-commerciale",
        "exécution":         "code-procedure-civile-commerciale",

        # ── Code des Douanes ──
        "douane":            "code-douanes",
        "ديوانة":            "code-douanes",
        "importation":       "code-douanes",
        "exportation":       "code-douanes",
        "dedouanement":      "code-douanes",
        "dédouanement":      "code-douanes",

        # ── Code des Collectivités Locales ──
        "بلدية":             "code-collectivites-locales",
        "local":             "code-collectivites-locales",
        "municipalite":      "code-collectivites-locales",
        "municipalité":      "code-collectivites-locales",
        "commune":           "code-collectivites-locales",
        "gouvernorat":       "code-collectivites-locales",

        # ── Code de Commerce Maritime ──
        "بحري":              "code-commerce-maritime",
        "maritime":          "code-commerce-maritime",
        "navire":            "code-commerce-maritime",
        "transport maritime":"code-commerce-maritime",

        # ── Code des Droits Réels ──
        "عيني":              "code-droits-reels",
        "propriete":         "code-droits-reels",
        "propriété":         "code-droits-reels",
        "immobilier":        "code-droits-reels",
        "foncier":           "code-droits-reels",
        "hypotheque":        "code-droits-reels",
        "hypothèque":        "code-droits-reels",

        # ── Code de Comptabilité Publique ──
        "comptabilite":      "code-comptabilite-publique",
        "comptabilité":      "code-comptabilite-publique",
        "budget":            "code-comptabilite-publique",
        "finances publiques":"code-comptabilite-publique",

        # ── Code Droit International Privé ──
        "international":     "code-droit-international-prive",
        "دولي":              "code-droit-international-prive",
        "extradition":       "code-droit-international-prive",
        "nationalite":       "code-droit-international-prive",
        "nationalité":       "code-droit-international-prive",
    }

    # Trouver le slug correspondant aux mots-clés
    slug = None
    kw_lower = keywords.lower()
    for key, val in CODE_MAP.items():
        if key.lower() in kw_lower:
            slug = val
            break

    # URL cible sur 9anoun.tn
    target_url = (
        f"https://9anoun.tn/kb/codes/{slug}"
        if slug
        else "https://9anoun.tn/kb/codes"
    )

    try:
        resp9 = requests.get(target_url, headers=HEADERS, timeout=8)
        soup9 = BeautifulSoup(resp9.text, "html.parser")

        # Extraire les paragraphes utiles (> 50 caractères)
        paras = [
            p.get_text().strip()
            for p in soup9.find_all("p")
            if len(p.get_text().strip()) > 50
        ]
        content = "\n\n".join(paras[:6])

        if content:
            results.append(
                f"[Source : 9anoun.tn | {target_url}]\n{content}"
            )
        else:
            # Fallback Google limité à 9anoun.tn
            google_9 = (
                f"https://www.google.com/search"
                f"?q={requests.utils.quote(keywords)}+site:9anoun.tn"
            )
            resp_g = requests.get(google_9, headers=HEADERS, timeout=8)
            soup_g = BeautifulSoup(resp_g.text, "html.parser")
            snips = [
                g.get_text()
                for g in soup_g.find_all("div", class_="BNeawe")[:3]
                if len(g.get_text()) > 40
            ]
            if snips:
                results.append(
                    "[Source : 9anoun.tn via Google]\n" +
                    "\n\n".join(snips)
                )
            else:
                results.append(
                    f"[9anoun.tn : aucun contenu extrait depuis {target_url}]"
                )

    except Exception as e:
        results.append(f"[9anoun.tn inaccessible : {str(e)}]")

    # ── Fusion des deux sources ───────────────────────────────────
    if not results:
        return "Aucun résultat trouvé sur JORT ni sur 9anoun.tn."

    separator = "\n\n" + "═" * 50 + "\n\n"
    return separator.join(results)


# ═══════════════════════════════════════════════════════════════════
# OUTIL 3 — Traduction arabe ↔ français
# ═══════════════════════════════════════════════════════════════════
@tool
def translate_legal_text(text: str, target_lang: str) -> str:
    """
    Traduit un texte juridique tunisien entre l'arabe et le français
    en utilisant Helsinki-NLP (gratuit sur HuggingFace).

    Paramètres :
      - text        : le texte à traduire (max 512 caractères par appel)
      - target_lang : 'fr' pour arabe→français | 'ar' pour français→arabe

    Utiliser cet outil quand :
      - L'utilisateur écrit sa question en arabe
      - Un article trouvé est en arabe et l'utilisateur veut le français
      - L'utilisateur demande explicitement la traduction d'un texte
      - 9anoun.tn retourne un texte en arabe à traduire
    """
    try:
        from transformers import pipeline as hf_pipeline

        # Choisir le modèle selon la direction de traduction
        if target_lang == "fr":
            model_name = "Helsinki-NLP/opus-mt-ar-fr"
            direction = "Arabe → Français"
        elif target_lang == "ar":
            model_name = "Helsinki-NLP/opus-mt-fr-ar"
            direction = "Français → Arabe"
        else:
            return (
                f"Paramètre target_lang invalide : '{target_lang}'. "
                f"Utiliser 'fr' ou 'ar'."
            )

        # Charger le pipeline (mis en cache après le premier appel)
        pipe = hf_pipeline("translation", model=model_name)

        # Tronquer à 512 caractères pour éviter les erreurs de mémoire
        text_truncated = text[:512]
        result = pipe(text_truncated)[0]["translation_text"]

        return (
            f"[Traduction {direction}]\n"
            f"Texte original : {text_truncated}\n\n"
            f"Traduction : {result}"
        )

    except ImportError:
        return (
            "Librairie 'transformers' manquante. "
            "Lance : pip install transformers"
        )
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

        # Nettoyer le texte : supprimer les lignes vides et trop courtes
        lines = [
            l.strip()
            for l in text_content.split("\n")
            if len(l.strip()) > 20
        ]

        total_lines = len(lines)
        # Prendre les 80 premières lignes utiles pour l'analyse
        preview_lines = lines[:80]
        preview = "\n".join(preview_lines)

        # Compter les mots et estimer la longueur
        word_count = len(text_content.split())

        return (
            f"[Document reçu — {total_lines} lignes utiles, "
            f"~{word_count} mots]\n\n"
            f"Contenu extrait pour analyse :\n"
            f"{'─' * 40}\n"
            f"{preview}\n"
            f"{'─' * 40}\n"
            f"{'[...document tronqué — 80 premières lignes]' if total_lines > 80 else ''}"
        )

    except Exception as e:
        return f"Erreur lors de l'analyse du document : {str(e)}"