from flask import Flask, request, jsonify, render_template, session, redirect, url_for
from flask_discord import DiscordOAuth2Session
from flask_cors import CORS
import json, os

app = Flask(__name__)
CORS(app)

# --- SECURITY ---
app.secret_key = os.environ.get("SECRET_KEY", "NEON_CYBER_2026_PRO")
os.environ["OAUTHLIB_INSECURE_TRANSPORT"] = "true" 

# --- DISCORD CONFIG ---
app.config["DISCORD_CLIENT_ID"] = "1466079509177438383"
app.config["DISCORD_CLIENT_SECRET"] = "PASTE_YOUR_NEW_RESET_SECRET_HERE"
app.config["DISCORD_REDIRECT_URI"] = "https://admin-system-mj0v.onrender.com/callback"

discord = DiscordOAuth2Session(app)
DB_FILE = "database.json"
MASTER_DISCORD_ID = "1463540341473804485" 

def load_db():
    if not os.path.exists(DB_FILE):
        return {"users": {}, "games": {}}
    with open(DB_FILE, "r") as f:
        try: return json.load(f)
        except: return {"users": {}, "games": {}}

def save_db(data):
    with open(DB_FILE, "w") as f: json.dump(data, f, indent=4)

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
    if not discord.authorized:
        return render_template('login.html')
    
    db = load_db()
    uid = session.get('user_id')
    role = "master" if uid == MASTER_DISCORD_ID else "client"
    user_data = db['users'].get(uid, {"gid": "None", "name": "Unknown"})
    
    return render_template('dashboard.html', 
                           user=session.get('username'), 
                           role=role, 
                           gid=user_data['gid'],
                           all_users=db['users'] if role == "master" else {})

@app.route('/master/assign', methods=['POST'])
def assign_game():
    if session.get('user_id') != MASTER_DISCORD_ID: return "Forbidden", 403
    db = load_db()
    data = request.json
    uid, gid, name = str(data['discord_id']), str(data['game_id']), data.get('username', 'N/A')
    
    db['users'][uid] = {"gid": gid, "name": name}
    if gid not in db['games']:
        db['games'][gid] = {"players": [], "cmds": {"target": "", "action": "", "msg": ""}}
    
    save_db(db)
    return jsonify({"success": True})

@app.route('/api/data')
def get_data():
    if not discord.authorized: return jsonify({"error": "Auth"}), 401
    db = load_db()
    gid = db['users'].get(session.get('user_id'), {}).get('gid', 'None')
    return jsonify(db['games'].get(gid, {"players": []}))

@app.route('/api/poll', methods=['POST'])
def roblox_poll():
    db = load_db()
    req = request.json
    gid = str(req.get("gameId"))
    if gid in db['games']:
        db['games'][gid]['players'] = req.get("players", [])
        save_db(db)
        # Returns and then clears the command to prevent repeat actions
        cmd = db['games'][gid]['cmds']
        db['games'][gid]['cmds'] = {"target": "", "action": "", "msg": ""}
        save_db(db)
        return jsonify(cmd)
    return jsonify({"error": "Unauthorized Game ID"}), 403

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
