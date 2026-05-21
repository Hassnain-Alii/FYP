"""
Flask Application Factory and Initialization
This module is the entry point for the 'app' package. It implements the 
Application Factory pattern to initialize Flask extensions, load configuration,
and register blueprints.
"""

import os
from pathlib import Path
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from dotenv import load_dotenv
from werkzeug.middleware.proxy_fix import ProxyFix

# Find the project root directory (one level up from this file)
project_root = Path(__file__).parent.parent
env_path = project_root / '.env'

# Load environment variables from .env if it exists
if env_path.exists():
    load_dotenv(dotenv_path=env_path)

# Global Extension Instances
# These are initialized without an app context initially
db = SQLAlchemy()
login_manager = LoginManager()


def create_app():
    """
    Construct and configure the Flask application instance.
    
    This function:
    1. Initializes the Flask app.
    2. Loads configuration from environment variables.
    3. Configures extensions (DB, Auth).
    4. Registers API and View blueprints.
    5. Syncs the database schema.

    Returns:
        Flask: The fully configured application object.
    """
    app = Flask(__name__)
    
    # Handle proxy headers (like ngrok's X-Forwarded-Proto)
    # x_proto=1 tells ProxyFix to trust one proxy for the scheme
    app.wsgi_app = ProxyFix(app.wsgi_app, x_proto=1, x_host=1)
    
    # --- Core Flask Configuration ---
    app.config['SECRET_KEY'] = os.getenv('FLASK_SECRET_KEY', 'dev-secret-key-change-in-production')
    app.config['PREFERRED_URL_SCHEME'] = 'https'
    
    # Vercel's filesystem is read-only except for /tmp.
    if os.environ.get('VERCEL') == '1':
        db_path = 'sqlite:////tmp/chat_agent.db'
    else:
        db_path = 'sqlite:///chat_agent.db'
        
    app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URL', db_path)
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    
    # --- Session & Security Configuration ---
    from datetime import timedelta
    app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(hours=2)
    app.config['SESSION_COOKIE_SECURE'] = True
    app.config['SESSION_COOKIE_HTTPONLY'] = True
    app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'
    
    # --- AI Service Configuration ---
    # These settings control which LLM provider and model are used.
    app.config['AI_API_ENDPOINT'] = os.getenv('AI_API_ENDPOINT', 'https://api.cerebras.ai/v1/chat/completions')
    app.config['AI_API_KEY'] = os.getenv('AI_API_KEY', '')
    app.config['AI_MODEL_NAME'] = os.getenv('AI_MODEL_NAME', 'gpt-oss-120b')
    
    # --- Business Logic Settings ---
    app.config['FREE_TIER_LIMIT'] = int(os.getenv('FREE_TIER_LIMIT', 100))
    
    # --- External Auth (Google OAuth) Configuration ---
    app.config['GOOGLE_CLIENT_ID'] = os.getenv('GOOGLE_CLIENT_ID', '')
    app.config['GOOGLE_CLIENT_SECRET'] = os.getenv('GOOGLE_CLIENT_SECRET', '')

    # --- WhatsApp Configuration ---
    app.config['WHATSAPP_VERIFY_TOKEN'] = os.getenv('WHATSAPP_VERIFY_TOKEN', '')
    
    # Development Helper: Allow OAuth over non-HTTPS connections
    # WARNING: Disable this in production environments!
    os.environ['OAUTHLIB_INSECURE_TRANSPORT'] = '1'
    
    # --- Extension Initialization ---
    db.init_app(app)
    login_manager.init_app(app)
    
    # Flask-Login User Session Management
    login_manager.login_view = 'auth.login'
    login_manager.login_message = 'Please sign in to access this page.'
    
    # --- Blueprint Registration ---
    # Blueprints partition the application into logical components
    from app.routes.auth import auth_bp, init_google_oauth
    from app.routes.chat import chat_bp
    from app.routes.integrations import integrations_bp
    from app.routes.whatsapp_webhook import webhook_bp
    
    # Setup OAuth provider client
    init_google_oauth(app)
    
    app.register_blueprint(auth_bp)        # Handles Sign-in/Sign-out
    app.register_blueprint(chat_bp)        # Handles Chat UI and AI API
    app.register_blueprint(integrations_bp) # Handles Third-party Settings
    app.register_blueprint(webhook_bp)      # Handles WhatsApp Webhook
    
    # --- Database Schema Setup ---.
    # Ensure tables exist before the first request. 
    # In a production app, use Migrations (e.g., Flask-Migrate).
    with app.app_context():
        from app import models
        db.create_all()
    
    # --- Auth: User Loader ---
    from app.models import User
    
    @login_manager.user_loader
    def load_user(user_id):
        """Callback to reload a user object from the session ID."""
        return User.query.get(int(user_id))
    
    return app
