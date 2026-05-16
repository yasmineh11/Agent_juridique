# src/agent.py
import os
import sys
import datetime

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from dotenv import load_dotenv
from langchain_groq import ChatGroq
from langgraph.prebuilt import create_react_agent
from langgraph.checkpoint.memory import MemorySaver
from langchain_core.messages import HumanMessage, SystemMessage
from config import LLM_MODEL, LLM_TEMPERATURE, LLM_MAX_TOKENS, AGENT_MAX_ITERATIONS
from tools import (
    search_legal_docs,
    web_search_jort,
    translate_legal_text,
    analyze_document
)

load_dotenv()

# ── LLM ──────────────────────────────────────────────────────────
llm = ChatGroq(
    model=LLM_MODEL,
    temperature=LLM_TEMPERATURE,
    max_tokens=LLM_MAX_TOKENS,
    api_key=os.getenv("GROQ_API_KEY")
)

# ── Outils ───────────────────────────────────────────────────────
tools = [
    search_legal_docs,
    web_search_jort,
    translate_legal_text,
    analyze_document
]

# ── Prompt système ────────────────────────────────────────────────
_today = datetime.date.today().strftime("%d %B %Y")

SYSTEM_PROMPT = (
    f"You are a Tunisian legal assistant. Today: {_today}. "
    "Always use tools. Never answer from memory alone. "
    "Rules: (1) Always call search_legal_docs first. "
    "(2) If it returns CONFIANCE_FAIBLE, call web_search_jort. "
    "(3) If user uploads a document, call analyze_document first. "
    "(4) If question is in Arabic, call translate_legal_text after searching. "
    "(5) Always cite the exact article and source. "
    "(6) Reply in French unless the user writes in Arabic. "
    "(7) You are not a lawyer. Answers are informational only."
)

# ── Mémoire ───────────────────────────────────────────────────────
memory = MemorySaver()

# ── Agent ─────────────────────────────────────────────────────────
# 'prompt' was renamed to 'state_modifier' in langgraph >= 0.2.x
agent_executor = create_react_agent(
    model=llm,
    tools=tools,
    state_modifier=SYSTEM_PROMPT,
    checkpointer=memory,
)


# ── Fonction principale ───────────────────────────────────────────
def ask_agent(question: str, thread_id: str = "default") -> str:
    config = {
        "configurable": {"thread_id": thread_id},
        "recursion_limit": AGENT_MAX_ITERATIONS * 3,
    }
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
    print(f"Agent pret — {LLM_MODEL}")
    print("=" * 55)
    questions = [
        "Quels sont mes droits en cas de licenciement sans preavis ?",
        "Et quel est le delai pour contester ?"
    ]
    for q in questions:
        print(f"\nQuestion : {q}")
        print(f"Reponse  : {ask_agent(q)}")
        print("-" * 55)