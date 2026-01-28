from flask import Flask, request, jsonify, render_template, session, redirect, url_for
from flask_discord import DiscordOAuth2Session
import json, os

app = Flask(__name__)
app.secret_key = "NEON_CYBER_2026"
os.environ["OAUTHLIB_INSECURE_TRANSPORT"] = "true" # Only for local testing

# --- DISCORD CONFIGURATION ---
# Get these from the Discord Developer Portal
app.config["DISCORD_CLIENT_ID"] = "1466079509177438383"
app.config["DISCORD_CLIENT_SECRET"] = "3kMJQyeLFWXo_n4jWu2k-P4M2J_PEdv8"
app.config["DISCORD_REDIRECT_URI"] = "https://admin-system-mj0v.onrender.com/callback"

discord = DiscordOAuth2Session(app)
DB_FILE = "database.json"
MASTER_DISCORD_ID = "1463540341473804485" # Your ID to see the Master Dashboard

def load_db():
    if not os.path.exists(DB_FILE):
        return {"users": {}, "games": {}}
    with open(DB_FILE, "r") as f: return json.load(f)

def save_db(data):
    with open(DB_FILE, "w") as f: json.dump(data, f, indent=4)

@app.route('/login')
def login():
    return discord.create_session()

@app.route('/callback')
def callback():
    discord.callback()
    user = discord.fetch_user()
    session['user_id'] = str(user.id)
    session['username'] = user.username
    return redirect(url_for('home'))

@app.route('/')
def home():
    if not discord.authorized:
        return render_template('login.html')
    
    db = load_db()
    uid = session['user_id']
    role = "master" if uid == MASTER_DISCORD_ID else "client"
    
    # Check what Game ID this Discord user is allowed to manage
    user_data = db['users'].get(uid, {"gid": "None"})
    return render_template('dashboard.html', user=session['username'], role=role, gid=user_data['gid'])

@app.route('/master/assign', methods=['POST'])
def assign_game():
    if session.get('user_id') != MASTER_DISCORD_ID: return "Unauthorized", 401
    db = load_db()
    data = request.json
    target_uid = data['discord_id']
    target_gid = data['game_id']
    
    db['users'][target_uid] = {"gid": target_gid}
    # Initialize the game slot if it doesn't exist
    if target_gid not in db['games']:
        db['games'][target_gid] = {"players": [], "cmds": {}}
        
    save_db(db)
    return jsonify({"success": True})

@app.route('/api/data')
def get_data():
    if not discord.authorized: return jsonify({"error": "Auth"}), 401
    db = load_db()
    uid = session['user_id']
    gid = db['users'].get(uid, {}).get('gid', 'None')
    return jsonify(db['games'].get(gid, {"players": []}))
    
if __name__ == '__main__':
port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
