"""
gradio_app.py - Interface web de l'Assistant Juridique Tunisien
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import gradio as gr
import fitz
import uuid
from agent import ask_agent


def extraire_texte_pdf(file_path: str) -> str:
    try:
        doc = fitz.open(file_path)
        texte = "".join(page.get_text() for page in doc)
        doc.close()
        # FIX: increased from 3000 to 8000 chars.
        # 3000 chars ≈ 1.5 pages — most real contracts would be truncated
        # to the cover page only, making analyze_document nearly useless.
        # 8000 chars ≈ 5-6 pages, sufficient for most employment contracts.
        return texte[:8000]
    except Exception as e:
        return f"[Erreur PDF : {str(e)}]"


def repondre(message, history, file, thread_id):
    if not message.strip():
        return "", history, file, thread_id

    if file is not None:
        texte_doc = extraire_texte_pdf(file)
        prompt = f"[DOCUMENT JOINT]\n{texte_doc}\n\n[QUESTION]\n{message}"
    else:
        prompt = message

    try:
        reponse = ask_agent(prompt, thread_id=thread_id)
    except Exception as e:
        reponse = f"⚠️ Erreur : {str(e)}"

    try:
        new_history = history + [
            {"role": "user", "content": message},
            {"role": "assistant", "content": reponse}
        ]
        return "", new_history, None, thread_id
    except Exception:
        new_history = history + [(message, reponse)]
        return "", new_history, None, thread_id


def nouvelle_conversation():
    return [], "", None, str(uuid.uuid4())


with gr.Blocks(title="Assistant Juridique Tunisien") as demo:

    # FIX: gr.State(value=lambda: ...) does NOT call the lambda as a factory —
    # Gradio stores the lambda object itself as the state value, meaning every
    # user session gets the string representation of the lambda as their
    # thread_id and they all share the same agent memory context.
    # Fix: generate a real UUID string at startup. For true per-session
    # isolation in multi-user deployments, regenerate it in nouvelle_conversation
    # (already done) and on the page load event below.
    thread_id = gr.State(value=str(uuid.uuid4()))

    gr.Markdown("# 🏛️ Assistant Juridique Tunisien")
    gr.Markdown(
        "Posez vos questions sur le **droit tunisien** en français ou en arabe.\n\n"
        "⚠️ Informatif uniquement — consultez un avocat pour toute décision juridique."
    )

    with gr.Row():
        with gr.Column(scale=3):

            chatbot = gr.Chatbot(height=500)

            msg_input = gr.Textbox(
                placeholder="Écrivez votre question ici et appuyez sur Entrée...",
                label="Votre question",
                lines=2,
            )

            with gr.Row():
                send_btn = gr.Button("Envoyer ▶", variant="primary")
                clear_btn = gr.Button("🗑️ Nouvelle conversation")

        with gr.Column(scale=1):
            gr.Markdown("### 📄 Joindre un document")
            file_upload = gr.File(
                label="PDF (contrat, mise en demeure...)",
                file_types=[".pdf"],
                type="filepath"
            )

            gr.Markdown("### 💡 Exemples")
            examples = [
                "Quels sont mes droits en cas de licenciement ?",
                "Quel est le délai légal de préavis pour un CDI ?",
                "Mon employeur peut-il baisser mon salaire ?",
                "Combien de jours de congé annuel ai-je droit ?",
                "Quels sont mes droits si mon salaire n'est pas payé ?",
            ]
            for ex in examples:
                gr.Button(ex, size="sm").click(
                    fn=lambda x=ex: x,
                    outputs=msg_input
                )

    # FIX: generate a fresh UUID for each new browser session so that
    # concurrent users don't share the same LangGraph memory thread.
    demo.load(
        fn=lambda: str(uuid.uuid4()),
        outputs=[thread_id]
    )

    send_btn.click(
        fn=repondre,
        inputs=[msg_input, chatbot, file_upload, thread_id],
        outputs=[msg_input, chatbot, file_upload, thread_id],
    )

    msg_input.submit(
        fn=repondre,
        inputs=[msg_input, chatbot, file_upload, thread_id],
        outputs=[msg_input, chatbot, file_upload, thread_id],
    )

    clear_btn.click(
        fn=nouvelle_conversation,
        outputs=[chatbot, msg_input, file_upload, thread_id],
    )


if __name__ == "__main__":
    demo.launch(
        server_name="0.0.0.0",
        server_port=7860,
        share=False,
        show_error=True,
    )
