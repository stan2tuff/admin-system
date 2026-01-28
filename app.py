from flask import Flask, request, jsonify, render_template, session, redirect, url_for
from flask_discord import DiscordOAuth2Session
from flask_cors import CORS
import json, os, time

app = Flask(__name__)
CORS(app)

# SECURITY: Use Render Environment Variables for these!
app.secret_key = os.environ.get("SECRET_KEY", "CYBER_KEY_99")
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

@app.route('/')
def home():
    if not discord.authorized: return redirect(url_for('login'))
    db = load_db()
    uid = session.get('user_id')
    role = "master" if uid == MASTER_DISCORD_ID else "client"
    user_data = db['users'].get(uid, {"gid": "None", "name": "Unknown"})
    return render_template('dashboard.html', user=session.get('username'), role=role, gid=user_data['gid'], all_users=db['users'] if role == "master" else {})

@app.route('/login')
def login(): return discord.create_session(scope=["identify"])

@app.route('/callback')
def callback():
    discord.callback()
    user = discord.fetch_user()
    session['user_id'] = str(user.id)
    session['username'] = user.username
    return redirect(url_for('home'))

@app.route('/api/command', methods=['POST'])
def send_command():
    if not discord.authorized: return "Unauthorized", 401
    db = load_db()
    uid = session.get('user_id')
    gid = db['users'].get(uid, {}).get('gid')
    if not gid: return "No GID", 400
    
    data = request.json
    db['games'][gid]['cmds'] = {
        "target": data.get('target', 'all'),
        "action": data.get('action'),
        "msg": data.get('msg', ''),
        "time": time.time()
    }
    save_db(db)
    return jsonify({"success": True})

@app.route('/api/poll', methods=['POST'])
def roblox_poll():
    db = load_db()
    req = request.json
    gid = str(req.get("gameId"))
    if gid in db['games']:
        db['games'][gid]['players'] = req.get("players", [])
        db['games'][gid]['last_seen'] = time.time() # Heartbeat tracking
        save_db(db)
        cmd = db['games'][gid]['cmds']
        db['games'][gid]['cmds'] = {"target": "", "action": "", "msg": ""}
        return jsonify(cmd)
    return "Invalid GID", 403

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
