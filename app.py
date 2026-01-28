from flask import Flask, request, jsonify, render_template, session, redirect, url_for
from flask_discord import DiscordOAuth2Session
from flask_cors import CORS
import json, os, time

app = Flask(__name__)
CORS(app)

# --- SECURITY CONFIG ---
app.secret_key = os.environ.get("SECRET_KEY", "SUPER_SECRET_NEON_KEY")
os.environ["OAUTHLIB_INSECURE_TRANSPORT"] = "true" 

app.config["DISCORD_CLIENT_ID"] = "1466079509177438383"
app.config["DISCORD_CLIENT_SECRET"] = "YOUR_NEW_RESET_SECRET" # RESET THIS IN DEV PORTAL!
app.config["DISCORD_REDIRECT_URI"] = "https://admin-system-mj0v.onrender.com/callback"

discord = DiscordOAuth2Session(app)
DB_FILE = "database.json"
MASTER_DISCORD_ID = "1463540341473804485" 

# --- DATABASE HELPERS ---
def load_db():
    if not os.path.exists(DB_FILE): return {"users": {}, "games": {}, "logs": []}
    with open(DB_FILE, "r") as f: 
        try: return json.load(f)
        except: return {"users": {}, "games": {}, "logs": []}

def save_db(data):
    with open(DB_FILE, "w") as f: json.dump(data, f, indent=4)

# --- ANTI-ABUSE: RATE LIMITING ---
user_last_request = {}
def is_spamming(uid):
    now = time.time()
    if uid in user_last_request and (now - user_last_request[uid]) < 0.5: # 0.5 second cooldown
        return True
    user_last_request[uid] = now
    return False

@app.route('/login')
def login():
    return discord.create_session(scope=["identify"])

@app.route('/callback')
def callback():
    discord.callback()
    user = discord.fetch_user()
    session['user_id'] = str(user.id)
    session['username'] = user.username
    return redirect(url_for('home'))

@app.route('/')
def home():
    if not discord.authorized: return render_template('login.html')
    db = load_db()
    uid = session.get('user_id')
    role = "master" if uid == MASTER_DISCORD_ID else "client"
    user_data = db['users'].get(uid, {"gid": "None"})
    # Passing the whole user list to the master so you can see passwords/IDs
    all_users = db['users'] if role == "master" else {}
    return render_template('dashboard.html', user=session.get('username'), role=role, gid=user_data['gid'], all_users=all_users)

@app.route('/master/assign', methods=['POST'])
def assign_game():
    if session.get('user_id') != MASTER_DISCORD_ID: return "Forbidden", 403
    db = load_db()
    data = request.json
    db['users'][str(data['discord_id'])] = {"gid": str(data['game_id']), "name": data.get('username', 'Unknown')}
    if str(data['game_id']) not in db['games']:
        db['games'][str(data['game_id'])] = {"players": [], "cmds": {}}
    save_db(db)
    return jsonify({"success": True})

@app.route('/api/poll', methods=['POST'])
def roblox_poll():
    # Only allow registered Game IDs to poll to prevent host abuse
    db = load_db()
    req = request.json
    gid = str(req.get("gameId"))
    if gid in db['games']:
        db['games'][gid]['players'] = req.get("players", [])
        save_db(db)
        return jsonify(db['games'][gid]['cmds'])
    return jsonify({"error": "Unauthorized Game ID"}), 403

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
