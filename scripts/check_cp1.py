import csv
import re
from pathlib import Path

D = Path("data/ecommerce-crawled-final")
REQ = ["doc_id", "title", "source_url", "retrieved_at", "document_version", "audience"]
mds = sorted(D.glob("*.md"))
rows = list(csv.DictReader(open(D / "sources.csv", encoding="utf-8")))
ids, auds = [], {}

for p in mds:
    raw_fm = p.read_text(encoding="utf-8").split("---")[1]
    fm = dict(re.findall(r"^(\w+):\s*(.+)$", raw_fm, re.M))
    doc_id = fm.get("doc_id")
    ids.append(doc_id)
    auds[fm.get("audience")] = auds.get(fm.get("audience"), 0) + 1
    status = "OK" if all(k in fm for k in REQ) and doc_id == p.stem else "THIEU METADATA"
    print(f"{p.name:40} {status}")
    if status != "OK":
        missing = [k for k in REQ if k not in fm]
        print(f"  -> Missing keys: {missing}")
        print(f"  -> fm.get('doc_id'): {repr(doc_id)} vs p.stem: {repr(p.stem)}")

print("so file :", len(mds), "(can 5-10)")
print("csv     :", "khop" if sorted(r["doc_id"] for r in rows) == sorted(ids) else "LECH")
print("audience:", auds)
