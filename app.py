from flask import Flask, request, jsonify, render_template
from flask_cors import CORS
import time

app = Flask(__name__)
CORS(app)

# Data storage
data = {
    "announcement": "",
    "active_servers": {} # Stores JobId: LastSeenTime
}

ADMIN_PASSWORD = "123"

@app.route('/')
def home():
    return render_template('index.html')

# Roblox calls this to check for messages AND report its status
@app.route('/get-announcement', methods=['POST'])
def get_announcement():
    server_info = request.json
    job_id = server_info.get("jobId", "Unknown")
    
    # Register the server as "Online"
    data["active_servers"][job_id] = time.time()
    
    return jsonify({
        "message": data["announcement"]
    })

# Website calls this to send the message
@app.route('/set-announcement', methods=['POST'])
def set_announcement():
    req_data = request.json
    if req_data.get("password") != ADMIN_PASSWORD:
        return jsonify({"error": "Unauthorized"}), 401
    
    data["announcement"] = req_data.get("message", "")
    return jsonify({"success": True})

# Website calls this to see how many servers are live
@app.get('/server-stats')
def get_stats():
    current_time = time.time()
    # Only count servers that pinged in the last 20 seconds
    live_count = sum(1 for t in data["active_servers"].values() if current_time - t < 20)
    return jsonify({"count": live_count})

if __name__ == '__main__':
    app.run()
