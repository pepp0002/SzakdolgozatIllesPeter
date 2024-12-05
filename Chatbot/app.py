from flask import Flask, render_template, request, jsonify, redirect, url_for, session
import mysql.connector
import requests
import os
from werkzeug.security import generate_password_hash, check_password_hash

RASA_API_URL = 'http://localhost:5005/webhooks/rest/webhook'
app = Flask(__name__)
app.secret_key = os.urandom(24)  # Biztonságos kulcs a munkamenethez

# MySQL adatbázis kapcsolat beállítása
user_db_config = {
    'host': 'localhost',
    'user': 'root',
    'password': '',
    'database': 'chatbot_users'
}

ticket_db_config = {
    'host': 'localhost',
    'user': 'root',
    'password': '',
    'database': 'adat'
}

# Adatbázis kapcsolat létrehozása
def get_user_db_connection():
    return mysql.connector.connect(**user_db_config)

def get_ticket_db_connection():
    return mysql.connector.connect(**ticket_db_config)

# Főoldal, amely elérhető a bejelentkezés után
@app.route('/')
def home():
    if 'logged_in' in session:
        if session.get('role') == 'admin':
            return redirect(url_for('admin_dashboard'))
        return render_template('index.html')
    return redirect(url_for('login'))

# Admin felület
@app.route('/admin')
def admin_dashboard():
    if 'logged_in' in session and session.get('role') == 'admin':
        connection = get_ticket_db_connection()
        cursor = connection.cursor(dictionary=True)
        cursor.execute("SELECT * FROM adatok WHERE status = 'nyitott'")
        tickets = cursor.fetchall()
        cursor.close()
        connection.close()
        return render_template('admin.html', tickets=tickets)
    return redirect(url_for('login'))

# Megoldott hibajegyek megtekintése
@app.route('/solved_tickets')
def solved_tickets():
    if 'logged_in' in session and session.get('role') == 'admin':
        connection = get_ticket_db_connection()
        cursor = connection.cursor(dictionary=True)
        cursor.execute("SELECT * FROM adatok WHERE status = 'zárt'")
        solved_tickets = cursor.fetchall()
        cursor.close()
        connection.close()
        return render_template('solved_tickets.html', tickets=solved_tickets)
    return redirect(url_for('login'))

# Hibajegy frissítése státusz és megjegyzés hozzáadásával
@app.route('/update_status/<int:ticket_id>', methods=['POST'])
def update_status(ticket_id):
    if 'logged_in' not in session or session.get('role') != 'admin':
        return redirect(url_for('login'))

    status = request.form.get('status')
    admin_comments = request.form.get('admin_comments')

    if not admin_comments and status == 'zárt':
        return "Admin megjegyzés szükséges a lezáráshoz.", 400

    connection = get_ticket_db_connection()
    cursor = connection.cursor()
    cursor.execute("UPDATE adatok SET status = %s, admin_comments = %s WHERE id = %s",
                   (status, admin_comments, ticket_id))
    connection.commit()
    cursor.close()
    connection.close()

    return redirect(url_for('admin_dashboard'))

# Bejelentkezés
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        connection = get_user_db_connection()
        cursor = connection.cursor(dictionary=True)
        cursor.execute("SELECT * FROM users WHERE username = %s", (username,))
        user = cursor.fetchone()
        cursor.close()
        connection.close()

        if user and check_password_hash(user['password'], password):
            session['logged_in'] = True
            session['username'] = username
            session['role'] = user['role']
            return redirect(url_for('home'))
        else:
            return "Hibás felhasználónév vagy jelszó."
    return render_template('login.html')

# Regisztráció
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        hashed_password = generate_password_hash(password)
        role = request.form.get('role', 'user')  # Alapértelmezett érték user

        connection = get_user_db_connection()
        cursor = connection.cursor()
        cursor.execute("INSERT INTO users (username, password, role) VALUES (%s, %s, %s)",
                       (username, hashed_password, role))
        connection.commit()
        cursor.close()
        connection.close()

        return redirect(url_for('login'))
    return render_template('register.html')

# Kijelentkezés
@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

# Webhook endpoint a Rasa chatbot kommunikációhoz
@app.route('/webhook', methods=['POST'])
def webhook():
    if 'logged_in' not in session:
        return jsonify({'error': 'Bejelentkezés szükséges!'}), 403

    user_message = request.json['message']
    rasa_response = requests.post(
        RASA_API_URL,
        json={'sender': 'user', 'message': user_message}
    )
    rasa_response_json = rasa_response.json()
    bot_responses = [response.get('text', '') for response in rasa_response_json]
    return jsonify({'response': bot_responses})

if __name__ == "__main__":
    app.run(debug=True, port=3000)
