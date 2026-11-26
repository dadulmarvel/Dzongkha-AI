import html
import os

import pandas as pd
import streamlit as st
from docx import Document
from pypdf import PdfReader

from translator import MODEL, glossary, save_correction, translate

st.set_page_config(page_title="Bhutanese Dzongkha", page_icon="🐉", layout="wide")

MAX_CHARS = 2000

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=Noto+Serif+Tibetan:wght@400;600&display=swap');
html, body, [class*="css"] { font-family: 'Inter', sans-serif; }
#MainMenu, footer { visibility: hidden; }
.block-container { padding-top: 2rem; max-width: 1200px; }

.hero { padding: 30px 34px; border-radius: 18px; margin-bottom: 24px; color: #fff;
        background: linear-gradient(135deg, #B45309 0%, #D97706 55%, #F59E0B 100%); }
.hero h1 { margin: 4px 0 0; font-size: 40px; font-weight: 700; color: #fff; }
.hero p { margin: 8px 0 0; font-size: 16px; opacity: .95; }
.hero-dz { font-family: 'Noto Serif Tibetan','Jomolhari','Microsoft Himalaya',serif;
           font-size: 20px; opacity: .95; }

.page-title { font-size: 30px; font-weight: 700; margin-bottom: 2px; }
.page-sub { opacity: .7; margin-bottom: 18px; }
.field-label { font-size: 12px; font-weight: 600; letter-spacing: .06em;
               text-transform: uppercase; opacity: .65; margin-bottom: 6px; }

.card { border: 1px solid rgba(128,128,128,.30); border-radius: 14px; overflow: hidden;
        background: rgba(128,128,128,.04); margin-bottom: 10px; }
.card-head { padding: 9px 16px; font-size: 12px; font-weight: 700; letter-spacing: .06em;
             text-transform: uppercase; color: #B45309; background: rgba(180,83,9,.08);
             border-bottom: 1px solid rgba(128,128,128,.20); }
.card-body { padding: 16px 18px; min-height: 200px; line-height: 1.7; }
.card-body.dz { font-family: 'Noto Serif Tibetan','Jomolhari','Microsoft Himalaya',serif;
                font-size: 26px; line-height: 2.2; }
.card-body.en { font-size: 18px; }
.card-body.compact { min-height: 0; padding: 12px 16px; }
.card-body.empty { opacity: .45; font-style: italic; }
.card-foot { padding: 7px 16px; font-size: 12px; opacity: .6;
             border-top: 1px solid rgba(128,128,128,.20); }

.brand { font-size: 22px; font-weight: 700; margin-bottom: 2px; }
.tool-title { font-weight: 700; font-size: 18px; margin: 0; }
.tool-desc { opacity: .7; font-size: 14px; margin: 2px 0 8px; }
.footer { text-align: center; font-size: 12.5px; opacity: .6; padding: 10px 0 2px; }

.ai-head { display: flex; align-items: center; gap: 14px; padding: 18px 22px;
           border-radius: 16px; margin-bottom: 14px; border: 1px solid rgba(128,128,128,.28);
           background: linear-gradient(135deg, rgba(180,83,9,.10), rgba(245,158,11,.10)); }
.ai-icon { width: 46px; height: 46px; border-radius: 14px; display: flex; align-items: center;
           justify-content: center; font-size: 24px;
           background: linear-gradient(135deg, #B45309, #F59E0B); }
.ai-title { font-size: 22px; font-weight: 700; line-height: 1.2; }
.ai-sub { font-size: 13.5px; opacity: .7; }
.ai-pill { margin-left: auto; font-size: 12px; font-weight: 600; padding: 5px 12px;
           border-radius: 999px; color: #B45309; background: rgba(180,83,9,.12); }
.ai-welcome { text-align: center; padding: 34px 10px 18px; }
.ai-welcome-icon { font-size: 46px; }
.ai-welcome h3 { margin: 6px 0 4px; font-size: 26px; }
.ai-welcome p { opacity: .7; margin: 0 0 18px; }
[data-testid="stChatMessage"] { border: 1px solid rgba(128,128,128,.20); border-radius: 14px;
                                padding: 12px 14px; background: rgba(128,128,128,.04); }
[data-testid="stChatInput"] { border-radius: 14px; }
</style>""", unsafe_allow_html=True)


# ---------- per-visitor storage (resets on refresh) ----------
def load_json(name):
    return st.session_state.setdefault(f"store_{name}", [])


def save_json(name, obj):
    st.session_state[f"store_{name}"] = obj


def log_history(src, out, direction):
    h = load_json("history")
    h.append({"src": src, "out": out, "dir": direction})
    save_json("history", h[-300:])


def save_item(src, out, direction):
    s = load_json("saved")
    s.append({"src": src, "out": out, "dir": direction})
    save_json("saved", s)


# ---------- display helpers ----------
def page_title(title, subtitle=""):
    st.markdown(f'<div class="page-title">{title}</div><div class="page-sub">{subtitle}</div>',
                unsafe_allow_html=True)


def result_card(text, lang="dz", label=None, placeholder="Your translation will appear here",
                compact=False):
    label = label or ("རྫོང་ཁ། · Dzongkha" if lang == "dz" else "English")
    cls = f"card-body {lang}" + (" compact" if compact else "")
    if text:
        body = html.escape(text).replace("\n", "<br>")
        foot = f'<div class="card-foot">{len(text)} characters</div>'
        st.markdown(f'<div class="card"><div class="card-head">{label}</div>'
                    f'<div class="{cls}">{body}</div>{foot}</div>', unsafe_allow_html=True)
    else:
        st.markdown(f'<div class="card"><div class="card-head">{label}</div>'
                    f'<div class="{cls} empty">{html.escape(placeholder)}</div></div>',
                    unsafe_allow_html=True)


def copy_box(text):
    try:
        st.code(text, language=None, wrap_lines=True)
    except TypeError:
        st.code(text, language=None)


def result_actions(text, key, filename="translation.txt"):
    if not text:
        return
    a, b = st.columns(2)
    a.download_button("⬇ Download .txt", text.encode("utf-8"), file_name=filename,
                      key=f"dl_{key}", use_container_width=True)
    with b.popover("📋 Copy", use_container_width=True):
        st.caption("Use the copy icon at the top-right of the box.")
        copy_box(text)


# ---------- navigation ----------
DIRS = {"English → Dzongkha": "en2dz", "Dzongkha → English": "dz2en"}
PAGES = ["Home", "Text", "AI assistant", "Files",
         "Phrasebook", "Dictionary", "History", "Saved"]
ICONS = {"Home": "🏠", "Text": "🔤", "AI assistant": "🤖",
         "Files": "📄", "Phrasebook": "📒", "Dictionary": "📖", "History": "🕘", "Saved": "🔖"}
TOOLS = [
    ("Text", "Text translation", "Type or paste English or Dzongkha and translate instantly."),
    ("AI assistant", "AI assistant", "Ask a question in English and get the answer in Dzongkha."),
    ("Files", "File translation", "Translate whole documents: .docx, .pdf, .txt."),
    ("Phrasebook", "Phrasebook", "Common everyday phrases in Dzongkha."),
    ("Dictionary", "Dictionary", "Look up words from the glossary."),
]

# The AI assistant needs Ollama, so it can be switched off for public hosting
AI_ENABLED = os.environ.get("ENABLE_AI", "1") == "1"
if not AI_ENABLED:
    PAGES.remove("AI assistant")
    TOOLS = [t for t in TOOLS if t[0] != "AI assistant"]

if "page" not in st.session_state or st.session_state.page not in PAGES:
    st.session_state.page = "Home"

with st.sidebar:
    st.markdown('<div class="brand">🐉 Bhutanese Dzongkha</div>', unsafe_allow_html=True)
    st.caption("རྫོང་ཁ། ⇄ English")
    st.radio("Menu", PAGES, key="page", format_func=lambda p: f"{ICONS[p]}  {p}",
             label_visibility="collapsed")
    st.divider()
    tuned = not MODEL.startswith("facebook/")
    st.caption("🟢 Fine-tuned model active" if tuned else "🔵 Base model (NLLB-200)")
    st.caption(f"📚 {len(glossary):,} glossary entries")

page = st.session_state.page


def go(p):
    st.session_state.page = p


def home_translate():
    st.session_state.text_in = st.session_state.get("home_q", "")
    st.session_state.autorun = True
    st.session_state.page = "Text"


def swap_direction():
    cur = st.session_state.get("text_dir", "English → Dzongkha")
    st.session_state.text_dir = ("Dzongkha → English" if cur == "English → Dzongkha"
                                 else "English → Dzongkha")
    st.session_state.text_in = st.session_state.get("text_out", "")
    st.session_state.text_out = ""


# ---------- pages ----------
def page_home():
    st.markdown('<div class="hero"><div class="hero-dz">རྫོང་ཁ། ⇄ English</div>'
                '<h1>Eng → Kha</h1>'
                '<p>English and Dzongkha by text, documents and chat.</p></div>',
                unsafe_allow_html=True)

    st.markdown('<div class="field-label">All tools</div>', unsafe_allow_html=True)
    for i in range(0, len(TOOLS), 2):
        cols = st.columns(2)
        for col, (p, title, desc) in zip(cols, TOOLS[i:i + 2]):
            with col.container(border=True):
                st.markdown(f'<p class="tool-title">{ICONS[p]} {title}</p>'
                            f'<p class="tool-desc">{desc}</p>', unsafe_allow_html=True)
                st.button("Open", key=f"open_{p}", on_click=go, args=(p,))

def page_text():
    page_title("Text translation", "Translate short texts in either direction.")
    c1, c2 = st.columns([5, 1])
    d_label = c1.radio("Direction", list(DIRS), horizontal=True, key="text_dir",
                       label_visibility="collapsed")
    c2.button("⇄ Swap", on_click=swap_direction, use_container_width=True)
    d = DIRS[d_label]

    left, right = st.columns(2, gap="large")
    with left:
        st.markdown('<div class="field-label">Input</div>', unsafe_allow_html=True)
        st.text_area("Input", height=260, key="text_in", label_visibility="collapsed",
                     placeholder="Type or paste text here...")
        b1, b2 = st.columns([1, 1])
        go_btn = b1.button("Translate", type="primary", use_container_width=True)
        b2.caption(f"{len(st.session_state.get('text_in', ''))} / {MAX_CHARS} characters")

    src = st.session_state.get("text_in", "").strip()
    if (go_btn or st.session_state.pop("autorun", False)) and src:
        if len(src) > MAX_CHARS:
            st.warning(f"Please keep the text under {MAX_CHARS} characters.")
        else:
            with st.spinner("Translating..."):
                st.session_state.text_out = translate(src, d)
            st.session_state.text_src = src
            st.session_state.text_out_dir = d
            log_history(src, st.session_state.text_out, d)

    out = st.session_state.get("text_out", "")
    out_dir = st.session_state.get("text_out_dir", d)
    with right:
        st.markdown('<div class="field-label">Result</div>', unsafe_allow_html=True)
        result_card(out, "dz" if out_dir == "en2dz" else "en")
        if out:
            result_actions(out, "text")
            if st.button("🔖 Save to my list", key="save_text", use_container_width=True):
                save_item(st.session_state.get("text_src", ""), out, out_dir)
                st.toast("Saved")

    if out and out_dir == "en2dz":
        with st.expander("Fix this translation (helps improve the model)"):
            fixed = st.text_area("Correct Dzongkha", out, height=120, key="fix_box")
            if st.button("Save correction"):
                save_correction(st.session_state.get("text_src", ""), fixed)
                st.success("Thank you! Your correction was saved for review.")


SUGGESTIONS = [
    "What is Gross National Happiness?",
    "Tell me about the Paro Tshechu festival.",
    "Give me simple tips to stay healthy.",
    "How do I greet someone politely?",
]


def ask_suggestion(text):
    st.session_state.ai_pending = text


def clear_chat():
    st.session_state.chat = []


def page_ai():
    import ollama
    SYSTEM = ("You are a friendly assistant for people in Bhutan. Answer in 2-4 SHORT, simple "
              "English sentences. Avoid idioms and slang, because the answer will be translated.")
    chat = st.session_state.setdefault("chat", [])

    st.markdown('<div class="ai-head"><div class="ai-icon">🤖</div>'
                '<div><div class="ai-title">Dzongkha Assistant</div>'
                '<div class="ai-sub">Ask in English · get answers in Dzongkha</div></div>'
                '<div class="ai-pill">English → རྫོང་ཁ།</div></div>', unsafe_allow_html=True)
    c1, c2 = st.columns([5, 1])
    c1.caption("Replies are written in English first, then translated into Dzongkha.")
    c2.button("🗑 New chat", on_click=clear_chat, disabled=not chat, use_container_width=True)

    prompt = st.chat_input("Ask me anything in English...") or st.session_state.pop("ai_pending", None)

    for m in chat:
        if m["role"] == "user":
            with st.chat_message("user", avatar="🙂"):
                st.write(m["en"])
        else:
            with st.chat_message("assistant", avatar="🐉"):
                result_card(m["dz"], "dz", compact=True)
                with st.expander("English version & copy"):
                    st.markdown("**English:** " + m["en"])
                    copy_box(m["dz"])

    if not chat and not prompt:
        st.markdown('<div class="ai-welcome"><div class="ai-welcome-icon">🐉</div>'
                    '<h3>How can I help you today?</h3>'
                    '<p>Ask a question in English and I will answer in Dzongkha.</p></div>',
                    unsafe_allow_html=True)
        cols = st.columns(2)
        for i, s in enumerate(SUGGESTIONS):
            cols[i % 2].button(s, key=f"sug{i}", on_click=ask_suggestion, args=(s,),
                               use_container_width=True)

    if prompt:
        if len(prompt) > MAX_CHARS:
            st.warning(f"Please keep messages under {MAX_CHARS} characters.")
            return
        with st.chat_message("user", avatar="🙂"):
            st.write(prompt)
        with st.chat_message("assistant", avatar="🐉"):
            try:
                with st.spinner("Thinking in Dzongkha..."):
                    convo = [{"role": "system", "content": SYSTEM}] + \
                            [{"role": m["role"], "content": m["en"]} for m in chat[-6:]] + \
                            [{"role": "user", "content": prompt}]
                    en = ollama.chat(model="qwen2.5:7b", messages=convo,
                                     options={"temperature": 0.3})["message"]["content"]
                    dz = translate(en, "en2dz")
            except Exception:
                st.error("The assistant could not answer right now. "
                         "Please make sure Ollama is running and try again.")
                return
        chat.append({"role": "user", "en": prompt, "dz": ""})
        chat.append({"role": "assistant", "en": en, "dz": dz})
        log_history(prompt, dz, "en2dz")
        st.rerun()


def page_files():
    page_title("File translation", "Upload a .docx, .pdf or .txt file. Up to 150 paragraphs are translated.")
    d_label = st.radio("Direction", list(DIRS), horizontal=True, key="file_dir")
    d = DIRS[d_label]
    f = st.file_uploader("Upload a document", type=["txt", "docx", "pdf"])
    if f and st.button("Translate document", type="primary"):
        if f.name.endswith(".docx"):
            paras = [p.text for p in Document(f).paragraphs]
        elif f.name.endswith(".pdf"):
            paras = "\n".join((p.extract_text() or "") for p in PdfReader(f).pages).split("\n")
        else:
            paras = f.read().decode("utf-8", errors="ignore").split("\n")
        paras = [p.strip() for p in paras if p.strip()][:150]
        if not paras:
            st.warning("No text found in this file.")
        else:
            out, bar = [], st.progress(0.0)
            for i, p in enumerate(paras):
                out.append(translate(p, d))
                bar.progress((i + 1) / len(paras))
            bar.empty()
            st.session_state.file_out = "\n\n".join(out)
            st.session_state.file_out_dir = d
            st.session_state.file_name = os.path.splitext(f.name)[0] + "_translated.txt"
    res = st.session_state.get("file_out", "")
    if res:
        result_card(res, "dz" if st.session_state.get("file_out_dir") == "en2dz" else "en",
                    label="Translated document")
        result_actions(res, "file", st.session_state.get("file_name", "translation.txt"))
    st.caption("The output is plain text; the original layout is not kept.")


def page_phrasebook():
    page_title("Phrasebook", "Common everyday phrases.")
    if os.path.exists("phrasebook.csv"):
        df = pd.read_csv("phrasebook.csv", encoding="utf-8-sig").fillna("")
    else:
        df = pd.DataFrame({"category": "General", "english": list(glossary.keys()),
                           "dzongkha": list(glossary.values())})
    cats = ["All"] + sorted(df["category"].unique())
    c1, c2 = st.columns(2)
    cat = c1.selectbox("Category", cats)
    q = c2.text_input("Search")
    if cat != "All":
        df = df[df["category"] == cat]
    if q:
        df = df[df["english"].str.contains(q, case=False) | df["dzongkha"].str.contains(q)]
    PER = 20
    pages = max(1, (len(df) + PER - 1) // PER)
    n = st.number_input(f"Page (of {pages})", 1, pages, 1)
    st.caption(f"{len(df)} entries")
    for _, r in df.iloc[(n - 1) * PER: n * PER].iterrows():
        with st.container(border=True):
            st.markdown("**" + r["english"] + "**")
            result_card(r["dzongkha"], "dz", compact=True)


def page_dictionary():
    page_title("Dictionary", "Search the glossary in English or Dzongkha.")
    q = st.text_input("Search a word").strip()
    if q:
        rows = [(e, d) for e, d in glossary.items() if q.lower() in e or q in d]
        if rows:
            st.dataframe(pd.DataFrame(rows, columns=["English", "Dzongkha"]),
                         use_container_width=True, hide_index=True)
        else:
            st.info("Not found. Add it to glossary.csv.")


def page_history():
    page_title("History", "Your recent translations in this session.")
    h = load_json("history")
    if st.button("Clear history"):
        save_json("history", [])
        st.rerun()
    if not h:
        st.info("Nothing here yet.")
    for r in reversed(h[-50:]):
        with st.container(border=True):
            st.write(r["src"])
            result_card(r["out"], "dz" if r["dir"] == "en2dz" else "en", compact=True)


def page_saved():
    page_title("Saved", "Translations you bookmarked in this session.")
    s = load_json("saved")
    if not s:
        st.info("Nothing saved yet. Use “Save to my list” on the Text page.")
    for i, r in enumerate(s):
        with st.container(border=True):
            st.write(r["src"])
            result_card(r["out"], "dz" if r["dir"] == "en2dz" else "en", compact=True)
            if st.button("Remove", key=f"rm{i}"):
                s.pop(i)
                save_json("saved", s)
                st.rerun()


{"Home": page_home, "Text": page_text, "AI assistant": page_ai,
 "Files": page_files, "Phrasebook": page_phrasebook,
 "Dictionary": page_dictionary, "History": page_history, "Saved": page_saved}[page]()

st.markdown("<div class='footer'>This model isn't fully completed. So, don't trust 100% it "
            "but it does work.</div>", unsafe_allow_html=True)