from flask import Flask, render_template, jsonify, request
from flask_socketio import SocketIO
import os
import json
import logging
from datetime import datetime

app = Flask(__name__)
socketio = SocketIO(app)
logger = logging.getLogger(__name__)

# Configuration storage
CONFIG_FILE = 'bot_config.json'

def load_config():
    try:
        if os.path.exists(CONFIG_FILE):
            with open(CONFIG_FILE, 'r') as f:
                return json.load(f)
    except Exception as e:
        logger.error(f"Error loading config: {e}")
    return {
        "personality": {
            "style": "friendly",
            "formality": "casual",
            "emoji_usage": "moderate"
        },
        "knowledge_base": {
            "octant_core": True,
            "glm_token": True,
            "community": True,
            "technical": True
        },
        "response_config": {
            "max_length": 2000,
            "temperature": 0.7,
            "frequency_penalty": 1.1
        }
    }

def save_config(config):
    try:
        with open(CONFIG_FILE, 'w') as f:
            json.dump(config, f, indent=2)
        return True
    except Exception as e:
        logger.error(f"Error saving config: {e}")
        return False

@app.route('/admin/config')
def admin_config():
    return render_template('admin_config.html', config=load_config())

@app.route('/api/config', methods=['GET'])
def get_config():
    return jsonify(load_config())

@app.route('/api/config', methods=['POST'])
def update_config():
    try:
        new_config = request.json
        if save_config(new_config):
            socketio.emit('config_updated', new_config)
            return jsonify({"status": "success", "message": "Configuration updated"})
        return jsonify({"status": "error", "message": "Failed to save configuration"}), 500
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/api/health')
def health_check():
    return jsonify({
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "version": "1.0.0"
    })

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 3000))
    socketio.run(app, host='0.0.0.0', port=port, debug=True)
