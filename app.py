from flask import Flask, request, jsonify, render_template, session, redirect, url_for
from flask_discord import DiscordOAuth2Session
from flask_cors import CORS
import json, os, time

app = Flask(__name__)
CORS(app)

# --- CONFIG ---
app.secret_key = os.environ.get("SECRET_KEY", "STXN_FINAL_SECURE_2026")
app.config["DISCORD_CLIENT_ID"] = "1466079509177438383"
app.config["DISCORD_CLIENT_SECRET"] = os.environ.get("DISCORD_CLIENT_SECRET")
app.config["DISCORD_REDIRECT_URI"] = "https://admin-system-mj0v.onrender.com/callback"

os.environ["OAUTHLIB_INSECURE_TRANSPORT"] = "true" 

discord = DiscordOAuth2Session(app)
DB_FILE = "database.json"
MASTER_DISCORD_ID = "1463540341473804485"

def load_db():
    if not os.path.exists(DB_FILE): return {"users": {}, "games": {}, "logs": []}
    with open(DB_FILE, "r") as f:
        try:
            db = json.load(f)
            now = time.time()
            for gid in list(db.get('games', {}).keys()):
                # Cleanup: If no poll in 45s, server is offline
                if now - db['games'][gid].get('last_heartbeat', 0) > 45:
                    db['games'][gid]['players'] = []
            return db
        except: return {"users": {}, "games": {}, "logs": []}

def save_db(data):
    with open(DB_FILE, "w") as f: json.dump(data, f, indent=4)

def add_log(user, action, target, gid):
    db = load_db()
    db['logs'].insert(0, {
        "time": time.strftime("%H:%M:%S"),
        "user": user,
        "action": action.upper(),
        "target": target,
        "gid": gid
    })
    db['logs'] = db['logs'][:30] # Keep logs light
    save_db(db)

# --- ROUTES ---

@app.route('/')
def home():
    if not discord.authorized: return render_template('login.html')
    db = load_db()
    uid = session.get('user_id')
    role = "master" if uid == MASTER_DISCORD_ID else "client"
    
    # Check if this user is registered in your system
    user_data = db['users'].get(uid)
    if not user_data and role != "master":
        return "Access Denied: You are not a registered STXN Client.", 403
    
    gid = user_data['gid'] if user_data else "NONE"
    return render_template('dashboard.html', user=session.get('username'), role=role, gid=gid, all_users=db['users'], logs=db['logs'])

@app.route('/login')
def login(): return discord.create_session(scope=["identify"])

@app.route('/callback')
def callback():
    discord.callback()
    user = discord.fetch_user()
    session['user_id'], session['username'] = str(user.id), user.username
    return redirect(url_for('home'))

@app.route('/api/command', methods=['POST'])
def set_command():
    if not discord.authorized: return "Unauthorized", 401
    db = load_db()
    uid = session.get('user_id')
    user_info = db['users'].get(uid)
    
    if not user_info and uid != MASTER_DISCORD_ID: return "Forbidden", 403
    gid = user_info['gid'] if uid != MASTER_DISCORD_ID else request.json.get('gid')
    
    if not gid: return "No GID", 400
    
    data = request.json
    db['games'][gid]['cmds'] = {"target": data['target'], "action": data['action'], "msg": data.get('msg', '')}
    save_db(db)
    add_log(session['username'], data['action'], data['target'], gid)
    return jsonify({"success": True})

@app.route('/api/poll', methods=['POST'])
def roblox_poll():
    db = load_db()
    req = request.json
    gid = str(req.get("gameId"))
    if gid in db['games']:
        db['games'][gid]['players'] = req.get("players", [])
        db['games'][gid]['last_heartbeat'] = time.time()
        save_db(db)
        cmd = db['games'][gid].get('cmds', {})
        db['games'][gid]['cmds'] = {} 
        save_db(db)
        return jsonify(cmd)
    return jsonify({"error": "Unauthorized GID"}), 403

@app.route('/api/data')
def get_data():
    if not discord.authorized: return jsonify({}), 401
    db = load_db()
    uid = session.get('user_id')
    gid = db['users'].get(uid, {}).get('gid', 'None')
    game_data = db['games'].get(gid, {"players": [], "last_heartbeat": 0})
    game_data['is_online'] = (time.time() - game_data.get('last_heartbeat', 0)) < 20
    return jsonify(game_data)

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

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 5000)))
