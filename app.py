import os
import logging
from flask import Flask, render_template, request, jsonify, session
from flask_cors import CORS
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from datetime import datetime
import uuid
import logging
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
CORS(app)

# Initialize rate limiter
limiter = Limiter(
    app=app,
    key_func=get_remote_address,
    default_limits=["200 per day", "50 per hour"],
    storage_uri="memory://"
)

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

@app.route('/chat', methods=['POST'])
@limiter.limit("30 per minute")
def chat():
    """Handle chat messages through HTTP."""
    try:
        # Basic validation
        if not request.is_json:
            logger.warning("Invalid request format - not JSON")
            return jsonify({"error": "Request must be JSON"}), 400
            
        data = request.get_json()
        if not data or 'message' not in data:
            logger.warning("Missing message in request data")
            return jsonify({"error": "Message is required"}), 400
            
        if not chat_handler:
            logger.error("Chat handler not initialized")
            return jsonify({"error": "Chat service unavailable"}), 503
        
        # Ensure session exists
        if 'session_id' not in session:
            session['session_id'] = str(uuid.uuid4())
            logger.info(f"Created new session: {session['session_id']}")
        
        message = data['message'].strip()
        client_id = session['session_id']
        
        # Get response from chat handler
        logger.info(f"Processing message from {client_id}: {message[:50]}...")
        try:
            response = chat_handler.get_response(client_id, message)
            if response:
                logger.info(f"Successfully generated response for {client_id}")
                return jsonify({
                    "response": response,
                    "timestamp": datetime.now().isoformat()
                })
            else:
                logger.warning(f"Empty response for message: {message[:50]}...")
                return jsonify({"error": "No response generated"}), 500
                
        except Exception as chat_error:
            logger.error(f"Chat handler error: {str(chat_error)}")
            return jsonify({"error": "Failed to generate response"}), 500
            
    except Exception as e:
        logger.error(f"Error processing chat message: {str(e)}", exc_info=True)
        return jsonify({"error": "Internal server error"}), 500

@app.route('/health')
def health_check():
    """Health check endpoint."""
    return jsonify({
        'status': 'healthy',
        'timestamp': datetime.now().isoformat(),
        'services': {
            'web': True,
            'chat_handler': chat_handler is not None
        }
    })

if __name__ == '__main__':
    try:
        port = int(os.environ.get('PORT', 5000))
        debug = os.environ.get('FLASK_ENV') != 'production'
        
        logger.info(f"""
━━━━━━ Server Starting ━━━━━━
Port: {port}
Debug: {debug}
Environment: {os.environ.get('FLASK_ENV', 'development')}
━━━━━━━━━━━━━━━━━━━━━━━━""")
        
        app.run(
            host='0.0.0.0',
            port=port,
            debug=debug
        )
        
    except Exception as e:
        logger.error(f"Failed to start server: {e}")
        raise
