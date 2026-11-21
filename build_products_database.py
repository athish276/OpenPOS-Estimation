import os
import re
import json
import sqlite3

doc_path = r"C:\Users\HP\.gemini\antigravity\brain\3050fbca-9958-4245-a8e7-aacff8fd33c8\extracted_items\Document from Athish.txt"
base_dir = os.path.dirname(os.path.abspath(__file__))
db_path = os.path.join(base_dir, "pos_estimation.db")
public_json_path = os.path.join(base_dir, "public", "products.json")
root_json_path = os.path.join(base_dir, "products.json")

def normalize_category(raw_cat, name_upper):
    raw_upper = raw_cat.upper()
    if "THINNER" in raw_upper or "THINNER" in name_upper:
        return "Thinners"
    elif "AUTO" in raw_upper or "DUCO" in raw_upper or "CAR" in name_upper or "MARUTI" in name_upper:
        return "Auto Paints"
    elif "ENAMEL" in raw_upper or "ENAMAL" in raw_upper or "SUPERGLOSS" in raw_upper or "ENAMEL" in name_upper:
        return "Enamels"
    elif "PRIMER" in raw_upper or "PRIMER" in name_upper:
        return "Primers"
    elif "PUTTY" in raw_upper or "PUTTY" in name_upper or "SEALER" in name_upper:
        return "Putty & Sealers"
    elif "EMULSION" in raw_upper or "DISTEMPER" in raw_upper or "EMULSION" in name_upper:
        return "Emulsions"
    elif "WOOD" in raw_upper or "POLISH" in raw_upper or "VARNISH" in name_upper or "WOOD" in name_upper:
        return "Wood Finish"
    elif "BRUSH" in raw_upper or "ROLLER" in raw_upper or "TOOL" in raw_upper or "TRAY" in name_upper or "BRUSH" in name_upper:
        return "Brushes & Tools"
    elif "DULUX" in raw_upper or "SHEENLAC" in raw_upper or "NECOL" in name_upper or "PAINT" in name_upper or "WHITE" in name_upper or "CLEAR" in name_upper or "COLOR" in name_upper or "COLOUR" in name_upper:
        return "Paints"
    else:
        return "General Hardware"

def normalize_unit(unit, name_upper):
    u = unit.strip()
    if u in ["Nos", "Primary", ""]:
        if "200 LIT" in name_upper or "200L" in name_upper: return "200 Ltr"
        elif "20 LIT" in name_upper or "20L" in name_upper: return "20 Ltr"
        elif "10 LIT" in name_upper or "10L" in name_upper: return "10 Ltr"
        elif "5 LIT" in name_upper or "5L" in name_upper: return "5 Ltr"
        elif "4 LIT" in name_upper or "4L" in name_upper: return "4 Ltr"
        elif "3 LIT" in name_upper or "3L" in name_upper: return "3 Ltr"
        elif "1 LIT" in name_upper or "1 LT" in name_upper or "1L" in name_upper: return "1 Ltr"
        elif "750 ML" in name_upper: return "750 ml"
        elif "500 ML" in name_upper: return "500 ml"
        elif "250 ML" in name_upper: return "250 ml"
        elif "200 ML" in name_upper: return "200 ml"
        elif "100 ML" in name_upper: return "100 ml"
        elif "50 ML" in name_upper: return "50 ml"
        elif "KG" in name_upper: return "kg"
        elif "GM" in name_upper: return "g"
        elif "MTR" in name_upper or "METER" in name_upper: return "mtr"
        elif "CAN" in name_upper: return "can"
        elif "BOX" in name_upper: return "box"
        elif "PC" in name_upper or "PCS" in name_upper: return "pcs"
        else: return "pcs"
    elif "Lit" in u or "LIT" in u:
        return u.replace("Lit", "Ltr").replace("LIT", "Ltr")
    elif "Ml" in u or "ML" in u:
        return u.lower()
    return u

def extract_clean_name_and_price(raw_name, parts):
    name = raw_name
    code = ""
    price = 0.0

    # check col 17
    if len(parts) > 17:
        try:
            val = float(parts[17].replace(",", "").strip())
            if val > 0:
                price = val
        except Exception:
            pass

    # check if CSV format: code,name,price
    if "," in raw_name:
        sub = [s.strip() for s in raw_name.split(",")]
        if len(sub) >= 2:
            if len(sub[0]) <= 8 and (sub[0].isalnum() or "-" in sub[0]):
                code = sub[0]
                name = sub[1]
                if len(sub) >= 3 and price == 0.0:
                    try:
                        p_val = float(sub[2].replace(",", "").strip())
                        if p_val > 0:
                            price = p_val
                    except Exception:
                        pass
            else:
                name = sub[0]

    name_clean = " ".join(name.split()).strip()
    return code, name_clean, round(price, 2)

parsed_products = []
seen = set()

with open(doc_path, "r", encoding="utf-8", errors="ignore") as f:
    for line in f:
        if line.startswith("[ItemStart") or not line.strip():
            continue
        parts = [p.strip() for p in line.split("\t")]
        if len(parts) < 3:
            continue

        raw_name = parts[2] if len(parts) > 2 and parts[1] in ["True", "False"] else parts[1]
        if not raw_name or raw_name in ["True", "False"]:
            continue

        code, name, price = extract_clean_name_and_price(raw_name, parts)
        if not name:
            continue

        raw_unit = "Nos"
        for p in parts:
            if p in ["Nos", "1 Lit", "200 Lit", "20 Lit", "3 Lit", "5 Lit", "500 Ml", "4 Lit", "Kgs", "Mtrs", "Bags", "Pairs", "Sets", "Dzn", "Box", "Roll", "Pcs", "Btl", "Can", "Gms"]:
                raw_unit = p
                break

        name_upper = name.upper()
        unit = normalize_unit(raw_unit, name_upper)

        raw_cat = ""
        for c_idx in [4, 5, 6, 7]:
            if len(parts) > c_idx and parts[c_idx] not in ["Primary", "Nil", "True", "False", "0", "Nos", ""]:
                raw_cat = parts[c_idx]
                break
        category = normalize_category(raw_cat, name_upper)

        dedup_key = (name.lower(), unit.lower())
        if dedup_key in seen:
            continue
        seen.add(dedup_key)

        parsed_products.append({
            "id": len(parsed_products) + 1,
            "code": code,
            "name": name,
            "default_price": price,
            "unit": unit,
            "category": category
        })

print(f"Total processed products: {len(parsed_products)}")

# 1. Save to JSON files
os.makedirs(os.path.dirname(public_json_path), exist_ok=True)
with open(public_json_path, "w", encoding="utf-8") as f:
    json.dump(parsed_products, f, ensure_ascii=False, indent=None)

with open(root_json_path, "w", encoding="utf-8") as f:
    json.dump(parsed_products, f, ensure_ascii=False, indent=None)

print(f"Saved products.json to {public_json_path} ({os.path.getsize(public_json_path)} bytes)")
print(f"Saved products.json to {root_json_path} ({os.path.getsize(root_json_path)} bytes)")

# 2. Update SQLite Database
conn = sqlite3.connect(db_path)
cur = conn.cursor()
cur.execute("DROP TABLE IF EXISTS products")
cur.execute("""
CREATE TABLE products (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    name_ta TEXT,
    default_price REAL DEFAULT 0,
    unit TEXT DEFAULT 'pcs',
    category TEXT DEFAULT 'Paints'
)
""")

db_rows = [(p["name"], "", p["default_price"], p["unit"], p["category"]) for p in parsed_products]
cur.executemany("""
INSERT INTO products (name, name_ta, default_price, unit, category)
VALUES (?, ?, ?, ?, ?)
""", db_rows)

conn.commit()
cur.execute("SELECT COUNT(*) FROM products")
print(f"SQLite products count: {cur.fetchone()[0]}")
conn.close()
