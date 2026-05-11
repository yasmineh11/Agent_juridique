# src/agent.py
import os
import sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from dotenv import load_dotenv
from langchain_groq import ChatGroq
from langchain_core.messages import HumanMessage, SystemMessage
from langgraph.prebuilt import create_react_agent
from langgraph.checkpoint.memory import MemorySaver

from tools import (
    search_legal_docs,
    web_search_jort,
    translate_legal_text,
    analyze_document
)

load_dotenv()

# ── LLM ──────────────────────────────────────────────────────────
llm = ChatGroq(
    model="llama-3.3-70b-versatile",
    temperature=0.1,
    api_key=os.getenv("GROQ_API_KEY")
)

# ── Outils ───────────────────────────────────────────────────────
tools = [
    search_legal_docs,
    web_search_jort,
    translate_legal_text,
    analyze_document
]

# ── Prompt système ───────────────────────────────────────────────
SYSTEM_PROMPT = """Tu es un assistant juridique expert en droit tunisien.
Tu aides les citoyens tunisiens a comprendre leurs droits de facon
simple et claire, en citant toujours tes sources.

REGLES OBLIGATOIRES :
1. Appelle TOUJOURS search_legal_docs EN PREMIER
2. Si search_legal_docs retourne CONFIANCE_FAIBLE
   → appelle immediatement web_search_jort
3. Si la question est en arabe
   → appelle translate_legal_text apres la recherche
4. Si l'utilisateur joint un document
   → appelle analyze_document avant tout
5. Cite TOUJOURS l'article exact et la source
6. Si aucun outil ne trouve → dis-le clairement, sans inventer
7. Reponds en francais sauf si l'utilisateur ecrit en arabe

IMPORTANT : tu n'es pas un avocat. Tes reponses sont
informatives uniquement."""

# ── Memoire ───────────────────────────────────────────────────────
memory = MemorySaver()

# ── Agent LangGraph 0.2.x ────────────────────────────────────────
agent_executor = create_react_agent(
    model=llm,
    tools=tools,
    state_modifier=SYSTEM_PROMPT,
    checkpointer=memory
)


# ── Fonction principale ───────────────────────────────────────────
def ask_agent(question: str, thread_id: str = "default") -> str:
    config = {"configurable": {"thread_id": thread_id}}
    try:
        result = agent_executor.invoke(
            {"messages": [HumanMessage(content=question)]},
            config=config
        )
        return result["messages"][-1].content
    except Exception as e:
        return f"Erreur agent : {str(e)}"


# ── Test direct ───────────────────────────────────────────────────
if __name__ == "__main__":
    print("Agent pret — langgraph 0.2.60 + llama-3.3-70b-versatile")
    print("=" * 55)

    questions = [
        "Quels sont mes droits en cas de licenciement sans preavis ?",
        "Et quel est le delai pour contester ?"
    ]

    for q in questions:
        print(f"\nQuestion : {q}")
        print(f"Reponse  : {ask_agent(q)}")
        print("-" * 55)