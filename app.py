import os
from flask import Flask, render_template
from flask_socketio import SocketIO
from chat_handler import ChatHandler

app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get("FLASK_SECRET_KEY", "octant-chat-secret")
socketio = SocketIO(app)
chat_handler = ChatHandler()

@app.route('/')
def index():
    return render_template('index.html')

@socketio.on('send_message')
def handle_message(data):
    message = data['message']
    response = chat_handler.get_response(message)
    socketio.emit('receive_message', {
        'message': response,
        'is_bot': True
    })

if __name__ == '__main__':
    socketio.run(app, host='0.0.0.0', port=5000, debug=True)
