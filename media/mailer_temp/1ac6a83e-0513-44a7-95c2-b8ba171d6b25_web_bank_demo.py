
from flask import Flask, request, jsonify, g
import sqlite3, hashlib, os, datetime

DB_PATH = os.path.join(os.path.dirname(__file__), "web_bank_demo.db")

def get_db():
    db = getattr(g, "_database", None)
    if db is None:
        db = g._database = sqlite3.connect(DB_PATH, detect_types=sqlite3.PARSE_DECLTYPES)
        db.row_factory = sqlite3.Row
    return db

def init_db():
    db = sqlite3.connect(DB_PATH)
    c = db.cursor()
    c.execute("""CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                balance INTEGER NOT NULL DEFAULT 0
    )""")
    c.execute("""CREATE TABLE IF NOT EXISTS transactions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                from_user INTEGER,
                to_user INTEGER,
                amount INTEGER NOT NULL,
                timestamp TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                description TEXT,
                FOREIGN KEY(from_user) REFERENCES users(id),
                FOREIGN KEY(to_user) REFERENCES users(id)
    )""")
    db.commit()
    db.close()

def hash_password(password: str) -> str:
    return hashlib.sha256(password.encode("utf-8")).hexdigest()

app = Flask(__name__)
app.config["JSON_SORT_KEYS"] = False

@app.teardown_appcontext
def close_connection(exception):
    db = getattr(g, "_database", None)
    if db is not None:
        db.close()

@app.route("/register", methods=["POST"])
def register():
    data = request.get_json(force=True)
    username = data.get("username")
    password = data.get("password")
    if not username or not password:
        return jsonify({"error":"username and password required"}), 400
    db = get_db()
    try:
        db.execute("INSERT INTO users (username, password_hash, balance) VALUES (?, ?, ?)",
                   (username, hash_password(password), 0))
        db.commit()
    except sqlite3.IntegrityError:
        return jsonify({"error":"username already exists"}), 400
    return jsonify({"status":"registered","username":username}), 201

@app.route("/deposit", methods=["POST"])
def deposit():
    data = request.get_json(force=True)
    username = data.get("username")
    amount = int(data.get("amount") or 0)
    if amount <= 0:
        return jsonify({"error":"amount must be positive"}), 400
    db = get_db()
    user = db.execute("SELECT * FROM users WHERE username = ?", (username,)).fetchone()
    if not user:
        return jsonify({"error":"user not found"}), 404
    db.execute("UPDATE users SET balance = balance + ? WHERE id = ?", (amount, user["id"]))
    db.execute("INSERT INTO transactions (from_user, to_user, amount, description) VALUES (?, ?, ?, ?)",
               (None, user["id"], amount, "deposit"))
    db.commit()
    return jsonify({"status":"ok","username":username,"new_balance":db.execute("SELECT balance FROM users WHERE id = ?", (user["id"],)).fetchone()["balance"]})

@app.route("/transfer", methods=["POST"])
def transfer():
    data = request.get_json(force=True)
    from_user = data.get("from_username")
    to_user = data.get("to_username")
    amount = int(data.get("amount") or 0)
    if amount <= 0:
        return jsonify({"error":"amount must be positive"}), 400
    db = get_db()
    fu = db.execute("SELECT * FROM users WHERE username = ?", (from_user,)).fetchone()
    tu = db.execute("SELECT * FROM users WHERE username = ?", (to_user,)).fetchone()
    if not fu or not tu:
        return jsonify({"error":"sender or receiver not found"}), 404
    if fu["balance"] < amount:
        return jsonify({"error":"insufficient funds"}), 400
    db.execute("UPDATE users SET balance = balance - ? WHERE id = ?", (amount, fu["id"]))
    db.execute("UPDATE users SET balance = balance + ? WHERE id = ?", (amount, tu["id"]))
    db.execute("INSERT INTO transactions (from_user, to_user, amount, description) VALUES (?, ?, ?, ?)",
               (fu["id"], tu["id"], amount, "transfer"))
    db.commit()
    return jsonify({"status":"ok","from":from_user,"to":to_user,"amount":amount})

@app.route("/balance/<username>", methods=["GET"])
def balance(username):
    db = get_db()
    u = db.execute("SELECT username, balance FROM users WHERE username = ?", (username,)).fetchone()
    if not u:
        return jsonify({"error":"user not found"}), 404
    return jsonify({"username":u["username"], "balance":u["balance"]})

@app.route("/transactions/<username>", methods=["GET"])
def transactions(username):
    db = get_db()
    u = db.execute("SELECT id FROM users WHERE username = ?", (username,)).fetchone()
    if not u:
        return jsonify({"error":"user not found"}), 404
    uid = u["id"]
    rows = db.execute("""SELECT id, from_user, to_user, amount, timestamp, description FROM transactions
                         WHERE from_user = ? OR to_user = ? ORDER BY timestamp DESC""", (uid, uid)).fetchall()
    def user_of(uid):
        if uid is None:
            return None
        r = db.execute("SELECT username FROM users WHERE id = ?", (uid,)).fetchone()
        return r["username"] if r else None
    results = []
    for r in rows:
        results.append({
            "id": r["id"],
            "from": user_of(r["from_user"]),
            "to": user_of(r["to_user"]),
            "amount": r["amount"],
            "timestamp": r["timestamp"],
            "description": r["description"]
        })
    return jsonify(results)

if __name__ == "__main__":
    init_db()
    print("Database initialized at", DB_PATH)
    app.run(port=5000, debug=True)
