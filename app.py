import eventlet
eventlet.monkey_patch()
import os
import logging
from datetime import datetime
from flask import Flask, render_template, request
logger = logging.getLogger('app')
logger.setLevel(logging.INFO)
handler = logging.StreamHandler()
handler.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
logger.addHandler(handler)
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

# Configure Socket.IO with enhanced connection handling
socketio = SocketIO(
    app,
    cors_allowed_origins="*",
    async_mode='eventlet',
    ping_timeout=20,
    ping_interval=10,
    reconnection=True,
    reconnection_attempts=3,
    reconnection_delay=2000,
    reconnection_delay_max=5000,
    max_http_buffer_size=5e6,
    async_handlers=True,
    logger=True,
    engineio_logger=True
)
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
@app.route('/health')
def health_check():
    return {
        'status': 'healthy',
        'timestamp': datetime.now().isoformat(),
        'services': {
            'web': True,
            'socket': socketio.server.manager.rooms != {},
            'chat_handler': chat_handler is not None
        }
    }

@app.route('/admin')
@limiter.limit("60 per minute")
def admin_dashboard():
    # Enhanced bot statistics
    stats = {
        'active_users': len(active_connections),
        'total_messages': sum(len(conn.get('messages', [])) for conn in active_connections.values()),
        'uptime': round((datetime.now() - app.start_time).total_seconds() / 3600, 2),
        'connection_status': 'Connected' if chat_handler else 'Disconnected',
        'avg_response_time': calculate_avg_response_time(),
        'error_rate': calculate_error_rate(),
        'commands_used': get_command_usage_stats(),
        'platform_stats': {
            'discord': get_discord_stats(),
            'telegram': get_telegram_stats(),
            'web': len(active_connections)
        }
    }
    
    return render_template('admin.html', stats=stats)

def calculate_avg_response_time():
    if not active_connections:
        return 0
    response_times = [
        msg.get('response_time', 0) 
        for conn in active_connections.values()
        for msg in conn.get('messages', [])
        if msg.get('response_time')
    ]
    return round(sum(response_times) / len(response_times)) if response_times else 0

def calculate_error_rate():
    total_messages = sum(len(conn.get('messages', [])) for conn in active_connections.values())
    error_count = sum(
        len([msg for msg in conn.get('messages', []) if msg.get('error')])
        for conn in active_connections.values()
    )
    return round((error_count / total_messages * 100) if total_messages else 0, 2)

def get_command_usage_stats():
    commands = {}
    for conn in active_connections.values():
        for msg in conn.get('messages', []):
            if msg.get('type') == 'command':
                cmd = msg['content'].split()[0]
                commands[cmd] = commands.get(cmd, 0) + 1
    return commands

def get_discord_stats():
    # Will be populated by Discord bot
    return {
        'guilds': 0,
        'users': 0,
        'messages': 0
    }

def get_telegram_stats():
    # Will be populated by Telegram bot
    return {
        'chats': 0,
        'users': 0,
        'messages': 0
    }

@app.route('/restart', methods=['POST'])
@limiter.limit("5 per minute")
def restart_services():
    try:
        logger.info("Restart request received")
        
        # Initial notification
        socketio.emit('restart_status', {
            'status': 'initializing',
            'message': 'Initiating restart sequence...',
            'countdown': 15
        }, namespace='/')
        
        def cleanup_and_restart():
            try:
                # Step 1: Prepare for restart
                logger.info("Starting cleanup process...")
                eventlet.sleep(1)
                
                # Save current state and notify clients
                active_connections = len(socketio.server.manager.rooms.get('/', set()))
                logger.info(f"Active connections: {active_connections}")
                
                socketio.emit('restart_status', {
                    'status': 'preparing',
                    'message': 'Preparing to restart server...',
                    'countdown': 10
                }, namespace='/')
                
                # Step 2: Close connections gracefully
                active_sids = list(socketio.server.manager.rooms.get('/', set()))
                for sid in active_sids:
                    try:
                        socketio.server.disconnect(sid, namespace='/')
                        logger.info(f"Disconnected client {sid}")
                    except Exception as e:
                        logger.warning(f"Error disconnecting client {sid}: {str(e)}")
                
                logger.info("All connections cleaned up")
                
                # Step 3: Final notification
                socketio.emit('restart_status', {
                    'status': 'restarting',
                    'message': 'Server is restarting...',
                    'countdown': 5
                }, broadcast=True)
                
                eventlet.sleep(2)
                
                # Step 4: Stop the server
                logger.info("Stopping server...")
                socketio.stop()
                
                # Step 5: Exit process to trigger workflow restart
                logger.info("Triggering restart...")
                os._exit(0)
                
            except Exception as e:
                error_msg = f"Error during restart: {str(e)}"
                logger.error(error_msg)
                socketio.emit('restart_status', {
                    'status': 'error',
                    'message': f'Restart failed: {error_msg}. Please try again.',
                    'countdown': 0
                }, namespace='/')
        
        # Schedule the cleanup and restart process
        eventlet.spawn(cleanup_and_restart)
        return {"status": "success", "message": "Restart sequence initiated"}
        
    except Exception as e:
        error_msg = f"Failed to initiate restart: {str(e)}"
        logger.error(error_msg)
        socketio.emit('restart_status', {
            'status': 'error',
            'message': error_msg,
            'countdown': 0
        }, namespace='/')
        return {"status": "error", "message": error_msg}, 500

# Track active connections and their state
active_connections = {}

@socketio.on('connect')
def handle_connect():
    """Handle client connection with enhanced error handling and state tracking."""
    try:
        client_info = {
            'sid': request.sid,
            'ip': request.remote_addr,
            'timestamp': datetime.now().isoformat(),
            'user_agent': request.headers.get('User-Agent', 'Unknown'),
            'reconnect_attempts': 0,
            'last_ping': datetime.now()
        }
        active_connections[request.sid] = client_info
        logger.info(f"Client connected: {client_info}")
        
        # Send connection acknowledgment with enhanced status
        socketio.emit('connection_status', {
            'status': 'connected',
            'sid': request.sid,
            'timestamp': datetime.now().isoformat(),
            'reconnect_info': {
                'attempts': client_info['reconnect_attempts'],
                'max_attempts': 5,
                'delay': 2000
            }
        }, room=request.sid)
        
        # Send welcome message with command help
        help_message = """
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📚 Available Commands
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

📋 Information Commands:
• /help - Show this help message
• /learn - Access learning modules

📌 Topic-Specific Commands:
• /funding - Learn about Octant's funding
• /governance - Understand governance
• /rewards - Explore reward system

Type any command to get started!
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"""
        socketio.emit('receive_message', {
            'message': help_message,
            'is_bot': True
        }, room=request.sid)
        
    except Exception as e:
        logger.error(f"Error in handle_connect: {str(e)}", exc_info=True)
        error_response = {
            'status': 'error',
            'message': 'Connection error occurred',
            'timestamp': datetime.now().isoformat(),
            'error_details': str(e),
            'reconnect_info': {
                'should_retry': True,
                'delay': 2000
            }
        }
        socketio.emit('connection_status', error_response, room=request.sid)

@socketio.on('disconnect')
def handle_disconnect():
    """Handle client disconnection with cleanup and reconnection support."""
    try:
        client_info = active_connections.get(request.sid)
        if client_info:
            logger.info(f"Client disconnected: {client_info}")
            # Update reconnection attempts for tracking
            client_info['reconnect_attempts'] += 1
            # Keep connection info for potential reconnection
            if client_info['reconnect_attempts'] < 5:
                client_info['last_disconnect'] = datetime.now().isoformat()
            else:
                # Clean up if max reconnection attempts reached
                active_connections.pop(request.sid, None)
    except Exception as e:
        logger.error(f"Error in handle_disconnect: {str(e)}", exc_info=True)

@socketio.on('ping')
def handle_ping():
    """Handle client ping to maintain connection state."""
    try:
        if request.sid in active_connections:
            active_connections[request.sid]['last_ping'] = datetime.now()
            return {'status': 'ok', 'timestamp': datetime.now().isoformat()}
    except Exception as e:
        logger.error(f"Error in handle_ping: {str(e)}")
        return {'status': 'error', 'message': str(e)}

@socketio.on('send_message')
def handle_message(data):
    try:
        message = data['message']
        logger.info(f"Received message from {request.sid}: {message[:50]}...")
        
        if chat_handler is None:
            logger.error("ChatHandler not initialized")
            raise RuntimeError("ChatHandler not initialized")
            
        response = chat_handler.get_response(message)
        socketio.emit('receive_message', {
            'message': response,
            'is_bot': True
        })
        logger.info(f"Sent response to {request.sid}")
    except KeyError as e:
        logger.error(f"Invalid message format from {request.sid}: {str(e)}")
        socketio.emit('receive_message', {
            'message': "I couldn't process your message. Please try again with a valid message format.",
            'is_bot': True
        })
    except RuntimeError as e:
        logger.error(f"Runtime error: {str(e)}")
        socketio.emit('receive_message', {
            'message': "The chat service is currently unavailable. Please try again in a few moments.",
            'is_bot': True
        })
    except Exception as e:
        logger.error(f"Unexpected error handling message: {str(e)}")
        socketio.emit('receive_message', {
            'message': "I apologize, but I encountered an unexpected error. Please try again.",
            'is_bot': True
        })

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    debug = os.environ.get('FLASK_ENV') != 'production'
    
    logger.info(f"Starting server on port {port} with debug={debug}")
    socketio.run(app, host='0.0.0.0', port=5000, debug=debug)
