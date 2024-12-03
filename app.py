import os
import eventlet
eventlet.monkey_patch()

from flask import Flask, render_template
from flask_socketio import SocketIO
from chat_handler import ChatHandler

app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get("FLASK_SECRET_KEY", "octant-chat-secret")
socketio = SocketIO(app, 
                   cors_allowed_origins="*", 
                   async_mode='eventlet',
                   ping_timeout=60,
                   ping_interval=25,
                   max_http_buffer_size=1e8)
chat_handler = ChatHandler()

@app.route('/')
def index():
    return render_template('index.html')

@socketio.on('connect')
def handle_connect():
    print("Client connected")

@socketio.on('disconnect')
def handle_disconnect():
    print("Client disconnected")

@socketio.on('send_message')
def handle_message(data):
    try:
        message = data.get('message', '')
        if not message:
            return
        
        print(f"Received message: {message}")
        response = chat_handler.get_response(message)
        print(f"Sending response: {response[:100]}...")  # Log first 100 chars of response
        
        socketio.emit('receive_message', {
            'message': response,
            'is_bot': True
        })
    except Exception as e:
        print(f"Error in handle_message: {str(e)}")
        socketio.emit('receive_message', {
            'message': "I encountered an error. Please try again.",
            'is_bot': True
        })

if __name__ == '__main__':
    socketio.run(app, host='0.0.0.0', port=5000, debug=True)
