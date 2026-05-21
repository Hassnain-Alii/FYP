"""
Database Models Module
This module defines the SQLAlchemy ORM models for the application,
including User profiles, Chat Messages, External Integrations, and Conversation History.
"""

from datetime import datetime, date
from flask_login import UserMixin
from flask import current_app
from app import db
import json
import base64
import hashlib
from cryptography.fernet import Fernet


class User(UserMixin, db.Model):
    """
    User model representing a registered individual.
    
    Includes authentication details (Google OAuth), profile information,
    and message usage tracking for free-tier enforcement.
    """
    __tablename__ = 'users'
    
    # Primary identifier and authentication
    id = db.Column(db.Integer, primary_key=True)
    google_id = db.Column(db.String(100), unique=True, nullable=False) # Unique ID from Google OAuth
    email = db.Column(db.String(120), unique=True, nullable=False)
    name = db.Column(db.String(100), nullable=False)
    picture = db.Column(db.String(500), nullable=True) # Profile picture URL
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Usage tracking fields for daily limits
    daily_message_count = db.Column(db.Integer, default=0) # Tracks messages sent today
    last_message_date = db.Column(db.Date, nullable=True)  # Used to identify a 'new day' for resets
    
    # Relationships to other models (one-to-many)
    messages = db.relationship('Message', backref='user', lazy='dynamic')
    integrations = db.relationship('Integration', backref='user', lazy='dynamic')
    conversations = db.relationship('ConversationHistory', backref='user', lazy='dynamic')
    
    def __repr__(self):
        return f'<User {self.email}>'
    
    def reset_daily_count_if_new_day(self):
        """
        Check if the current date is different from the last message date.
        If so, reset the daily message counter to zero.
        """
        today = date.today()
        if self.last_message_date != today:
            self.daily_message_count = 0
            self.last_message_date = today
            db.session.commit()
    
    def can_send_message(self, limit=100):
        """
        Determine if the user is within their allowed daily message quota.
        
        Args:
            limit (int): The maximum messages allowed per day (default: 100).
            
        Returns:
            bool: True if user can send a message, False otherwise.
        """
        self.reset_daily_count_if_new_day()
        return self.daily_message_count < limit
    
    def increment_message_count(self):
        """
        Atomically increment the user's daily message counter.
        Also resets the count if it's the start of a new day.
        """
        self.reset_daily_count_if_new_day()
        self.daily_message_count += 1
        db.session.commit()
    
    def get_remaining_messages(self, limit=100):
        """
        Calculate how many messages the user has left in their daily quota.
        
        Args:
            limit (int): The maximum quota.
            
        Returns:
            int: Remaining messages (minimum 0).
        """
        self.reset_daily_count_if_new_day()
        return max(0, limit - self.daily_message_count)


class Message(db.Model):
    """
    Message model for persistence of individual chat exchanges.
    
    Stores both the user's prompt and the AI's response for historical audit.
    """
    __tablename__ = 'messages'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    content = db.Column(db.Text, nullable=False)   # User's input
    response = db.Column(db.Text, nullable=False)  # AI's output
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    
    def __repr__(self):
        return f'<Message {self.id}>'
    
    def to_dict(self):
        """
        Serialize the message object to a dictionary for JSON API responses.
        
        Returns:
            dict: Serialized message data.
        """
        return {
            'id': self.id,
            'content': self.content,
            'response': self.response,
            'timestamp': self.timestamp.isoformat()
        }



def _get_fernet():
    """
    Generate a stable Fernet key derived from the Flask SECRET_KEY.
    """
    secret = current_app.config.get('SECRET_KEY', 'default_fallback_secret').encode()
    key = base64.urlsafe_b64encode(hashlib.sha256(secret).digest())
    return Fernet(key)


class Integration(db.Model):
    """
    Integration model (Multi-provider secure version)
    Supports WhatsApp, Shopify, WooCommerce, custom APIs
    """

    __tablename__ = 'integrations'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)

    # 🔥 NEW: provider-based system (instead of type)
    provider = db.Column(db.String(50), nullable=False)
    name = db.Column(db.String(100), nullable=True)  # user label
    phone_number_id = db.Column(db.String(100), nullable=True)

    # secure config storage
    config_json = db.Column(db.Text, nullable=False)

    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    __table_args__ = (
        db.UniqueConstraint('user_id', 'provider', name='unique_user_provider'),
    )

    def __repr__(self):
        return f'<Integration {self.provider} for User {self.user_id}>'

    # =========================
    # CONFIG HANDLING
    # =========================
    @property
    def config(self):
        if not self.config_json:
            return {}
        try:
            f = _get_fernet()
            decrypted = f.decrypt(self.config_json.encode()).decode()
            return json.loads(decrypted)
        except Exception:
            # Fallback for old unencrypted data
            try:
                return json.loads(self.config_json)
            except Exception:
                return {}

    @config.setter
    def config(self, value):
        f = _get_fernet()
        json_data = json.dumps(value)
        self.config_json = f.encrypt(json_data.encode()).decode()

    def to_dict(self):
        return {
            "id": self.id,
            "provider": self.provider,
            "name": self.name,
            "config": self.config,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat()
        }

class ConversationHistory(db.Model):
    """
    ConversationHistory model for session-based message persistence.
    
    Unlike the flat 'Message' table, this groups exchanges into logical sessions
    for better contextual retrieval in the chat interface.
    """
    __tablename__ = 'conversation_history'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    session_id = db.Column(db.String(100), nullable=False) # Frontend-generated session identifier
    title = db.Column(db.String(200), nullable=True)      # Custom chat name
    messages_json = db.Column(db.Text, nullable=False)     # Serialized list of {role, content}
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def __repr__(self):
        return f'<ConversationHistory {self.session_id}>'
    
    @property
    def messages(self):
        """
        Getter property for session messages.
        Returns a list of dictionaries.
        """
        return json.loads(self.messages_json) if self.messages_json else []
    
    @messages.setter
    def messages(self, value):
        """
        Setter property for session messages.
        Serializes the list of dictionaries back to JSON.
        """
        self.messages_json = json.dumps(value)
    
    def add_message(self, role, content):
        """
        Append a new message to the local session history and persist to DB.
        
        Args:
            role (str): 'user' or 'assistant'.
            content (str): The text message content.
        """
        msgs = self.messages
        msgs.append({'role': role, 'content': content})
        self.messages = msgs
        db.session.commit()
class WhatsAppConversation(db.Model):

    __tablename__ = 'whatsapp_conversations'

    id = db.Column(db.Integer, primary_key=True)

    phone_number = db.Column(db.String(30), unique=True, nullable=False)

    messages_json = db.Column(db.Text, nullable=False, default='[]')

    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    @property
    def messages(self):

        return json.loads(self.messages_json)

    @messages.setter
    def messages(self, value):

        self.messages_json = json.dumps(value)

    def add_message(self, role, content):

        msgs = self.messages
        msgs.append({
            "role": role,
            "content": content
        })

        self.messages = msgs