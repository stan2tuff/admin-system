from flask import Flask, request, jsonify, render_template
from flask_cors import CORS
import time

app = Flask(__name__)
CORS(app)

data = {
    "announcement": "",
    "kick_user": "",
    "kill_user": "",
    "warn_user": "",
    "warn_text": "",
    "active_servers": {}, # { jobId: {"players": [], "last_ping": 0} }
    "logs": []
}

ADMIN_PASSWORD = "1234"

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/get-announcement', methods=['POST'])
def get_announcement():
    global data
    server_info = request.json
    job_id = server_info.get("jobId", "Unknown")
    
    # Store the player list sent from Roblox
    data["active_servers"][job_id] = {
        "players": server_info.get("players", []),
        "last_ping": time.time()
    }
    
    response = {
        "message": data["announcement"],
        "kick": data["kick_user"],
        "kill": data["kill_user"],
        "warn": data["warn_user"],
        "warn_msg": data["warn_text"]
    }
    
    # Reset single-use commands
    data["kick_user"] = ""
    data["kill_user"] = ""
    data["warn_user"] = ""
    
    return jsonify(response)

@app.route('/set-command', methods=['POST'])
def set_command():
    req_data = request.json
    if req_data.get("password") != ADMIN_PASSWORD:
        return jsonify({"error": "Unauthorized"}), 401
    
    cmd_type = req_data.get("type")
    target = req_data.get("target")
    
    if cmd_type == "announce":
        data["announcement"] = req_data.get("message")
        data["logs"].insert(0, f"Announced: {data['announcement']}")
    elif cmd_type == "kick":
        data["kick_user"] = target
        data["logs"].insert(0, f"Kicked: {target}")
    elif cmd_type == "kill":
        data["kill_user"] = target
        data["logs"].insert(0, f"Killed: {target}")
    elif cmd_type == "warn":
        data["warn_user"] = target
        data["warn_text"] = req_data.get("message", "You have been warned.")
        data["logs"].insert(0, f"Warned: {target}")

    data["logs"] = data["logs"][:10]
    return jsonify({"success": True})

@app.get('/get-data')
def get_all_data():
    current_time = time.time()
    # Clean up old servers and build a master player list
    all_players = []
    for jid, info in list(data["active_servers"].items()):
        if current_time - info["last_ping"] < 20:
            all_players.extend(info["players"])
        else:
            del data["active_servers"][jid]
            
    return jsonify({
        "players": list(set(all_players)), # Unique names
        "logs": data["logs"]
    })

if __name__ == '__main__':
    app.run()
