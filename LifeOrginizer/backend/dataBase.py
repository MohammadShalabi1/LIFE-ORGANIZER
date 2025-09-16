from flask import Flask, request, jsonify
from flask_cors import CORS
import mysql.connector
import datetime
import hashlib
from google import genai

# ================= FLASK APP ================= #
app = Flask(__name__)
CORS(app)

# ================= GEMINI CLIENT ================= #
client = genai.Client(api_key="AIzaSyD4IcFq0ctSfJcocvc_5E5IDN6OEq9aeKg")  # <-- replace with your key

def coaching_agent(message):
    prompt = f"""
    You are a world-class productivity and financial coach. 
    Your mission is to give short, clear, and practical answers (2–4 sentences max). 
    Always focus on helping the user optimize their daily tasks and expenses based on their priorities. 
    Be supportive but direct, avoid long explanations or generic motivation. 
    If tasks are mentioned, suggest ways to prioritize, simplify, or delegate them. 
    If expenses are mentioned, suggest how to cut costs, invest wisely, or align spending with goals. 
    Only provide actionable advice tailored to the message. 

    Here is the message you need to respond to:
    {message}
    """
    response = client.models.generate_content(
        model="gemini-2.5-flash",
        contents=prompt
    )
    return response.text

@app.route("/ask", methods=["POST"])
def ask_ai():
    data = request.get_json()
    user_message = data.get("message", "")
    if not user_message:
        return jsonify({"error": "Message is required"}), 400

    ai_response = coaching_agent(user_message)
    return jsonify({"response": ai_response})

# ================= DB CONNECTION ================= #
def get_db():
    return mysql.connector.connect(
        host="127.0.0.1",
        port=3307,
        user="root",
        password="HASSAN123321hassan",   # <-- replace with your DB password
        database="Lifeorgnizer"
    )

# ================= AUTH ================= #
@app.route("/register", methods=["POST"])
def register():
    data = request.json
    name = data.get("name")
    email = data.get("email")
    password = data.get("password")
    if not name or not email or not password:
        return jsonify({"status": "error", "message": "All fields are required"}), 400

    hashed = hashlib.sha256(password.encode()).hexdigest()

    con = get_db()
    cur = con.cursor()
    try:
        cur.execute(
            "INSERT INTO users (full_name, email, password) VALUES (%s,%s,%s)",
            (name, email, hashed)
        )
        con.commit()
        return jsonify({"status": "ok", "message": "User registered successfully"})
    except mysql.connector.IntegrityError:
        return jsonify({"status": "error", "message": "Email already exists"}), 400
    finally:
        cur.close()
        con.close()

@app.route("/login", methods=["POST"])
def login():
    data = request.json
    email = data.get("email")
    password = data.get("password")
    if not email or not password:
        return jsonify({"status": "error", "message": "Email and password required"}), 400

    hashed = hashlib.sha256(password.encode()).hexdigest()
    con = get_db()
    cur = con.cursor(dictionary=True)
    cur.execute(
        "SELECT id, full_name FROM users WHERE email=%s AND password=%s",
        (email, hashed)
    )
    user = cur.fetchone()
    cur.close()
    con.close()

    if user:
        return jsonify({"status": "ok", "user_id": user["id"], "name": user["full_name"]})
    else:
        return jsonify({"status": "error", "message": "Invalid email or password"}), 401

# ================= TASKS ================= #
@app.route("/tasks", methods=["GET", "POST"])
def tasks():
    con = get_db()
    cur = con.cursor(dictionary=True)

    if request.method == "GET":
        user_id = request.args.get("user_id")
        date = request.args.get("date", datetime.date.today().isoformat())
        cur.execute("SELECT * FROM tasks WHERE user_id=%s AND date=%s", (user_id, date))
        rows = cur.fetchall()
        cur.close()
        con.close()
        return jsonify(rows)

    if request.method == "POST":
        data = request.json
        cur.execute(
            "INSERT INTO tasks (user_id, date, name, hours) VALUES (%s,%s,%s,%s)",
            (data["user_id"], data["date"], data["name"], data["hours"])
        )
        con.commit()
        cur.close()
        con.close()
        return jsonify({"status": "ok"})

@app.route("/tasks/<int:task_id>", methods=["DELETE"])
def delete_task(task_id):
    con = get_db()
    cur = con.cursor()
    cur.execute("DELETE FROM tasks WHERE id=%s", (task_id,))
    con.commit()
    cur.close()
    con.close()
    return jsonify({"status": "deleted"})

# ================= EXPENSES ================= #
@app.route("/expenses", methods=["GET", "POST"])
def expenses():
    con = get_db()
    cur = con.cursor(dictionary=True)

    if request.method == "GET":
        user_id = request.args.get("user_id")
        date = request.args.get("date", datetime.date.today().isoformat())
        cur.execute("SELECT * FROM expenses WHERE user_id=%s AND date=%s", (user_id, date))
        rows = cur.fetchall()
        cur.close()
        con.close()
        return jsonify(rows)

    if request.method == "POST":
        data = request.json
        cur.execute(
            "INSERT INTO expenses (user_id, date, name, amount) VALUES (%s,%s,%s,%s)",
            (data["user_id"], data["date"], data["name"], data["amount"])
        )
        con.commit()
        cur.close()
        con.close()
        return jsonify({"status": "ok"})

@app.route("/expenses/<int:expense_id>", methods=["DELETE"])
def delete_expense(expense_id):
    con = get_db()
    cur = con.cursor()
    cur.execute("DELETE FROM expenses WHERE id=%s", (expense_id,))
    con.commit()
    cur.close()
    con.close()
    return jsonify({"status": "deleted"})

# ================= GET ALL DATA ================= #
@app.route("/all_data/<int:user_id>", methods=["GET"])
def all_data(user_id):
    con = get_db()
    cur = con.cursor(dictionary=True)

    # Get all tasks
    cur.execute("SELECT * FROM tasks WHERE user_id=%s", (user_id,))
    tasks = cur.fetchall()

    # Get all expenses
    cur.execute("SELECT * FROM expenses WHERE user_id=%s", (user_id,))
    expenses = cur.fetchall()

    cur.close()
    con.close()

    # Organize by date
    daily_data = {}
    for t in tasks:
        date = t["date"].isoformat()
        if date not in daily_data:
            daily_data[date] = {"tasks": [], "expenses": []}
        daily_data[date]["tasks"].append({"name": t["name"], "hours": t["hours"], "id": t["id"]})

    for e in expenses:
        date = e["date"].isoformat()
        if date not in daily_data:
            daily_data[date] = {"tasks": [], "expenses": []}
        daily_data[date]["expenses"].append({"name": e["name"], "amount": e["amount"], "id": e["id"]})

    return jsonify(daily_data)

# ================= RUN ================= #
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
