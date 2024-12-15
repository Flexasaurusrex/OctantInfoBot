import os
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

if __name__ == "__main__":
    try:
        # Import app after logging configuration
        from app import socketio, app
        
        port = int(os.environ.get('PORT', 5000))
        logger.info(f"Starting server on port {port}")
        
        with app.app_context():
            # Enhanced WebSocket configuration
            socketio.run(
                app,
                host='0.0.0.0',
                port=port,
                debug=False,
                use_reloader=False,
                log_output=True
            )
    except Exception as e:
        logger.error(f"Error starting server: {e}")
        raise
