import csv, sacrebleu
from translator import en_to_dz, MODEL

with open("data/test.csv", encoding="utf-8-sig") as f:
    rows = list(csv.DictReader(f))
hyps = [en_to_dz(r["english"], use_glossary=False) for r in rows]   # model only, no lookup
refs = [r["dzongkha"] for r in rows]

print("Model :", MODEL)
print("Test  :", len(rows), "sentences")
print("chrF++:", round(sacrebleu.corpus_chrf(hyps, [refs], word_order=2).score, 1))
print("BLEU  :", round(sacrebleu.corpus_bleu(hyps, [refs]).score, 1))
for r, h in list(zip(rows, hyps))[:5]:
    print("\nEN :", r["english"], "\nREF:", r["dzongkha"], "\nOUT:", h)