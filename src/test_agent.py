# test_agent.py
import sys
import uuid
sys.path.insert(0, "./src")

from agent import ask_agent

# ── Questions de test couvrant tous les scénarios ─────────────────

# FIX: each test gets its own unique thread_id so tests don't bleed into
# each other's memory context. The memory follow-up test (id=6) explicitly
# reuses the thread from test id=1 to verify cross-turn context works.
thread_local   = str(uuid.uuid4())   # Tests 1, 6 share this thread (memory test)
thread_jort    = str(uuid.uuid4())
thread_multi   = str(uuid.uuid4())
thread_arabic  = str(uuid.uuid4())
thread_doc     = str(uuid.uuid4())

questions = [

    # Teste search_legal_docs seul (dans la base locale)
    {
        "id": 1,
        "label": "Recherche locale simple",
        "question": "Quels sont mes droits si mon employeur me licencie sans préavis ?",
        "thread_id": thread_local,
    },

    # Teste l'enchaînement search_legal_docs → web_search_jort
    {
        "id": 2,
        "label": "Fallback vers JORT + 9anoun.tn",
        "question": "Quelles sont les nouvelles dispositions du décret 2024 sur les contrats de travail ?",
        "thread_id": thread_jort,
    },

    # Teste search_legal_docs + web_search_jort (2 outils en séquence)
    {
        "id": 3,
        "label": "Multi-outils — loi + source web",
        "question": "Mon patron peut-il baisser mon salaire sans mon accord ? Cherche dans les lois et sur le JORT.",
        "thread_id": thread_multi,
    },

    # Teste translate_legal_text (question en arabe)
    {
        "id": 4,
        "label": "Question en arabe + traduction",
        "question": "ما هي حقوقي في حالة الطرد التعسفي من العمل؟",
        "thread_id": thread_arabic,
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
        ),
        "thread_id": thread_doc,
    },

    # Teste la mémoire conversationnelle
    # FIX: explicitly reuses thread_local (same as test 1) so the agent
    # has real context to refer back to. Previously all tests used the
    # default thread, making the memory test non-deterministic depending
    # on which question happened to run last.
    {
        "id": 6,
        "label": "Mémoire — question de suivi (contexte de test 1)",
        "question": "Et quel est le délai légal pour contester cette décision ?",
        "thread_id": thread_local,
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
    print(f"THREAD   : {test['thread_id'][:8]}...")
    print(f"{'─'*60}")

    try:
        response = ask_agent(test["question"], thread_id=test["thread_id"])
        print(f"RÉPONSE :\n{response}")
    except Exception as e:
        print(f"❌ ERREUR : {e}")

    print()

print("\n" + "█"*60)
print("   FIN DES TESTS")
print("█"*60)
