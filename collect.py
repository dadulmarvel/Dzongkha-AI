import re, json, requests
from bs4 import BeautifulSoup
from pypdf import PdfReader
from sources import SOURCES, PDF_FILES

TIBETAN = re.compile(r"[\u0F00-\u0FFF]")

def dz_ratio(text):
    letters = [c for c in text if not c.isspace()]
    return len(TIBETAN.findall(text)) / max(len(letters), 1)

def chunk(text, size=400):
    parts = re.split(r"(?<=[།\n])", text)   # split on Dzongkha shad (།)
    out, cur = [], ""
    for p in parts:
        if len(cur) + len(p) > size:
            if cur.strip(): out.append(cur.strip())
            cur = p
        else:
            cur += p
    if cur.strip(): out.append(cur.strip())
    return out

def from_web(url):
    try:
        r = requests.get(url, timeout=20, headers={"User-Agent": "Mozilla/5.0"})
        r.encoding = "utf-8"
        soup = BeautifulSoup(r.text, "html.parser")
        for t in soup(["script", "style", "nav", "footer"]): t.decompose()
        return soup.get_text("\n")
    except Exception as e:
        print("FAILED", url, e); return ""

def from_pdf(path):
    try:
        return "\n".join(p.extract_text() or "" for p in PdfReader(path).pages)
    except Exception as e:
        print("FAILED", path, e); return ""

docs = []
for u in SOURCES:
    for c in chunk(from_web(u)):
        if dz_ratio(c) > 0.4:               # keep mostly-Dzongkha chunks only
            docs.append({"source": u, "text": c})
for p in PDF_FILES:
    for c in chunk(from_pdf(p)):
        if dz_ratio(c) > 0.4:
            docs.append({"source": p, "text": c})

json.dump(docs, open("data/corpus.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
print(f"Saved {len(docs)} Dzongkha chunks")