import os
import sys
from pathlib import Path

# Add the project root directory to the Python path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app import create_app

# Vercel looks for 'app' to serve the WSGI application
app = create_app()
