import csv, re
from collections import Counter

TIB = re.compile(r"[\u0F00-\u0FFF]")
LAT = re.compile(r"[A-Za-z]")

rows, bad = [], []
with open("glossary.csv", encoding="utf-8-sig") as f:
    reader = csv.DictReader(f)
    if not reader.fieldnames or [h.strip().lower() for h in reader.fieldnames][:2] != ["english", "dzongkha"]:
        print("HEADER PROBLEM: first line must be exactly: english,dzongkha ->", reader.fieldnames)
    for i, r in enumerate(reader, start=2):
        en = (r.get("english") or "").strip()
        dz = (r.get("dzongkha") or "").strip()
        if not en or not dz:
            bad.append((i, "empty cell", en, dz)); continue
        if not TIB.search(dz):
            bad.append((i, "no Dzongkha script in dzongkha column", en, dz)); continue
        if len(LAT.findall(dz)) > 3:
            bad.append((i, "English letters inside Dzongkha", en, dz))
        if TIB.search(en):
            bad.append((i, "Dzongkha script inside English column", en, dz))
        rows.append((en, dz))

dup = [k for k, v in Counter(en.lower() for en, _ in rows).items() if v > 1]
conflicts = {}
for en, dz in rows:
    conflicts.setdefault(en.lower(), set()).add(dz)
conflicts = {k: v for k, v in conflicts.items() if len(v) > 1}

words = sum(1 for en, _ in rows if len(en.split()) == 1)
print(f"Valid rows        : {len(rows)}")
print(f"Single-word rows  : {words}")
print(f"Duplicate English : {len(dup)}  (same English, listed more than once)")
print(f"Conflicting       : {len(conflicts)}  (same English, different Dzongkha)")
print(f"Problem rows      : {len(bad)}")
for b in bad[:20]:
    print("  line", b[0], "-", b[1], "|", b[2][:40], "|", b[3][:40])
for k in list(conflicts)[:10]:
    print("  conflict:", k, "->", list(conflicts[k])[:3])

# write a de-duplicated copy (keeps the LAST occurrence); review it, then replace glossary.csv
seen = {}
for en, dz in rows:
    seen[en.lower()] = (en, dz)
with open("glossary_clean.csv", "w", encoding="utf-8-sig", newline="") as f:
    w = csv.writer(f)
    w.writerow(["english", "dzongkha"])
    w.writerows(seen.values())
print(f"\nWrote glossary_clean.csv with {len(seen)} unique rows")