from flask import Flask, request, jsonify, render_template
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

# Storage for the current announcement
# Note: This clears if the server restarts. 
current_announcement = ""
ADMIN_PASSWORD = "stxn123"  # CHANGE THIS!

@app.route('/')
def home():
    # Serves the index.html file from the /templates folder
    return render_template('index.html')

@app.route('/set-announcement', methods=['POST'])
def set_announcement():
    global current_announcement
    data = request.json
    
    # Simple security check
    if data.get("password") != ADMIN_PASSWORD:
        return jsonify({"error": "Unauthorized"}), 401
    
    current_announcement = data.get("message", "")
    return jsonify({"success": True, "message": "Announcement set!"})

@app.route('/get-announcement', methods=['GET'])
def get_announcement():
    return jsonify({"message": current_announcement})

if __name__ == '__main__':
    app.run(debug=False)
