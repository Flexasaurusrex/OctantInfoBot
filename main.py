import os
import logging
import psutil
import signal
import sys
import traceback
import time
from datetime import datetime, timezone
from app import socketio, app
from flask import request #Added import
from flask_socketio import emit #Added import

# Enhanced logging for Railway with structured logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('railway.log')
    ]
)
logger = logging.getLogger(__name__)

def log_system_metrics():
    """Log system metrics for Railway's monitoring"""
    metrics = {
        'memory_percent': psutil.Process().memory_percent(),
        'cpu_percent': psutil.cpu_percent(),
        'disk_usage': psutil.disk_usage('/').percent,
        'open_files': len(psutil.Process().open_files()),
        'connections': len(psutil.Process().connections())
    }
    
    logger.info(f"""
━━━━━━ System Metrics ━━━━━━
Memory Usage: {metrics['memory_percent']:.1f}%
CPU Usage: {metrics['cpu_percent']:.1f}%
Disk Usage: {metrics['disk_usage']:.1f}%
Open Files: {metrics['open_files']}
Active Connections: {metrics['connections']}
━━━━━━━━━━━━━━━━━━━━━━━━""")
    return metrics

if __name__ == "__main__":
    retry_count = 0
    max_retries = 5
    retry_delay = 5  # seconds
    
    while retry_count < max_retries:
        try:
            # Enhanced environment validation with detailed feedback
            required_vars = {
                'TOGETHER_API_KEY': 'Required for chat functionality',
                'DISCORD_BOT_TOKEN': 'Required for Discord bot integration',
                'TELEGRAM_BOT_TOKEN': 'Required for Telegram bot integration'
            }
            
            # Check and log environment variables status
            logger.info("━━━━━━ Environment Check ━━━━━━")
            missing_vars = []
            
            for var, description in required_vars.items():
                value = os.getenv(var)
                if not value:
                    missing_vars.append(var)
                    logger.error(f"✗ {var}: MISSING - {description}")
                else:
                    logger.info(f"✓ {var}: SET")
            
            if missing_vars:
                error_msg = f"""
━━━━━━ Environment Error ━━━━━━
Missing required variables:
{chr(10).join(f'• {var}: {required_vars[var]}' for var in missing_vars)}
Please set these variables in your Railway project settings.
━━━━━━━━━━━━━━━━━━━━━━━━"""
                logger.error(error_msg)
                raise ValueError(error_msg)
            
            port = int(os.getenv('PORT', 5000))
            env = os.getenv('RAILWAY_ENVIRONMENT', 'development')
            debug = env != 'production'
            
            # Check system resources
            memory_usage = psutil.Process().memory_percent()
            cpu_usage = psutil.cpu_percent()
            
            if memory_usage > 90 or cpu_usage > 90:
                logger.warning(f"""
━━━━━━ Resource Warning ━━━━━━
Memory: {memory_usage:.1f}%
CPU: {cpu_usage:.1f}%
━━━━━━━━━━━━━━━━━━━━━━━━""")
            
            # Configure process monitoring
            def handle_sigterm(signum, frame):
                logger.info("Received SIGTERM signal, initiating graceful shutdown")
                try:
                    socketio.stop()
                except Exception as e:
                    logger.error(f"Error during shutdown: {e}")
                finally:
                    sys.exit(0)
            
            signal.signal(signal.SIGTERM, handle_sigterm)
            
            # Enhanced startup logging
            logger.info(f"""
━━━━━━ Railway Startup ━━━━━━
Environment: {env}
Port: {port}
Debug: {debug}
Memory: {memory_usage:.1f}%
CPU: {cpu_usage:.1f}%
Python: {sys.version.split()[0]}
Time: {datetime.now(timezone.utc).isoformat()}
Retry: {retry_count + 1}/{max_retries}
━━━━━━━━━━━━━━━━━━━━━━━━""")
            
            # Initialize socket.io with Railway-optimized settings
            from chat_handler import ChatHandler
            chat_handler = ChatHandler()
            
            @socketio.on('connect')
            def handle_connect():
                logger.info(f"Client connected: {request.sid}")
                emit('bot_status', {'status': 'connected'}, room=request.sid)
                return True

            @socketio.on('disconnect')
            def handle_disconnect():
                logger.info(f"Client disconnected: {request.sid}")

            @socketio.on('send_message')
            def handle_message(data):
                try:
                    if not isinstance(data, dict) or 'message' not in data:
                        logger.error("Invalid message format received")
                        raise ValueError("Invalid message format")
                    
                    message = data['message']
                    logger.info(f"Message received from {request.sid}: {message}")
                    
                    # Initialize chat handler if not exists
                    if not hasattr(handle_message, 'chat_handler'):
                        from chat_handler import ChatHandler
                        handle_message.chat_handler = ChatHandler()
                    
                    # Get response from chat handler
                    response = handle_message.chat_handler.handle_socket_message(request.sid, message)
                    logger.info(f"Generated response: {response}")
                    
                    if response:
                        # Emit response back to client
                        emit('receive_message', {
                            'message': response,
                            'is_bot': True
                        }, room=request.sid)
                        logger.info(f"Response emitted to {request.sid}")
                    else:
                        logger.error("No response generated from chat handler")
                        raise ValueError("No response generated")
                        
                except Exception as e:
                    error_msg = str(e)
                    logger.error(f"Error handling message: {error_msg}")
                    logger.error(traceback.format_exc())
                    emit('receive_message', {
                        'message': 'I apologize, but I encountered an error. Please try again.',
                        'is_bot': True
                    }, room=request.sid)

            socketio.init_app(
                app,
                cors_allowed_origins="*",
                ping_timeout=60,
                ping_interval=25,
                async_mode='eventlet',
                logger=True,
                engineio_logger=True
            )
            
            # Start server with enhanced error handling
            socketio.run(
                app,
                host="0.0.0.0",
                port=port,
                debug=debug,
                use_reloader=False,  # Disable reloader for Railway
                log_output=True,
                allow_unsafe_werkzeug=True  # Required for Railway deployment
            )
            
            # If we get here, startup was successful
            break
            
        except Exception as e:
            retry_count += 1
            logger.error(f"""
━━━━━━ Startup Error ━━━━━━
Type: {type(e).__name__}
Error: {str(e)}
Traceback: {traceback.format_exc()}
Memory: {psutil.Process().memory_info().rss / 1024 / 1024:.1f}MB
CPU: {psutil.cpu_percent()}%
Time: {datetime.now(timezone.utc).isoformat()}
Retry: {retry_count}/{max_retries}
━━━━━━━━━━━━━━━━━━━━━━━━""")
            
            if retry_count < max_retries:
                logger.info(f"Waiting {retry_delay} seconds before retry {retry_count + 1}...")
                time.sleep(retry_delay)
                retry_delay *= 2  # Exponential backoff
            else:
                logger.critical("Max retries reached, exiting...")
                sys.exit(1)  # Exit with error for Railway to detect