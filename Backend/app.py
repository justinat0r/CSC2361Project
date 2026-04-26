# ============================================================
#  Sendrr Webmail App -- Flask Backend (app.py)
#  Drop this file in your /Backend folder.
#  Run it with: python3 app.py
# ============================================================

from flask import Flask, request, jsonify, session, redirect, url_for, send_from_directory
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
import secrets
import pymysql
import os


app = Flask(__name__, static_folder="../Frontend")
app.secret_key = secrets.token_hex(32)  # used to encrypt session cookies
limiter = Limiter(
    key_func=get_remote_address,
    app=app,
    default_limits=["200 per day", "50 per hour"]
)
@app.errorhandler(429)
def ratelimit_handler(e):
    return jsonify({
        "error": "Too many requests. Please slow down."
    }), 429
# ============================================================
#  DATABASE CONNECTION
#  Change DB_USER and DB_PASSWORD tpip install flasko match your MySQL setup.
# ============================================================
DB_HOST = "localhost"
DB_USER = "root"        # change this if your MySQL user is different
DB_PASSWORD = "Firefly164"        # change this to your MySQL root password
DB_NAME = "sendrr"

def get_db():
    # Opens a fresh connection to the database for each request
    return pymysql.connect(
        host=DB_HOST,
        user=DB_USER,
        password=DB_PASSWORD,
        database=DB_NAME,
        cursorclass=pymysql.cursors.DictCursor  # returns rows as dictionaries
    )

def login_rate_limit_key():
    data = request.get_json(silent=True) or {}
    email = data.get("email", "")
    return f"{get_remote_address()}:{email}"
# ============================================================
#  SERVE HTML PAGES
#  These routes just send back the HTML files your group made.
# ============================================================

@app.route("/")
def index():
    # Root URL redirects to login
    return redirect(url_for("login_page"))

@app.route("/login")
def login_page():
    return send_from_directory("../Frontend", "login.html")

@app.route("/signup")
def signup_page():
    return send_from_directory("../Frontend", "signup.html")

@app.route("/inbox")
def inbox_page():
    if "user_id" not in session:
        return redirect(url_for("login_page"))
    return send_from_directory("../Frontend", "inbox.html")

@app.route("/admin")
def admin_page():
    if "user_id" not in session or not session.get("is_admin"):
        return redirect(url_for("login_page"))
    return send_from_directory("../Frontend", "adminpage.html")


# ============================================================
#  AUTHENTICATION ROUTES
# ============================================================

# SIGNUP -- creates a new user account
@app.route("/api/signup", methods=["POST"])
@limiter.limit("3 per minute")
@limiter.limit("10 per hour")
def signup():
    data = request.get_json()
    username = data.get("username")
    email = data.get("email")
    password = data.get("password")
    region = data.get("region", "NA")

    db = get_db()
    cursor = db.cursor()

    # Check if username or email already exists
    cursor.execute("SELECT user_id FROM users WHERE username = %s OR email = %s", (username, email))
    existing = cursor.fetchone()
    if existing:
        return jsonify({"error": "Username or email already taken"}), 400

    # Insert new user -- password stored plain text (intentionally insecure)
    cursor.execute(
        "INSERT INTO users (username, email, password, region) VALUES (%s, %s, %s, %s)",
        (username, email, password, region)
    )
    db.commit()
    db.close()
    return jsonify({"message": "Account created successfully"}), 201


# LOGIN -- checks credentials and starts a session
@app.route("/api/login", methods=["POST"])
@limiter.limit("5 per minute", key_func=login_rate_limit_key)
@limiter.limit("20 per hour", key_func=login_rate_limit_key)
def login():
    data = request.get_json()
    email = data.get("email")
    password = data.get("password")

    db = get_db()
    cursor = db.cursor()

    # Vulnerable query -- no hashing, plain text password comparison
    # Also vulnerable to SQL injection if you swap this for string formatting
    cursor.execute("SELECT * FROM users WHERE email = %s AND password = %s", (email, password))
    user = cursor.fetchone()

    if not user:
        return jsonify({"error": "Invalid email or password"}), 401

    # Save login to sessions table
    import secrets
    token = secrets.token_hex(32)
    cursor.execute(
        "INSERT INTO sessions (user_id, session_token, ip_address) VALUES (%s, %s, %s)",
        (user["user_id"], token, request.remote_addr)
    )
    db.commit()
    db.close()

    # Store user info in session cookie
    session["user_id"] = user["user_id"]
    session["username"] = user["username"]
    session["is_admin"] = user["is_admin"]

    if user["is_admin"]:
        return jsonify({"redirect": "/admin"})
    return jsonify({"redirect": "/inbox"})


# LOGOUT -- clears the session
@app.route("/api/logout", methods=["POST"])
def logout():
    session.clear()
    return jsonify({"redirect": "/login"})


# ============================================================
#  EMAIL ROUTES
# ============================================================

# SEND EMAIL -- logged in user sends a message to another account
@app.route("/api/send", methods=["POST"])
@limiter.limit("30 per minute")
def send_email():
    if "user_id" not in session:
        return jsonify({"error": "Not logged in"}), 401

    data = request.get_json()
    recipient_email = data.get("to")
    subject = data.get("subject", "(no subject)")
    body = data.get("body")

    db = get_db()
    cursor = db.cursor()

    # Look up recipient
    cursor.execute("SELECT user_id FROM users WHERE email = %s", (recipient_email,))
    recipient = cursor.fetchone()
    if not recipient:
        return jsonify({"error": "Recipient not found"}), 404

    cursor.execute(
        "INSERT INTO emails (sender_id, recipient_id, subject, body) VALUES (%s, %s, %s, %s)",
        (session["user_id"], recipient["user_id"], subject, body)
    )
    db.commit()
    db.close()
    return jsonify({"message": "Email sent"})


# INBOX -- returns all emails sent to the logged in user
@app.route("/api/inbox", methods=["GET"])
def inbox():
    if "user_id" not in session:
        return jsonify({"error": "Not logged in"}), 401

    db = get_db()
    cursor = db.cursor()
    cursor.execute("""
        SELECT e.email_id, u.username AS sender, e.subject, e.body, e.sent_at, e.is_read
        FROM emails e
        JOIN users u ON e.sender_id = u.user_id
        WHERE e.recipient_id = %s
        ORDER BY e.sent_at DESC
    """, (session["user_id"],))
    emails = cursor.fetchall()
    db.close()

    # Convert datetime to string so it can be sent as JSON
    for email in emails:
        email["sent_at"] = str(email["sent_at"])

    return jsonify(emails)


# ============================================================
#  ADMIN ROUTES
#  These are only accessible if is_admin = 1 in the session
# ============================================================

# GET ALL USERS -- admin panel user table with optional search
@app.route("/api/users", methods=["GET"])
def get_users():
    if not session.get("is_admin"):
        return jsonify({"error": "Unauthorized"}), 403

    search = request.args.get("search", "")
    db = get_db()
    cursor = db.cursor()

    # NOTE: this query is intentionally vulnerable to SQL injection
    # because the search term is dropped directly into the query string
    query = "SELECT user_id AS id, username AS name, email, region, is_admin, created_at FROM users WHERE username LIKE '%" + search + "%' OR email LIKE '%" + search + "%'"
    cursor.execute(query)
    users = cursor.fetchall()
    db.close()

    for user in users:
        user["created_at"] = str(user["created_at"])

    return jsonify(users)


# GET ALL MESSAGES -- admin panel messages table with optional search
@app.route("/api/messages", methods=["GET"])
def get_messages():
    if not session.get("is_admin"):
        return jsonify({"error": "Unauthorized"}), 403

    search = request.args.get("search", "")
    db = get_db()
    cursor = db.cursor()

    # Also intentionally vulnerable to SQL injection
    query = "SELECT email_id AS id, sender_id AS user_id, subject AS message, sent_at AS date FROM emails WHERE subject LIKE '%" + search + "%' OR body LIKE '%" + search + "%'"
    cursor.execute(query)
    messages = cursor.fetchall()
    db.close()

    for message in messages:
        message["date"] = str(message["date"])

    return jsonify(messages)


# GET LOGIN ACTIVITY -- admin panel sessions table
@app.route("/api/sessions", methods=["GET"])
def get_sessions():
    if not session.get("is_admin"):
        return jsonify({"error": "Unauthorized"}), 403

    db = get_db()
    cursor = db.cursor()
    cursor.execute("""
        SELECT s.session_id, u.username, u.email, s.ip_address, s.login_at, s.is_active
        FROM sessions s
        JOIN users u ON s.user_id = u.user_id
        ORDER BY s.login_at DESC
    """)
    sessions_data = cursor.fetchall()
    db.close()

    for s in sessions_data:
        s["login_at"] = str(s["login_at"])

    return jsonify(sessions_data)


# ============================================================
#  RUN THE APP
# ============================================================
if __name__ == "__main__":
    app.run(debug=True, port=5050)
