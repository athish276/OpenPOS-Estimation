#!/usr/bin/env python3
"""
OpenPOS - Estimation POS System Server
Built for flexible item entry with fluctuating/manual prices.
Zero external dependencies (uses standard library http.server + sqlite3).
"""

import os
import sys
import json
import sqlite3
import mimetypes
from urllib.parse import urlparse, parse_qs
from http.server import HTTPServer, BaseHTTPRequestHandler
from datetime import datetime

PORT = int(os.environ.get("PORT", 3000))
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PUBLIC_DIR = os.path.join(BASE_DIR, "public")
DB_PATH = os.path.join(BASE_DIR, "pos_estimation.db")

def init_db():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("""
    CREATE TABLE IF NOT EXISTS products (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        name_ta TEXT,
        default_price REAL DEFAULT 0,
        unit TEXT DEFAULT 'kg',
        category TEXT DEFAULT 'Groceries'
    )
    """)
    cur.execute("""
    CREATE TABLE IF NOT EXISTS estimates (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        estimate_no TEXT UNIQUE,
        customer_name TEXT,
        customer_phone TEXT,
        subtotal REAL,
        discount REAL,
        grand_total REAL,
        items_json TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """)
    
    # Check if products exist, seed some starter items if empty
    cur.execute("SELECT COUNT(*) FROM products")
    count = cur.fetchone()[0]
    if count == 0:
        seed_items = [
            ("Tomato", "", 40.0, "kg", "Vegetables"),
            ("Onion", "", 50.0, "kg", "Vegetables"),
            ("Potato", "", 35.0, "kg", "Vegetables"),
            ("Carrot", "", 60.0, "kg", "Vegetables"),
            ("Green Chilli", "", 80.0, "kg", "Vegetables"),
            ("Ponni Rice", "", 62.0, "kg", "Groceries"),
            ("Toor Dal", "", 160.0, "kg", "Groceries"),
            ("Sugar", "", 44.0, "kg", "Groceries"),
            ("Sunflower Oil", "", 145.0, "ltr", "Groceries"),
            ("Atta Flour", "", 52.0, "kg", "Groceries"),
            ("Apple", "", 180.0, "kg", "Fruits"),
            ("Banana", "", 50.0, "dozen", "Fruits"),
            ("Milk", "", 30.0, "packet", "Dairy"),
            ("Tea Powder", "", 95.0, "pack", "Groceries"),
            ("Coffee Powder", "", 120.0, "pack", "Groceries")
        ]
        cur.executemany("""
            INSERT INTO products (name, name_ta, default_price, unit, category)
            VALUES (?, ?, ?, ?, ?)
        """, seed_items)
        conn.commit()
    conn.close()

class PosRequestHandler(BaseHTTPRequestHandler):
    def end_headers(self):
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, DELETE, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        super().end_headers()

    def do_OPTIONS(self):
        self.send_response(200)
        self.end_headers()

    def send_json(self, data, status=200):
        body = json.dumps(data, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        parsed = urlparse(self.path)
        path = parsed.path

        # REST API Endpoints
        if path == "/api/products":
            conn = sqlite3.connect(DB_PATH)
            conn.row_factory = sqlite3.Row
            cur = conn.cursor()
            cur.execute("SELECT * FROM products ORDER BY category, name")
            rows = [dict(r) for r in cur.fetchall()]
            conn.close()
            return self.send_json(rows)

        if path == "/api/estimates":
            conn = sqlite3.connect(DB_PATH)
            conn.row_factory = sqlite3.Row
            cur = conn.cursor()
            cur.execute("SELECT * FROM estimates ORDER BY id DESC LIMIT 50")
            rows = []
            for r in cur.fetchall():
                d = dict(r)
                try:
                    d["items"] = json.loads(d["items_json"])
                except Exception:
                    d["items"] = []
                rows.append(d)
            conn.close()
            return self.send_json(rows)

        # Static File Serving
        if path == "/" or path == "/index.html" or path == "/pos":
            target_file = os.path.join(PUBLIC_DIR, "estimation_pos.html")
        else:
            # remove leading slash
            rel_path = path.lstrip("/").replace("/", os.sep)
            target_file = os.path.join(PUBLIC_DIR, rel_path)
            if not os.path.exists(target_file):
                target_file = os.path.join(BASE_DIR, rel_path)

        if os.path.isfile(target_file):
            ctype, _ = mimetypes.guess_type(target_file)
            if not ctype:
                ctype = "application/octet-stream"
            try:
                with open(target_file, "rb") as f:
                    content = f.read()
                self.send_response(200)
                self.send_header("Content-Type", ctype)
                self.send_header("Content-Length", str(len(content)))
                self.end_headers()
                self.wfile.write(content)
            except Exception as e:
                self.send_response(500)
                self.end_headers()
                self.wfile.write(str(e).encode("utf-8"))
        else:
            self.send_response(404)
            self.end_headers()
            self.wfile.write(b"404 Not Found")

    def do_POST(self):
        parsed = urlparse(self.path)
        path = parsed.path
        length = int(self.headers.get("Content-Length", 0))
        raw_body = self.rfile.read(length) if length > 0 else b"{}"
        try:
            body = json.loads(raw_body.decode("utf-8"))
        except Exception:
            body = {}

        if path == "/api/products":
            name = body.get("name", "").strip()
            if not name:
                return self.send_json({"error": "Item name is required"}, status=400)
            name_ta = body.get("name_ta", "").strip()
            price = float(body.get("default_price", 0.0) or 0.0)
            unit = body.get("unit", "kg").strip()
            category = body.get("category", "General").strip()

            conn = sqlite3.connect(DB_PATH)
            cur = conn.cursor()
            cur.execute("""
                INSERT INTO products (name, name_ta, default_price, unit, category)
                VALUES (?, ?, ?, ?, ?)
            """, (name, name_ta, price, unit, category))
            new_id = cur.lastrowid
            conn.commit()
            conn.close()
            return self.send_json({"success": True, "id": new_id, "name": name, "price": price}, status=201)

        if path == "/api/estimates":
            items = body.get("items", [])
            if not items:
                return self.send_json({"error": "Cannot save empty estimate"}, status=400)
            subtotal = float(body.get("subtotal", 0.0))
            discount = float(body.get("discount", 0.0))
            grand_total = float(body.get("grand_total", 0.0))
            cust_name = body.get("customer_name", "").strip()
            cust_phone = body.get("customer_phone", "").strip()
            
            # Generate Estimate No e.g. EST-20261120-1001
            now_str = datetime.now().strftime("%Y%m%d")
            conn = sqlite3.connect(DB_PATH)
            cur = conn.cursor()
            cur.execute("SELECT COUNT(*) FROM estimates WHERE estimate_no LIKE ?", (f"EST-{now_str}-%",))
            todays_count = cur.fetchone()[0] + 1
            estimate_no = f"EST-{now_str}-{todays_count:04d}"

            cur.execute("""
                INSERT INTO estimates (estimate_no, customer_name, customer_phone, subtotal, discount, grand_total, items_json)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (estimate_no, cust_name, cust_phone, subtotal, discount, grand_total, json.dumps(items, ensure_ascii=False)))
            est_id = cur.lastrowid
            conn.commit()
            conn.close()
            return self.send_json({
                "success": True,
                "id": est_id,
                "estimate_no": estimate_no,
                "created_at": datetime.now().strftime("%d/%m/%Y %I:%M %p")
            }, status=201)

        self.send_response(404)
        self.end_headers()

    def do_DELETE(self):
        parsed = urlparse(self.path)
        path = parsed.path
        if path.startswith("/api/products/"):
            try:
                prod_id = int(path.split("/")[-1])
                conn = sqlite3.connect(DB_PATH)
                cur = conn.cursor()
                cur.execute("DELETE FROM products WHERE id = ?", (prod_id,))
                conn.commit()
                conn.close()
                return self.send_json({"success": True})
            except Exception as e:
                return self.send_json({"error": str(e)}, status=400)

        if path.startswith("/api/estimates/"):
            try:
                est_id = int(path.split("/")[-1])
                conn = sqlite3.connect(DB_PATH)
                cur = conn.cursor()
                cur.execute("DELETE FROM estimates WHERE id = ?", (est_id,))
                conn.commit()
                conn.close()
                return self.send_json({"success": True})
            except Exception as e:
                return self.send_json({"error": str(e)}, status=400)

        self.send_response(404)
        self.end_headers()

def run_server():
    init_db()
    server_address = ("0.0.0.0", PORT)
    httpd = HTTPServer(server_address, PosRequestHandler)
    print(f"OpenPOS Estimation Server running at http://localhost:{PORT}/")
    print(f"Accessible on local network via http://0.0.0.0:{PORT}/")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down server.")
        httpd.server_close()

if __name__ == "__main__":
    run_server()
