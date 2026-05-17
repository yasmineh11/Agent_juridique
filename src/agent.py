# src/agent.py
import os
import sys
import datetime

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from dotenv import load_dotenv
from langchain_groq import ChatGroq
from langgraph.prebuilt import create_react_agent
from langgraph.checkpoint.memory import MemorySaver
from langchain_core.messages import HumanMessage, SystemMessage, AIMessage
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
    api_key=os.getenv("GROQ_API_KEY"),
    model_kwargs={"parallel_tool_calls": False},
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

# ── Mémoire manuelle (fenêtre glissante) ─────────────────────────
# We manage history manually instead of using MemorySaver so we can
# trim it to the last N exchanges before each request — this prevents
# the conversation from growing large enough to trigger Groq's XML
# fallback or exceed the free-tier TPM limit.
_histories: dict[str, list] = {}
MAX_HISTORY_EXCHANGES = 2  # keep last 2 Q&A pairs = 4 messages


def _get_messages(thread_id: str, question: str) -> list:
    """Build the messages list with trimmed history + new question."""
    history = _histories.get(thread_id, [])
    # Keep only the last MAX_HISTORY_EXCHANGES exchanges
    trimmed = history[-(MAX_HISTORY_EXCHANGES * 2):]
    return [SystemMessage(content=SYSTEM_PROMPT)] + trimmed + [HumanMessage(content=question)]


def _save_exchange(thread_id: str, question: str, answer: str) -> None:
    """Append the latest Q&A to the thread history."""
    if thread_id not in _histories:
        _histories[thread_id] = []
    _histories[thread_id].append(HumanMessage(content=question))
    _histories[thread_id].append(AIMessage(content=answer))


# ── Agent (no checkpointer — we manage memory ourselves) ──────────
agent_executor = create_react_agent(
    model=llm,
    tools=tools,
)


# ── Fonction principale ───────────────────────────────────────────
def ask_agent(question: str, thread_id: str = "default") -> str:
    config = {"recursion_limit": AGENT_MAX_ITERATIONS * 3}
    try:
        messages = _get_messages(thread_id, question)
        result = agent_executor.invoke({"messages": messages}, config=config)
        answer = result["messages"][-1].content
        _save_exchange(thread_id, question, answer)
        return answer
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