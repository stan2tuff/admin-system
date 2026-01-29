from flask import Flask, request, jsonify, render_template, session, redirect, url_for
from flask_discord import DiscordOAuth2Session
import json, os, time, secrets

app = Flask(__name__)

# --- STXN CONFIG ---
app.secret_key = os.environ.get("SECRET_KEY", secrets.token_hex(32))
app.config["DISCORD_CLIENT_ID"] = "1466079509177438383"
app.config["DISCORD_CLIENT_SECRET"] = os.environ.get("DISCORD_CLIENT_SECRET")
app.config["DISCORD_REDIRECT_URI"] = "https://admin-system-mj0v.onrender.com/callback"

# Security Key: Must match your Roblox Script!
STXN_KEY = os.environ.get("STXN_API_KEY", "STXN-SECURE-ACCESS-2026")
MASTER_ID = "1463540341473804485"
DB_FILE = "database.json"

discord = DiscordOAuth2Session(app)

def load_db():
    if not os.path.exists(DB_FILE):
        return {"users": {}, "games": {}, "logs": []}
    with open(DB_FILE, "r") as f:
        try: return json.load(f)
        except: return {"users": {}, "games": {}, "logs": []}

def save_db(db):
    with open(DB_FILE, "w") as f:
        json.dump(db, f, indent=4)

@app.route('/')
def home():
    if not discord.authorized: return render_template('login.html')
    db = load_db()
    uid = str(session.get('user_id'))
    if uid not in db['users'] and uid != MASTER_ID:
        return "Access Denied: You are not a licensed admin.", 403
    user_data = db['users'].get(uid, {"gid": "N/A", "name": "Admin"})
    return render_template('dashboard.html', user=session.get('username'), gid=user_data['gid'], logs=db['logs'], all_users=db['users'], role=("master" if uid == MASTER_ID else "client"))

@app.route('/login')
def login(): return discord.create_session(scope=["identify"])

@app.route('/callback')
def callback():
    discord.callback()
    user = discord.fetch_user()
    session['user_id'], session['username'] = str(user.id), user.username
    return redirect(url_for('home'))

@app.route('/api/poll', methods=['POST'])
def poll():
    if request.headers.get("X-STXN-KEY") != STXN_KEY: return "Forbidden", 403
    db = load_db()
    data = request.json
    gid = str(data.get("gameId"))
    
    if gid in db['games']:
        db['games'][gid]['players'] = data.get("players", [])
        db['games'][gid]['last_heartbeat'] = time.time()
        
        # Batch logging: process all events sent by Roblox
        for event in data.get("events", []):
            db['logs'].insert(0, {"time": time.strftime("%H:%M:%S"), "msg": event})
        
        db['logs'] = db['logs'][:30] # Anti-Abuse: Only store last 30 logs
        cmd = db['games'][gid].get('cmds', {})
        db['games'][gid]['cmds'] = {} 
        save_db(db)
        return jsonify(cmd)
    return "Invalid GID", 404

@app.route('/api/command', methods=['POST'])
def set_command():
    if not discord.authorized: return "Unauthorized", 401
    db = load_db()
    uid = str(session.get('user_id'))
    gid = db['users'].get(uid, {}).get('gid')
    if not gid or gid == "None": return "No GID linked", 403
    
    data = request.json
    db['games'][gid]['cmds'] = {"action": data['action'], "target": data['target'], "msg": data.get('msg', '')}
    save_db(db)
    return jsonify({"success": True})

@app.route('/api/data')
def get_data():
    if not discord.authorized: return jsonify({"error": "Auth"}), 401
    db = load_db()
    uid = str(session.get('user_id'))
    gid = db['users'].get(uid, {}).get('gid', 'None')
    game_data = db['games'].get(gid, {"players": [], "last_heartbeat": 0})
    game_data['is_online'] = (time.time() - game_data.get('last_heartbeat', 0)) < 25
    game_data['logs'] = db['logs']
    return jsonify(game_data)

@app.route('/master/assign', methods=['POST'])
def assign():
    if str(session.get('user_id')) != MASTER_ID: return "Forbidden", 403
    db = load_db()
    data = request.json
    uid, gid, name = str(data['discord_id']), str(data['game_id']), data['username']
    db['users'][uid] = {"gid": gid, "name": name}
    if gid not in db['games']: db['games'][gid] = {"players": [], "cmds": {}, "last_heartbeat": 0}
    save_db(db)
    return jsonify({"success": True})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 5000)))
