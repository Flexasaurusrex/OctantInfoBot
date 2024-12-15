import eventlet
eventlet.monkey_patch()
import os
import logging
import random
from datetime import datetime
from flask import Flask, render_template, request, jsonify
from typing import Dict, Set, Optional
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

# Configure Socket.IO with balanced settings for stability
socketio = SocketIO(
    app,
    cors_allowed_origins="*",
    async_mode='eventlet',
    ping_timeout=60,  # More lenient timeout
    ping_interval=25,  # More balanced ping interval
    reconnection=True,
    reconnection_attempts=float('inf'),
    reconnection_delay=1000,  # More gradual reconnect
    reconnection_delay_max=5000,  # More patient max delay
    max_http_buffer_size=1e8,
    logger=True,
    engineio_logger=True,
    async_handlers=True,
    manage_session=True,  # Enable session management for better state tracking
    always_connect=True,
    transports=['websocket', 'polling'],  # Allow fallback to polling
    upgrade_timeout=5000,  # More lenient upgrade timeout
    allow_upgrades=True,
    http_compression=True,
    compression_threshold=1024,  # Standard compression threshold
    cookie={'httpOnly': True, 'secure': True},  # Enhanced security
    max_payload_length=1e6,
    ping_interval_grace_period=5,  # More lenient grace period
    close_timeout=10  # More graceful close timeout
)

# Enhanced connection state tracking
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
    """Implement smoother exponential backoff with jitter for reconnection attempts."""
    import random
    current_backoff = connection_manager['backoff_times'].get(sid, 1.0)  # Start with 1 second
    attempts = connection_manager['reconnection_attempts'].get(sid, 0)
    
    # Progressive backoff based on attempt count
    base_delay = min(2 ** attempts, connection_manager['max_backoff'])
    
    # Add jitter to prevent thundering herd
    jitter = random.uniform(0, 0.1 * base_delay)
    new_backoff = min(base_delay + jitter, connection_manager['max_backoff'])
    connection_manager['backoff_times'][sid] = new_backoff

    # Reset if we've reached max backoff
    if new_backoff >= connection_manager['max_backoff']:
        connection_manager['reconnection_attempts'][sid] = 0
    
    # Log detailed backoff information
    logger.info(f"""━━━━━━ Connection Backoff ━━━━━━
Client: {sid}
Previous Backoff: {current_backoff:.2f}s
New Backoff: {new_backoff:.2f}s
Jitter Applied: {jitter:.2f}s
Max Backoff: {connection_manager['max_backoff']}s
━━━━━━━━━━━━━━━━━━━━━━━━""")
    
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
    """Enhanced error handler with sophisticated recovery mechanisms."""
    sid = request.sid if hasattr(request, 'sid') else 'unknown'
    error_type = type(e).__name__
    error_msg = str(e)
    
    logger.error(f"""━━━━━━ WebSocket Error ━━━━━━
Type: {error_type}
SID: {sid}
Error: {error_msg}
Time: {datetime.now()}
━━━━━━━━━━━━━━━━━━━━━━━━""", exc_info=True)
    
    try:
        if sid in connection_manager['active_connections']:
            # Update failure metrics with error categorization
            breaker = connection_manager['circuit_breakers'].get(sid, {
                'failures': 0,
                'last_failure': None,
                'error_types': {},
                'recovery_attempts': 0
            })
            
            # Track error types for pattern detection
            breaker['error_types'][error_type] = breaker['error_types'].get(error_type, 0) + 1
            breaker['failures'] += 1
            breaker['last_failure'] = datetime.now()
            breaker['recovery_attempts'] += 1
            
            # Advanced recovery strategy based on error patterns
            recovery_strategy = determine_recovery_strategy(error_type, breaker)
            backoff_time = implement_backoff(sid)
            
            # Implement progressive recovery steps
            recovery_steps = [
                {'action': 'reconnect', 'timeout': backoff_time},
                {'action': 'transport_upgrade', 'timeout': backoff_time * 1.5},
                {'action': 'session_refresh', 'timeout': backoff_time * 2}
            ]
            
            current_step = min(breaker['recovery_attempts'] - 1, len(recovery_steps) - 1)
            step = recovery_steps[current_step]
            
            # Send detailed recovery information to client
            socketio.emit('connection_recovery', {
                'status': 'recovering',
                'message': f'Implementing recovery step {current_step + 1}: {step["action"]}',
                'action': step['action'],
                'backoff': step['timeout'],
                'attempt': breaker['recovery_attempts'],
                'error_type': error_type,
                'strategy': recovery_strategy
            }, to=sid)
            
            # Circuit breaker logic with error pattern analysis
            if should_trigger_circuit_breaker(breaker):
                logger.warning(f"""━━━━━━ Circuit Breaker Triggered ━━━━━━
SID: {sid}
Failures: {breaker['failures']}
Error Pattern: {dict(breaker['error_types'])}
Recovery Attempts: {breaker['recovery_attempts']}
━━━━━━━━━━━━━━━━━━━━━━━━""")
                
                cleanup_connection(sid)
                return False
            
            connection_manager['circuit_breakers'][sid] = breaker
            
    except Exception as recovery_error:
        logger.error(f"Error in recovery handler: {str(recovery_error)}", exc_info=True)
        try:
            socketio.emit('connection_recovery', {
                'status': 'failed',
                'message': 'Recovery mechanism failed, please refresh the page',
                'error': str(recovery_error)
            }, to=sid)
        except:
            pass
    return False

def determine_recovery_strategy(error_type, breaker):
    """Determine the best recovery strategy based on error patterns."""
    if error_type in ['ConnectionError', 'TimeoutError']:
        return 'reconnect'
    elif error_type in ['TransportError']:
        return 'transport_upgrade'
    elif breaker['failures'] > 3:
        return 'session_refresh'
    return 'reconnect'

def should_trigger_circuit_breaker(breaker):
    """Enhanced circuit breaker decision logic."""
    if breaker['failures'] >= connection_manager['circuit_breaker_threshold']:
        # Check error pattern severity
        error_pattern_severity = sum(
            count * (2 if error_type in ['ConnectionError', 'TimeoutError'] else 1)
            for error_type, count in breaker['error_types'].items()
        )
        return error_pattern_severity >= connection_manager['circuit_breaker_threshold']
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
    """Handle client connection with intelligent transport selection and state recovery."""
    try:
try:
    current_time = datetime.now()
    sid = request.sid
    
    # Get preserved reconnection state if available
    reconnection_state = connection_manager.get('reconnection_state', {}).get(sid, {})
    reconnection_data = reconnection_state.get('reconnection_data', {})
    
    # Intelligent transport selection
    current_transport = request.args.get('transport', 'websocket')
    last_transport = reconnection_data.get('last_transport')
    
    if last_transport and last_transport != current_transport:
        logger.info(f"Transport changed from {last_transport} to {current_transport}")
        
        # If websocket failed previously, try polling
        if last_transport == 'websocket' and reconnection_data.get('attempts', 0) > 2:
            logger.info("Multiple websocket failures detected, suggesting polling transport")
            socketio.emit('transport_suggestion', {
                'suggested_transport': 'polling',
                'reason': 'websocket_stability'
            }, to=sid)
    
    # Initialize enhanced connection metrics
    connection_manager['transport_type'][sid] = current_transport
    connection_manager['active_connections'].add(sid)
    connection_manager['connection_times'][sid] = current_time
    connection_manager['last_activity'][sid] = current_time
    
    # Restore reconnection counters with decay
    if 'attempts' in reconnection_data:
        decay_factor = min(1.0, (datetime.now() - reconnection_state.get('last_cleanup', datetime.now())).total_seconds() / 300)
        connection_manager['reconnection_attempts'][sid] = int(reconnection_data['attempts'] * decay_factor)
    else:
        connection_manager['reconnection_attempts'][sid] = 0
    
    # Initialize quality metrics
    connection_manager['connection_quality'][sid] = {
        'latency': 0,
        'failed_pings': 0,
        'successful_pings': 0,
        'transport_upgrades': 0,
        'ping_history': [],
        'error_count': 0,
        'transport_history': [current_transport]
    }
    
    # Send enhanced connection acknowledgment
    socketio.emit('connection_status', {
        'status': 'connected',
        'sid': sid,
        'timestamp': current_time.isoformat(),
        'transport': current_transport,
        'reconnection_enabled': True,
        'ping_interval': 25000,
        'ping_timeout': 60000,
        'connection_info': {
            'previous_transport': last_transport,
            'reconnection_count': connection_manager['reconnection_attempts'][sid],
            'suggested_transport': 'polling' if reconnection_data.get('attempts', 0) > 2 else 'websocket'
        }
    })
    
    # Start enhanced monitoring
    eventlet.spawn(monitor_connection_quality, sid)
    
except Exception as e:
    logger.error(f"Error in connection handler: {str(e)}", exc_info=True)
    try:
        if not request.sid:
            return
        
        socketio.emit('connection_recovery', {
            'status': 'error',
            'message': 'Connection initialization failed, retrying...',
            'timestamp': datetime.now().isoformat()
        }, to=request.sid)
    except Exception as emit_error:
        logger.error(f"Failed to send error status: {str(emit_error)}")
        current_time = datetime.now()
        sid = request.sid
        
        # Enhanced connection handling with transport optimization
        transport = request.args.get('transport', 'websocket')
        
        # If reconnecting, check previous state
        if sid in connection_manager['active_connections']:
            prev_transport = connection_manager.get('transport_type', {}).get(sid)
            if prev_transport and prev_transport != transport:
                logger.info(f"Transport change detected for {sid}: {prev_transport} -> {transport}")
                
            # Reset failure counters on successful reconnect
            if sid in connection_manager['circuit_breakers']:
                connection_manager['circuit_breakers'][sid]['consecutive_failures'] = 0
                
            cleanup_connection(sid)  # Clean old state
            
        # Track transport type
        connection_manager.setdefault('transport_type', {})[sid] = transport
        
        # Initialize connection state with defaults
        connection_manager['active_connections'].add(sid)
        connection_manager['connection_times'][sid] = current_time
        connection_manager['last_activity'][sid] = current_time
        connection_manager['reconnection_attempts'][sid] = 0
        connection_manager['backoff_times'][sid] = 0.1  # Initial backoff
        
        # Initialize quality metrics
        connection_manager['connection_quality'][sid] = {
            'latency': 0,
            'failed_pings': 0,
            'successful_pings': 0,
            'transport_upgrades': 0,
            'ping_history': [],
            'error_count': 0
        }
        
        # Send enhanced connection acknowledgment
        socketio.emit('connection_status', {
            'status': 'connected',
            'sid': sid,
            'timestamp': current_time.isoformat(),
            'transport': request.args.get('transport', 'websocket'),
            'ping_timeout': socketio.ping_timeout,
            'ping_interval': socketio.ping_interval
        }, to=sid)
        
        logger.info(f"""━━━━━━ New Connection ━━━━━━
Client: {sid}
Transport: {request.args.get('transport', 'websocket')}
Time: {current_time}
━━━━━━━━━━━━━━━━━━━━━━━━""")
        
    except Exception as e:
        logger.error(f"Error in connection handler: {str(e)}", exc_info=True)
        # Attempt graceful recovery
        try:
            socketio.emit('connection_recovery', {
                'status': 'error',
                'message': 'Connection initialization failed, retrying...',
                'timestamp': datetime.now().isoformat()
            }, to=request.sid)
        except:
            pass
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
            'transport_upgrades': 0,
            'ping_history': []
        }
        
        # Aggressive connection status monitoring
        def monitor_connection_quality():
            """Enhanced connection quality monitoring with adaptive thresholds."""
            while sid in connection_manager['active_connections']:
                try:
                    # Calculate advanced connection quality metrics
                    current_time = datetime.now()
                    time_connected = (current_time - connection_manager['connection_times'][sid]).total_seconds()
                    quality = connection_manager['connection_quality'][sid]
                    
                    # Initialize quality metrics if not exist
                    quality = connection_manager['connection_quality'].get(sid, {
                        'latency': 0,
                        'failed_pings': 0,
                        'successful_pings': 0,
                        'transport_upgrades': 0,
                        'ping_history': [],
                        'weighted_success_rate': 1.0
                    })
                    
                    # Calculate weighted success rate based on recent activity
                    recent_window = 300  # Last 5 minutes
                    
                    # Add current ping to history with timestamp
                    quality['ping_history'].append({
                        'success': True,
                        'latency': quality['latency'],
                        'timestamp': current_time
                    })
                    
                    # Remove old entries
                    quality['ping_history'] = [
                        ping for ping in quality['ping_history']
                        if (current_time - ping['timestamp']).total_seconds() <= recent_window
                    ]
                    
                    # Calculate weighted metrics
                    recent_pings = quality['ping_history']
                    total_pings = len(recent_pings)
                    weighted_success = 1.0  # Default to perfect score
                    
                    if total_pings > 0:
                        # Weight more recent pings higher
                        weighted_success = sum(
                            ping['success'] * (1 + (current_time - ping['timestamp']).total_seconds() / recent_window)
                            for ping in recent_pings
                        ) / total_pings
                        
                    # Update quality metrics in connection manager
                    connection_manager['connection_quality'][sid] = quality
                        
                        # Calculate metrics based on ping history
                    if total_pings > 0:
                        avg_latency = sum(ping['latency'] for ping in recent_pings) / total_pings
                        latency_variance = sum((ping['latency'] - avg_latency) ** 2 for ping in recent_pings) / total_pings
                    else:
                        weighted_success = 1.0
                        avg_latency = 0
                        latency_variance = 0
                    
                    # Update quality metrics
                    quality['weighted_success_rate'] = weighted_success
                    quality['avg_latency'] = avg_latency
                    quality['latency_variance'] = latency_variance
                    
                    # Log detailed metrics periodically
                    if time_connected % 60 == 0:  # Log every minute
                        logger.info(f"""━━━━━━ Enhanced Connection Quality ━━━━━━
Client: {sid}
Uptime: {time_connected:.1f}s
Weighted Success: {weighted_success:.2%}
Avg Latency: {avg_latency:.2f}ms
Latency Variance: {latency_variance:.2f}
Recent Pings: {total_pings}
Transport: {request.args.get('transport', 'unknown')}
Upgrades: {quality['transport_upgrades']}
━━━━━━━━━━━━━━━━━━━━━━━━""")
                    
                    # Adaptive recovery thresholds
                    should_recover = (
                        weighted_success < 0.7 or  # Poor success rate
                        avg_latency > 1000 or      # High latency
                        latency_variance > 5000 or  # Unstable connection
                        total_pings < 10           # Too few pings
                    )
                    
                    if should_recover:
                        logger.warning(f"""━━━━━━ Connection Recovery Needed ━━━━━━
Client: {sid}
Reason: {'Success Rate' if weighted_success < 0.7 else 'High Latency' if avg_latency > 1000 else 'Unstable Connection' if latency_variance > 5000 else 'Low Ping Count'}
Metrics:
- Success Rate: {weighted_success:.2%}
- Avg Latency: {avg_latency:.2f}ms
- Variance: {latency_variance:.2f}
━━━━━━━━━━━━━━━━━━━━━━━━""")
                        
                        # Implement progressive transport upgrade
                        current_transport = request.args.get('transport', 'polling')
                        new_transport = 'websocket' if current_transport == 'polling' else 'polling'
                        
                        socketio.emit('connection_recovery', {
                            'action': 'transport_upgrade',
                            'current_transport': current_transport,
                            'new_transport': new_transport,
                            'metrics': {
                                'success_rate': weighted_success,
                                'avg_latency': avg_latency,
                                'variance': latency_variance
                            }
                        }, to=sid)
                        
                        quality['transport_upgrades'] += 1
                        
                except Exception as e:
                    logger.error(f"Error in connection monitoring: {str(e)}", exc_info=True)
                    quality['failed_pings'] += 1
                finally:
                    # Adaptive monitoring interval based on connection quality
                    sleep_time = 1 if weighted_success > 0.8 else 0.5
                    eventlet.sleep(sleep_time)
                    
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
            while request.sid in connection_manager['active_connections']:
                eventlet.sleep(10)  # Check every 10 seconds
                if request.sid in connection_manager['last_activity']:
                    last_activity = connection_manager['last_activity'][request.sid]
                    if (datetime.now() - last_activity).total_seconds() > 30:
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
    """Enhanced disconnect handler with intelligent reconnection strategy and state management."""
    try:
        current_time = datetime.now()
        sid = request.sid
        
        if not sid:
            logger.warning("Disconnect event without SID")
            return
            
        # Get disconnect reason and classify it
        reason = request.args.get('reason', 'unknown')
        is_clean_disconnect = reason in ['client_disconnect', 'ping_timeout']
        transport = connection_manager.get('transport_type', {}).get(sid, 'unknown')
        
        # Log enhanced disconnect information
        logger.info(f"""━━━━━━ Enhanced Disconnect ━━━━━━
Client: {sid}
Reason: {reason}
def monitor_connection_quality(sid):
    """Monitor connection quality and implement adaptive transport selection."""
    if not sid:
        logger.error("Invalid SID provided to monitor_connection_quality")
        return
        
    try:
        while sid in connection_manager.get('active_connections', set()):
            current_time = datetime.now()
            quality = connection_manager.get('connection_quality', {}).get(sid, {})
            
            # Initialize quality metrics if not present
            if 'ping_history' not in quality:
                quality['ping_history'] = []
                quality['failed_pings'] = 0
                quality['successful_pings'] = 0
                connection_manager['connection_quality'][sid] = quality
            
            # Calculate quality metrics
            ping_history = quality.get('ping_history', [])
            recent_pings = [p for p in ping_history if (current_time - p['timestamp']).total_seconds() <= 300]
            
            if recent_pings:
                # Calculate weighted metrics
                total_weight = sum(1 + (current_time - p['timestamp']).total_seconds() / 300 for p in recent_pings)
                weighted_latency = sum(p['latency'] * (1 + (current_time - p['timestamp']).total_seconds() / 300) 
                                    for p in recent_pings) / total_weight
                
                # Detect degrading connection
                if weighted_latency > 1000 or quality.get('failed_pings', 0) > 3:
                    current_transport = connection_manager.get('transport_type', {}).get(sid)
                    if current_transport == 'websocket':
                        logger.warning(f"Connection quality degrading for {sid}, suggesting transport fallback")
                        socketio.emit('transport_suggestion', {
                            'suggested_transport': 'polling',
                            'reason': 'quality_degradation',
                            'metrics': {
                                'latency': weighted_latency,
                                'failed_pings': quality.get('failed_pings', 0)
                            }
                        }, to=sid)
            
            # Update quality metrics
            quality['ping_history'] = recent_pings
            connection_manager['connection_quality'][sid] = quality
            
            # Adaptive monitoring interval
            sleep_time = 5 if len(recent_pings) < 5 or weighted_latency > 500 else 10
            eventlet.sleep(sleep_time)
            
    except Exception as e:
        logger.error(f"Error monitoring connection quality for {sid}: {str(e)}", exc_info=True)
    finally:
        if sid in connection_manager['active_connections']:
            logger.info(f"Stopping quality monitoring for {sid}")
Transport: {transport}
Clean Disconnect: {is_clean_disconnect}
Time: {current_time}
━━━━━━━━━━━━━━━━━━━━━━━━""")
            
        # Get connection metrics
        connected_duration = 0
        if sid in connection_manager['connection_times']:
            connected_duration = (current_time - connection_manager['connection_times'][sid]).total_seconds()
        
        # Increment reconnection counter
        if sid in connection_manager['reconnection_attempts']:
            connection_manager['reconnection_attempts'][sid] += 1
            attempts = connection_manager['reconnection_attempts'][sid]
        else:
            connection_manager['reconnection_attempts'][sid] = 1
            attempts = 1
            
        # Calculate backoff with jitter
        base_delay = min(connection_manager['backoff_times'].get(sid, 0.1) * 2, 30)
        jitter = random.uniform(0, 0.1 * base_delay)
        backoff_time = base_delay + jitter
        connection_manager['backoff_times'][sid] = backoff_time
        
        # Log disconnect details
        logger.info(f"""━━━━━━ Client Disconnected ━━━━━━
SID: {sid}
Duration: {connected_duration:.1f}s
Attempts: {attempts}
Backoff: {backoff_time:.2f}s
Reason: {request.args.get('reason', 'unknown')}
━━━━━━━━━━━━━━━━━━━━━━━━""")
        
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
        
        # Enhanced reconnection handling with exponential backoff
        current_attempts = connection_manager['reconnection_attempts'].get(sid, 0) + 1
        connection_manager['reconnection_attempts'][sid] = current_attempts
        
        # Calculate exponential backoff with jitter
        base_delay = min(2 ** (current_attempts - 1), 30)  # Cap at 30 seconds
        jitter = random.uniform(0, 0.1 * base_delay)
        backoff_time = base_delay + jitter
        
        # Implement progressive recovery for unexpected disconnects
        if disconnect_info['reason'] not in ['client_disconnect', 'ping_timeout']:
            try:
                # Select appropriate transport based on connection history
                suggested_transport = 'websocket'
                if sid in connection_manager.get('transport_type', {}) and \
                   connection_manager['transport_type'][sid] == 'websocket':
                    suggested_transport = 'polling'  # Try alternative transport
                
                recovery_message = {
                    'action': 'reconnect',
                    'attempt': current_attempts,
                    'backoff': backoff_time,
                    'timestamp': current_time.isoformat(),
                    'suggested_transport': suggested_transport,
                    'next_attempt': (current_time + eventlet.Timeout(backoff_time)).isoformat()
                }
                
                # Send recovery instructions to client
                socketio.emit('connection_recovery', recovery_message, to=sid)
                logger.info(f"""━━━━━━ Recovery Attempt ━━━━━━
Client: {sid}
Attempt: {current_attempts}
Backoff: {backoff_time:.2f}s
Transport: {suggested_transport}
━━━━━━━━━━━━━━━━━━━━━━━━""")
                
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
    """Clean up connection state with enhanced error handling and resource management."""
    if not sid:
        logger.warning("Attempted cleanup with invalid SID")
        return
        
    logger.info(f"Starting cleanup for client {sid}")
    current_time = datetime.now()
    
    try:
        # Safely calculate connection duration
        if sid in connection_manager.get('connection_times', {}):
            connected_duration = (current_time - connection_manager['connection_times'][sid]).total_seconds()
            logger.info(f"Connection duration: {connected_duration:.1f}s")
            
        # Initialize cleanup status tracking
        cleanup_status = {
            'active_connections': False,
            'connection_times': False,
            'reconnection_attempts': False,
            'last_activity': False,
            'connection_quality': False,
            'transport_type': False,
            'backoff_times': False,
            'circuit_breakers': False
        }
            
        # Cleanup all tracking data
        tracking_keys = [
            'active_connections',
            'connection_times',
            'reconnection_attempts',
            'last_activity',
            'connection_quality',
            'backoff_times',
            'circuit_breakers',
            'transport_type'
        ]
        
        for key in tracking_keys:
            try:
                if sid in connection_manager.get(key, {}):
                    if isinstance(connection_manager[key], set):
                        connection_manager[key].discard(sid)
                    else:
                        del connection_manager[key][sid]
            except Exception as e:
                logger.warning(f"Error cleaning up {key} for {sid}: {str(e)}")
                
        # Force socket disconnect if still connected
        try:
            socketio.disconnect(sid)
        except Exception as e:
            logger.debug(f"Error disconnecting socket for {sid}: {str(e)}")
            
        logger.info(f"Cleanup completed for client {sid}")
        
    except Exception as e:
        logger.error(f"Error in connection cleanup: {str(e)}", exc_info=True)
    finally:
        # Ensure critical cleanup always happens
        if sid in connection_manager['active_connections']:
            connection_manager['active_connections'].discard(sid)
        connection_manager['active_connections'].discard(sid)
        connection_manager['connection_times'].pop(sid, None)
        connection_manager['last_activity'].pop(sid, None)
        connection_manager['connection_quality'].pop(sid, None)
        
        logger.info(f"Connection state cleaned up for {sid}")
    except Exception as e:
        logger.error(f"Error cleaning up connection state: {str(e)}")

@socketio.on('heartbeat')
def handle_heartbeat():
    """Advanced heartbeat handler with sophisticated connection analysis."""
    try:
        current_time = datetime.now()
        sid = request.sid if hasattr(request, 'sid') else None
        
        if not sid:
            logger.error("No SID available in heartbeat request")
            return {'status': 'error', 'message': 'Invalid session'}
            
        try:
            # Initialize connection tracking if needed
            if sid not in connection_manager.get('active_connections', set()):
                connection_manager.setdefault('active_connections', set()).add(sid)
                connection_manager.setdefault('connection_quality', {})[sid] = {
                    'latency': 0,
                    'successful_pings': 0,
                    'failed_pings': 0,
                    'ping_history': [],
                    'last_ping_time': current_time,
                    'transport': request.args.get('transport', 'websocket')
                }
                connection_manager.setdefault('last_activity', {})[sid] = current_time
                
                # Log new connection
                logger.info(f"""━━━━━━ New Connection ━━━━━━
Client: {sid}
Transport: {request.args.get('transport', 'websocket')}
Time: {current_time}
━━━━━━━━━━━━━━━━━━━━━━━━""")
        except Exception as e:
            logger.error(f"Error initializing connection for {sid}: {str(e)}")
            return {'status': 'error', 'message': 'Connection initialization failed'}
            
        quality = connection_manager['connection_quality'][sid]
        last_activity = connection_manager['last_activity'].get(sid)
            
            if last_activity:
                # Calculate detailed timing metrics
                interval = (current_time - last_activity).total_seconds() * 1000
                expected_interval = socketio.ping_interval * 1000
                drift = abs(interval - expected_interval)
                
                # Update connection quality metrics
                quality.setdefault('timing_stats', {
                    'intervals': [],
                    'drifts': [],
                    'jitter': 0,
                    'drift_threshold': expected_interval * 0.2  # 20% tolerance
                })
                
                # Update timing statistics
                stats = quality['timing_stats']
                stats['intervals'].append(interval)
                stats['drifts'].append(drift)
                
                # Keep only recent history
                max_history = 50
                if len(stats['intervals']) > max_history:
                    stats['intervals'] = stats['intervals'][-max_history:]
                    stats['drifts'] = stats['drifts'][-max_history:]
                
                # Calculate jitter (variation in intervals)
                if len(stats['intervals']) >= 2:
                    differences = [abs(stats['intervals'][i] - stats['intervals'][i-1])
                                 for i in range(1, len(stats['intervals']))]
                    stats['jitter'] = sum(differences) / len(differences)
                
                # Analyze connection health
                avg_drift = sum(stats['drifts']) / len(stats['drifts'])
                max_drift = max(stats['drifts'])
                
                # Detect timing anomalies
                timing_issues = []
                if avg_drift > stats['drift_threshold']:
                    timing_issues.append('high_average_drift')
                if max_drift > stats['drift_threshold'] * 2:
                    timing_issues.append('excessive_drift_spike')
                if stats['jitter'] > expected_interval * 0.1:
                    timing_issues.append('high_jitter')
                
                # Log timing anomalies
                if timing_issues:
                    logger.warning(f"""━━━━━━ Heartbeat Timing Issues ━━━━━━
Client: {sid}
Issues: {', '.join(timing_issues)}
Metrics:
- Avg Drift: {avg_drift:.2f}ms
- Max Drift: {max_drift:.2f}ms
- Jitter: {stats['jitter']:.2f}ms
Expected Interval: {expected_interval}ms
━━━━━━━━━━━━━━━━━━━━━━━━""")
                
                # Update quality metrics
                quality['latency'] = interval
                quality['successful_pings'] += 1
                
                # Calculate health score (0-100)
                drift_score = max(0, 100 - (avg_drift / stats['drift_threshold']) * 50)
                jitter_score = max(0, 100 - (stats['jitter'] / (expected_interval * 0.1)) * 50)
                health_score = (drift_score + jitter_score) / 2
                
                # Determine connection status
                connection_status = (
                    'excellent' if health_score >= 90 else
                    'good' if health_score >= 70 else
                    'fair' if health_score >= 50 else
                    'poor'
                )
                
                # Enhanced response with detailed metrics
                response = {
                    'status': 'ok',
                    'timestamp': current_time.isoformat(),
                    'metrics': {
                        'latency': interval,
                        'jitter': stats['jitter'],
                        'drift': avg_drift,
                        'health_score': health_score
                    },
                    'connection_quality': connection_status,
                    'timing_issues': timing_issues if timing_issues else None
                }
                
                # Update last activity
                connection_manager['last_activity'][sid] = current_time
                
                return response
                
    except Exception as e:
        logger.error(f"""━━━━━━ Heartbeat Error ━━━━━━
SID: {sid if 'sid' in locals() else 'unknown'}
Error: {str(e)}
Time: {datetime.now()}
━━━━━━━━━━━━━━━━━━━━━━━━""", exc_info=True)
        
        if 'sid' in locals() and sid in connection_manager['connection_quality']:
            connection_manager['connection_quality'][sid]['failed_pings'] += 1
        
        return {
            'status': 'error',
            'message': str(e),
            'timestamp': datetime.now().isoformat()
        }

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