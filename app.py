from flask import Flask, request, jsonify
from flask_cors import CORS

app = Flask(__name__)
CORS(app)  # Allows your website to talk to this API

# This variable stores the current message in the server's memory
current_announcement = ""
ADMIN_PASSWORD = "stxn123"

@app.route('/set-announcement', methods=['POST'])
def set_announcement():
    global current_announcement
    data = request.json
    
    # Security check
    if data.get("password") != ADMIN_PASSWORD:
        return jsonify({"error": "Unauthorized"}), 401
    
    current_announcement = data.get("message", "")
    print(f"New Announcement: {current_announcement}")
    return jsonify({"success": True})

@app.route('/get-announcement', methods=['GET'])
def get_announcement():
    return jsonify({"message": current_announcement})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
