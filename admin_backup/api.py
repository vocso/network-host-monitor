from flask import Flask, request, jsonify, send_from_directory
import json
import os

app = Flask(__name__)
BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))  # ping/
ADMIN_DIR = os.path.dirname(__file__)  # ping/admin/
JSON_FILE = os.path.join(BASE_DIR, "hosts.json")

@app.route('/')
def index():
    return send_from_directory(ADMIN_DIR, "editor.html")

@app.route('/data.json')
def get_json():
    return send_from_directory(BASE_DIR, "hosts.json")

@app.route('/save', methods=['POST'])
def save_json():
    try:
        data = request.get_json()
        with open(JSON_FILE, 'w') as f:
            json.dump(data, f, indent=4)
        return jsonify(success=True)
    except Exception as e:
        return jsonify(success=False, error=str(e)), 400

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
