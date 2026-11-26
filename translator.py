import csv, glob, os, re, difflib
from transformers import AutoTokenizer, AutoModelForSeq2SeqLM

BASE = "facebook/nllb-200-distilled-600M"
LOCAL = "models/nllb-dz"                      # fine-tuned model, used automatically if it exists
MODEL = LOCAL if os.path.isdir(LOCAL) else BASE

tok = AutoTokenizer.from_pretrained(MODEL, src_lang="eng_Latn")
model = AutoModelForSeq2SeqLM.from_pretrained(MODEL)
DZ_ID = tok.convert_tokens_to_ids("dzo_Tibt")

# On the public site, corrections go to a pending file for you to review
PUBLIC = os.environ.get("PUBLIC_MODE", "0") == "1"
CORR_FILE = "data/pending/user_corrections.csv" if PUBLIC else "data/parallel/user_corrections.csv"

SEP = " / "          # shown between different meanings of the same English word


def _norm(s):
    return re.sub(r"[^\w\s]", "", s.lower()).strip()


def _normdz(s):
    return re.sub(r"[\s།༎,.!?]", "", s)


def _load_meanings():
    """english -> [dzongkha, ...]. glossary.csv keeps ALL meanings of a word.
    Files in data/parallel (e.g. corrections) replace earlier meanings: last entry wins."""
    merged = {}
    for f in ["glossary.csv"] + sorted(glob.glob("data/parallel/*.csv")):
        if not os.path.exists(f):
            continue
        keep_all = (f == "glossary.csv")
        local = {}
        with open(f, encoding="utf-8-sig") as fh:
            for r in csv.DictReader(fh):
                en = (r.get("english") or "").strip()
                dz = (r.get("dzongkha") or "").strip()
                if not (en and dz):
                    continue
                key = _norm(en)
                if keep_all:
                    lst = local.setdefault(key, [])
                    if dz not in lst:
                        lst.append(dz)
                else:
                    local[key] = [dz]
        merged.update(local)
    return merged


_meanings = _load_meanings()
glossary = {k: SEP.join(v) for k, v in _meanings.items()}   # display form, used by app.py


def save_correction(english, dzongkha):
    os.makedirs(os.path.dirname(CORR_FILE), exist_ok=True)
    new = not os.path.exists(CORR_FILE)
    with open(CORR_FILE, "a", encoding="utf-8-sig", newline="") as f:
        w = csv.writer(f)
        if new:
            w.writerow(["english", "dzongkha"])
        w.writerow([english.strip(), dzongkha.strip()])
    if not PUBLIC:                       # public corrections wait for your review
        key = _norm(english)
        _meanings[key] = [dzongkha.strip()]
        glossary[key] = dzongkha.strip()


def _lookup(sentence):
    key = _norm(sentence)
    if key in glossary:
        return glossary[key]
    close = difflib.get_close_matches(key, glossary.keys(), n=1, cutoff=0.93)
    return glossary[close[0]] if close else None


def _build_rev():
    rev = {}
    for en, dzs in _meanings.items():
        for dz in dzs:
            rev.setdefault(_normdz(dz), []).append(en)
    return rev


def en_to_dz(text, use_glossary=True):
    out = []
    for s in re.split(r"(?<=[.!?])\s+", text.strip()):
        if not s:
            continue
        hit = _lookup(s) if use_glossary else None
        if hit:
            out.append(hit)
            continue
        inputs = tok(s, return_tensors="pt", truncation=True, max_length=256)
        gen = model.generate(**inputs, forced_bos_token_id=DZ_ID,
                             num_beams=5, max_new_tokens=256)
        out.append(tok.batch_decode(gen, skip_special_tokens=True)[0])
    return " ".join(out)


def dz_to_en(text, use_glossary=True):
    rev = _build_rev()
    en_id = tok.convert_tokens_to_ids("eng_Latn")
    out = []
    tok.src_lang = "dzo_Tibt"
    try:
        for s in re.split(r"(?<=།)\s*|\n+", text.strip()):
            if not s.strip():
                continue
            if use_glossary and _normdz(s) in rev:
                out.append(SEP.join(e.capitalize() for e in rev[_normdz(s)]))
                continue
            inputs = tok(s, return_tensors="pt", truncation=True, max_length=256)
            gen = model.generate(**inputs, forced_bos_token_id=en_id,
                                 num_beams=5, max_new_tokens=256)
            out.append(tok.batch_decode(gen, skip_special_tokens=True)[0])
    finally:
        tok.src_lang = "eng_Latn"
    return " ".join(out)


def translate(text, direction="en2dz"):
    return en_to_dz(text) if direction == "en2dz" else dz_to_en(text)