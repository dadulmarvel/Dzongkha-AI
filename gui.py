import html
import ollama
import streamlit as st
from translator import en_to_dz

st.set_page_config(page_title="Dzongkha Chatbot", page_icon="🇧🇹", layout="centered")

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Noto+Serif+Tibetan&display=swap');
.dz { font-family: 'Noto Serif Tibetan','Jomolhari','Microsoft Himalaya',serif;
      font-size: 24px; line-height: 2.1; white-space: pre-wrap; }
</style>""", unsafe_allow_html=True)

SYSTEM = ("You are a friendly assistant for people in Bhutan. Answer in 2-4 SHORT, "
          "simple English sentences. Avoid idioms, slang and complex words, "
          "because your answer will be translated into Dzongkha.")

# ---------- sidebar ----------
with st.sidebar:
    st.header("Settings")
    mode = st.radio("Mode", ["Chatbot (AI answers)", "Translate only"])
    show_en = st.checkbox("Show English version of replies", value=False)
    if st.button("New chat", use_container_width=True):
        st.session_state.messages = []
        st.rerun()

st.title("🇧🇹 Dzongkha Chatbot")
st.caption("Type in English. The bot replies in Dzongkha.")

if "messages" not in st.session_state:
    st.session_state.messages = []   # {"role", "en", "dz"}

# ---------- show history ----------
for m in st.session_state.messages:
    with st.chat_message(m["role"]):
        if m["role"] == "user":
            st.write(m["en"])
        else:
            st.markdown(f'<div class="dz">{html.escape(m["dz"])}</div>', unsafe_allow_html=True)
            if show_en:
                st.caption("English: " + m["en"])

# ---------- new message ----------
prompt = st.chat_input("Type your message in English...")
if prompt:
    st.session_state.messages.append({"role": "user", "en": prompt, "dz": ""})
    with st.chat_message("user"):
        st.write(prompt)

    with st.chat_message("assistant"):
        with st.spinner("Thinking in Dzongkha..."):
            if mode.startswith("Chatbot"):
                convo = [{"role": "system", "content": SYSTEM}]
                for m in st.session_state.messages[-7:]:
                    convo.append({"role": m["role"], "content": m["en"]})
                english = ollama.chat(model="qwen2.5:7b", messages=convo,
                                      options={"temperature": 0.3})["message"]["content"]
            else:
                english = prompt
            dz = en_to_dz(english)
        st.markdown(f'<div class="dz">{html.escape(dz)}</div>', unsafe_allow_html=True)
        if show_en:
            st.caption("English: " + english)

    st.session_state.messages.append({"role": "assistant", "en": english, "dz": dz})