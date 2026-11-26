import csv, shutil

SRC = "glossary.csv"
shutil.copyfile(SRC, "glossary_before_dedupe.csv")

rows, seen, removed = [], set(), 0
with open(SRC, encoding="utf-8-sig") as f:
    for r in csv.DictReader(f):
        en = (r.get("english") or "").strip()
        dz = (r.get("dzongkha") or "").strip()
        if not en or not dz:
            continue
        key = (en.lower(), dz)
        if key in seen:            # identical English AND identical Dzongkha -> real copy
            removed += 1
            continue
        seen.add(key)
        rows.append((en, dz))

meanings = {}
for en, dz in rows:
    meanings.setdefault(en.lower(), []).append(dz)
multi = {k: v for k, v in meanings.items() if len(v) > 1}

with open(SRC, "w", encoding="utf-8-sig", newline="") as f:
    w = csv.writer(f)
    w.writerow(["english", "dzongkha"])
    w.writerows(rows)

print(f"Removed {removed} exact copies. Rows now: {len(rows)}")
print(f"Kept {len(multi)} English entries with more than one meaning:")
for k, v in multi.items():
    print("  ", k, "->", " | ".join(v))