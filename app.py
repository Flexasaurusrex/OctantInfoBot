import eventlet
eventlet.monkey_patch()
import os
import time
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
    ping_timeout=10,
    ping_interval=5,
    reconnection=True,
    reconnection_attempts=5,
    reconnection_delay=1000,
    reconnection_delay_max=5000
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
                # Step 1: Enhanced prepare for restart
                logger.info("━━━━━━ Initiating Restart Sequence ━━━━━━")
                logger.info("Phase 1: Preparing for service shutdown...")
                
                # Enhanced process cleanup with force kill if needed
                import psutil
                current_pid = os.getpid()
                logger.info("━━━━━━ Cleaning up existing processes ━━━━━━")
                
                def force_kill_process(proc):
                    """Force kill a process if it doesn't terminate gracefully"""
                    try:
                        proc.terminate()
                        try:
                            proc.wait(timeout=5)
                        except psutil.TimeoutExpired:
                            logger.warning(f"Process {proc.pid} didn't terminate gracefully, forcing kill...")
                            proc.kill()
                            proc.wait(timeout=5)
                        return True
                    except (psutil.NoSuchProcess, psutil.AccessDenied) as e:
                        logger.error(f"Error killing process {proc.pid}: {str(e)}")
                        return False
                
                # First pass: collect all target processes
                target_processes = []
                for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
                    try:
                        if proc.info['name'] == 'python' and proc.pid != current_pid:
                            cmdline = proc.info['cmdline']
                            if cmdline and any(x in cmdline[-1] for x in ['discord_bot.py', 'telegram_bot.py']):
                                target_processes.append(proc)
                    except (psutil.NoSuchProcess, psutil.AccessDenied) as e:
                        continue
                
                # Second pass: terminate all collected processes
                for proc in target_processes:
                    try:
                        cmdline = proc.cmdline()[-1]
                        logger.info(f"Terminating process: {proc.pid} ({cmdline})")
                        if force_kill_process(proc):
                            logger.info(f"Successfully terminated process {proc.pid}")
                        else:
                            logger.warning(f"Failed to terminate process {proc.pid}")
                    except Exception as e:
                        logger.error(f"Unexpected error terminating process: {str(e)}")
                        continue
                
                # Verify all processes are terminated
                time.sleep(1)
                remaining = []
                for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
                    try:
                        if proc.info['name'] == 'python' and proc.pid != current_pid:
                            cmdline = proc.info['cmdline']
                            if cmdline and any(x in cmdline[-1] for x in ['discord_bot.py', 'telegram_bot.py']):
                                remaining.append(proc)
                    except (psutil.NoSuchProcess, psutil.AccessDenied):
                        continue
                
                if remaining:
                    logger.warning(f"Warning: {len(remaining)} bot processes still running after cleanup")
                else:
                    logger.info("All bot processes successfully terminated")

                # Enhanced state tracking
                active_connections = len(socketio.server.manager.rooms.get('/', set()))
                logger.info(f"Current active connections: {active_connections}")
                logger.info("Memory usage before cleanup: {:.2f}MB".format(
                    psutil.Process(os.getpid()).memory_info().rss / 1024 / 1024
                ))
                
                # Notify clients with enhanced status
                socketio.emit('restart_status', {
                    'status': 'preparing',
                    'message': 'Preparing to restart services...',
                    'countdown': 10,
                    'details': 'Cleaning up connections'
                }, namespace='/')
                
                # Step 2: Enhanced connection cleanup
                logger.info("Phase 2: Gracefully closing connections...")
                active_sids = list(socketio.server.manager.rooms.get('/', set()))
                
                for sid in active_sids:
                    try:
                        socketio.server.disconnect(sid, namespace='/')
                        logger.info(f"Successfully disconnected client {sid}")
                    except Exception as e:
                        logger.warning(f"Warning: Error disconnecting client {sid}: {str(e)}")
                        # Continue with other disconnections even if one fails
                
                logger.info("Phase 3: Verifying cleanup...")
                remaining_connections = len(socketio.server.manager.rooms.get('/', set()))
                logger.info(f"Remaining connections: {remaining_connections}")
                
                if remaining_connections == 0:
                    logger.info("All connections successfully cleaned up")
                else:
                    logger.warning(f"Warning: {remaining_connections} connections still active")
                
                # Step 3: Final notification with enhanced logging
                logger.info("Sending final restart notification...")
                try:
                    socketio.emit('restart_status', {
                        'status': 'restarting',
                        'message': 'Server is restarting...',
                        'countdown': 5
                    }, namespace='/')  # Using namespace instead of broadcast
                    
                    eventlet.sleep(2)
                    
                    # Step 4: Start discord and telegram bots with enhanced monitoring
                    logger.info("Starting Discord and Telegram bots...")
                    import subprocess
                    import time
                    
                    try:
                        # Enhanced process management for Discord bot with retries
                        logger.info("Starting Discord bot with enhanced monitoring...")
                        max_retries = 3
                        retry_count = 0
                        discord_process = None
                        
                        while retry_count < max_retries:
                            try:
                                # Kill any existing Discord bot processes first
                                subprocess.run(['pkill', '-f', 'discord_bot.py'], stderr=subprocess.PIPE)
                                time.sleep(2)  # Wait for process cleanup
                                
                                # Start Discord bot with full environment
                                env = os.environ.copy()
                                env['PYTHONUNBUFFERED'] = '1'  # Ensure output is not buffered
                                
                                discord_process = subprocess.Popen(
                                    ['python', 'discord_bot.py'],
                                    stdout=subprocess.PIPE,
                                    stderr=subprocess.PIPE,
                                    universal_newlines=True,
                                    env=env
                                )
                                
                                # Enhanced startup verification with detailed logging
                                startup_timeout = 30  # 30 seconds total
                                check_interval = 5    # Check every 5 seconds
                                checks = startup_timeout // check_interval
                                
                                for i in range(checks):
                                    time.sleep(check_interval)
                                    if discord_process.poll() is not None:
                                        stdout, stderr = discord_process.communicate()
                                        logger.error(f"Discord bot terminated early!\nStdout: {stdout}\nStderr: {stderr}")
                                        raise Exception(f"Discord bot terminated unexpectedly after {(i+1)*check_interval}s")
                                    
                                    # Log startup progress
                                    logger.info(f"Discord bot startup check {i+1}/{checks} passed")
                                
                                logger.info("Discord bot process verified and running stably")
                                break
                                
                            except Exception as e:
                                retry_count += 1
                                logger.warning(f"Discord bot start attempt {retry_count} failed: {str(e)}")
                                
                                if discord_process:
                                    try:
                                        discord_process.terminate()
                                        discord_process.wait(timeout=5)
                                    except:
                                        try:
                                            discord_process.kill()
                                        except:
                                            pass
                                
                                if retry_count >= max_retries:
                                    raise Exception(f"Failed to start Discord bot after {max_retries} attempts")
                                
                                # Exponential backoff with logging
                                backoff = 2 * retry_count
                                logger.info(f"Waiting {backoff}s before retry {retry_count + 1}")
                                time.sleep(backoff)
                        
                        # Start Telegram bot with similar monitoring
                        logger.info("Starting Telegram bot...")
                        telegram_process = subprocess.Popen(
                            ['python', 'telegram_bot.py'],
                            stdout=subprocess.PIPE,
                            stderr=subprocess.PIPE,
                            universal_newlines=True
                        )
                        
                        time.sleep(2)
                        if telegram_process.poll() is None:
                            logger.info("Telegram bot process started successfully")
                        else:
                            stdout, stderr = telegram_process.communicate()
                            logger.error(f"Telegram bot failed to start! Stdout: {stdout}, Stderr: {stderr}")
                            raise Exception("Telegram bot failed to start properly")
                            
                    except Exception as e:
                        logger.error(f"Failed to start bot processes: {str(e)}")
                        raise
                    
                    # Step 5: Stop the server with enhanced logging
                    logger.info("Initiating server shutdown sequence...")
                    socketio.stop()
                    
                    # Step 6: Exit process to trigger workflow restart
                    logger.info("Triggering restart sequence...")
                    os._exit(0)
                except Exception as e:
                    logger.error(f"Critical error during final restart sequence: {str(e)}")
                    raise
                
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
    """Handle client connection with enhanced error handling and state tracking."""
    try:
        client_info = {
            'sid': request.sid,
            'ip': request.remote_addr,
            'timestamp': datetime.now().isoformat(),
            'user_agent': request.headers.get('User-Agent', 'Unknown')
        }
        logger.info(f"Client connected: {client_info}")
        
        # Send connection acknowledgment
        socketio.emit('connection_status', {
            'status': 'connected',
            'sid': request.sid,
            'timestamp': datetime.now().isoformat()
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
        socketio.emit('connection_status', {
            'status': 'error',
            'message': 'Connection error occurred',
            'timestamp': datetime.now().isoformat()
        }, room=request.sid)

@socketio.on('disconnect')
def handle_disconnect():
    logger.info(f"Client disconnected: {request.sid}")

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