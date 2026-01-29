from flask import Flask, request, jsonify, render_template, session, redirect, url_for
from flask_discord import DiscordOAuth2Session
from flask_cors import CORS
import json, os, time, secrets

app = Flask(__name__)
CORS(app)

# --- SECURITY & AUTH CONFIG ---
app.secret_key = os.environ.get("SECRET_KEY", secrets.token_hex(32))
app.config["DISCORD_CLIENT_ID"] = "1466079509177438383"
app.config["DISCORD_CLIENT_SECRET"] = os.environ.get("DISCORD_CLIENT_SECRET")
app.config["DISCORD_REDIRECT_URI"] = "https://admin-system-mj0v.onrender.com/callback"

# This must be identical in your Roblox Script!
STXN_INTERNAL_KEY = os.environ.get("STXN_API_KEY", "STXN-PRO-SECURE-2026")

discord = DiscordOAuth2Session(app)
DB_FILE = "database.json"
MASTER_DISCORD_ID = "1463540341473804485"

def load_db():
    if not os.path.exists(DB_FILE): 
        return {"users": {}, "games": {}, "logs": []}
    with open(DB_FILE, "r") as f:
        try: return json.load(f)
        except: return {"users": {}, "games": {}, "logs": []}

def save_db(data):
    with open(DB_FILE, "w") as f: 
        json.dump(data, f, indent=4)

@app.route('/')
def home():
    if not discord.authorized: return render_template('login.html')
    db = load_db()
    uid = str(session.get('user_id'))
    role = "master" if uid == MASTER_DISCORD_ID else "client"
    if uid not in db['users'] and role != "master":
        return "Access Denied: Your Discord account is not licensed.", 403
    user_data = db['users'].get(uid, {"gid": "None", "name": "Unknown"})
    return render_template('dashboard.html', user=session.get('username'), role=role, gid=user_data['gid'], all_users=db['users'], logs=db['logs'])

@app.route('/login')
def login(): return discord.create_session(scope=["identify"])

@app.route('/callback')
def callback():
    discord.callback()
    user = discord.fetch_user()
    session['user_id'], session['username'] = str(user.id), user.username
    return redirect(url_for('home'))

@app.route('/api/poll', methods=['POST'])
def roblox_poll():
    if request.headers.get("X-STXN-KEY") != STXN_INTERNAL_KEY:
        return jsonify({"error": "Unauthorized"}), 403
    db = load_db()
    req = request.json
    gid = str(req.get("gameId"))
    if gid in db['games']:
        db['games'][gid]['players'] = req.get("players", [])
        db['games'][gid]['last_heartbeat'] = time.time()
        cmd = db['games'][gid].get('cmds', {})
        db['games'][gid]['cmds'] = {} 
        save_db(db)
        return jsonify(cmd)
    return jsonify({"error": "GID Not Registered"}), 404

@app.route('/api/command', methods=['POST'])
def set_command():
    if not discord.authorized: return "Login Required", 401
    db = load_db()
    uid = session.get('user_id')
    gid = db['users'].get(uid, {}).get('gid')
    if not gid or gid == "None": return "No GID linked", 403
    data = request.json
    db['games'][gid]['cmds'] = {"action": data.get('action'), "target": data.get('target'), "msg": data.get('msg', '')}
    db['logs'].insert(0, {"time": time.strftime("%H:%M:%S"), "user": session.get('username'), "action": data.get('action'), "target": data.get('target')})
    db['logs'] = db['logs'][:50]
    save_db(db)
    return jsonify({"success": True})

@app.route('/api/data')
def get_data():
    if not discord.authorized: return jsonify({"error": "Auth"}), 401
    db = load_db()
    gid = db['users'].get(session.get('user_id'), {}).get('gid', 'None')
    game_data = db['games'].get(gid, {"players": [], "last_heartbeat": 0})
    game_data['is_online'] = (time.time() - game_data.get('last_heartbeat', 0)) < 20
    return jsonify(game_data)

@app.route('/master/assign', methods=['POST'])
def assign():
    if session.get('user_id') != MASTER_DISCORD_ID: return "Forbidden", 403
    db = load_db()
    data = request.json
    uid, gid, name = str(data['discord_id']), str(data['game_id']), data['username']
    db['users'][uid] = {"gid": gid, "name": name}
    if gid not in db['games']: db['games'][gid] = {"players": [], "cmds": {}, "last_heartbeat": 0}
    save_db(db)
    return jsonify({"success": True})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 5000)))
