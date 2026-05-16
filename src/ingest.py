"""
============================================================
ingest.py - Ingestion et vectorisation des documents PDF
============================================================

Ce script est exécuté UNE SEULE FOIS avant le lancement de l'agent.
Il lit les PDFs, les découpe en fragments, les vectorise et les stocke
dans ChromaDB pour des recherches sémantiques ultra-rapides.

Workflow :
    PDF  →  texte brut  →  fragments  →  vecteurs  →  ChromaDB
           (PyMuPDF)     (splitter)    (embeddings)   (stockage)

Usage :
    python ingest.py
"""

import os
import sys
import fitz  # PyMuPDF - bibliothèque de lecture PDF
from pathlib import Path

import chromadb
from chromadb.utils.embedding_functions import SentenceTransformerEmbeddingFunction

from langchain_text_splitters import RecursiveCharacterTextSplitter

from config import (
    CHROMA_DB_PATH,
    COLLECTION_NAME,
    EMBEDDING_MODEL,
    CHUNK_SIZE,
    CHUNK_OVERLAP,
    PDF_DIR,
)


# ─────────────────────────────────────────────
# ÉTAPE 1 : Extraction du texte des PDFs
# ─────────────────────────────────────────────

def extraire_texte_pdf(chemin_pdf: str) -> list[dict]:
    """
    Extrait le texte d'un PDF page par page avec PyMuPDF.

    Pourquoi PyMuPDF (fitz) plutôt que pdfplumber ou PyPDF2 ?
    - Meilleure gestion des PDFs scannés
    - Support natif de l'arabe (RTL - Right To Left)
    - Plus rapide pour les grands documents

    Args:
        chemin_pdf: Chemin absolu ou relatif vers le fichier PDF

    Returns:
        Liste de dicts {"texte": str, "page": int, "source": str}
    """
    pages = []
    nom_fichier = Path(chemin_pdf).stem  # Nom sans extension

    try:
        doc = fitz.open(chemin_pdf)

        for numero_page in range(len(doc)):
            page = doc[numero_page]
            texte = page.get_text("text")

            if len(texte.strip()) > 50:
                pages.append({
                    "texte": texte.strip(),
                    "page": numero_page + 1,
                    "source": nom_fichier,
                })

        doc.close()
        print(f"  ✅ {nom_fichier} : {len(pages)} pages extraites")

    except Exception as e:
        print(f"  ❌ Erreur lecture {chemin_pdf}: {e}")

    return pages


# ─────────────────────────────────────────────
# ÉTAPE 2 : Découpage intelligent (chunking)
# ─────────────────────────────────────────────

def decouper_en_fragments(pages: list[dict]) -> list[dict]:
    """
    Découpe le texte extrait en fragments de taille optimale pour les embeddings.

    Pourquoi découper ?
    - Les modèles d'embeddings ont une limite de tokens (512 tokens)
    - Des fragments plus petits = embeddings plus précis = recherche plus pertinente
    - Le chevauchement (overlap) évite de couper des articles de loi en deux

    Stratégie RecursiveCharacterTextSplitter :
    1. Essaie d'abord de couper aux doubles sauts de ligne (entre paragraphes)
    2. Puis aux sauts de ligne simples (entre phrases)
    3. Puis aux espaces
    4. En dernier recours, coupe au caractère

    Args:
        pages: Liste de dicts {"texte", "page", "source"}

    Returns:
        Liste de fragments avec métadonnées enrichies
    """
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=CHUNK_SIZE,
        chunk_overlap=CHUNK_OVERLAP,
        separators=[
            "\nArticle",      # Coupe prioritairement aux articles de loi (français)
            # FIX: the original separator used Arabic Presentation Forms (U+FE80
            # range), which are rarely used in modern PDFs. Replaced with standard
            # Unicode Arabic (U+0627 + U+0644 + U+0645 + U+0627 + U+062F + U+0629)
            # so the splitter actually matches article headings in source PDFs.
            "\nالمادة",       # Coupe aux articles en arabe (Unicode standard)
            "\n\n",           # Puis aux paragraphes
            "\n",             # Puis aux lignes
            ".",              # Puis aux phrases
            " ",              # En dernier recours
        ],
        length_function=len,
    )

    fragments = []

    for page_info in pages:
        morceaux = splitter.split_text(page_info["texte"])

        for i, morceau in enumerate(morceaux):
            if len(morceau.strip()) < 30:
                continue

            fragments.append({
                "texte": morceau.strip(),
                "source": page_info["source"],
                "page": page_info["page"],
                "fragment_id": i,
                "contient_article": (
                    "article" in morceau.lower() or
                    "المادة" in morceau  # FIX: normalised Arabic
                ),
            })

    return fragments


# ─────────────────────────────────────────────
# ÉTAPE 3 : Vectorisation et stockage ChromaDB
# ─────────────────────────────────────────────

def stocker_dans_chromadb(fragments: list[dict]) -> chromadb.Collection:
    """
    Vectorise les fragments et les stocke dans ChromaDB.

    Que sont les embeddings (vecteurs) ?
    - Chaque fragment de texte est transformé en un tableau de ~384 nombres
    - Deux textes sémantiquement proches → vecteurs proches dans l'espace
    - Exemple : "licenciement abusif" et "rupture injustifiée du contrat"
      auront des vecteurs proches → même résultat de recherche

    ChromaDB stocke :
    - Le texte original (documents)
    - Son vecteur (pour la recherche)
    - Les métadonnées (source, page, etc.)

    Args:
        fragments: Liste de fragments avec leurs métadonnées

    Returns:
        La collection ChromaDB prête pour les requêtes
    """
    print("\n🔧 Initialisation de ChromaDB...")

    client = chromadb.PersistentClient(path=CHROMA_DB_PATH)

    embedding_function = SentenceTransformerEmbeddingFunction(
        model_name=EMBEDDING_MODEL
    )

    try:
        client.delete_collection(COLLECTION_NAME)
        print(f"  🗑️  Ancienne collection '{COLLECTION_NAME}' supprimée")
    except Exception:
        pass

    collection = client.create_collection(
        name=COLLECTION_NAME,
        embedding_function=embedding_function,
        metadata={"hnsw:space": "cosine"},
    )

    print(f"  📦 Vectorisation de {len(fragments)} fragments...")
    print("  ⏳ (première exécution : téléchargement du modèle d'embeddings ~130Mo)")

    BATCH_SIZE = 100
    for debut in range(0, len(fragments), BATCH_SIZE):
        lot = fragments[debut:debut + BATCH_SIZE]

        collection.add(
            ids=[f"{f['source']}_p{f['page']}_f{f['fragment_id']}" for f in lot],
            documents=[f["texte"] for f in lot],
            metadatas=[{
                "source": f["source"],
                "page": f["page"],
                "contient_article": str(f["contient_article"]),
            } for f in lot],
        )

        print(f"  ✅ Lot {debut // BATCH_SIZE + 1} ingéré ({min(debut + BATCH_SIZE, len(fragments))}/{len(fragments)})")

    return collection


# ─────────────────────────────────────────────
# PIPELINE PRINCIPAL
# ─────────────────────────────────────────────

def main():
    """
    Exécute le pipeline complet d'ingestion.
    Lance avec : python ingest.py
    """
    print("=" * 60)
    print("  GUIDE JURIDIQUE TUNISIEN - Ingestion des documents")
    print("=" * 60)

    if not os.path.exists(PDF_DIR):
        os.makedirs(PDF_DIR)
        print(f"\n📁 Répertoire '{PDF_DIR}' créé.")
        print("   → Placez vos PDFs tunisiens dans ce répertoire")
        print("   → Exemples : code_travail.pdf, code_penal.pdf, jort.pdf")
        print("\n💡 Pour un test rapide, téléchargez depuis :")
        print("   https://legislation.tn/")
        return

    pdfs = list(Path(PDF_DIR).glob("*.pdf"))

    if not pdfs:
        print(f"\n⚠️  Aucun PDF trouvé dans '{PDF_DIR}'")
        print("   → Placez vos PDFs et relancez : python ingest.py")
        return

    print(f"\n📚 {len(pdfs)} PDF(s) trouvé(s) :")
    for pdf in pdfs:
        print(f"   - {pdf.name}")

    print("\n📖 Étape 1/3 : Extraction du texte...")
    toutes_les_pages = []
    for pdf in pdfs:
        pages = extraire_texte_pdf(str(pdf))
        toutes_les_pages.extend(pages)

    print(f"   Total : {len(toutes_les_pages)} pages extraites")

    print("\n✂️  Étape 2/3 : Découpage en fragments...")
    fragments = decouper_en_fragments(toutes_les_pages)
    print(f"   Total : {len(fragments)} fragments créés")

    print("\n🧠 Étape 3/3 : Vectorisation et stockage...")
    collection = stocker_dans_chromadb(fragments)

    count = collection.count()
    print(f"\n{'=' * 60}")
    print(f"  ✅ INGESTION TERMINÉE : {count} fragments indexés")
    print(f"  📂 Base vectorielle : {CHROMA_DB_PATH}")
    print(f"  🚀 Lancez maintenant : python gradio_app.py")
    print("=" * 60)


if __name__ == "__main__":
    main()
