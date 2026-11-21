import os
import re
import json

doc_path = r"C:\Users\HP\.gemini\antigravity\brain\3050fbca-9958-4245-a8e7-aacff8fd33c8\extracted_items\Document from Athish.txt"

parsed_items = []
seen_names = set()

# Common categories and units
with open(doc_path, "r", encoding="utf-8", errors="ignore") as f:
    for idx, line in enumerate(f):
        if line.startswith("[ItemStart") or not line.strip():
            continue
        parts = [p.strip() for p in line.split("\t")]
        if len(parts) < 3:
            continue

        raw_name = parts[2] if len(parts) > 2 and parts[1] in ["True", "False"] else parts[1]
        if not raw_name or raw_name in ["True", "False"]:
            continue

        unit = "Nos"
        for p in parts:
            if p in ["Nos", "1 Lit", "200 Lit", "20 Lit", "3 Lit", "5 Lit", "500 Ml", "4 Lit", "Kgs", "Mtrs", "Bags", "Pairs", "Sets", "Dzn", "Box", "Roll", "Pcs", "Btl", "Can", "Gms", "Meter", "Ltr", "Pack"]:
                unit = p
                break

        price = 0.0
        # check col 17
        if len(parts) > 17:
            try:
                p_cand = float(parts[17].replace(",", ""))
                if p_cand > 0:
                    price = p_cand
            except Exception:
                pass

        # check if raw_name is CSV format e.g. "10001,NECOL MILKY WHITE 1 LIT,155.00"
        name = raw_name
        code = ""
        if "," in raw_name:
            sub = [s.strip() for s in raw_name.split(",")]
            # e.g. ["10001", "NECOL MILKY WHITE 1 LIT", "155.00"]
            if len(sub) >= 2:
                # if first part is code (digits or short alphanumeric)
                if len(sub[0]) <= 8 and (sub[0].isalnum() or "-" in sub[0]):
                    code = sub[0]
                    name = sub[1]
                    if len(sub) >= 3 and price == 0.0:
                        try:
                            price_val = float(sub[2].replace(",", ""))
                            if price_val > 0:
                                price = price_val
                        except Exception:
                            pass
                else:
                    name = sub[0]

        # Extract unit from name if unit is Nos but name says "1 LIT", "500 ML", etc.
        name_upper = name.upper()
        if unit == "Nos":
            if "200 LIT" in name_upper or "200L" in name_upper: unit = "200 Lit"
            elif "20 LIT" in name_upper or "20L" in name_upper: unit = "20 Lit"
            elif "10 LIT" in name_upper or "10L" in name_upper: unit = "10 Lit"
            elif "5 LIT" in name_upper or "5L" in name_upper: unit = "5 Lit"
            elif "4 LIT" in name_upper or "4L" in name_upper: unit = "4 Lit"
            elif "1 LIT" in name_upper or "1 LT" in name_upper or "1L" in name_upper: unit = "1 Lit"
            elif "500 ML" in name_upper: unit = "500 ml"
            elif "250 ML" in name_upper: unit = "250 ml"
            elif "200 ML" in name_upper: unit = "200 ml"
            elif "100 ML" in name_upper: unit = "100 ml"
            elif "50 ML" in name_upper: unit = "50 ml"
            elif "KG" in name_upper: unit = "kg"
            elif "GM" in name_upper: unit = "g"
            elif "MTR" in name_upper: unit = "mtr"

        # Determine Category
        category = "Paints & Hardware"
        for col_idx in [4, 5, 6, 7]:
            if len(parts) > col_idx:
                c = parts[col_idx]
                if c and c not in ["Primary", "SHEENLAC", "Nil", "True", "False", "0", "Nos"]:
                    category = c
                    break

        # Fallback category based on keyword in name
        if category in ["Paints & Hardware", "Hardware"]:
            if "THINNER" in name_upper: category = "Thinner"
            elif "ENAMEL" in name_upper: category = "Enamel"
            elif "EMULSION" in name_upper: category = "Emulsion"
            elif "PRIMER" in name_upper: category = "Primer"
            elif "DISTEMPER" in name_upper: category = "Distemper"
            elif "VARNISH" in name_upper: category = "Varnish"
            elif "SEALER" in name_upper: category = "Sealer"
            elif "PUTTY" in name_upper: category = "Putty"
            elif "BRUSH" in name_upper or "ROLLER" in name_upper: category = "Brushes & Tools"
            elif "STAINER" in name_upper: category = "Stainer"
            elif "WHITE" in name_upper or "CLEAR" in name_upper or "RED" in name_upper or "BLUE" in name_upper or "BLACK" in name_upper: category = "Paints"

        # Deduplicate
        name_clean = " ".join(name.split()).strip()
        if not name_clean:
            continue
        dedup_key = (name_clean.lower(), unit.lower())
        if dedup_key in seen_names:
            continue
        seen_names.add(dedup_key)

        parsed_items.append({
            "id": len(parsed_items) + 1,
            "name": name_clean,
            "default_price": round(price, 2),
            "unit": unit,
            "category": category
        })

print(f"Total unique items extracted: {len(parsed_items)}")
priced_count = sum(1 for p in parsed_items if p["default_price"] > 0)
print(f"Items with positive price: {priced_count}")

# Print categories breakdown
cat_counts = {}
for p in parsed_items:
    cat_counts[p["category"]] = cat_counts.get(p["category"], 0) + 1

sorted_cats = sorted(cat_counts.items(), key=lambda x: x[1], reverse=True)
print("\nTop categories:")
for cat, cnt in sorted_cats[:15]:
    print(f"  {cat}: {cnt}")

print("\nSample parsed items:")
for item in parsed_items[15:25]:
    print(" ", item)
