"""
Message Limiter Service
Handles free tier message limit enforcement
"""

from datetime import date
from app import db


class MessageLimiter:
    """Service for managing user message limits."""
    
    def __init__(self, daily_limit=100):
        self.daily_limit = daily_limit
    
    def check_limit(self, user):
        """
        Check if user has remaining messages for today.
        
        Args:
            user: User model instance
            
        Returns:
            dict with limit status information
        """
        # Reset count if it's a new day
        user.reset_daily_count_if_new_day()
        
        remaining = max(0, self.daily_limit - user.daily_message_count)
        can_send = remaining > 0
        
        return {
            'can_send': can_send,
            'daily_count': user.daily_message_count,
            'limit': self.daily_limit,
            'remaining': remaining,
            'percentage_used': (user.daily_message_count / self.daily_limit) * 100
        }
    
    def increment_count(self, user):
        """
        Increment user's daily message count.
        
        Args:
            user: User model instance
            
        Returns:
            Updated count
        """
        user.increment_message_count()
        return user.daily_message_count
    
    def reset_count(self, user):
        """
        Reset user's daily message count.
        
        Args:
            user: User model instance
        """
        user.daily_message_count = 0
        user.last_message_date = date.today()
        db.session.commit()
    
    def get_usage_stats(self, user):
        """
        Get detailed usage statistics for a user.
        
        Args:
            user: User model instance
            
        Returns:
            dict with usage statistics
        """
        user.reset_daily_count_if_new_day()
        
        remaining = max(0, self.daily_limit - user.daily_message_count)
        
        # Determine tier status
        if remaining == 0:
            tier_status = 'limit_reached'
            tier_message = 'You have reached your free tier limit for today.'
        elif remaining <= 10:
            tier_status = 'low'
            tier_message = f'Only {remaining} messages remaining today.'
        elif remaining <= 25:
            tier_status = 'medium'
            tier_message = f'{remaining} messages remaining today.'
        else:
            tier_status = 'good'
            tier_message = f'{remaining} messages remaining today.'
        
        return {
            'daily_count': user.daily_message_count,
            'limit': self.daily_limit,
            'remaining': remaining,
            'percentage_used': round((user.daily_message_count / self.daily_limit) * 100, 1),
            'tier_status': tier_status,
            'tier_message': tier_message,
            'is_premium': False,  # For future premium feature
            'premium_info': {
                'name': 'Premium Plan',
                'price': '$9.99/month',
                'features': [
                    'Unlimited messages',
                    'Priority support',
                    'Advanced integrations',
                    'Custom AI training'
                ]
            }
        }
