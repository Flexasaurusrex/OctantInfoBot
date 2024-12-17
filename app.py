import os
import logging
import json
from flask import Flask, render_template, request, Response, stream_with_context
from flask_socketio import SocketIO, emit
from flask_cors import CORS
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
import queue
import threading
import psutil
from datetime import datetime
import eventlet
from chat_handler import ChatHandler

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('app.log')
    ]
)
logger = logging.getLogger(__name__)

# Initialize Flask app
app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get("FLASK_SECRET_KEY", "octant-chat-secret")
socketio = SocketIO(app, cors_allowed_origins="*")

# Initialize rate limiter
limiter = Limiter(
    get_remote_address,
    app=app,
    default_limits=["200 per day", "50 per hour"],
    storage_uri="memory://"
)

def message_stream(client_id):
    """Generate SSE stream for client."""
    if client_id not in client_queues:
        with client_lock:
            client_queues[client_id] = queue.Queue()
    
    def generate():
        try:
            while True:
                message = client_queues[client_id].get()
                yield f"data: {json.dumps(message)}\n\n"
        except GeneratorExit:
            with client_lock:
                if client_id in client_queues:
                    del client_queues[client_id]
                    
    return generate()

@app.route('/stream')
def stream():
    """SSE endpoint for real-time messages."""
    client_id = request.args.get('client_id')
    if not client_id:
        return "Client ID required", 400
        
    return Response(
        stream_with_context(message_stream(client_id)),
        mimetype='text/event-stream',
        headers={
            'Cache-Control': 'no-cache',
            'Connection': 'keep-alive',
            'X-Accel-Buffering': 'no'
        }
    )

@app.route('/send', methods=['POST'])
def send_message():
    """Endpoint for sending messages to the bot."""
    try:
        data = request.json
        if not data or 'message' not in data or 'client_id' not in data:
            return {'error': 'Invalid request format'}, 400
            
        client_id = data['client_id']
        message = data['message']
        
        # Process message using chat handler
        response = chat_handler.handle_socket_message(client_id, message)
        
        # Send response to client's queue
        if client_id in client_queues:
            client_queues[client_id].put({
                'message': response,
                'is_bot': True
            })
            
        return {'status': 'success'}
        
    except Exception as e:
        logger.error(f"Error processing message: {str(e)}")
        return {'error': 'Internal server error'}, 500
CORS(app)

# Message queues for each client
client_queues = {}
client_lock = threading.Lock()

# Initialize chat handler
try:
    chat_handler = ChatHandler()
except Exception as e:
    logger.error(f"Failed to initialize ChatHandler: {e}")
    chat_handler = None

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
                socketio.emit('health_update', health_data, namespace='/', room=None)
            except Exception as e:
                logger.error(f"Health monitoring error: {str(e)}")
            eventlet.sleep(5)  # Update every 5 seconds
    
    if not hasattr(app, '_health_monitor_started'):
        eventlet.spawn(emit_health_update)
        app._health_monitor_started = True
        logger.info("Health monitoring started")

@socketio.on('connect')
def handle_connect():
    """Handle client connection with enhanced state tracking"""
    try:
        client_id = request.sid
        logger.info(f"Client connected: {client_id}")
        
        # Initialize client state
        active_connections[client_id] = {
            'connected_at': datetime.now().isoformat(),
            'messages': [],
            'last_ping': datetime.now()
        }
        
        # Send connection acknowledgment
        emit('connection_status', {
            'status': 'connected',
            'client_id': client_id,
            'timestamp': datetime.now().isoformat()
        }, room=client_id)
        
        # Send welcome message
        emit('receive_message', {
            'message': "👋 Hello! I'm the Octant Information Bot. How can I help you today?",
            'is_bot': True
        }, room=client_id)
        
        return True
        
    except Exception as e:
        logger.error(f"Error in handle_connect: {e}")
        emit('connection_status', {
            'status': 'error', 
            'message': str(e)
        }, room=client_id)
        return False

@socketio.on('disconnect')
def handle_disconnect():
    """Handle client disconnection with cleanup"""
    try:
        client_id = request.sid
        logger.info(f"Client disconnected: {client_id}")
        
        
    except Exception as e:
        logger.error(f"Error in handle_disconnect: {e}")

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
    """Handle incoming messages with enhanced error recovery"""
    try:
        client_id = request.sid
        
        if not isinstance(data, dict) or 'message' not in data:
            raise ValueError("Invalid message format")
        
        message = data['message']
        logger.info(f"Message received from {client_id}: {message[:50]}...")
        
        if not chat_handler:
            raise RuntimeError("Chat handler not initialized")
        
        # Process message and get response
        response = chat_handler.handle_socket_message(client_id, message)
        
        if response:
            # Send response to client
            emit('receive_message', {
                'message': response,
                'is_bot': True
            })
            logger.info(f"Response sent to {client_id}")
            
        else:
            raise ValueError("No response generated")
            
    except Exception as e:
        logger.error(f"Error handling message: {e}")
        emit('receive_message', {
            'message': 'I apologize, but I encountered an error. Please try again.',
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
start_health_monitoring()

def start_server():
    """Start the server with enhanced error handling"""
    try:
        port = int(os.environ.get('PORT', 5000))
        debug = os.environ.get('FLASK_ENV') != 'production'
        app.start_time = datetime.now()
        
        logger.info(f"""
━━━━━━ Server Starting ━━━━━━
Port: {port}
Debug: {debug}
Environment: {os.environ.get('FLASK_ENV', 'development')}
Memory: {psutil.Process().memory_info().rss / 1024 / 1024:.1f}MB
CPU: {psutil.cpu_percent()}%
━━━━━━━━━━━━━━━━━━━━━━━━""")
        
        socketio.run(
            app,
            host='0.0.0.0',
            port=port,
            debug=debug,
            use_reloader=False,
            log_output=True
        )
        
    except Exception as e:
        logger.error(f"Failed to start server: {e}")
        raise

if __name__ == '__main__':
    start_server()