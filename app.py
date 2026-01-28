from flask import Flask, request, jsonify, render_template
from flask_cors import CORS
import time

app = Flask(__name__)
CORS(app)

# Data storage
data = {
    "announcement": "",
    "kick_user": "", # Stores the name of the person to kick
    "active_servers": {} 
}

ADMIN_PASSWORD = "1234" # USE THIS ON THE WEBSITE

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/get-announcement', methods=['POST'])
def get_announcement():
    global data
    server_info = request.json
    job_id = server_info.get("jobId", "Unknown")
    data["active_servers"][job_id] = time.time()
    
    response = {
        "message": data["announcement"],
        "kick": data["kick_user"]
    }
    
    # FIX: Reset the kick target so they aren't stuck in a kick-loop
    data["kick_user"] = "" 
    
    return jsonify(response)

@app.route('/set-command', methods=['POST'])
def set_command():
    req_data = request.json
    if req_data.get("password") != ADMIN_PASSWORD:
        return jsonify({"error": "Unauthorized"}), 401
    
    # Update announcement or kick target
    data["announcement"] = req_data.get("message", "")
    data["kick_user"] = req_data.get("kick", "")
    return jsonify({"success": True})

@app.get('/server-stats')
def get_stats():
    current_time = time.time()
    live_count = sum(1 for t in data["active_servers"].values() if current_time - t < 20)
    return jsonify({"count": live_count})

if __name__ == '__main__':
    app.run()
