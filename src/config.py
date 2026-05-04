"""
============================================================
config.py - Configuration centrale du projet
============================================================

Ce fichier centralise TOUTES les constantes et paramètres.
L'avantage : modifier un seul endroit pour changer tout le comportement.

Principe de conception : séparation configuration / logique.
"""

import os
from dotenv import load_dotenv

# Charge les variables depuis le fichier .env
# Si .env n'existe pas, les variables d'environnement système sont utilisées
load_dotenv()

# ─────────────────────────────────────────────
# PARAMÈTRES LLM
# ─────────────────────────────────────────────

# Modèle Groq utilisé - Llama 3 70B est le plus puissant disponible gratuitement
LLM_MODEL = "llama3-70b-8192"

# Température = créativité du modèle
# 0.0 = déterministe (mêmes réponses aux mêmes questions)
# 1.0 = très créatif (réponses variées, moins fiables pour du droit)
# 0.1 est idéal pour un assistant juridique : fiable et peu variable
LLM_TEMPERATURE = 0.1

# Nombre maximum de tokens générés par réponse
# 2048 tokens ≈ environ 1500 mots - amplement suffisant pour une réponse juridique
LLM_MAX_TOKENS = 2048

# ─────────────────────────────────────────────
# PARAMÈTRES AGENT ReAct
# ─────────────────────────────────────────────

# Nombre maximum d'itérations de la boucle Thought → Action → Observation
# Si l'agent n'a pas trouvé de réponse après 6 itérations, il s'arrête
# Évite les boucles infinies et contrôle les coûts d'API
AGENT_MAX_ITERATIONS = 6

# Nombre d'échanges conservés en mémoire (5 derniers tours)
# Plus = meilleur contexte, mais plus de tokens consommés à chaque requête
MEMORY_WINDOW_SIZE = 5

# ─────────────────────────────────────────────
# PARAMÈTRES CHROMADB (base vectorielle)
# ─────────────────────────────────────────────

# Chemin de stockage persistant (survit aux redémarrages)
CHROMA_DB_PATH = os.getenv("CHROMA_DB_PATH", "./chroma_db")

# Nom de la collection dans ChromaDB
# Une collection = une table dans une base relationnelle
COLLECTION_NAME = "lois_tunisiennes"

# Nombre de documents retournés par la recherche sémantique
# 3 documents = bonne balance pertinence/contexte
# Augmenter si les réponses manquent de détails, diminuer si trop verbeux
TOP_K_RESULTS = 3

# ─────────────────────────────────────────────
# PARAMÈTRES EMBEDDINGS
# ─────────────────────────────────────────────

# Modèle d'embeddings multilingue de HuggingFace
# "paraphrase-multilingual-MiniLM-L12-v2" supporte 50+ langues dont fr et ar
# Téléchargé automatiquement au premier lancement (~130 Mo)
EMBEDDING_MODEL = "paraphrase-multilingual-MiniLM-L12-v2"

# ─────────────────────────────────────────────
# PARAMÈTRES DÉCOUPAGE DES DOCUMENTS (chunking)
# ─────────────────────────────────────────────

# Taille maximale d'un fragment de texte en caractères
# 512 caractères ≈ 1 ou 2 articles de loi
# Trop grand → contexte dilué, trop petit → articles coupés au milieu
CHUNK_SIZE = 512

# Chevauchement entre deux fragments consécutifs
# 100 caractères de chevauchement évite de couper une phrase en deux
# Garantit la continuité du texte entre fragments
CHUNK_OVERLAP = 100

# ─────────────────────────────────────────────
# CHEMINS DES FICHIERS
# ─────────────────────────────────────────────

# Répertoire contenant les PDFs tunisiens à ingérer
PDF_DIR = os.getenv("PDF_DIR", "./data")

# ─────────────────────────────────────────────
# SEUIL DE CONFIANCE (pour le fallback web)
# ─────────────────────────────────────────────

# Score de similarité minimum pour considérer un résultat pertinent
# ChromaDB retourne des scores entre 0 (identique) et 2 (très différent)
# Sous ce seuil → l'agent bascule sur web_search_jort
CONFIDENCE_THRESHOLD = 1.2
