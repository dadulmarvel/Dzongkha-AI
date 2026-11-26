import csv, json, re, numpy as np, ollama

CHAT_MODEL = "qwen2.5:7b"
EMBED_MODEL = "bge-m3"
TIBETAN = re.compile(r"[\u0F00-\u0FFF]")

docs = json.load(open("data/corpus.json", encoding="utf-8"))
vecs = np.load("data/vectors.npy")
vecs_n = vecs / np.linalg.norm(vecs, axis=1, keepdims=True)
glossary = list(csv.DictReader(open("glossary.csv", encoding="utf-8")))

SYSTEM = """You are a Bhutanese assistant. The user writes in English.
You must reply ONLY in pure Bhutanese Dzongkha, written in Dzongkha (Tibetan) script.
Rules:
- Do NOT use English, Hindi, Chinese or romanized text in your reply.
- Use formal, standard Dzongkha as promoted by the Dzongkha Development Commission.
- End sentences with the shad (།).
- Use the reference text and glossary below for vocabulary and style.
- If you are unsure of a word, use a simpler Dzongkha word. Never invent English words."""

def dz_ratio(t):
    letters = [c for c in t if not c.isspace() and c not in "།༎,.!?"]
    return len(TIBETAN.findall(t)) / max(len(letters), 1)

def retrieve(q, k=4):
    e = np.array(ollama.embeddings(model=EMBED_MODEL, prompt=q)["embedding"])
    e /= np.linalg.norm(e)
    top = np.argsort(vecs_n @ e)[::-1][:k]
    return [docs[i]["text"] for i in top]

def glossary_hits(q):
    ql = q.lower()
    return [f'{g["english"]} = {g["dzongkha"]}' for g in glossary if g["english"].lower() in ql]

def ask(question, history):
    context = "\n".join(retrieve(question))
    gl = "\n".join(glossary_hits(question)) or "(none)"
    system = f"{SYSTEM}\n\nGLOSSARY:\n{gl}\n\nREFERENCE DZONGKHA TEXT:\n{context}"
    msgs = [{"role": "system", "content": system}] + history + \
           [{"role": "user", "content": question}]
    for attempt in range(3):                      # retry until output is really Dzongkha
        out = ollama.chat(model=CHAT_MODEL, messages=msgs,
                          options={"temperature": 0.3})["message"]["content"]
        if dz_ratio(out) > 0.85:
            return out
        msgs.append({"role": "user",
                     "content": "Your reply was not pure Dzongkha script. Answer again ONLY in Dzongkha script."})
    return out

if __name__ == "__main__":
    history = []
    print("Type English (or 'exit').")
    while True:
        q = input("\nYou: ").strip()
        if q.lower() in ("exit", "quit"): break
        a = ask(q, history)
        print("Bot:", a)
        history += [{"role": "user", "content": q}, {"role": "assistant", "content": a}]
        history = history[-6:]