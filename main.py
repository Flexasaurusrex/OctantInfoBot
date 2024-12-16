
import os
import logging
import psutil
from datetime import datetime
from app import socketio, app

# Enhanced logging for Railway with structured logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
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
    # Enhanced Railway environment detection
    is_railway = os.getenv('RAILWAY_ENVIRONMENT') is not None
    port = int(os.getenv('PORT', 5000))
    env = os.getenv('RAILWAY_ENVIRONMENT', 'development')
    debug = env != 'production'
    
    # Log startup configuration with enhanced metrics
    metrics = log_system_metrics()
    logger.info(f"""
━━━━━━ Server Configuration ━━━━━━
Environment: {env}
Port: {port}
Debug Mode: {debug}
Platform: Railway
Start Time: {datetime.now().isoformat()}
━━━━━━━━━━━━━━━━━━━━━━━━""")
    
    # Railway-optimized startup configuration
    socketio.run(
        app,
        host="0.0.0.0",
        port=port,
        debug=debug,
        use_reloader=False,  # Railway handles reloading
        log_output=True,
        allow_unsafe_werkzeug=True  # Required for Railway deployment
    )
