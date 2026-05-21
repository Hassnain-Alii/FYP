from flask import Blueprint, request, jsonify, current_app
from app.services.whatsapp_service import send_whatsapp_message
from app.services.ai_service import generate_ai_response
from app.models import WhatsAppConversation, Integration
from app import db

webhook_bp = Blueprint("webhook", __name__)


# =====================================================
# VERIFY WEBHOOK
# =====================================================
@webhook_bp.route("/webhook", methods=["GET"])
def verify_webhook():
    verify_token = current_app.config.get('WHATSAPP_VERIFY_TOKEN')

    mode = request.args.get("hub.mode")
    token = request.args.get("hub.verify_token")
    challenge = request.args.get("hub.challenge")

    if mode == "subscribe" and token == verify_token:
        return challenge, 200

    return "Verification failed", 403


# =====================================================
# RECEIVE MESSAGE
# =====================================================
@webhook_bp.route("/webhook", methods=["POST"])
def receive_message():

    data = request.get_json()

    try:
        entry = data.get("entry", [])
        if not entry:
            return jsonify({"status": "no entry"}), 200

        changes = entry[0].get("changes", [])
        if not changes:
            return jsonify({"status": "no changes"}), 200

        value = changes[0].get("value", {})
        metadata = value.get("metadata", {})
        received_phone_id = metadata.get("phone_number_id")

        if "messages" not in value:
            return jsonify({"status": "no message"}), 200

        message = value["messages"][0]
        phone_number = message["from"]
        
        if message.get("type") != "text":
            return jsonify({"status": "unsupported message type"}), 200

        user_message = message["text"]["body"]

        # =====================================================
        # FIND USER INTEGRATION BY PHONE NUMBER ID
        # =====================================================
        integration = Integration.query.filter_by(
            provider="meta_whatsapp",
            phone_number_id=received_phone_id
        ).first()

        if not integration:
            print(f"No integration found for Phone ID: {received_phone_id}")
            return jsonify({"error": "WhatsApp integration not configured"}), 200

        config = integration.config or {}

        access_token = config.get("access_token")
        phone_id = config.get("phone_number_id")

        # validate required config
        if not access_token or not phone_id:
            return jsonify({"error": "Invalid WhatsApp configuration"}), 200

        # =====================================================
        # CHAT HISTORY
        # =====================================================
        conversation = WhatsAppConversation.query.filter_by(
            phone_number=phone_number
        ).first()

        if not conversation:
            conversation = WhatsAppConversation(phone_number=phone_number)
            db.session.add(conversation)
            db.session.commit()

        history = conversation.messages[-10:]

        # =====================================================
        # AI RESPONSE
        # =====================================================
        ai_reply = generate_ai_response(
            user_message=user_message,
            conversation_history=history,
            api_endpoint=current_app.config.get('AI_API_ENDPOINT'),
            api_key=current_app.config.get('AI_API_KEY'),
            model_name=current_app.config.get('AI_MODEL_NAME'),
            user_id=integration.user_id
        )

        # =====================================================
        # SEND WHATSAPP MESSAGE
        # =====================================================
        send_whatsapp_message(
            phone_number_id=phone_id,
            access_token=access_token,
            to=phone_number,
            message=ai_reply
        )

        # =====================================================
        # SAVE HISTORY
        # =====================================================
        conversation.add_message("user", user_message)
        conversation.add_message("assistant", ai_reply)

        db.session.commit()

    except Exception as e:
        print("Webhook Error:", str(e))

    return jsonify({"status": "received"}), 200