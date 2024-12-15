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

# Configure Socket.IO with robust connection handling and stability
socketio = SocketIO(
    app,
    cors_allowed_origins="*",
    async_mode='eventlet',
    ping_timeout=120,  # Increased timeout for better stability
    ping_interval=15,  # More frequent ping for faster detection
    reconnection=True,
    reconnection_attempts=float('inf'),
    reconnection_delay=1000,
    reconnection_delay_max=5000,
    max_http_buffer_size=1e8,
    logger=True,
    engineio_logger=True,
    async_handlers=True,
    manage_session=True,
    always_connect=True,  # Ensure connection is maintained
    transports=['websocket', 'polling']  # Enable fallback to polling
)

# Track connection state
connection_state = {
    'connected_clients': set(),
    'last_heartbeat': {}
}

# Configure websocket error handlers
@socketio.on_error()
def error_handler(e):
    logger.error(f"SocketIO error: {str(e)}", exc_info=True)
    return False

@socketio.on_error_default
def default_error_handler(e):
    logger.error(f"SocketIO default error: {str(e)}", exc_info=True)
    return False
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
                
                try:
                    # Save current state and notify clients
                    active_connections = len(socketio.server.manager.rooms.get('/', set()) or set())
                    logger.info(f"Active connections: {active_connections}")
                except AttributeError:
                    logger.warning("Could not get active connections count")
                    active_connections = 0
                
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

@socketio.on('connect')
def handle_connect():
    """Handle client connection with robust error handling and state tracking."""
    try:
        client_info = {
            'sid': request.sid,
            'ip': request.remote_addr,
            'timestamp': datetime.now().isoformat(),
            'user_agent': request.headers.get('User-Agent', 'Unknown')
        }
        logger.info(f"Client connected: {client_info}")
        
        # Update connection state
        connection_state['connected_clients'].add(request.sid)
        connection_state['last_heartbeat'][request.sid] = datetime.now()
        
        # Send connection acknowledgment with retry mechanism
        def send_connection_status(retries=3):
            for attempt in range(retries):
                try:
                    socketio.emit('connection_status', {
                        'status': 'connected',
                        'sid': request.sid,
                        'timestamp': datetime.now().isoformat(),
                        'reconnection_enabled': True
                    }, to=request.sid)
                    return True
                except Exception as e:
                    if attempt == retries - 1:
                        logger.error(f"Failed to send connection status after {retries} attempts: {str(e)}")
                        return False
                    eventlet.sleep(0.5)
            return False

        if send_connection_status():
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
            }, to=request.sid)
            
        # Start heartbeat monitoring for this client
        def monitor_heartbeat():
            while request.sid in connection_state['connected_clients']:
                eventlet.sleep(10)  # Check every 10 seconds
                if request.sid in connection_state['last_heartbeat']:
                    last_beat = connection_state['last_heartbeat'][request.sid]
                    if (datetime.now() - last_beat).total_seconds() > 30:
                        logger.warning(f"Client {request.sid} heartbeat timeout")
                        handle_disconnect()
                        break
                        
        eventlet.spawn(monitor_heartbeat)
        
    except Exception as e:
        logger.error(f"Error in handle_connect: {str(e)}", exc_info=True)
        try:
            socketio.emit('connection_status', {
                'status': 'error',
                'message': 'Connection error occurred',
                'timestamp': datetime.now().isoformat()
            }, to=request.sid)
        except Exception as emit_error:
            logger.error(f"Failed to send error status: {str(emit_error)}")
            
    # Setup error recovery handler
    @socketio.on_error_default
    def error_handler(e):
        logger.error(f"SocketIO error: {str(e)}", exc_info=True)
        try:
            socketio.emit('error', {
                'message': 'An error occurred, attempting to recover connection',
                'timestamp': datetime.now().isoformat()
            }, to=request.sid)
        except Exception as emit_error:
            logger.error(f"Error sending error message: {str(emit_error)}")

@socketio.on('disconnect')
def handle_disconnect():
    """Enhanced disconnect handler with connection cleanup and reconnection support."""
    try:
        client_info = {
            'sid': request.sid,
            'ip': request.remote_addr,
            'timestamp': datetime.now().isoformat(),
            'reason': request.args.get('reason', 'unknown')
        }
        logger.info(f"Client disconnected: {client_info}")
        
        # Clean up connection state
        if request.sid in connection_state['connected_clients']:
            connection_state['connected_clients'].remove(request.sid)
        if request.sid in connection_state['last_heartbeat']:
            del connection_state['last_heartbeat'][request.sid]
        
        # Notify about disconnection
        try:
            socketio.emit('connection_status', {
                'status': 'disconnected',
                'sid': request.sid,
                'timestamp': datetime.now().isoformat(),
                'reason': request.args.get('reason', 'unknown'),
                'reconnection_enabled': True
            }, to=request.sid)
        except Exception as emit_error:
            logger.error(f"Failed to send disconnect status: {str(emit_error)}")
            
    except Exception as e:
        logger.error(f"Error in disconnect handler: {str(e)}", exc_info=True)

@socketio.on('heartbeat')
def handle_heartbeat():
    """Handle client heartbeat to monitor connection health."""
    try:
        if request.sid in connection_state['connected_clients']:
            connection_state['last_heartbeat'][request.sid] = datetime.now()
            return {'status': 'ok', 'timestamp': datetime.now().isoformat()}
    except Exception as e:
        logger.error(f"Error in heartbeat handler: {str(e)}", exc_info=True)
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
    socketio.run(app, host='0.0.0.0', port=port, debug=debug)