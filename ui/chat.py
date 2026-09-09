"""Accueil, conversation et extraits documentaires."""

from html import escape
from typing import Any

import streamlit as st


def _html_texte(texte: Any) -> str:
    return escape(str(texte or "")).replace("\n", "<br>")


def _page_affichee(page: Any) -> str:
    return str(page + 1) if isinstance(page, int) else str(page or "?")


def afficher_etat_vide(disabled: bool = False) -> None:
    st.markdown("""
        <div class="welcome">
            <div class="document-mark" aria-hidden="true">
                <svg viewBox="0 0 40 40" fill="none" stroke="#436b48" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round">
                    <path d="M12 7H27L33 13V32H12Z"/><path d="M27 7V14H33M7 12V36H26M17 20H27M17 25H25"/>
                </svg>
            </div>
            <div class="eyebrow">Votre assistant documentaire</div>
            <h1>Chaque courrier.<br><em>Une réponse claire.</em></h1>
            <p>Retrouvez l'information dans vos courriers administratifs.<br>Posez une question, puis explorez les extraits associés.</p>
            <p class="arabic-intro" lang="ar" dir="rtl">اسأل عن مراسلاتك، بالعربية أو بالفرنسية.</p>
        </div>
        <div class="suggestion-label">UN POINT DE DÉPART POUR VOTRE RECHERCHE</div>
    """, unsafe_allow_html=True)
    examples = [
        ("Retrouver une information", "Rechercher un objet ou une date", "Quels courriers mentionnent une réunion ?", ":material/search:"),
        ("Comprendre un courrier", "Identifier les points essentiels", "Quels sont les points essentiels du courrier concernant la réunion ?", ":material/subject:"),
        ("Poser une question en arabe", "البحث في المراسلات الإدارية", "ما هي المراسلات المتعلقة بالاجتماعات؟", ":material/translate:"),
    ]
    with st.container(key="suggestions"):
        columns = st.columns(3, gap="small")
        for i, (title, description, question, icon) in enumerate(examples):
            with columns[i]:
                if st.button(f"**{title}**\n\n{description}", icon=icon, key=f"example_{i}",
                             use_container_width=True, disabled=disabled,
                             help="Préremplir la question ; vous pourrez la modifier avant de l'envoyer."):
                    st.session_state["chat_prompt"] = question
    st.markdown('<div class="reading-note"><span>↳</span> Les exemples préremplissent votre question. Vous gardez la main.</div>', unsafe_allow_html=True)


def afficher_historique() -> None:
    history = st.session_state.history
    label = "échange" if len(history) == 1 else "échanges"
    st.markdown(f'<div class="conversation-heading"><h1>Votre conversation</h1><span>{len(history)} {label}</span></div>', unsafe_allow_html=True)
    with st.container(key="conversation"):
        for exchange in history:
            with st.chat_message("user", avatar=":material/person:"):
                st.markdown('<div class="message-author">Vous</div>', unsafe_allow_html=True)
                st.markdown(f'<div class="chat-bubble user" dir="auto">{_html_texte(exchange.get("question"))}</div>', unsafe_allow_html=True)
            with st.chat_message("assistant", avatar=":material/auto_stories:"):
                st.markdown('<div class="message-author">Assistant DSIT</div>', unsafe_allow_html=True)
                # Le rendu Markdown conserve listes et emphases ; le HTML du modèle est désactivé.
                st.markdown(str(exchange.get("reponse", "")), unsafe_allow_html=False)
                sources = exchange.get("sources", [])
                source_label = f"{len(sources)} extrait{'s' if len(sources) != 1 else ''} documentaire{'s' if len(sources) != 1 else ''}"
                if sources:
                    with st.expander(source_label, icon=":material/library_books:", expanded=False):
                        for number, src in enumerate(sources, 1):
                            file = escape(str(src.get("fichier", "?")))
                            page = escape(_page_affichee(src.get("page", "?")))
                            text = _html_texte(str(src.get("extrait", "") or "")[:300])
                            st.markdown(f'<div class="source-card"><div class="source-heading"><span class="source-number">{number}</span><strong>{file}</strong><span class="source-page">Page {page}</span></div><p dir="auto">{text}</p></div>', unsafe_allow_html=True)
                else:
                    st.caption("Aucun extrait documentaire associé.")
