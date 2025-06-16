# SAGA App - MVP with Admin Tools and External Templates
from flask import Flask, request, jsonify, render_template, redirect, url_for, session
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
import os

app = Flask(__name__)
app.secret_key = 'your_secret_key_here'

# In-memory databases (for testing only)
users_db = {}  # {email: {password_hash: str, username: str, entries: list, messages: list, private_videos: list, notes: str, links: list}}
public_videos = []  # List of public video dicts: {title, url}

# Auto-create admin account for development
users_db["admin@thelegacyforge.com"] = {
    "password_hash": generate_password_hash("admin123"),
    "username": "Admin",
    "entries": [],
    "messages": [],
    "private_videos": [],
    "notes": "",
    "links": []
}

# Ensure templates directory exists
os.makedirs("templates", exist_ok=True)

@app.route("/")
def home():
    if not session.get('user'):
        return render_template("home.html", entries=[])

    user_email = session['user']
    if user_email not in users_db:
        return f"User not found in database: {user_email}. Please <a href='/logout'>log out</a> and sign up again."

    user_data = users_db[user_email]
    entries = user_data['entries']
    messages = user_data.get('messages', [])
    private_videos = user_data.get('private_videos', [])

    return render_template("home.html", entries=entries, messages=messages, private_videos=private_videos, public_videos=public_videos)

@app.route("/signup", methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        email = request.form['email']
        username = request.form['username']
        password = request.form['password']
        if email in users_db:
            return "User already exists. <a href='/signup'>Try again</a>"
        users_db[email] = {
            'password_hash': generate_password_hash(password),
            'username': username,
            'entries': [],
            'messages': [],
            'private_videos': [],
            'notes': '',
            'links': []
        }
        session['user'] = email
        return redirect(url_for('home'))
    return render_template("signup.html")

@app.route("/login", methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        input_id = request.form['email']  # could be email or username
        password = request.form['password']

        # Dev shortcut for admin login
        if input_id == "admin@thelegacyforge.com":
            session['user'] = input_id
            return redirect(url_for('admin_dashboard'))

        # Try to find the user by email or username
        user_email = None
        for email, data in users_db.items():
            if email == input_id or data.get('username') == input_id:
                user_email = email
                break

        # Validate credentials
        if user_email and check_password_hash(users_db[user_email]['password_hash'], password):
            session['user'] = user_email
            return redirect(url_for('home'))

        return "Invalid credentials. <a href='/login'>Try again</a>"

    return render_template("login.html")

@app.route("/logout")
def logout():
    session.pop('user', None)
    return redirect(url_for('home'))

@app.route("/checkin", methods=["POST"])
def check_in():
    if not session.get('user'):
        return redirect(url_for('login'))

    user_email = session['user']
    if user_email not in users_db:
        return "Error: User not found in system. Please sign up again."

    summary = request.form.get("summary")
    entry = {
        "date": datetime.now().isoformat(),
        "summary": summary
    }
    users_db[user_email]['entries'].append(entry)
    return redirect(url_for('home'))

@app.route("/prompt", methods=["GET"])
def get_prompt():
    prompts = [
        "What did today teach you?",
        "Share a breakthrough moment.",
        "What challenge did you face and how did you respond?",
        "Describe a memory that shaped you.",
        "What story are you rewriting by showing up today?"
    ]
    import random
    return jsonify({"prompt": random.choice(prompts)})

@app.route("/admin")
def admin_dashboard():
    if session.get('user') != 'admin@thelegacyforge.com':
        return redirect(url_for('login'))

    user_stats = [
        {
            "email": email,
            "username": data.get('username', '—'),
            "total_entries": len(data['entries']),
            "last_entry": data['entries'][-1]['date'] if data['entries'] else 'N/A'
        }
        for email, data in users_db.items()
    ]
    return render_template("admin.html", user_stats=user_stats)

@app.route("/admin/message", methods=["POST"])
def send_message():
    if session.get('user') != 'admin@thelegacyforge.com':
        return "Unauthorized", 403

    target_email = request.form.get('email')
    message = request.form.get('message')
    if target_email in users_db:
        users_db[target_email].setdefault('messages', []).append({
            "text": message,
            "timestamp": datetime.now().isoformat()
        })
        return f"Message sent to {target_email}!"
    return "User not found.", 404

@app.route("/admin/video", methods=["POST"])
def post_video():
    if session.get('user') != 'admin@thelegacyforge.com':
        return "Unauthorized", 403

    visibility = request.form.get('visibility')  # 'public' or 'private'
    title = request.form.get('title')
    url = request.form.get('url')
    target_email = request.form.get('email')

    video = {"title": title, "url": url, "timestamp": datetime.now().isoformat()}

    if visibility == 'public':
        public_videos.append(video)
        return "Public video added."
    elif visibility == 'private' and target_email in users_db:
        users_db[target_email].setdefault('private_videos', []).append(video)
        return f"Private video added for {target_email}."
    else:
        return "Invalid request.", 400

@app.route("/admin/manage", methods=["GET", "POST"])
def manage_seekers():
    if session.get('user') != 'admin@thelegacyforge.com':
        return redirect(url_for('login'))

    if request.method == 'POST':
        email = request.form['email']
        username = request.form['username']
        entries = int(request.form.get('entries', 0))
        notes = request.form.get('notes', '')
        links = request.form.get('links', '').split(',')
        if email not in users_db:
            users_db[email] = {
                'password_hash': generate_password_hash('manualUser123'),
                'username': username,
                'entries': [{"date": datetime.now().isoformat(), "summary": "Manual Entry"}] * entries,
                'messages': [],
                'private_videos': [],
                'notes': notes,
                'links': links
            }
    return render_template("manage.html", users=users_db)

import os

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
