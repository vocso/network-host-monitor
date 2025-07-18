from flask import Flask, request, jsonify, send_from_directory, abort
import os
import json

# === Setup ===
app = Flask(__name__)
BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))  # /ping
ADMIN_DIR = os.path.dirname(__file__)  # /ping/admin
JSON_FILE = os.path.join(BASE_DIR, "hosts.json")
CONFIG_FILE = os.path.join(BASE_DIR, "config.json")

with open(CONFIG_FILE) as f:
    CONFIG = json.load(f)

AUTH_TOKEN = CONFIG.get("auth_token")

# === Auth Middleware ===
def check_auth():
    token = request.headers.get("Authorization")
    if token != f"Bearer {AUTH_TOKEN}":
        abort(401, description="Unauthorized")

# === Routes ===

@app.route('/')
def index():
    #check_auth()
    return send_from_directory(ADMIN_DIR, "editor.html")

@app.route('/style.css')
def css():
    return send_from_directory(ADMIN_DIR, "style.css")

@app.route('/script.js')
def js():
    return send_from_directory(ADMIN_DIR, "script.js")

@app.route('/data.json')
def get_json():
    check_auth()
    return send_from_directory(BASE_DIR, "hosts.json")

@app.route('/save', methods=['POST'])
def save_json():
    check_auth()
    try:
        data = request.get_json()
        with open(JSON_FILE, 'w') as f:
            json.dump(data, f, indent=4)
        return jsonify(success=True)
    except Exception as e:
        return jsonify(success=False, error=str(e)), 400

# === Run App ===
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5055)
