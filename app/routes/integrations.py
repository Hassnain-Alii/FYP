
"""
Integration Settings Routes (Multi-Provider System)
WhatsApp, Shopify, WooCommerce, Custom APIs
"""

from flask import Blueprint, request, jsonify, render_template, url_for, current_app
from flask_login import login_required, current_user
from app import db
from app.models import Integration
import requests
import secrets
import dotenv
import os
from pathlib import Path

integrations_bp = Blueprint('integrations', __name__)


# =====================================================
# SETTINGS PAGE
# =====================================================
@integrations_bp.route('/settings')
@login_required
def settings_page():
    webhook_url = url_for('webhook.receive_message', _external=True)
    verify_token = current_app.config.get('WHATSAPP_VERIFY_TOKEN', '')
    return render_template('settings.html', webhook_url=webhook_url, verify_token=verify_token)


# =====================================================
# GET ALL INTEGRATIONS
# =====================================================
@integrations_bp.route('/api/integrations')
@login_required
def get_integrations():
    integrations = Integration.query.filter_by(user_id=current_user.id).all()

    return jsonify({
        "integrations": [i.to_dict() for i in integrations]
    })


# =====================================================
# UPDATE VERIFY TOKEN
# =====================================================
@integrations_bp.route('/api/integrations/token', methods=['POST'])
@login_required
def update_verify_token():
    new_token = secrets.token_hex(32)
    
    # Update .env
    env_path = Path(current_app.root_path).parent / '.env'
    if env_path.exists():
        dotenv.set_key(env_path, 'WHATSAPP_VERIFY_TOKEN', new_token)
    
    # Update in memory
    current_app.config['WHATSAPP_VERIFY_TOKEN'] = new_token
    
    return jsonify({"token": new_token})


# =====================================================
# MAIN MULTI-PROVIDER HANDLER
# =====================================================
@integrations_bp.route('/api/integrations/<provider>', methods=['GET', 'POST', 'DELETE'])
@login_required
def handle_integration(provider):

    # =================================================
    # GET
    # =================================================
    if request.method == 'GET':
        integration = Integration.query.filter_by(
            user_id=current_user.id,
            provider=provider
        ).first()

        return jsonify(integration.to_dict() if integration else {"config": {}})

    # =================================================
    # POST (CREATE / UPDATE)
    # =================================================
    if request.method == 'POST':
        data = request.get_json()

        if not data:
            return jsonify({"error": "No data provided"}), 400

        # =================================================
        # WHATSAPP (META)
        # =================================================
        if provider == "meta_whatsapp":

            access_token = data.get("access_token")
            phone_number_id = data.get("phone_number_id")

            if not access_token or not phone_number_id:
                return jsonify({"error": "Missing WhatsApp credentials"}), 400

            # ---- validate token ----
            try:
                url = "https://graph.facebook.com/v18.0/me"
                headers = {"Authorization": f"Bearer {access_token}"}
                res = requests.get(url, headers=headers, timeout=10)

                if res.status_code != 200:
                    return jsonify({"error": "Invalid WhatsApp Access Token"}), 400

            except Exception as e:
                 return jsonify({"error": f"Token validation failed: {str(e)}"}), 500


            # ---- validate phone number id ----
            try:
                url = f"https://graph.facebook.com/v18.0/{phone_number_id}"
                headers = {"Authorization": f"Bearer {access_token}"}

                res = requests.get(url, headers=headers, timeout=10)

                if res.status_code != 200:
                    return jsonify({"error": "Invalid phone number ID"}), 400

            except Exception as e:
                return jsonify({"error": str(e)}), 500

        # =================================================
        # SHOPIFY / GENERIC STORE
        # =================================================
        elif provider in ["shopify", "woocommerce", "custom_api"]:

            store_url = data.get("store_url")
            client_id = data.get("client_id")
            client_secret = data.get("client_secret")
            access_token = data.get("access_token")
            webhook_url = data.get("webhook_url")

            if provider == "shopify":
                if not store_url or not client_id or not access_token:
                    return jsonify({"error": "Missing Shopify credentials"}), 400
                test_url = store_url.rstrip("/") + "/admin/api/2025-01/shop.json"
                headers = {"X-Shopify-Access-Token": access_token}
                auth = None
            elif provider == "woocommerce":
                if not store_url or not client_id or not client_secret:
                    return jsonify({"error": "Missing WooCommerce credentials"}), 400
                test_url = store_url.rstrip("/") + "/wp-json/wc/v3/products"
                headers = {}
                auth = (client_id, client_secret)
            else: # custom_api
                if not store_url:
                    return jsonify({"error": "Missing Custom API endpoint"}), 400
                test_url = store_url
                headers = {"Authorization": f"Bearer {access_token}"} if access_token else {}
                if client_secret:
                    headers.update({"x-api-secret": client_secret})
                auth = None

            # ---- test store connection ----
            try:
                res = requests.get(test_url, headers=headers, auth=auth, timeout=10)
                if res.status_code >= 400:
                    return jsonify({"error": f"Store API not reachable or unauthorized (Status {res.status_code})"}), 400
            except Exception as e:
                 return jsonify({"error": f"Store validation failed: {str(e)}"}), 500

            # ---------------- WEBHOOK CHECK (OPTIONAL) ----------------
            if webhook_url:
                try:
                    r = requests.get(webhook_url, timeout=10)
                    if r.status_code >= 400:
                        return jsonify({"error": "Webhook URL not reachable"}), 400
                except Exception:
                    return jsonify({"error": "Invalid webhook URL"}), 400

        else:
            return jsonify({"error": "Unsupported provider"}), 400

        # =================================================
        # SAVE TO DATABASE
        # =================================================
        integration = Integration.query.filter_by(
            user_id=current_user.id,
            provider=provider
        ).first()

        if not integration:
            integration = Integration(
                user_id=current_user.id,
                provider=provider
            )
            db.session.add(integration)

        integration.config = data
        if provider == "meta_whatsapp":
            integration.phone_number_id = data.get("phone_number_id")
            
        db.session.commit()

        return jsonify({
            "message": "Integration saved successfully",
            "integration": integration.to_dict()
        })


    # =====================================================
    # DELETE
    # =====================================================
    if request.method == 'DELETE':
        Integration.query.filter_by(
            user_id=current_user.id,
            provider=provider
        ).delete()

        db.session.commit()

        return jsonify({"message": "Integration removed successfully"})
