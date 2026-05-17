"""
gradio_app.py - Interface web de l'Assistant Juridique Tunisien (Wakili)
Version améliorée — thème sombre navy/gold, UX optimisée
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import gradio as gr
import fitz
import uuid
from agent import ask_agent


# ─── CSS personnalisé ────────────────────────────────────────────────────────

CUSTOM_CSS = """
/* ── Variables de couleur Wakili ── */
:root {
    --navy:      #0D1B3E;
    --navy-mid:  #162444;
    --navy-soft: #1E2F55;
    --gold:      #C9A84C;
    --gold-pale: #F0E6C8;
    --white:     #FFFFFF;
    --gray-100:  #F5F5F5;
    --gray-300:  #CCCCCC;
    --gray-600:  #666666;
    --red-risk:  #D32F2F;
    --green:     #2E7D32;
}

/* ── Corps général ── */
body, .gradio-container {
    background: var(--navy) !important;
    font-family: 'Segoe UI', Arial, sans-serif !important;
}

/* ── En-tête principal ── */
#wakili-header {
    background: linear-gradient(135deg, var(--navy) 0%, var(--navy-soft) 100%);
    border-bottom: 3px solid var(--gold);
    padding: 20px 28px 16px;
    border-radius: 12px 12px 0 0;
    margin-bottom: 4px;
}
#wakili-header h1 {
    color: var(--white) !important;
    font-size: 2rem !important;
    font-weight: 800 !important;
    letter-spacing: 1px;
    margin: 0 0 4px !important;
}
#wakili-header .subtitle {
    color: var(--gold-pale);
    font-size: 0.9rem;
    margin: 0;
}
#wakili-header .warning-badge {
    display: inline-block;
    background: rgba(201,168,76,0.15);
    border: 1px solid var(--gold);
    color: var(--gold);
    border-radius: 20px;
    padding: 3px 12px;
    font-size: 0.78rem;
    margin-top: 8px;
}

/* ── Zone de chat ── */
#chatbox {
    background: var(--navy-mid) !important;
    border: 1px solid var(--navy-soft) !important;
    border-radius: 10px !important;
}
#chatbox .message.user {
    background: var(--gold) !important;
    color: var(--navy) !important;
    font-weight: 600;
    border-radius: 18px 18px 4px 18px !important;
    margin-left: 15% !important;
}
#chatbox .message.bot {
    background: var(--navy-soft) !important;
    color: var(--white) !important;
    border: 1px solid rgba(201,168,76,0.3) !important;
    border-radius: 18px 18px 18px 4px !important;
    margin-right: 10% !important;
}

/* ── Champ de saisie ── */
#msg-input textarea {
    background: var(--navy-soft) !important;
    color: var(--white) !important;
    border: 2px solid var(--navy-soft) !important;
    border-radius: 10px !important;
    font-size: 0.95rem !important;
    transition: border-color 0.2s;
}
#msg-input textarea:focus {
    border-color: var(--gold) !important;
    outline: none !important;
    box-shadow: 0 0 0 3px rgba(201,168,76,0.2) !important;
}
#msg-input textarea::placeholder { color: var(--gray-600) !important; }
#msg-input label { color: var(--gold) !important; font-weight: 600 !important; }

/* ── Bouton Envoyer ── */
#send-btn {
    background: linear-gradient(135deg, var(--gold) 0%, #a8832e 100%) !important;
    color: var(--navy) !important;
    font-weight: 800 !important;
    font-size: 1rem !important;
    border: none !important;
    border-radius: 10px !important;
    height: 46px !important;
    letter-spacing: 0.5px;
    transition: opacity 0.2s, transform 0.1s;
}
#send-btn:hover  { opacity: 0.9; transform: translateY(-1px); }
#send-btn:active { transform: translateY(0); }

/* ── Bouton Nouvelle conversation ── */
#clear-btn {
    background: transparent !important;
    color: var(--gray-300) !important;
    border: 1px solid var(--navy-soft) !important;
    border-radius: 10px !important;
    height: 46px !important;
    transition: border-color 0.2s, color 0.2s;
}
#clear-btn:hover {
    border-color: var(--red-risk) !important;
    color: var(--red-risk) !important;
}

/* ── Panneau latéral ── */
#sidebar {
    background: var(--navy-mid) !important;
    border: 1px solid var(--navy-soft) !important;
    border-radius: 10px !important;
    padding: 16px !important;
}

/* ── Section titre panneau ── */
.panel-title {
    color: var(--gold) !important;
    font-size: 0.8rem !important;
    font-weight: 700 !important;
    letter-spacing: 1.5px !important;
    text-transform: uppercase !important;
    margin: 0 0 10px !important;
    padding-bottom: 6px !important;
    border-bottom: 1px solid rgba(201,168,76,0.3) !important;
}

/* ── Upload PDF ── */
#file-upload {
    background: var(--navy-soft) !important;
    border: 2px dashed rgba(201,168,76,0.4) !important;
    border-radius: 10px !important;
    color: var(--gray-300) !important;
    transition: border-color 0.2s;
}
#file-upload:hover { border-color: var(--gold) !important; }
#file-upload .upload-text { color: var(--gray-300) !important; }
#file-upload label { color: var(--gold) !important; font-size: 0.82rem !important; }

/* ── Badge PDF chargé ── */
#pdf-status {
    background: rgba(46,125,50,0.15);
    border: 1px solid var(--green);
    border-radius: 8px;
    color: #81C784;
    padding: 6px 12px;
    font-size: 0.82rem;
    text-align: center;
    display: none;
}

/* ── Boutons d'exemples ── */
.example-btn button {
    background: var(--navy-soft) !important;
    color: var(--gray-100) !important;
    border: 1px solid rgba(201,168,76,0.2) !important;
    border-radius: 8px !important;
    font-size: 0.8rem !important;
    text-align: left !important;
    padding: 8px 12px !important;
    transition: all 0.2s;
    white-space: normal !important;
    height: auto !important;
    line-height: 1.4 !important;
}
.example-btn button:hover {
    background: rgba(201,168,76,0.12) !important;
    border-color: var(--gold) !important;
    color: var(--white) !important;
}

/* ── Compteur de tokens ── */
#token-counter {
    color: var(--gray-600);
    font-size: 0.75rem;
    text-align: right;
    padding: 2px 6px;
}

/* ── Statut de traitement ── */
#status-bar {
    background: rgba(201,168,76,0.08);
    border-left: 3px solid var(--gold);
    border-radius: 0 6px 6px 0;
    color: var(--gold-pale);
    font-size: 0.82rem;
    padding: 6px 12px;
    margin-top: 4px;
    display: none;
}

/* ── Pied de page ── */
#footer {
    color: var(--gray-600);
    font-size: 0.72rem;
    text-align: center;
    padding: 10px 0 4px;
    border-top: 1px solid var(--navy-soft);
    margin-top: 8px;
}

/* ── Responsive mobile ── */
@media (max-width: 768px) {
    #wakili-header h1 { font-size: 1.4rem !important; }
    #chatbox { height: 350px !important; }
}
"""

# ─── Helpers ─────────────────────────────────────────────────────────────────

def extraire_texte_pdf(file_path: str) -> str:
    try:
        doc = fitz.open(file_path)
        texte = "".join(page.get_text() for page in doc)
        doc.close()
        return texte[:2000]
    except Exception as e:
        return f"[Erreur PDF : {str(e)}]"


def repondre(message, history, file, thread_id):
    """Envoie le message à l'agent et retourne la réponse."""
    if not message.strip():
        return "", history, file, thread_id, ""

    if file is not None:
        texte_doc = extraire_texte_pdf(file)
        prompt = (
            f"[DOCUMENT JOINT — utilise analyze_document uniquement, "
            f"ne pas appeler web_search_jort]\n{texte_doc}"
            f"\n\n[QUESTION]\n{message}"
        )
        status = "📄 Analyse du document en cours…"
    else:
        prompt = message
        status = "⚖️ Recherche juridique en cours…"

    try:
        reponse = ask_agent(prompt, thread_id=thread_id)
    except Exception as e:
        reponse = f"⚠️ Erreur : {str(e)}"

    new_history = history + [
        {"role": "user",      "content": message},
        {"role": "assistant", "content": reponse},
    ]
    return "", new_history, None, thread_id, ""


def nouvelle_conversation():
    return [], "", None, str(uuid.uuid4()), ""


def set_example(text):
    return text


# ─── Interface ───────────────────────────────────────────────────────────────

EXEMPLES = [
    "Quels sont mes droits en cas de licenciement ?",
    "Quel est le délai légal de préavis pour un CDI ?",
    "Mon employeur peut-il baisser mon salaire ?",
    "Combien de jours de congé annuel ai-je droit ?",
    "Quels sont mes droits si mon salaire n'est pas payé ?",
    "Analyse ce contrat de travail",
]

with gr.Blocks(
    title="Wakili — Assistant Juridique Tunisien",
    css=CUSTOM_CSS,
    theme=gr.themes.Base(
        primary_hue=gr.themes.colors.yellow,
        neutral_hue=gr.themes.colors.slate,
        font=gr.themes.GoogleFont("Inter"),
    ),
) as demo:

    thread_id = gr.State(value=str(uuid.uuid4()))

    # ── En-tête ──────────────────────────────────────────────────────────────
    gr.HTML("""
    <div id="wakili-header">
      <h1>⚖️ &nbsp;Wakili</h1>
      <p class="subtitle">L'Assistant Juridique Intelligent — Droit Tunisien</p>
      <span class="warning-badge">
        ⚠️ Informatif uniquement — consultez un avocat pour toute décision juridique
      </span>
    </div>
    """)

    # ── Layout principal ──────────────────────────────────────────────────────
    with gr.Row(equal_height=True):

        # Colonne chat (70 %)
        with gr.Column(scale=7):

            chatbot = gr.Chatbot(
                elem_id="chatbox",
                height=480,
                show_label=False,
                avatar_images=(None, "https://img.icons8.com/fluency/48/scales--v1.png"),
                #bubble_full_width=False,
                placeholder=(
                    "<div style='text-align:center; color:#666; padding:40px 20px;'>"
                    "<div style='font-size:2.5rem; margin-bottom:12px;'>⚖️</div>"
                    "<b style='color:#C9A84C;'>Bonjour ! Je suis Wakili.</b><br>"
                    "<span style='font-size:0.9rem;'>Posez votre question juridique ou uploadez un contrat PDF.</span>"
                    "</div>"
                ),
                #type="messages",
            )

            # Statut de traitement
            status_display = gr.Textbox(
                elem_id="status-bar",
                show_label=False,
                interactive=False,
                visible=False,
                max_lines=1,
            )

            with gr.Row():
                msg_input = gr.Textbox(
                    elem_id="msg-input",
                    placeholder="Posez votre question juridique… (Entrée pour envoyer)",
                    label="Votre question",
                    lines=2,
                    scale=5,
                    show_label=True,
                )

            with gr.Row():
                send_btn = gr.Button(
                    "Envoyer ▶",
                    elem_id="send-btn",
                    variant="primary",
                    scale=3,
                )
                clear_btn = gr.Button(
                    "🗑️ Nouvelle conversation",
                    elem_id="clear-btn",
                    scale=2,
                )

        # Colonne latérale (30 %)
        with gr.Column(scale=3, elem_id="sidebar"):

            gr.HTML('<p class="panel-title">📄 Document</p>')

            file_upload = gr.File(
                elem_id="file-upload",
                label="Glissez un PDF ici (contrat, mise en demeure…)",
                file_types=[".pdf"],
                type="filepath",
            )

            gr.HTML("""
            <div style="
                background: rgba(46,125,50,0.12);
                border: 1px solid #2E7D32;
                border-radius: 8px;
                color: #81C784;
                padding: 6px 12px;
                font-size: 0.8rem;
                margin-top: 4px;
                text-align: center;
            ">
                💡 L'agent détecte les clauses risquées automatiquement
            </div>
            """)

            gr.HTML('<p class="panel-title" style="margin-top:20px;">💡 Questions fréquentes</p>')

            for ex in EXEMPLES:
                gr.Button(ex, size="sm", elem_classes=["example-btn"]).click(
                    fn=set_example,
                    inputs=gr.State(ex),
                    outputs=msg_input,
                )

            gr.HTML("""
            <div id="footer">
                Wakili · TEK-UP 2025-2026<br>
                Droit tunisien · Code du Travail · Loi n° 66-27
            </div>
            """)

    # ── Événements ────────────────────────────────────────────────────────────

    demo.load(fn=lambda: str(uuid.uuid4()), outputs=[thread_id])

    send_btn.click(
        fn=repondre,
        inputs=[msg_input, chatbot, file_upload, thread_id],
        outputs=[msg_input, chatbot, file_upload, thread_id, status_display],
    )

    msg_input.submit(
        fn=repondre,
        inputs=[msg_input, chatbot, file_upload, thread_id],
        outputs=[msg_input, chatbot, file_upload, thread_id, status_display],
    )

    clear_btn.click(
        fn=nouvelle_conversation,
        outputs=[chatbot, msg_input, file_upload, thread_id, status_display],
    )


# ─── Lancement ───────────────────────────────────────────────────────────────

if __name__ == "__main__":
    demo.launch(
        server_name="0.0.0.0",
        server_port=7860,
        share=False,
        show_error=True,
    )