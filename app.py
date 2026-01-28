from flask import Flask, request, jsonify, render_template, session, redirect, url_for
from flask_discord import DiscordOAuth2Session
from flask_cors import CORS
import json, os, time

app = Flask(__name__)
CORS(app)

# --- SECURITY & CONFIG ---
# On Render, add these in the "Environment" tab
app.secret_key = os.environ.get("SECRET_KEY", "CYBER_OS_ULTIMATE_2026")
os.environ["OAUTHLIB_INSECURE_TRANSPORT"] = "true" 

app.config["DISCORD_CLIENT_ID"] = "1466079509177438383"
app.config["DISCORD_CLIENT_SECRET"] = os.environ.get("DISCORD_CLIENT_SECRET")
app.config["DISCORD_REDIRECT_URI"] = "https://admin-system-mj0v.onrender.com/callback"

discord = DiscordOAuth2Session(app)
DB_FILE = "database.json"
MASTER_DISCORD_ID = "1463540341473804485"

def load_db():
    if not os.path.exists(DB_FILE): return {"users": {}, "games": {}}
    with open(DB_FILE, "r") as f:
        try: return json.load(f)
        except: return {"users": {}, "games": {}}

def save_db(data):
    with open(DB_FILE, "w") as f: json.dump(data, f, indent=4)

# --- ROUTES ---

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

@app.route('/login')
def login():
    return discord.create_session(scope=["identify"])

@app.route('/callback')
def callback():
    try:
        discord.callback()
        user = discord.fetch_user()
        session['user_id'] = str(user.id)
        session['username'] = user.username
        return redirect(url_for('home'))
    except Exception as e:
        return f"Auth Error: Ensure your Client Secret and Redirect URI match perfectly. Error: {str(e)}"

@app.route('/master/assign', methods=['POST'])
def assign_game():
    if session.get('user_id') != MASTER_DISCORD_ID: return "Forbidden", 403
    db = load_db()
    data = request.json
    uid, gid, name = str(data['discord_id']), str(data['game_id']), data.get('username', 'N/A')
    
    db['users'][uid] = {"gid": gid, "name": name}
    if gid not in db['games']:
        db['games'][gid] = {"players": [], "cmds": {}, "last_heartbeat": 0}
    
    save_db(db)
    return jsonify({"success": True})

@app.route('/api/command', methods=['POST'])
def set_command():
    if not discord.authorized: return "Unauthorized", 401
    db = load_db()
    uid = session.get('user_id')
    gid = db['users'].get(uid, {}).get('gid')
    
    if not gid or gid == "None": return "No Game Assigned", 400
    
    data = request.json
    db['games'][gid]['cmds'] = {
        "target": data.get('target', 'all'),
        "action": data.get('action'),
        "msg": data.get('msg', ''),
        "timestamp": time.time()
    }
    save_db(db)
    return jsonify({"success": True})

@app.route('/api/data')
def get_data():
    if not discord.authorized: return jsonify({"error": "Auth"}), 401
    db = load_db()
    gid = db['users'].get(session.get('user_id'), {}).get('gid', 'None')
    game_data = db['games'].get(gid, {"players": [], "last_heartbeat": 0})
    
    # Check if server is "Alive" (Active in last 15 seconds)
    game_data['is_online'] = (time.time() - game_data.get('last_heartbeat', 0)) < 15
    return jsonify(game_data)

@app.route('/api/poll', methods=['POST'])
def roblox_poll():
    db = load_db()
    req = request.json
    gid = str(req.get("gameId"))
    if gid in db['games']:
        db['games'][gid]['players'] = req.get("players", [])
        db['games'][gid]['last_heartbeat'] = time.time()
        save_db(db)
        
        cmd = db['games'][gid]['cmds']
        db['games'][gid]['cmds'] = {} # Clear after sending
        save_db(db)
        return jsonify(cmd)
    return jsonify({"error": "Unauthorized GID"}), 403

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
