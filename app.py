import os
import eventlet
import logging
eventlet.monkey_patch()

from flask import Flask, render_template
from flask_socketio import SocketIO
from chat_handler import ChatHandler

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get("FLASK_SECRET_KEY", "octant-chat-secret")

# Configure SocketIO with production settings
socketio = SocketIO(
    app,
    async_mode='eventlet',
    cors_allowed_origins="*",
    ping_timeout=60,
    ping_interval=25,
    reconnection=True,
    reconnection_attempts=5,
    logger=True,
    engineio_logger=True
)

chat_handler = ChatHandler()

@app.route('/')
def index():
    return render_template('index.html')

@socketio.on('connect')
def handle_connect():
    logger.info('Client connected')

@socketio.on('disconnect')
def handle_disconnect():
    logger.info('Client disconnected')

@socketio.on_error()
def error_handler(e):
    logger.error(f'SocketIO error: {str(e)}')

@socketio.on('send_message')
def handle_message(data):
    try:
        message = data['message']
        response = chat_handler.get_response(message)
        socketio.emit('receive_message', {
            'message': response,
            'is_bot': True
        })
    except Exception as e:
        logger.error(f'Error handling message: {str(e)}')
        socketio.emit('receive_message', {
            'message': 'Sorry, I encountered an error processing your message. Please try again.',
            'is_bot': True
        })

if __name__ == '__main__':
    logger.info('Starting SocketIO server...')
    socketio.run(
        app, 
        host='0.0.0.0', 
        port=5000,
        debug=False,
        use_reloader=False,
        log_output=True
    )
