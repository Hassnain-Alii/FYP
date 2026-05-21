"""
AI Service - LLM API Integration Layer
This module handles communication with external AI providers (Cerebras, GroqCloud)
using the OpenAI-compatible chat completions interface.
"""

import requests
import logging
from app.services.ecommerce_service import get_products

# Configure logger for this module
logger = logging.getLogger(__name__)


def generate_ai_response(user_message, conversation_history, api_endpoint, api_key, model_name, user_id=None):
    """
    Generate an AI response using the specified LLM model.
    
    This function constructs the necessary message payload (including system prompt
    and conversation history), sends a request to the configured API endpoint,
    and returns the extracted AI reply.

    Args:
        user_message (str): The latest message from the user.
        conversation_history (list): A list of dictionaries representing previous messages.
            Each dictionary should have 'role' (user/assistant) and 'content' keys.
        api_endpoint (str): The full URL of the chat completions API.
        api_key (str): The authentication bearer token for the API.
        model_name (str): The specific model identifier (e.g., 'gpt-oss-120b').
    
    Returns:
        str: The AI-generated response text or a user-friendly error message.
    """
    
    # API key validation - required for non-mocked responses
    if not api_key:
        logger.warning("AI_API_KEY is not configured. Returning demo mode message.")
        return ("I'm currently running in demo mode. To get AI responses, "
                "please configure your API key in the .env file. "
                "You can get an API key from Cerebras or GroqCloud.")
    
    try:
        # ============================================
        # E-COMMERCE PRODUCT FETCHING
        # ============================================

        ecommerce_keywords = [
            "product",
            "products",
            "store",
            "shop",
            "price",
            "item",
            "buy",
            "purchase",
            "available",
            "catalog"
        ]

        if any(keyword in user_message.lower() for keyword in ecommerce_keywords):

            products = get_products(user_id)

            if products:

                response_text = "Here are some available products:\n\n"

                for product in products[:3]:

                    response_text += (
                        f"Product: {product['title']}\n"
                        f"Price: ${product['price']}\n"
                        f"Category: {product['category']}\n\n"
                    )

                return response_text

        
        # 1. Initialize message list with the System Prompt
        # This defines the AI's persona and behavior constraints.
        messages = [
            {
                "role": "system",
                "content": (
                    "You are a helpful AI assistant for a customer support chat application. "
                    "Be friendly, concise, and helpful. If asked about WhatsApp or e-commerce "
                    "integration, explain that the user can configure these in the Settings page."
                )
            }
        ]
        
        # 2. Append conversation history for contextual awareness
        for msg in conversation_history:
            messages.append({
                "role": msg.get("role", "user"),
                "content": msg.get("content", "")
            })
        
        # 3. Add the current user query
        messages.append({
            "role": "user",
            "content": user_message
        })
        
        # 4. Prepare HTTP request headers and body
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }
        
        payload = {
    
            "model": model_name,
            "messages": messages,
            "max_tokens": 1024, # Limit response length to manage costs/performance
            "temperature": 0.7  # Balance between creativity and focus
        }
        
        # 5. Execute synchronous POST request to the API
        logger.info(f"Sending request to AI provider: {model_name}")
        response = requests.post(
            api_endpoint,
            headers=headers,
            json=payload,
            timeout=30 # Prevent hanging if the service is slow
        )
        
        # 6. Handle HTTP status codes
        if response.status_code != 200:
            logger.error(f"API provider error: {response.status_code} - {response.text}")
            return get_fallback_response(response.status_code)
        
        # 7. Parse JSON response and extract content
        result = response.json()
        
        # Standard OpenAI-compatible response traversal
        if "choices" in result and len(result["choices"]) > 0:
            ai_reply = result["choices"][0]["message"]["content"]
            logger.info("Successfully received AI response.")
            return ai_reply
        else:
            logger.error(f"Invalid API response structure: {result}")
            return "I received an unexpected response format. Please try again."
            
    except requests.exceptions.Timeout:
        logger.error("The AI service took too long to respond (timeout).")
        return "I'm taking too long to respond. Please try again in a moment."
    
    except requests.exceptions.ConnectionError:
        logger.error("Failed to establish a connection with the AI API.")
        return "I'm having trouble connecting to the AI service. Please check your internet connection."
    
    except Exception as e:
        logger.critical(f"Uncaught exception in AI Service: {str(e)}")
        return f"I'm having a little trouble thinking straight right now. Could you try asking me again in a moment? <br> error: {str(e)}"


def get_fallback_response(status_code):
    """
    Map HTTP status codes to user-friendly error messages.

    Args:
        status_code (int): The HTTP status code returned by the API.

    Returns:
        str: A helpful message explaining the issue to the user.
    """
    if status_code == 401:
        return "I'm having a little trouble verifying my credentials. Please check the system settings. <br> error (Status: 401) Authentication failure."
    elif status_code == 404:
        return "I couldn't find the specific AI model requested. I'm looking for a solution, please try again in a moment! <br> error (Status: 404) Not found."
    elif status_code == 429:
        return "I'm having a little trouble keeping up with your requests. Please slow down a bit. <br> error (Status: 429) Rate limit exceeded."
    elif status_code == 500:
        return "I'm having a little trouble thinking straight right now. Could you try asking me again in a moment? <br> error (Status: 500) Internal server error."
    elif status_code == 503:
        return "I'm currently undergoing some quick maintenance to get even better. I'll be back online very soon! <br> error (Status: 503) Service unavailable."
    else:
        return f"I'm having a brief connection issue. Could you try sending that message one more time? <br> error (Status: {status_code}). Please try again."


def test_api_connection(api_endpoint, api_key, model_name):
    """
    Perform a health check on the API connection.
    
    Sends a minimal 'Hello' request to verify authentication and endpoint availability.

    Args:
        api_endpoint (str): The API URL.
        api_key (str): The API bearer token.
        model_name (str): The model identifier.

    Returns:
        dict: { 'success': bool, 'message': str }
    """
    if not api_key:
        return {"success": False, "message": "API Key is missing from configuration."}
    
    try:
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "model": model_name,
            "messages": [{"role": "user", "content": "Hello"}],
            "max_tokens": 5 # Minimal tokens for verification
        }
        
        response = requests.post(
            api_endpoint,
            headers=headers,
            json=payload,
            timeout=10
        )
        
        if response.status_code == 200:
        # Test e-commerce API also
            try:
                products = get_products(1)

                if products:
                    ecommerce_status = "E-commerce API working."
                else:
                    ecommerce_status = "E-commerce API returned no products."

            except Exception:
                ecommerce_status = "E-commerce API failed."

            return {
                "success": True,
                "message": f"API connection established successfully. {ecommerce_status}"
            }
        else:
            return {
                "success": False,
                "message": f"API returned error {response.status_code}: {response.text[:100]}..."
            }
            
    except Exception as e:
        return {"success": False, "message": f"Connection attempt failed: {str(e)}"}
