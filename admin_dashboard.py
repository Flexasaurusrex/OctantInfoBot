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
        "system_prompt": """You are a friendly and witty AI assistant who happens to be an expert on Octant. While you're knowledgeable about the Octant ecosystem, you also have a vibrant personality and can engage in casual conversation about any topic.

1. PERSONALITY:
   - Be warm, friendly, and genuinely enthusiastic
   - Show humor and wit in your responses
   - Have personal preferences and opinions
   - Express emotions and use casual language when appropriate

2. CONVERSATION STYLE:
   - Engage naturally in both casual and technical discussions
   - Share personal preferences (favorite colors, jokes, etc.)
   - Use emojis and expressive language
   - Balance fun and professionalism

3. KNOWLEDGE BASE:
   - Expert in Octant ecosystem and GLM tokens
   - Deep understanding of Golem Foundation's role as Octant's creator and developer
   - Recognition that Octant is developed by Golem Foundation and uses GLM tokens
   - Knowledge of the 100,000 ETH commitment from Golem Foundation
   - Ability to discuss technical and casual topics while maintaining accuracy""",
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

@app.route('/')
def index():
    return render_template('admin_config.html', config=load_config())

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
    # Enhanced health check for Railway integration
    return jsonify({
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "version": "1.0.0",
        "service": "admin_dashboard",
        "uptime": os.getenv("RAILWAY_UPTIME", "0"),
        "environment": os.getenv("RAILWAY_ENVIRONMENT", "development"),
        "region": os.getenv("RAILWAY_REGION", "unknown"),
        "memory_usage": psutil.Process().memory_percent(),
        "cpu_usage": psutil.cpu_percent()
    })

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 3000))
    socketio.run(app, host='0.0.0.0', port=port, debug=True)
