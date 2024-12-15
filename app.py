import os
import logging
from datetime import datetime

# Initialize eventlet first
import eventlet
eventlet.monkey_patch(os=True, select=True, socket=True, thread=True, time=True)

from flask import Flask, render_template, request, current_app
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

# Configure Socket.IO with robust error handling and connection management
socketio = SocketIO(
    app,
    cors_allowed_origins="*",
    async_mode='eventlet',
    ping_timeout=20,
    ping_interval=10,
    reconnection=True,
    reconnection_attempts=10,
    reconnection_delay=1000,
    reconnection_delay_max=5000,
    logger=True,
    engineio_logger=True,
    max_http_buffer_size=1e8,
    async_handlers=True,
    always_connect=True,
    http_compression=True
)

# Track client connections and their state
connected_clients = {}

# Connection state monitoring
@socketio.on_error_default
def default_error_handler(e):
    """Handle all unnamed events."""
    logger.error(f"SocketIO Error: {str(e)}", exc_info=True)
    if request.sid in connected_clients:
        connected_clients[request.sid]['error_count'] = connected_clients[request.sid].get('error_count', 0) + 1

@socketio.on('connect_error')
def handle_connect_error(error):
    """Handle connection errors."""
    logger.error(f"Connection error for client {request.sid}: {str(error)}")
    socketio.emit('connection_status', {
        'status': 'error',
        'message': 'Connection error occurred, attempting to reconnect...',
        'timestamp': datetime.now().isoformat()
    }, room=request.sid)

@socketio.on('disconnect_request')
def handle_disconnect_request():
    """Handle client disconnect requests."""
    logger.info(f"Client {request.sid} requested disconnect")
    if request.sid in connected_clients:
        connected_clients.pop(request.sid, None)
    socketio.emit('connection_status', {
        'status': 'disconnecting',
        'message': 'Disconnecting by request...',
        'timestamp': datetime.now().isoformat()
    }, room=request.sid)
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
                
                # Step 4: Clean up socket connections
                logger.info("Cleaning up socket connections...")
                for namespace in socketio.server.namespace_handlers:
                    socketio.server.namespace_handlers[namespace].clear()
                
                # Step 5: Stop the server
                logger.info("Stopping server...")
                try:
                    socketio.stop()
                except Exception as e:
                    logger.error(f"Error stopping socketio: {e}")
                
                # Step 6: Exit process to trigger workflow restart
                logger.info("Triggering restart...")
                try:
                    import signal
                    os.kill(os.getpid(), signal.SIGTERM)
                except Exception:
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

@socketio.on('connect')
def handle_connect():
    """Handle client connection with comprehensive error handling and state tracking."""
    try:
        # Initialize client state
        client_info = {
            'sid': request.sid,
            'ip': request.remote_addr,
            'timestamp': datetime.now().isoformat(),
            'user_agent': request.headers.get('User-Agent', 'Unknown'),
            'error_count': 0,
            'reconnect_count': 0,
            'last_activity': datetime.now().isoformat()
        }
        connected_clients[request.sid] = client_info
        logger.info(f"Client connected: {client_info}")
        
        # Send enhanced connection acknowledgment
        socketio.emit('connection_status', {
            'status': 'connected',
            'sid': request.sid,
            'timestamp': datetime.now().isoformat(),
            'ping_interval': socketio.ping_interval,
            'ping_timeout': socketio.ping_timeout
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
            'is_bot': True,
            'timestamp': datetime.now().isoformat()
        }, room=request.sid)
        
    except Exception as e:
        logger.error(f"Error in handle_connect: {str(e)}", exc_info=True)
        socketio.emit('connection_status', {
            'status': 'error',
            'message': 'Connection error occurred, retrying...',
            'timestamp': datetime.now().isoformat(),
            'retry': True
        }, room=request.sid)
        raise

@socketio.on('disconnect')
def handle_disconnect():
    """Handle client disconnection with cleanup."""
    try:
        client_info = connected_clients.get(request.sid, {})
        logger.info(f"Client disconnected: {client_info}")
        
        # Perform cleanup
        if request.sid in connected_clients:
            # Log disconnect reason if available
            reason = request.args.get('reason', 'unknown')
            logger.info(f"Disconnect reason for {request.sid}: {reason}")
            
            # Clean up client state
            connected_clients.pop(request.sid, None)
            
        # Notify remaining clients about user count
        active_users = len(connected_clients)
        socketio.emit('user_count_update', {'count': active_users}, broadcast=True)
        
    except Exception as e:
        logger.error(f"Error in handle_disconnect: {str(e)}", exc_info=True)

@socketio.on('send_message')
def handle_message(data):
    """Handle incoming messages with comprehensive error handling and recovery."""
    if request.sid not in connected_clients:
        logger.error(f"Message received from unknown client: {request.sid}")
        return
    
    try:
        # Update client activity timestamp
        connected_clients[request.sid]['last_activity'] = datetime.now().isoformat()
        
        message = data['message']
        logger.info(f"Received message from {request.sid}: {message[:50]}...")
        
        # Validate chat handler
        if chat_handler is None:
            logger.error("ChatHandler not initialized")
            raise RuntimeError("ChatHandler not initialized")
        
        # Send typing indicator
        socketio.emit('bot_typing', {'typing': True}, room=request.sid)
        
        # Get response with timeout handling
        try:
            response = chat_handler.get_response(message)
            
            # Reset error count on successful response
            connected_clients[request.sid]['error_count'] = 0
            
            # Send response with timestamp
            socketio.emit('receive_message', {
                'message': response,
                'is_bot': True,
                'timestamp': datetime.now().isoformat()
            }, room=request.sid)
            
            logger.info(f"Sent response to {request.sid}")
            
        except Exception as response_error:
            # Increment error count
            connected_clients[request.sid]['error_count'] = connected_clients[request.sid].get('error_count', 0) + 1
            error_count = connected_clients[request.sid]['error_count']
            
            # Handle repeated errors
            if error_count >= 3:
                logger.error(f"Multiple errors for client {request.sid}, suggesting refresh")
                error_message = "I'm having trouble maintaining a stable connection. Please refresh your browser."
            else:
                error_message = "I encountered an issue. Please try your message again."
            
            socketio.emit('receive_message', {
                'message': error_message,
                'is_bot': True,
                'error': True,
                'timestamp': datetime.now().isoformat()
            }, room=request.sid)
            
            raise response_error
            
    except KeyError as e:
        logger.error(f"Invalid message format from {request.sid}: {str(e)}")
        socketio.emit('receive_message', {
            'message': "I couldn't process your message. Please try again with a valid message format.",
            'is_bot': True,
            'error': True,
            'timestamp': datetime.now().isoformat()
        }, room=request.sid)
        
    except RuntimeError as e:
        logger.error(f"Runtime error: {str(e)}")
        socketio.emit('receive_message', {
            'message': "The chat service is currently unavailable. Please try again in a few moments.",
            'is_bot': True,
            'error': True,
            'timestamp': datetime.now().isoformat()
        }, room=request.sid)
        
    except Exception as e:
        logger.error(f"Unexpected error handling message: {str(e)}", exc_info=True)
        socketio.emit('receive_message', {
            'message': "I apologize, but I encountered an unexpected error. Please try again.",
            'is_bot': True,
            'error': True,
            'timestamp': datetime.now().isoformat()
        }, room=request.sid)
    
    finally:
        # Always clear typing indicator
        socketio.emit('bot_typing', {'typing': False}, room=request.sid)

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    debug = os.environ.get('FLASK_ENV') != 'production'
    
    logger.info(f"Starting server on port {port} with debug={debug}")
    socketio.run(app, host='0.0.0.0', port=port, debug=debug)
