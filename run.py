"""
Main Entry Point
Startup script for the AI Chat Agent Flask application.
Run this file to launch the development server.
"""

from app import create_app

# 1. Initialize the application using the factory pattern
# This loads all configurations, extensions, and routes.
app = create_app()

if __name__ == '__main__':
    # 2. Start-up Banner: Useful for debugging and CLI feedback
    print("=" * 60)
    print("🚀 AI Chat Agent Interface - Developer Environment")
    print("-" * 60)
    print("🌍 Backend: Flask (Local Server)")
    print("🤖 Model:  gpt-oss-120b")
    print("📍 URL:    http://127.0.0.1:5000")
    print("-" * 60)
    print("💡 Status: Monitoring for incoming chat requests...")
    print("=" * 60)
    
    # 3. Launch Server: Configured for local development with auto-reload
    app.run(debug=True, host='0.0.0.0', port=5000)
