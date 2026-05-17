# test_agent.py
import sys
import uuid
import time
sys.path.insert(0, "./src")

from agent import ask_agent

thread_local  = str(uuid.uuid4())
thread_jort   = str(uuid.uuid4())
thread_multi  = str(uuid.uuid4())
thread_arabic = str(uuid.uuid4())
thread_doc    = str(uuid.uuid4())

questions = [
    {
        "id": 1,
        "label": "Recherche locale simple",
        "question": "Quels sont mes droits si mon employeur me licencie sans préavis ?",
        "thread_id": thread_local,
    },
    {
        "id": 2,
        "label": "Fallback vers JORT + 9anoun.tn",
        "question": "Décret 2024 contrats de travail Tunisie nouveautés",
        "thread_id": thread_jort,
    },
    {
        "id": 3,
        "label": "Multi-outils — loi + source web",
        "question": "Mon patron peut-il baisser mon salaire sans mon accord ?",
        "thread_id": thread_multi,
    },
    {
        "id": 4,
        "label": "Question en arabe + traduction",
        "question": "ما هي حقوقي في حالة الطرد التعسفي من العمل؟",
        "thread_id": thread_arabic,
    },
    {
        "id": 5,
        "label": "Analyse de document",
        # Pass contract text directly to analyze_document tool via the
        # tool's own input format — avoids triggering web_search_jort
        # which would add thousands of tokens and exceed the free TPM limit.
        "question": (
            "Utilise l'outil analyze_document avec ce texte exactement, "
            "puis dis-moi si les clauses sont légales :\n"
            "CONTRAT DE TRAVAIL. Société ABC et M. Mohamed Ben Ali. "
            "Article 1: CDI, période d'essai 6 mois. "
            "Article 2: Salaire 900 TND. "
            "Article 3: Préavis 15 jours. "
            "Article 4: Non-concurrence 3 ans."
        ),
        "thread_id": thread_doc,
    },
    {
        "id": 6,
        "label": "Mémoire — question de suivi (contexte de test 1)",
        "question": "Et quel est le délai légal pour contester cette décision ?",
        "thread_id": thread_local,
    },
]

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
    print("⏳ Pause 25s (limite débit Groq free tier)...")
    time.sleep(25)

print("\n" + "█"*60)
print("   FIN DES TESTS")
print("█"*60)