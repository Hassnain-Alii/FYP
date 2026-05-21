"""
Google OAuth Authentication Routes
"""

from flask import Blueprint, redirect, url_for, flash, render_template, jsonify, current_app, session
from flask_login import login_user, logout_user, login_required, current_user
from flask_dance.contrib.google import make_google_blueprint, google
from flask_dance.consumer import oauth_authorized
from app import db
from app.models import User

auth_bp = Blueprint('auth', __name__)

# Google OAuth blueprint (will be configured in init_google_oauth)
google_bp = None


def init_google_oauth(app):
    """Initialize Google OAuth with the Flask app."""
    global google_bp
    
    google_bp = make_google_blueprint(
        client_id=app.config['GOOGLE_CLIENT_ID'],
        client_secret=app.config['GOOGLE_CLIENT_SECRET'],
        scope=[
            'openid',
            'https://www.googleapis.com/auth/userinfo.email',
            'https://www.googleapis.com/auth/userinfo.profile'
        ],
        redirect_to='auth.oauth_callback'  # Redirect to our handler after OAuth
    )
    
    app.register_blueprint(google_bp, url_prefix='/login')
    
    # Signal handler for successful OAuth - this logs in the user
    @oauth_authorized.connect_via(google_bp)
    def google_logged_in(blueprint, token):
        """Handle successful Google OAuth login."""
        if not token:
            flash('Failed to log in with Google.', 'error')
            return False
        
        try:
            # Get user info from Google
            resp = google.get('/oauth2/v2/userinfo')
            if not resp.ok:
                flash('Failed to get user info from Google.', 'error')
                return False
            
            user_info = resp.json()
            google_id = user_info.get('id')
            email = user_info.get('email')
            name = user_info.get('name', email.split('@')[0] if email else 'User')
            picture = user_info.get('picture', '')
            
            # Find or create user
            user = User.query.filter_by(google_id=google_id).first()
            
            if user is None:
                # Create new user
                user = User(
                    google_id=google_id,
                    email=email,
                    name=name,
                    picture=picture
                )
                db.session.add(user)
                db.session.commit()
                current_app.logger.info(f'Created new user: {email}')
            else:
                # Update existing user info
                user.name = name
                user.picture = picture
                db.session.commit()
                current_app.logger.info(f'Updated user: {email}')
            
            # Log in the user with Flask-Login
            session.permanent = True
            login_user(user)
            flash(f'Welcome, {user.name}!', 'success')
            
            # Return False to prevent Flask-Dance from saving token to session
            # This also prevents Flask-Dance's default redirect behavior
            return False
            
        except Exception as e:
            current_app.logger.error(f'OAuth error: {str(e)}')
            flash('An error occurred during authentication.', 'error')
            return False


@auth_bp.route('/')
def index():
    """Home page - redirect to chat if logged in, else to login."""
    if current_user.is_authenticated:
        return redirect(url_for('chat.chat_page'))
    return redirect(url_for('auth.login'))


@auth_bp.route('/login')
def login():
    """Login page."""
    if current_user.is_authenticated:
        return redirect(url_for('chat.chat_page'))
    return render_template('login.html')


@auth_bp.route('/oauth/callback')
def oauth_callback():
    """Handle redirect after OAuth completes."""
    # If user is logged in, go to chat
    if current_user.is_authenticated:
        return redirect(url_for('chat.chat_page'))
    # Otherwise go back to login
    flash('Authentication failed. Please try again.', 'error')
    return redirect(url_for('auth.login'))


@auth_bp.route('/logout')
@login_required
def logout():
    """Log out the current user."""
    # Clear the OAuth token from session
    token_key = 'google_oauth_token'
    if token_key in session:
        del session[token_key]
    logout_user()
    flash('You have been logged out.', 'info')
    return redirect(url_for('auth.login'))


@auth_bp.route('/api/user')
@login_required
def get_current_user():
    """Get current user information."""
    limit = current_app.config['FREE_TIER_LIMIT']
    return jsonify({
        'id': current_user.id,
        'name': current_user.name,
        'email': current_user.email,
        'picture': current_user.picture,
        'daily_message_count': current_user.daily_message_count,
        'remaining_messages': current_user.get_remaining_messages(limit),
        'free_tier_limit': limit
    })
