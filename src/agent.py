# src/agent.py
import os
import sys
import time
import datetime
import json
import re

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from dotenv import load_dotenv
from langchain_groq import ChatGroq
from langchain_core.messages import HumanMessage, SystemMessage, AIMessage
from config import LLM_MODEL, LLM_TEMPERATURE, LLM_MAX_TOKENS, AGENT_MAX_ITERATIONS
from tools import (
    search_legal_docs,
    web_search_jort,
    translate_legal_text,
    analyze_document
)

load_dotenv()

# ── Outils ───────────────────────────────────────────────────────
tools_by_name = {
    "search_legal_docs":  search_legal_docs,
    "web_search_jort":    web_search_jort,
    "translate_legal_text": translate_legal_text,
    "analyze_document":   analyze_document,
}

# ── LLM sans bind_tools ───────────────────────────────────────────
# FIX: on n'utilise PAS bind_tools() — LangChain génère un format XML
# <function=...> que llama-3.3-70b produit souvent de façon incomplète.
# On passe les outils dans le prompt système en JSON et on parse
# la réponse nous-mêmes.
llm = ChatGroq(
    model=LLM_MODEL,
    temperature=LLM_TEMPERATURE,
    max_tokens=LLM_MAX_TOKENS,
    api_key=os.getenv("GROQ_API_KEY"),
)

# ── Prompt système ────────────────────────────────────────────────
_today = datetime.date.today().strftime("%d %B %Y")

SYSTEM_PROMPT = f"""Tu es un assistant juridique tunisien. Date: {_today}.

Pour répondre, tu peux appeler ces outils en écrivant exactement ce format JSON :
TOOL_CALL: {{"tool": "nom_outil", "input": "ta requête"}}

Outils disponibles :
- search_legal_docs : recherche dans les lois tunisiennes locales (appelle EN PREMIER)
- web_search_jort : recherche sur 9anoun.tn et le JORT (si search_legal_docs retourne CONFIANCE_FAIBLE)
- translate_legal_text : traduit arabe↔français (format: "fr|texte arabe" ou "ar|texte français")
- analyze_document : analyse un document juridique

Règles :
1. Appelle toujours search_legal_docs en premier
2. Si résultat contient CONFIANCE_FAIBLE → appelle web_search_jort
3. Si [DOCUMENT JOINT] dans le message → appelle analyze_document en premier
4. Si question en arabe → appelle translate_legal_text après la recherche
5. Cite toujours la source exacte
6. Réponds en français sauf si l'utilisateur écrit en arabe
7. Tu n'es pas avocat, tes réponses sont informatives uniquement

Quand tu as toutes les informations, réponds directement sans TOOL_CALL."""

# ── Mémoire manuelle ─────────────────────────────────────────────
_histories: dict[str, list] = {}
MAX_HISTORY_EXCHANGES = 2


def _get_messages(thread_id: str, question: str) -> list:
    history = _histories.get(thread_id, [])
    trimmed = history[-(MAX_HISTORY_EXCHANGES * 2):]
    return [SystemMessage(content=SYSTEM_PROMPT)] + trimmed + [HumanMessage(content=question)]


def _save_exchange(thread_id: str, question: str, answer: str) -> None:
    if thread_id not in _histories:
        _histories[thread_id] = []
    _histories[thread_id].append(HumanMessage(content=question))
    _histories[thread_id].append(AIMessage(content=answer))


# ── Parser d'appel d'outil ────────────────────────────────────────
def _parse_tool_call(text: str):
    """Extrait TOOL_CALL: {...} du texte généré par le LLM."""
    match = re.search(r'TOOL_CALL:\s*(\{.*?\})', text, re.DOTALL)
    if not match:
        return None, None
    try:
        data = json.loads(match.group(1))
        return data.get("tool"), data.get("input", "")
    except json.JSONDecodeError:
        return None, None


# ── Boucle ReAct manuelle ─────────────────────────────────────────
def _run_agent_loop(messages: list) -> str:
    for _ in range(AGENT_MAX_ITERATIONS):
        response = llm.invoke(messages)
        text = response.content

        tool_name, tool_input = _parse_tool_call(text)

        # Pas d'appel d'outil → réponse finale
        if not tool_name:
            return text

        # Appel d'outil reconnu
        if tool_name in tools_by_name:
            print(f"  🔧 Outil: {tool_name}({tool_input[:60]}...)")
            try:
                result = tools_by_name[tool_name].invoke(tool_input)
            except Exception as e:
                result = f"Erreur outil {tool_name}: {str(e)}"
        else:
            result = f"Outil inconnu: {tool_name}"

        # Ajoute l'échange outil dans les messages
        messages.append(AIMessage(content=text))
        messages.append(HumanMessage(content=f"Résultat de {tool_name}:\n{result}"))

    return messages[-1].content


# ── Fonction principale ───────────────────────────────────────────
def ask_agent(question: str, thread_id: str = "default") -> str:
    try:
        messages = _get_messages(thread_id, question)
        answer = _run_agent_loop(messages)
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