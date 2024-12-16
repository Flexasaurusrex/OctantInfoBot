
import os
import logging
import psutil
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
    # Enhanced Railway environment detection and configuration
    is_railway = os.getenv('RAILWAY_ENVIRONMENT') is not None
    port = int(os.getenv('PORT', 5000))
    env = os.getenv('RAILWAY_ENVIRONMENT', 'development')
    debug = env != 'production'
    version = os.getenv('RAILWAY_GIT_COMMIT_SHA', 'local')[:7]
    
    # Log startup configuration with enhanced metrics
    metrics = log_system_metrics()
    logger.info(f"""
━━━━━━ Railway Deployment Info ━━━━━━
Environment: {env}
Port: {port}
Debug Mode: {debug}
Version: {version}
Start Time: {datetime.now(timezone.utc).isoformat()}
Memory Usage: {metrics['memory_percent']:.1f}%
CPU Usage: {metrics['cpu_percent']:.1f}%
━━━━━━━━━━━━━━━━━━━━━━━━""")
    
    # Railway-optimized startup configuration
    try:
        socketio.run(
            app,
            host="0.0.0.0",
            port=port,
            debug=debug,
            use_reloader=False,  # Railway handles reloading
            log_output=True,
            allow_unsafe_werkzeug=True  # Required for Railway deployment
        )
    except Exception as e:
        logger.error(f"""
━━━━━━ Startup Error ━━━━━━
Error Type: {type(e).__name__}
Error Message: {str(e)}
Version: {version}
Time: {datetime.now(timezone.utc).isoformat()}
━━━━━━━━━━━━━━━━━━━━━━━━""")
        raise
