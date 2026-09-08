"""Point d'entrée : python -m streamlit run app.py."""

import logging
import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parent / ".env")

import streamlit as st

from rag.qa_engine import poser_question, memoriser_echange, message_erreur
from ui.chat import afficher_etat_vide, afficher_historique
from ui.sidebar import afficher_sidebar
from ui.styles import injecter_styles


def main() -> None:
    st.set_page_config(page_title="DSIT · Assistant documentaire", page_icon=":material/auto_stories:", layout="wide")
    injecter_styles()
    st.session_state.setdefault("history", [])
    top_k, style = afficher_sidebar()
    st.markdown('''<div class="topbar"><div class="breadcrumb">Espace documentaire<span>/</span><strong>Assistant</strong></div><div class="language-tag">Français &nbsp;·&nbsp; <span lang="ar">العربية</span></div></div>''', unsafe_allow_html=True)

    db = st.session_state.get("db")
    try:
        ready = db is not None and bool(db.get(limit=1, include=[])["ids"])
    except Exception:
        logging.getLogger(__name__).exception("Lecture de la base impossible")
        ready = False
        st.error("La base documentaire est indisponible. Relancez l'application ou mettez la base à jour.")
    has_key = bool(os.getenv("GROQ_API_KEY", "").strip())
    if st.session_state.history:
        afficher_historique()
    else:
        afficher_etat_vide(disabled=not ready or not has_key)
    if not ready:
        st.info("Ajoutez vos PDF dans le dossier pdfs/, puis cliquez sur « Mettre à jour la base ».")
    if not has_key:
        st.warning("Configurez GROQ_API_KEY dans le fichier .env, puis relancez l'application.")
    question = st.chat_input("Posez votre question sur les courriers… / اطرح سؤالك", key="chat_prompt", disabled=not ready or not has_key, max_chars=2000)
    if question and question.strip():
        try:
            with st.spinner("Recherche dans les courriers…"):
                answer, sources = poser_question(db, question, top_k, style, st.session_state.history)
            memoriser_echange(question, answer, sources)
        except Exception as exc:
            logging.getLogger(__name__).exception("Échec de la question documentaire")
            st.error(message_erreur(exc))
        else:
            st.rerun()


if __name__ == "__main__":
    main()
