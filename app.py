import os
import logging
from datetime import datetime
from flask import Flask, render_template, request
from flask_socketio import SocketIO
from flask_cors import CORS
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from chat_handler import ChatHandler

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get("FLASK_SECRET_KEY", "octant-chat-secret")

# Configure CORS for production
if os.environ.get('FLASK_ENV') == 'production':
    CORS(app, resources={r"/*": {"origins": "*"}})
else:
    CORS(app)
# Configure rate limiter
limiter = Limiter(
    app=app,
    key_func=get_remote_address,
    default_limits=["200 per day", "50 per hour"],
    storage_uri="memory://"
)

socketio = SocketIO(app, cors_allowed_origins="*")
chat_handler = None

try:
    chat_handler = ChatHandler()
except ValueError as e:
    logger.error(f"Failed to initialize ChatHandler: {str(e)}")
    raise

@app.before_request
def log_request_info():
    if not request.path.startswith('/static'):
        logger.info(f'Request: {request.method} {request.path} from {request.remote_addr}')

@app.route('/')
def index():
    return render_template('index.html')

@socketio.on('connect')
def handle_connect():
    logger.info(f"Client connected: {request.sid}")

@socketio.on('disconnect')
def handle_disconnect():
    logger.info(f"Client disconnected: {request.sid}")

@socketio.on('send_message')
def handle_message(data):
    try:
        message = data['message']
        logger.info(f"Received message from {request.sid}: {message[:50]}...")
        
        if chat_handler is None:
            raise RuntimeError("ChatHandler not initialized")
            
        response = chat_handler.get_response(message)
        socketio.emit('receive_message', {
            'message': response,
            'is_bot': True
        })
        logger.info(f"Sent response to {request.sid}")
    except Exception as e:
        logger.error(f"Error handling message: {str(e)}")
        socketio.emit('receive_message', {
            'message': "I apologize, but I encountered an error processing your message. Please try again.",
            'is_bot': True
        })

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    debug = os.environ.get('FLASK_ENV') != 'production'
    
    logger.info(f"Starting server on port {port} with debug={debug}")
    socketio.run(app, host='0.0.0.0', port=port, debug=debug)
