import os
import logging
import psutil
import signal
import sys
import traceback
from datetime import datetime, timezone
from app import socketio, app

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
    # Enhanced startup with proper error handling for Railway
    try:
        # Validate environment
        port = int(os.getenv('PORT', 5000))
        env = os.getenv('RAILWAY_ENVIRONMENT', 'development')
        
        # Check system resources
        memory_usage = psutil.Process().memory_percent()
        if memory_usage > 90:
            logger.warning(f"High memory usage detected: {memory_usage}%")
        
        # Configure process monitoring
        def handle_sigterm(signum, frame):
            logger.info("Received SIGTERM signal, initiating graceful shutdown")
            socketio.stop()
            sys.exit(0)
            
        signal.signal(signal.SIGTERM, handle_sigterm)
        
        # Start server with Railway-optimized settings
        logger.info(f"""
━━━━━━ Railway Startup ━━━━━━
Environment: {env}
Port: {port}
Memory: {memory_usage:.1f}%
CPU: {psutil.cpu_percent()}%
Python: {sys.version.split()[0]}
Time: {datetime.now(timezone.utc).isoformat()}
━━━━━━━━━━━━━━━━━━━━━━━━""")
        
        socketio.run(
            app,
            host="0.0.0.0",
            port=port,
            debug=env != 'production',
            use_reloader=False,
            log_output=True,
            allow_unsafe_werkzeug=True
        )
    except Exception as e:
        logger.error(f"""
━━━━━━ Fatal Error ━━━━━━
Type: {type(e).__name__}
Error: {str(e)}
Traceback: {traceback.format_exc()}
Memory: {psutil.Process().memory_info().rss / 1024 / 1024:.1f}MB
CPU: {psutil.cpu_percent()}%
Time: {datetime.now(timezone.utc).isoformat()}
━━━━━━━━━━━━━━━━━━━━━━━━""")
        sys.exit(1)  # Exit with error for Railway to detect