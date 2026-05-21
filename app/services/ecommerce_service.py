import requests
import logging
from app.models import Integration

logger = logging.getLogger(__name__)

def get_products(user_id):
    """
    Fetch products from the user's configured e-commerce integration.
    """
    integration = Integration.query.filter(
        Integration.user_id == user_id,
        Integration.provider.in_(['shopify', 'woocommerce', 'custom_api'])
    ).first()

    if not integration:
        logger.info(f"No e-commerce integration found for user {user_id}")
        return []

    provider = integration.provider
    config = integration.config

    store_url = config.get("store_url", "").rstrip("/")
    
    products = []

    try:
        if provider == "shopify":
            access_token = config.get("access_token")
            headers = {"X-Shopify-Access-Token": access_token}
            
            # Try fetching products first
            products_url = f"{store_url}/admin/api/2025-01/products.json"
            res = requests.get(products_url, headers=headers, timeout=10)
            
            if res.status_code == 200:
                data = res.json().get("products", [])
                for item in data:
                    price = item.get("variants", [{}])[0].get("price", "0.00")
                    products.append({
                        "title": item.get("title", "Unknown"),
                        "price": price,
                        "category": item.get("product_type", "General")
                    })
                return products
            elif res.status_code == 403:
                # Fallback to store info if read_products scope is missing
                shop_url = f"{store_url}/admin/api/2025-01/shop.json"
                shop_res = requests.get(shop_url, headers=headers, timeout=10)
                if shop_res.status_code == 200:
                    shop_data = shop_res.json().get("shop", {})
                    products.append({
                        "title": f"Store: {shop_data.get('name', 'Shopify Store')}",
                        "price": "N/A",
                        "category": shop_data.get("domain", "Store Info")
                    })
                    return products

        elif provider == "woocommerce":
            client_id = config.get("client_id")
            client_secret = config.get("client_secret")
            auth = (client_id, client_secret)
            
            url = f"{store_url}/wp-json/wc/v3/products"
            res = requests.get(url, auth=auth, timeout=10)
            
            if res.status_code == 200:
                data = res.json()
                for item in data:
                    products.append({
                        "title": item.get("name", "Unknown"),
                        "price": item.get("price", "0.00"),
                        "category": item.get("categories", [{}])[0].get("name", "General") if item.get("categories") else "General"
                    })
                return products
                
        elif provider == "custom_api":
            access_token = config.get("access_token")
            client_secret = config.get("client_secret")
            headers = {"Authorization": f"Bearer {access_token}"} if access_token else {}
            if client_secret:
                headers.update({"x-api-secret": client_secret})
                
            res = requests.get(store_url, headers=headers, timeout=10)
            if res.status_code == 200:
                # Best-effort extraction
                data = res.json()
                if isinstance(data, dict) and "products" in data:
                    data = data["products"]
                
                if isinstance(data, list):
                    for item in data:
                        products.append({
                            "title": item.get("name", item.get("title", "Unknown")),
                            "price": item.get("price", "0.00"),
                            "category": "Custom API Item"
                        })
                return products

    except Exception as e:
        logger.error(f"Error fetching data from {provider}: {str(e)}")

    return products