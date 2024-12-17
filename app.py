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
from flask_socketio import SocketIO, emit
from flask_cors import CORS
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from chat_handler import ChatHandler
import psutil

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
    """Enhanced health check endpoint for Railway."""
    try:
        # Check critical services
        services_status = {
            'web': True,
            'socket': bool(socketio and hasattr(socketio, 'server')),
            'chat_handler': chat_handler is not None
        }
        
        # Check system resources
        process = psutil.Process()
        memory_usage = process.memory_percent()
        cpu_usage = process.cpu_percent()
        
        response = {
            'status': 'healthy',
            'timestamp': datetime.now().isoformat(),
            'services': services_status,
            'system': {
                'memory_usage': f"{memory_usage:.1f}%",
                'cpu_usage': f"{cpu_usage:.1f}%",
                'uptime': str(datetime.now() - app.start_time) if hasattr(app, 'start_time') else 'N/A'
            }
        }
        return response, 200
    except Exception as e:
        logger.error(f"Health check failed: {str(e)}")
        return {
            'status': 'unhealthy',
            'timestamp': datetime.now().isoformat(),
            'error': str(e)
        }, 500

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

def get_service_health():
    """Get real-time health metrics for all services with enhanced monitoring."""
    try:
        # Get process metrics
        process = psutil.Process()
        web_memory = process.memory_percent()
        web_cpu = process.cpu_percent()
        web_health = 100 - (web_memory + web_cpu) / 2
        
        # Enhanced disk and network metrics
        disk = psutil.disk_usage('/')
        net_io = psutil.net_io_counters()
        
        # Calculate service health and status with more detailed metrics
        services = {
            'web': {
                'status': 'connected' if web_health > 50 else 'warning',
                'metrics': {
                    'health': round(web_health, 1),
                    'memory': round(web_memory, 1),
                    'cpu': round(web_cpu, 1),
                    'disk': round(disk.percent, 1),
                    'network': {
                        'sent': round(net_io.bytes_sent / 1024 / 1024, 2),  # MB
                        'received': round(net_io.bytes_recv / 1024 / 1024, 2)  # MB
                    }
                }
            },
            'discord': {
                'status': 'connecting',
                'metrics': {
                    'health': 0,
                    'guilds': 0,
                    'latency': 0,
                    'uptime': 0
                }
            },
            'telegram': {
                'status': 'connecting',
                'metrics': {
                    'health': 0,
                    'chats': 0,
                    'updates': 0,
                    'uptime': 0
                }
            }
        }
        
        # Enhanced Discord bot monitoring
        try:
            with open('discord_bot.log', 'r') as f:
                logs = f.readlines()[-100:]
                latest_status = {
                    'ready': False,
                    'guilds': 0,
                    'latency': 0,
                    'error_count': 0,
                    'last_health_check': None
                }
                
                for line in reversed(logs):
                    if 'Bot Ready' in line:
                        latest_status['ready'] = True
                    if 'Guilds:' in line:
                        try:
                            latest_status['guilds'] = int(line.split('Guilds:')[1].strip())
                        except ValueError:
                            pass
                    if 'Latency:' in line and 'ms' in line:
                        try:
                            latency = float(line.split('Latency:')[1].split('ms')[0].strip())
                            latest_status['latency'] = round(latency, 2)
                        except ValueError:
                            pass
                    if 'Error Count:' in line:
                        try:
                            latest_status['error_count'] = int(line.split('Error Count:')[1].strip())
                        except ValueError:
                            pass
                    if 'Health Check' in line:
                        latest_status['last_health_check'] = line.split('[')[0].strip()
                
                if latest_status['ready']:
                    services['discord']['status'] = 'connected'
                    services['discord']['metrics'].update({
                        'health': max(0, 100 - latest_status['error_count'] * 10),
                        'guilds': latest_status['guilds'],
                        'latency': latest_status['latency'],
                        'error_count': latest_status['error_count']
                    })
                elif 'Connection Error' in ''.join(logs[-10:]):
                    services['discord']['status'] = 'error'
                    
        except Exception as e:
            logger.error(f"Error reading Discord logs: {str(e)}")
            
        # Enhanced Telegram bot monitoring
        try:
            with open('telegram_bot.log', 'r') as f:
                logs = f.readlines()[-100:]
                latest_status = {
                    'polling': False,
                    'chats': 0,
                    'updates': 0,
                    'memory': 0,
                    'cpu': 0
                }
                
                for line in reversed(logs):
                    if 'Bot started polling' in line:
                        latest_status['polling'] = True
                    if 'Active chats:' in line:
                        try:
                            latest_status['chats'] = int(line.split('Active chats:')[1].strip())
                        except ValueError:
                            pass
                    if 'Memory Usage:' in line and 'MB' in line:
                        try:
                            latest_status['memory'] = float(line.split('Memory Usage:')[1].split('MB')[0].strip())
                        except ValueError:
                            pass
                    if 'CPU Usage:' in line and '%' in line:
                        try:
                            latest_status['cpu'] = float(line.split('CPU Usage:')[1].split('%')[0].strip())
                        except ValueError:
                            pass
                
                if latest_status['polling']:
                    services['telegram']['status'] = 'connected'
                    services['telegram']['metrics'].update({
                        'health': max(0, 100 - (latest_status['memory'] / 2 + latest_status['cpu'] / 2)),
                        'chats': latest_status['chats'],
                        'updates': latest_status['updates'],
                        'memory': round(latest_status['memory'], 1),
                        'cpu': round(latest_status['cpu'], 1)
                    })
                elif 'Error' in ''.join(logs[-10:]):
                    services['telegram']['status'] = 'error'
                    
        except Exception as e:
            logger.error(f"Error reading Telegram logs: {str(e)}")
        
        # Add warnings and errors
        warnings = []
        errors = []
        
        # Check high resource usage
        if web_memory > 80:
            warnings.append(f"High memory usage: {web_memory:.1f}%")
        if web_cpu > 80:
            warnings.append(f"High CPU usage: {web_cpu:.1f}%")
        if disk.percent > 85:
            warnings.append(f"High disk usage: {disk.percent}%")
            
        return {
            'services': services,
            'warnings': warnings,
            'errors': errors,
            'timestamp': datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error getting service health: {str(e)}")
        return {
            'services': {},
            'warnings': [],
            'errors': [str(e)],
            'timestamp': datetime.now().isoformat()
        }

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

def start_health_monitoring():
    """Start periodic health monitoring updates."""
    def emit_health_update():
        while True:
            try:
                health_data = get_service_health()
                socketio.emit('health_update', health_data, broadcast=True)
            except Exception as e:
                logger.error(f"Health monitoring error: {str(e)}")
            eventlet.sleep(5)  # Update every 5 seconds
    
    if not hasattr(app, '_health_monitor_started'):
        eventlet.spawn(emit_health_update)
        app._health_monitor_started = True
        logger.info("Health monitoring started")

@socketio.on('connect')
def handle_connect():
    """Handle client connection with enhanced error handling and state tracking."""
    try:
        # Start health monitoring if not already started

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
        emit('connection_status', {
            'status': 'connected',
            'sid': request.sid,
            'timestamp': datetime.now().isoformat(),
            'reconnect_info': {
                'attempts': client_info['reconnect_attempts'],
                'max_attempts': 5,
                'delay': 2000
            }
        })
        
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
        emit('receive_message', {
            'message': help_message,
            'is_bot': True
        })
        
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
        emit('connection_status', error_response)

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

@socketio.on('request_health_update')
def handle_health_update_request():
    """Handle client request for health update with enhanced error handling."""
    try:
        health_data = get_service_health()
        emit('health_update', health_data)
        logger.info("Health update sent successfully")
    except Exception as e:
        error_msg = f"Error sending health update: {str(e)}"
        logger.error(error_msg, exc_info=True)
        emit('health_update', {
            'status': 'error',
            'message': error_msg,
            'timestamp': datetime.now().isoformat(),
            'services': {
                'web': {'status': 'error', 'metrics': {}},
                'discord': {'status': 'error', 'metrics': {}},
                'telegram': {'status': 'error', 'metrics': {}}
            }
        })


# Initialize health monitoring when the app starts

# Initialize health monitoring when SocketIO starts
# This function is now called only once within the start_health_monitoring function.

if __name__ == '__main__':
    try:
        # Railway specific configuration
        port = int(os.environ.get('PORT', 5000))
        debug = os.environ.get('FLASK_ENV') != 'production'
        app.start_time = datetime.now()
        
        # Initialize required services
        if not chat_handler:
            logger.warning("Chat handler not initialized, attempting to initialize...")
            try:
                chat_handler = ChatHandler()
            except Exception as e:
                logger.error(f"Failed to initialize chat handler: {e}")
                # Continue anyway as this is not critical for health checks
        
        # Enhanced startup logging with Railway specific info
        logger.info(f"""
━━━━━━ Railway Server Starting ━━━━━━
Port: {port}
Host: 0.0.0.0
Debug: {debug}
Environment: {os.environ.get('RAILWAY_ENVIRONMENT', 'development')}
Memory: {psutil.Process().memory_info().rss / 1024 / 1024:.1f}MB
CPU: {psutil.cpu_percent()}%
Services:
- Chat Handler: {'✓' if chat_handler else '✗'}
- Socket.IO: ✓
━━━━━━━━━━━━━━━━━━━━━━━━""")
        
        # Start health monitoring
        start_health_monitoring()
        
        # Run the application with Railway optimized settings
        socketio.run(
            app,
            host='0.0.0.0',  # Required for Railway
            port=port,
            debug=debug,
            use_reloader=False,  # Disable reloader for Railway
            log_output=True,
            allow_unsafe_werkzeug=True  # Required for Railway
        )
    except Exception as e:
        error_msg = f"""
━━━━━━ Railway Startup Error ━━━━━━
Error: {str(e)}
Type: {type(e).__name__}
Time: {datetime.now().isoformat()}
Memory: {psutil.Process().memory_info().rss / 1024 / 1024:.1f}MB
CPU: {psutil.cpu_percent()}%
━━━━━━━━━━━━━━━━━━━━━━━━"""
        logger.error(error_msg)
        # Ensure the error is visible in Railway logs
        print(error_msg, file=sys.stderr)
        raise  # Re-raise for Railway to detect failure