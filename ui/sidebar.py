"""Navigation et bibliothèque documentaire."""

import logging
from html import escape

import streamlit as st

from config import PDF_DIR
from rag.pdf_loader import lister_pdfs
from rag.vectorstore import obtenir_base, synchroniser_base

DEFAULT_TOP_K = 4
DEFAULT_STYLE = "Concis"


def afficher_sidebar() -> tuple[int, str]:
    with st.sidebar:
        st.markdown('''<div class="brand"><div class="brand-monogram" aria-hidden="true">D.</div><div><strong>DSIT</strong><small>Province de Berkane</small></div></div>''', unsafe_allow_html=True)
        if st.button("Nouvelle conversation", icon=":material/add:", use_container_width=True,
                     disabled=not bool(st.session_state.get("history"))):
            st.session_state.history = []
            st.rerun()

        try:
            st.session_state.db = obtenir_base()
        except Exception:
            logging.getLogger(__name__).exception("Chargement de la base impossible")
            st.session_state.db = None
            st.error("Impossible de charger la base. Consultez les journaux de l'application.")

        db = st.session_state.get("db")
        pdfs = lister_pdfs() if PDF_DIR.exists() else []
        status = "Base connectée" if db is not None else "En attente d'indexation"
        dot = "" if db is not None else " waiting"
        st.markdown(f'''<div class="sidebar-label">Votre bibliothèque</div><div class="library-card"><div class="library-number">{len(pdfs):02d}<span>PDF dans le dossier</span></div><div class="library-status"><span class="status-dot{dot}"></span>{status}</div></div>''', unsafe_allow_html=True)

        with st.expander("Parcourir les documents", icon=":material/folder_open:"):
            if pdfs:
                search = st.text_input("Rechercher un document", placeholder="Nom du document…", label_visibility="collapsed")
                matches = [p for p in pdfs if search.casefold() in p.casefold()]
                if not matches:
                    st.caption("Aucun document ne correspond à votre recherche.")
                for name in matches:
                    st.markdown(f'<div class="pdf-item"><b>PDF</b><span>{escape(name)}</span></div>', unsafe_allow_html=True)
            else:
                st.caption("Ajoutez vos courriers dans le dossier pdfs/ pour commencer.")

        st.markdown('<div class="sidebar-label">Gestion des documents</div>', unsafe_allow_html=True)
        if st.button("Mettre à jour la base", icon=":material/sync:", use_container_width=True, type="primary"):
            with st.spinner("Synchronisation des documents…"):
                try:
                    result = synchroniser_base()
                except Exception as exc:
                    logging.getLogger(__name__).exception("Synchronisation impossible")
                    st.error(f"Mise à jour interrompue : {exc}")
                else:
                    st.session_state.db = result
                    st.session_state.history = []
                    st.session_state["index_updated"] = True
                    st.rerun()
        if st.session_state.pop("index_updated", False):
            st.success("Base documentaire à jour.")
        st.caption("Après un ajout ou une modification de vos PDF, actualisez la bibliothèque.")

        st.markdown('''<div class="sidebar-footer"><strong>Du document à l'information.</strong><p>Consultez les extraits associés aux réponses pour retrouver leur contexte.</p><p lang="ar" dir="rtl">المعلومة أقرب إليك.</p></div>''', unsafe_allow_html=True)
    return DEFAULT_TOP_K, DEFAULT_STYLE
