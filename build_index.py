import json, numpy as np, ollama

docs = json.load(open("data/corpus.json", encoding="utf-8"))
vecs = []
for i, d in enumerate(docs):
    e = ollama.embeddings(model="bge-m3", prompt=d["text"])["embedding"]
    vecs.append(e)
    if i % 50 == 0: print(i, "/", len(docs))
np.save("data/vectors.npy", np.array(vecs, dtype="float32"))
print("Index built")