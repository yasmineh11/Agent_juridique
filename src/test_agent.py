# test_agent.py
import sys
sys.path.insert(0, "./src")

from agent import ask_agent

# ── Questions de test couvrant tous les scénarios ─────────────────

questions = [

    # Teste search_legal_docs seul (dans la base locale)
    {
        "id": 1,
        "label": "Recherche locale simple",
        "question": "Quels sont mes droits si mon employeur me licencie sans préavis ?"
    },

    # Teste l'enchaînement search_legal_docs → web_search_jort
    {
        "id": 2,
        "label": "Fallback vers JORT + 9anoun.tn",
        "question": "Quelles sont les nouvelles dispositions du décret 2024 sur les contrats de travail ?"
    },

    # Teste search_legal_docs + web_search_jort (2 outils en séquence)
    {
        "id": 3,
        "label": "Multi-outils — loi + source web",
        "question": "Mon patron peut-il baisser mon salaire sans mon accord ? Cherche dans les lois et sur le JORT."
    },

    # Teste translate_legal_text (question en arabe)
    {
        "id": 4,
        "label": "Question en arabe + traduction",
        "question": "ما هي حقوقي في حالة الطرد التعسفي من العمل؟"
    },

    # Teste analyze_document
    {
        "id": 5,
        "label": "Analyse de document",
        "question": (
            "Analyse ce contrat de travail et dis-moi si les clauses sont légales :\n\n"
            "CONTRAT DE TRAVAIL\n"
            "Entre : Société ABC et M. Mohamed Ben Ali\n"
            "Article 1 : Durée indéterminée, période d'essai 6 mois\n"
            "Article 2 : Salaire brut 900 TND\n"
            "Article 3 : Préavis de 15 jours en cas de rupture\n"
            "Article 4 : Clause de non-concurrence 3 ans sur tout le territoire tunisien"
        )
    },

    # Teste la mémoire conversationnelle
    {
        "id": 6,
        "label": "Mémoire — question de suivi",
        "question": "Et quel est le délai légal pour contester cette décision ?"
        # Cette question fait référence à la réponse précédente
        # → l'agent doit utiliser la mémoire pour comprendre "cette décision"
    },
]

# ── Lancer les tests ──────────────────────────────────────────────
print("\n" + "█"*60)
print("   TESTS AGENT IA JURIDIQUE TUNISIEN")
print("█"*60)

for test in questions:
    print(f"\n{'─'*60}")
    print(f"TEST {test['id']} — {test['label']}")
    print(f"QUESTION : {test['question'][:80]}...")
    print(f"{'─'*60}")

    try:
        response = ask_agent(test["question"])
        print(f"RÉPONSE :\n{response}")
    except Exception as e:
        print(f"❌ ERREUR : {e}")

    print()

print("\n" + "█"*60)
print("   FIN DES TESTS")
print("█"*60)