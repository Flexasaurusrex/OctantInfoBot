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

# Configure Socket.IO with hyper-aggressive Core-optimized settings
socketio = SocketIO(
    app,
    cors_allowed_origins="*",
    async_mode='eventlet',
    ping_timeout=30,  # Even more aggressive timeout
    ping_interval=5,  # Ultra-aggressive ping interval
    reconnection=True,
    reconnection_attempts=float('inf'),
    reconnection_delay=100,  # Super fast initial reconnect
    reconnection_delay_max=1000,  # More aggressive max delay
    max_http_buffer_size=1e8,
    logger=True,
    engineio_logger=True,
    async_handlers=True,
    manage_session=False,  # Disable session management for better performance
    always_connect=True,
    transports=['websocket'],  # WebSocket only for better performance
    upgrade_timeout=2000,  # Ultra-fast upgrade timeout
    allow_upgrades=True,
    http_compression=True,
    compression_threshold=512,  # More aggressive compression
    cookie=None,
    max_payload_length=1e6,  # Limit payload size
    ping_interval_grace_period=2,  # Shorter grace period
    close_timeout=5  # Faster close timeout
)

# Enhanced connection state tracking
connection_manager = {
    'active_connections': set(),
    'connection_times': {},
    'reconnection_attempts': {},
    'last_activity': {},
# Connection and error tracking
connection_manager = {
    'active_connections': set(),
    'connection_times': {},
    'reconnection_attempts': {},
    'last_activity': {},
    'connection_quality': {},
    'backoff_times': {},
    'circuit_breakers': {},
    'max_backoff': 30,  # Maximum backoff in seconds
    'circuit_breaker_threshold': 5,  # Number of failures before circuit breaks
    'circuit_breaker_timeout': 60  # Time in seconds before circuit resets
}

def implement_backoff(sid):
    """Implement exponential backoff for reconnection attempts."""
    current_backoff = connection_manager['backoff_times'].get(sid, 0.1)
    new_backoff = min(current_backoff * 2, connection_manager['max_backoff'])
    connection_manager['backoff_times'][sid] = new_backoff
    logger.info(f"Implementing backoff for {sid}: {new_backoff}s")
    return new_backoff

def check_circuit_breaker(sid):
    """Check if circuit breaker should prevent reconnection."""
    breaker = connection_manager['circuit_breakers'].get(sid, {
        'failures': 0,
        'last_failure': None
    })
    
    if breaker['failures'] >= connection_manager['circuit_breaker_threshold']:
        if breaker['last_failure']:
            time_since_failure = (datetime.now() - breaker['last_failure']).seconds
            if time_since_failure < connection_manager['circuit_breaker_timeout']:
                logger.warning(f"Circuit breaker active for {sid}, {time_since_failure}s since last failure")
                return False  # Circuit is broken
            else:
                # Reset circuit breaker after timeout
                connection_manager['circuit_breakers'][sid] = {
                    'failures': 0,
                    'last_failure': None
                }
                logger.info(f"Circuit breaker reset for {sid}")
    return True  # Circuit is closed

# Enhanced error handlers with recovery mechanisms
@socketio.on_error()
def error_handler(e):
    """Handle specific SocketIO errors with recovery."""
    sid = request.sid if hasattr(request, 'sid') else 'unknown'
    logger.error(f"SocketIO error for {sid}: {str(e)}", exc_info=True)
    
    try:
        if sid in connection_manager['active_connections']:
            # Update failure metrics
            breaker = connection_manager['circuit_breakers'].get(sid, {
                'failures': 0,
                'last_failure': None
            })
            breaker['failures'] += 1
            breaker['last_failure'] = datetime.now()
            connection_manager['circuit_breakers'][sid] = breaker
            
            # Implement recovery strategy
            backoff_time = implement_backoff(sid)
            socketio.emit('connection_recovery', {
                'status': 'error',
                'message': 'Connection error detected, implementing recovery...',
                'backoff': backoff_time
            }, to=sid)
            
            # Force disconnect if too many failures
            if breaker['failures'] >= connection_manager['circuit_breaker_threshold']:
                logger.warning(f"Circuit breaker triggered for {sid}, forcing disconnect")
                cleanup_connection(sid)
                return False
    except Exception as recovery_error:
        logger.error(f"Error in error recovery for {sid}: {str(recovery_error)}")
    return False

@socketio.on_error_default
def default_error_handler(e):
    """Handle uncaught SocketIO errors."""
    sid = request.sid if hasattr(request, 'sid') else 'unknown'
    logger.error(f"Unhandled SocketIO error for {sid}: {str(e)}", exc_info=True)
    
    try:
        socketio.emit('error', {
            'message': 'An unexpected error occurred',
            'reconnect': True
        }, to=sid)
    except Exception as emit_error:
        logger.error(f"Error sending error message to {sid}: {str(emit_error)}")
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
    """Handle client connection with hyper-aggressive Core-optimized error handling and monitoring."""
    # Reset any existing connection state for this client
    if request.sid in connection_manager['active_connections']:
        cleanup_connection(request.sid)
    try:
        current_time = datetime.now()
        sid = request.sid
        
        # Enhanced client info tracking
        client_info = {
            'sid': sid,
            'ip': request.remote_addr,
            'timestamp': current_time.isoformat(),
            'user_agent': request.headers.get('User-Agent', 'Unknown'),
            'transport': request.args.get('transport', 'unknown'),
            'query_string': request.args.get('query', ''),
            'origin': request.headers.get('Origin', 'Unknown')
        }
        logger.info(f"""━━━━━━ Client Connected ━━━━━━
SID: {sid}
IP: {client_info['ip']}
Transport: {client_info['transport']}
Time: {current_time}
Agent: {client_info['user_agent']}
━━━━━━━━━━━━━━━━━━━━━━━━""")
        
        # Reset reconnection tracking on successful connection
        if sid in connection_manager['reconnection_attempts']:
            logger.info(f"Client {sid} reconnected after {connection_manager['reconnection_attempts'][sid]} attempts")
            connection_manager['reconnection_attempts'][sid] = 0
        
        # Initialize connection metrics
        connection_manager['active_connections'].add(sid)
        connection_manager['connection_times'][sid] = current_time
        connection_manager['last_activity'][sid] = current_time
        connection_manager['connection_quality'][sid] = {
            'latency': 0,
            'failed_pings': 0,
            'successful_pings': 0,
            'transport_upgrades': 0
        }
        
        # Aggressive connection status monitoring
        def monitor_connection_quality():
            while sid in connection_manager['active_connections']:
                try:
                    # Calculate connection quality metrics
                    time_connected = (datetime.now() - connection_manager['connection_times'][sid]).total_seconds()
                    quality = connection_manager['connection_quality'][sid]
                    success_rate = quality['successful_pings'] / (quality['successful_pings'] + quality['failed_pings']) if (quality['successful_pings'] + quality['failed_pings']) > 0 else 1
                    
                    # Log connection quality metrics
                    if time_connected % 60 == 0:  # Log every minute
                        logger.info(f"""━━━━━━ Connection Quality ━━━━━━
Client: {sid}
Uptime: {time_connected:.1f}s
Success Rate: {success_rate:.2%}
Latency: {quality['latency']}ms
Transport Upgrades: {quality['transport_upgrades']}
━━━━━━━━━━━━━━━━━━━━━━━━""")
                    
                    # Implement recovery if needed
                    if success_rate < 0.5:
                        logger.warning(f"Poor connection quality for {sid}, initiating recovery...")
                        socketio.emit('connection_recovery', {
                            'action': 'transport_upgrade',
                            'current_transport': request.args.get('transport', 'unknown')
                        }, to=sid)
                        
                except Exception as e:
                    logger.error(f"Error monitoring connection quality: {str(e)}")
                finally:
                    eventlet.sleep(1)  # Check every second
                    
        eventlet.spawn(monitor_connection_quality)
        
        # Enhanced connection acknowledgment with retry mechanism
        def send_connection_status(retries=5, backoff_factor=1.5):
            for attempt in range(retries):
                try:
                    socketio.emit('connection_status', {
                        'status': 'connected',
                        'sid': sid,
                        'timestamp': datetime.now().isoformat(),
                        'reconnection_enabled': True,
                        'transport': request.args.get('transport', 'unknown'),
                        'ping_interval': socketio.ping_interval,
                        'ping_timeout': socketio.ping_timeout
                    }, to=sid)
                    return True
                except Exception as e:
                    wait_time = backoff_factor ** attempt
                    logger.warning(f"Attempt {attempt + 1}/{retries} failed: {str(e)}. Waiting {wait_time}s...")
                    eventlet.sleep(wait_time)
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
    """Handle client disconnection with aggressive recovery and cleanup."""
    try:
        current_time = datetime.now()
        sid = request.sid
        
        # Enhanced disconnect logging
        disconnect_info = {
            'sid': sid,
            'ip': request.remote_addr,
            'connected_duration': (current_time - connection_manager['connection_times'].get(sid, current_time)).total_seconds(),
            'reason': request.args.get('reason', 'unknown'),
            'transport': request.args.get('transport', 'unknown'),
            'timestamp': current_time.isoformat()
        }
        logger.info(f"""━━━━━━ Client Disconnected ━━━━━━
SID: {sid}
Reason: {disconnect_info['reason']}
Duration: {disconnect_info['connected_duration']:.1f}s
Transport: {disconnect_info['transport']}
Time: {current_time}
━━━━━━━━━━━━━━━━━━━━━━━━""")
        
        # Track reconnection attempts
        if sid in connection_manager['reconnection_attempts']:
            connection_manager['reconnection_attempts'][sid] += 1
        else:
            connection_manager['reconnection_attempts'][sid] = 1
        
        # Implement aggressive recovery for unexpected disconnects
        if disconnect_info['reason'] not in ['client_disconnect', 'ping_timeout']:
            try:
                # Attempt immediate reconnection
                socketio.emit('connection_recovery', {
                    'action': 'reconnect',
                    'attempt': connection_manager['reconnection_attempts'][sid],
                    'timestamp': current_time.isoformat(),
                    'transport_suggestions': ['websocket', 'polling']
                }, broadcast=True)  # Broadcast to ensure delivery
                
                # Schedule delayed cleanup
                def delayed_cleanup():
                    eventlet.sleep(30)  # Wait 30 seconds before cleanup
                    if sid not in connection_manager['active_connections']:
                        cleanup_connection(sid)
                eventlet.spawn(delayed_cleanup)
                
            except Exception as recovery_error:
                logger.error(f"Recovery attempt failed: {str(recovery_error)}")
                cleanup_connection(sid)
        else:
            cleanup_connection(sid)
            
    except Exception as e:
        logger.error(f"Error in disconnect handler: {str(e)}", exc_info=True)
        cleanup_connection(request.sid)

def cleanup_connection(sid):
    """Clean up connection state with proper error handling."""
    try:
        # Remove from all tracking
        connection_manager['active_connections'].discard(sid)
        connection_manager['connection_times'].pop(sid, None)
        connection_manager['last_activity'].pop(sid, None)
        connection_manager['connection_quality'].pop(sid, None)
        
        logger.info(f"Connection state cleaned up for {sid}")
    except Exception as e:
        logger.error(f"Error cleaning up connection state: {str(e)}")

@socketio.on('heartbeat')
def handle_heartbeat():
    """Enhanced heartbeat handler with connection quality monitoring."""
    try:
        current_time = datetime.now()
        sid = request.sid
        
        if sid in connection_manager['active_connections']:
            # Update activity timestamp
            last_activity = connection_manager['last_activity'].get(sid)
            if last_activity:
                # Calculate and update connection quality metrics
                latency = (current_time - last_activity).total_seconds() * 1000  # Convert to ms
                quality = connection_manager['connection_quality'][sid]
                quality['latency'] = latency
                quality['successful_pings'] += 1
                
                # Log excessive latency
                if latency > 1000:  # More than 1 second
                    logger.warning(f"""━━━━━━ High Latency Detected ━━━━━━
Client: {sid}
Latency: {latency:.2f}ms
Timestamp: {current_time}
━━━━━━━━━━━━━━━━━━━━━━━━""")
            
            connection_manager['last_activity'][sid] = current_time
            
            return {
                'status': 'ok',
                'timestamp': current_time.isoformat(),
                'latency': quality['latency'] if 'quality' in locals() else 0,
                'connection_quality': 'good' if not quality.get('failed_pings') else 'degraded'
            }
    except Exception as e:
        logger.error(f"Heartbeat error: {str(e)}", exc_info=True)
        if sid in connection_manager['connection_quality']:
            connection_manager['connection_quality'][sid]['failed_pings'] += 1
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