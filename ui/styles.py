"""Identité visuelle de l'assistant documentaire, sans ressources externes."""

import streamlit as st

CSS = """
<style>
:root {
    --paper: #f7f8f4;
    --ink: #203d36;
    --muted: #66776f;
    --green: #256650;
    --line: #dce3da;
}
.stApp { background: var(--paper); color: var(--ink); }
header[data-testid="stHeader"] { background: transparent; }
.stMainBlockContainer, .block-container {
    max-width: 1100px; padding: 3.5rem 3.2rem 3rem;
}
[data-testid="stMain"] [data-testid="stVerticalBlock"] { gap: 1rem; }
[data-testid="stSidebar"] {
    background: #173e35; border-right: 0; color: #f4f7ef;
}
[data-testid="stSidebarContent"] { padding-top: 1rem; }
[data-testid="stSidebar"] [data-testid="stSidebarUserContent"] { padding: 1rem 1.4rem 2rem; }
[data-testid="stSidebar"] [data-testid="stMarkdownContainer"],
[data-testid="stSidebar"] [data-testid="stCaptionContainer"] { color: #c1d1c6; }
[data-testid="stSidebar"] button { color: #f2f6ed; }
.brand { display: flex; align-items: center; gap: 12px; margin: 0 0 1.7rem; }
.brand-monogram {
    width: 44px; height: 44px; border: 1px solid #789084; border-radius: 12px;
    display: grid; place-items: center; color: #e3edc7; font: 24px Georgia, serif;
}
.brand strong { color: #fff; font-size: 1.18rem; letter-spacing: .06em; }
.brand small { display: block; color: #b2c7ba; font-size: .74rem; margin-top: 2px; }
.sidebar-label {
    color: #b1c7b9; font-size: .66rem; font-weight: 650; letter-spacing: .13em;
    text-transform: uppercase; margin: 1.8rem 0 .75rem;
}
.library-card { border-top: 1px solid #466356; border-bottom: 1px solid #466356; padding: 1.2rem 0; }
.library-number { color: #eef3dc; font: 42px Georgia, serif; line-height: 1.15; }
.library-number span { font: 13px 'Segoe UI', sans-serif; color: #c1d1c6; margin-left: 9px; }
.library-status { display: flex; align-items: center; gap: 7px; color: #c1d1c6; font-size: .76rem; margin-top: 10px; }
.status-dot { width: 6px; height: 6px; border-radius: 50%; background: #b9d89b; display: inline-block; }
.status-dot.waiting { background: #e3bf82; }
.sidebar-footer { margin-top: 2rem; padding-top: 1.2rem; border-top: 1px solid #466356; }
.sidebar-footer strong { color: #e5edde; font-size: .78rem; font-weight: 500; }
.sidebar-footer p { color: #b2c7ba; font-size: .73rem; line-height: 1.6; margin: .4rem 0; }
[data-testid="stSidebar"] .stButton button {
    background: transparent; border: 1px solid #627f6e; border-radius: 9px;
    padding: .65rem .85rem; justify-content: flex-start; box-shadow: none;
}
[data-testid="stSidebar"] .stButton button:hover { background: #254f42; border-color: #abc497; color: #fff; }
[data-testid="stSidebar"] .stButton button[kind="primary"] {
    background: #e2ebcd; border-color: #e2ebcd; color: #173e35;
}
[data-testid="stSidebar"] .stButton button[kind="primary"]:hover { background: #f0f4df; }
[data-testid="stSidebar"] .stButton button:disabled { opacity: .5; }
[data-testid="stSidebar"] [data-testid="stExpander"] details { border: none; background: transparent; }
[data-testid="stSidebar"] [data-testid="stExpander"] summary { color: #e2edde; padding-left: 0; font-size: .83rem; }
[data-testid="stSidebar"] [data-testid="stExpanderDetails"] { padding: .5rem 0; }
[data-testid="stSidebar"] [data-baseweb="input"] { background: #21483d; color: #f4f7ef; border-color: #627f6e; }
[data-testid="stSidebar"] input { color: #fff; -webkit-text-fill-color: #fff; }
[data-testid="stSidebar"] input::placeholder { color: #b9cbbb; -webkit-text-fill-color: #b9cbbb; }
.pdf-item { display: flex; gap: 9px; align-items: flex-start; padding: 9px 0; border-bottom: 1px solid #34574a; font-size: .76rem; color: #d4e0d5; }
.pdf-item b { flex-shrink: 0; font-size: .58rem; letter-spacing: .03em; color: #e2ebcd; border: 1px solid #627f6e; padding: 3px 4px; border-radius: 4px; }
.pdf-item span { overflow-wrap: anywhere; }
.topbar { display: flex; align-items: center; justify-content: space-between; gap: 1rem; padding: .25rem 0 1.2rem; border-bottom: 1px solid var(--line); }
.breadcrumb { color: var(--muted); font-size: .76rem; }
.breadcrumb span { color: #a5b2a6; margin: 0 .65rem; }
.breadcrumb strong { color: var(--ink); font-weight: 550; }
.language-tag { font-size: .7rem; color: #4f695b; white-space: nowrap; border: 1px solid var(--line); border-radius: 30px; padding: 5px 11px; }
.welcome { padding: 2.8rem 0 .9rem; max-width: 790px; margin: auto; text-align: center; }
.document-mark { margin: 0 auto 1.3rem; width: 62px; height: 62px; display: grid; place-items: center; background: #e8eddf; border: 1px solid #dce4d1; border-radius: 19px; transform: rotate(-5deg); }
.document-mark svg { width: 33px; height: 33px; transform: rotate(5deg); }
.eyebrow { color: #607561; font-size: .65rem; letter-spacing: .16em; font-weight: 650; text-transform: uppercase; margin-bottom: 1rem; }
.welcome h1 { font: 400 clamp(2.3rem, 4vw, 3.5rem)/1.12 Georgia, 'Times New Roman', serif; color: #243e33; letter-spacing: -.04em; padding: 0; margin: 0 0 1.25rem; }
.welcome h1 em { color: #497351; font-weight: 400; }
.welcome p { color: var(--muted); font-size: .93rem; line-height: 1.8; max-width: 510px; margin: 0 auto; }
.welcome .arabic-intro { margin-top: .8rem; font-size: 1.05rem; color: #58715c; }
.suggestion-label { text-align: center; color: #6a7a6c; font-size: .7rem; margin: 1.15rem 0 .1rem; }
.st-key-suggestions .stButton button {
    background: #fff; border: 1px solid var(--line); color: #2d4739; border-radius: 12px;
    min-height: 118px; padding: 1.1rem; width: 100%; text-align: left; justify-content: flex-start;
    align-items: flex-start; transition: border-color .16s, background .16s, transform .16s;
}
.st-key-suggestions .stButton button p { font-size: .78rem; line-height: 1.55; }
.st-key-suggestions .stButton button strong { font-weight: 600; font-size: .88rem; display: block; margin-bottom: .35rem; }
.st-key-suggestions .stButton button:hover { border-color: #729674; background: #f0f4e9; transform: translateY(-2px); }
.st-key-suggestions .stButton button:disabled { opacity: .55; }
.reading-note { display: flex; align-items: center; justify-content: center; gap: .5rem; color: #6c7c6e; font-size: .71rem; padding: .7rem 0 1rem; text-align: center; }
.reading-note span { color: #849579; }
.conversation-heading { display: flex; justify-content: space-between; align-items: baseline; padding: 1.3rem 0 .6rem; }
.conversation-heading h1 { font: 30px Georgia, serif; padding: 0; color: var(--ink); }
.conversation-heading span { color: var(--muted); font-size: .75rem; }
[data-testid="stChatMessage"] { background: transparent; padding: .75rem 0 1rem; gap: .8rem; }
[data-testid="stChatMessageContent"] { min-width: 0; }
[data-testid="stChatMessageAvatarUser"] { background: #e4e9de; color: #42614a; }
[data-testid="stChatMessageAvatarAssistant"] { background: #245440; color: #ecf1df; }
.message-author { font-size: .69rem; text-transform: uppercase; letter-spacing: .08em; color: #687e6c; margin: .35rem 0 .7rem; font-weight: 600; }
.chat-bubble { unicode-bidi: plaintext; overflow-wrap: anywhere; text-align: start; font-size: .94rem; line-height: 1.85; }
.chat-bubble.user { background: #e9eddf; color: #2b4937; border-radius: 0 13px 13px 13px; display: inline-block; padding: .8rem 1.1rem; }
.st-key-conversation [data-testid="stMarkdownContainer"] p,
.st-key-conversation [data-testid="stMarkdownContainer"] li { unicode-bidi: plaintext; line-height: 1.85; }
.st-key-conversation [data-testid="stExpander"] details { background: #fff; border: 1px solid var(--line); border-radius: 10px; margin-top: .65rem; }
.st-key-conversation [data-testid="stExpander"] summary { font-size: .78rem; color: #54705a; }
.source-card { padding: .8rem 0; border-bottom: 1px solid #e8ece3; }
.source-card:last-child { border-bottom: 0; }
.source-heading { display: flex; align-items: center; gap: .65rem; color: #39533e; font-size: .76rem; }
.source-number { border: 1px solid #d4dec9; background: #edf2e5; border-radius: 5px; padding: 2px 7px; font-size: .67rem; }
.source-heading strong { overflow-wrap: anywhere; font-weight: 550; }
.source-page { white-space: nowrap; color: #6c7c6e; margin-left: auto; }
.source-card p { margin: .7rem 0 0; color: #68766a; font-size: .8rem; line-height: 1.7; }
[data-testid="stBottom"] { background: var(--paper); }
[data-testid="stBottomBlockContainer"] { max-width: 1100px; padding: 1rem 3.2rem 1.5rem; }
[data-testid="stChatInput"] { background: #fff; border: 1px solid #bdcbb7; border-radius: 14px; box-shadow: 0 5px 22px #23453209; }
[data-testid="stChatInput"]:focus-within { border-color: #497c54; box-shadow: 0 0 0 3px #497c5415; }
[data-testid="stChatInput"] textarea { color: #253f32; font-size: .92rem; unicode-bidi: plaintext; }
[data-testid="stChatInputSubmitButton"] { background: #245440; color: #f1f5e9; border-radius: 9px; }
.stButton button:focus-visible, button:focus-visible { outline: 3px solid #94ad76; outline-offset: 3px; }
[data-testid="stAlert"] { border-radius: 10px; font-size: .84rem; }
@media (max-width: 900px) {
    .stMainBlockContainer, .block-container { padding: 3.5rem 1.5rem 2rem; }
    [data-testid="stBottomBlockContainer"] { padding: .75rem 1.5rem 1rem; }
    .welcome { padding-top: 2rem; }
    .st-key-suggestions .stButton button { padding: .85rem; }
}
@media (max-width: 640px) {
    .stMainBlockContainer, .block-container { padding: 2.9rem 1rem 1rem; }
    [data-testid="stBottomBlockContainer"] { padding: .6rem 1rem 1rem; }
    .topbar { gap: .5rem; }
    .breadcrumb { font-size: .69rem; }
    .breadcrumb span { margin: 0 .25rem; }
    .language-tag { font-size: .63rem; padding: 4px 7px; }
    .welcome { padding-top: 1.5rem; }
    .welcome h1 { font-size: 2.3rem; }
    .welcome p { font-size: .86rem; }
    .document-mark { width: 49px; height: 49px; margin-bottom: 1rem; }
    .st-key-suggestions [data-testid="stHorizontalBlock"] { flex-direction: column; gap: .6rem; }
    .st-key-suggestions [data-testid="stColumn"] { width: 100%; flex: 1 1 100%; min-width: 0; }
    .st-key-suggestions .stButton button { min-height: 78px; padding: .8rem 1rem; }
    .source-heading { flex-wrap: wrap; }
}
@media (prefers-reduced-motion: reduce) {
    .st-key-suggestions .stButton button { transition: none; }
    .st-key-suggestions .stButton button:hover { transform: none; }
}
</style>
"""


def injecter_styles() -> None:
    st.markdown(CSS, unsafe_allow_html=True)
