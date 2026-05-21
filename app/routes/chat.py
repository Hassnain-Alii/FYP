"""
Chat Controller Module
This module defines the Flask routes for the chat interface and the 
backend API endpoints for message processing, history retrieval, and usage tracking.
"""

from flask import Blueprint, request, jsonify, render_template, current_app
from flask_login import login_required, current_user
from app import db
from app.models import Message, ConversationHistory
from app.services.ai_service import generate_ai_response
import uuid

# Define the chat blueprint
chat_bp = Blueprint('chat', __name__)


@chat_bp.route('/chat')
@login_required
def chat_page():
    """
    Render the main chat interface.
    
    Returns:
        The rendered 'chat.html' template.
    """
    return render_template('chat.html')


@chat_bp.route('/api/conversations/<int:conv_id>/rename', methods=['POST'])
@login_required
def rename_conversation(conv_id):
    """Rename a conversation title."""
    data = request.get_json()
    new_title = data.get('title')
    
    if not new_title:
        return jsonify({'error': 'Title is required'}), 400
        
    conversation = ConversationHistory.query.filter_by(
        id=conv_id, 
        user_id=current_user.id
    ).first()
    
    if not conversation:
        return jsonify({'error': 'Conversation not found'}), 404
        
    conversation.title = new_title
    db.session.commit()
    
    return jsonify({'message': 'Conversation renamed', 'title': new_title})


@chat_bp.route('/api/chat', methods=['POST'])
@login_required
def send_message():
    """
    Process a user message and return an AI-generated response.
    
    This endpoint:
    1. Validates the user's daily message limit.
    2. Retrieves or creates a conversation session.
    3. Calls the AI service with conversation context.
    4. Persists the exchange to the database and session history.
    5. Returns the AI response and updated usage stats.

    JSON Request Body:
        message (str): The user's input text.
        session_id (str, optional): The ID of the current chat session.

    Returns:
        JSON response with 'response', 'message_id', and usage statistics.
    """
    try:
        limit = current_app.config['FREE_TIER_LIMIT']
        
        # 1. Enforcement: Check if user has exceeded their daily free-tier limit
        if not current_user.can_send_message(limit):
            return jsonify({
                'error': 'limit_exceeded',
                'message': 'You have reached your daily message limit.',
                'daily_count': current_user.daily_message_count,
                'limit': limit,
                'remaining': 0
            }), 429
        # 2. Input Validation
        data = request.get_json()
        if not data or not data.get('message'):
            return jsonify({'error': 'No message provided'}), 400
        
        user_message = data.get('message', '').strip()
        if not user_message:
            return jsonify({'error': 'Empty message'}), 400
        
        # 3. Session Management: Retrieve conversation history by session ID
        session_id = data.get('session_id', str(uuid.uuid4()))
        conversation = ConversationHistory.query.filter_by(
            user_id=current_user.id,
            session_id=session_id
        ).first()
        
        if not conversation:
            # Create a new conversation record if it doesn't exist
            conversation = ConversationHistory(
                user_id=current_user.id,
                session_id=session_id,
                messages_json='[]'
            )
            db.session.add(conversation)
            db.session.commit()
        
        # 4. Context Retrieval: Get the last 10 messages for short-term memory
        history = conversation.messages[-10:] if conversation.messages else []
        
        # 5. AI Generation: Delegate to the ai_service layer
        ai_response = generate_ai_response(
            user_message,
            history,
            current_app.config['AI_API_ENDPOINT'],
            current_app.config['AI_API_KEY'],
            current_app.config['AI_MODEL_NAME'],
            current_user.id
        )

        # 6. Persistence: Record the actual message and AI response
        message = Message(
            user_id=current_user.id,
            content=user_message,
            response=ai_response
        )
        db.session.add(message)
        
        # 7. History Update: Append to the session's message list
        conversation.add_message('user', user_message)
        conversation.add_message('assistant', ai_response)
        
        # 8. Usage Tracking: Increment the user's daily counter
        current_user.increment_message_count()
        
        # Set conversation title to first 40 chars of user message if not set
        if not conversation.title:
            conversation.title = user_message[:40]
        
        # Commit all changes to the database
        db.session.commit()
        
    except Exception as e:
        import traceback
        return jsonify({'error': 'Internal Server Error', 'details': str(e), 'trace': traceback.format_exc()}), 500
    
    return jsonify({
        'response': ai_response,
        'message_id': message.id,
        'session_id': session_id,
        'daily_count': current_user.daily_message_count,
        'remaining': current_user.get_remaining_messages(limit),
        'limit': limit
    })


@chat_bp.route('/api/messages')
@login_required
def get_messages():
    """
    Retrieve a paginated list of all messages for the current user.
    
    Query Parameters:
        page (int): The page number (default: 1).
        per_page (int): Messages per page (default: 50).

    Returns:
        JSON object containing the list of messages and pagination metadata.
    """
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 50, type=int)
    
    messages = Message.query.filter_by(user_id=current_user.id)\
        .order_by(Message.timestamp.desc())\
        .paginate(page=page, per_page=per_page, error_out=False)
    
    return jsonify({
        'messages': [msg.to_dict() for msg in messages.items],
        'total': messages.total,
        'pages': messages.pages,
        'current_page': page
    })


@chat_bp.route('/api/usage')
@login_required
def get_usage():
    """
    Retrieve current message usage statistics for the user.

    Returns:
        JSON object with daily count, limit, and availability status.
    """
    limit = current_app.config['FREE_TIER_LIMIT']
    
    return jsonify({
        'daily_count': current_user.daily_message_count,
        'limit': limit,
        'remaining': current_user.get_remaining_messages(limit),
        'can_send': current_user.can_send_message(limit)
    })


@chat_bp.route('/api/conversations')
@login_required
def get_conversations():
    """
    Retrieve the most recent conversation sessions for the sidebar list.

    Returns:
        JSON array of conversation summary objects.
    """
    conversations = ConversationHistory.query.filter_by(user_id=current_user.id)\
        .order_by(ConversationHistory.created_at.desc())\
        .limit(20).all()
    
    return jsonify({
        'conversations': [
            {
                'id': conv.id,
                'session_id': conv.session_id,
                'title': conv.title,
                'created_at': conv.created_at.isoformat(),
                'message_count': len(conv.messages)
            }
            for conv in conversations
        ]
    })


@chat_bp.route('/api/conversations/<session_id>')
@login_required
def get_conversation(session_id):
    """
    Retrieve all messages within a specific conversation session.

    Args:
        session_id (str): The unique ID of the session to fetch.

    Returns:
        JSON object containing session messages or an error if not found.
    """
    conversation = ConversationHistory.query.filter_by(
        user_id=current_user.id,
        session_id=session_id
    ).first()
    
    if not conversation:
        return jsonify({'error': 'Conversation not found'}), 404
    
    return jsonify({
        'id': conversation.id,
        'session_id': conversation.session_id,
        'title': conversation.title,
        'messages': conversation.messages,
        'created_at': conversation.created_at.isoformat()
    })
