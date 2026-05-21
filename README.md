# 🤖 AI Chat Agent

An intelligent AI-powered chat application featuring Google OAuth authentication, GPT-OSS-120B integration, and support for WhatsApp and e-commerce integrations.

![Python](https://img.shields.io/badge/Python-3.11+-blue.svg)
![Flask](https://img.shields.io/badge/Flask-3.0-green.svg)
![License](https://img.shields.io/badge/License-MIT-yellow.svg)

## 🌐 How to Access / Run the Project

You can experience and test this project in two ways: online via our live deployment or by running a local server on your machine.

### Option 1: View Online (Live Web App)
The easiest way to see the project in action is to visit the live deployment!
- **Live Web App:** [https://fyp-xi-flame.vercel.app](https://fyp-xi-flame.vercel.app)
- **GitHub Repository:** [https://github.com/Hassnain-Alii/FYP](https://github.com/Hassnain-Alii/FYP)

*(Note: The live version is hosted on Vercel and connects to a Supabase PostgreSQL database for persistent storage).*

### Option 2: Run Local Server
If you want to view the code, test modifications, or run the project locally on your PC, you can easily start the Flask server. 

To start the local server, run the following command in your terminal:
```bash
python run.py
```
This will start the application locally at `http://localhost:5000`.

#### Using Ngrok for WhatsApp Webhooks
If you are testing the **WhatsApp Business Webhook** integration locally, you will need a stable, public domain for Meta to send WhatsApp messages to. This is where `ngrok` comes in!

**What is ngrok and why do we use it?**
`ngrok` is a developer tool that safely exposes your local server to the public internet. Since Meta/WhatsApp cannot send data to `http://localhost:5000` (because that address only exists on your private computer), `ngrok` generates a secure, public URL (like `https://random-string.ngrok-free.app`) that instantly forwards traffic directly to your local PC.

To use it, first start your Flask app (`python run.py`), and then in a new terminal window run:
```bash
ngrok http 5000
```
Copy the secure `https` forwarding URL provided by ngrok and paste it into your WhatsApp Developer Dashboard to receive real-time messages locally!

---

## ✨ Features

- **🔐 Google OAuth Authentication** - Secure sign-in with Google accounts
- **💬 AI-Powered Chat** - Conversations powered by GPT-OSS-120B via Cerebras/GroqCloud
- **📊 Usage Tracking** - 100 free messages per day with usage visualization
- **📱 WhatsApp Integration** - Configure WhatsApp Business API settings
- **🛒 E-commerce Integration** - Connect with Shopify, WooCommerce, Magento, and more
- **💾 Conversation History** - Persistent message storage with session management
- **🎨 Modern UI** - Beautiful dark theme with glassmorphism effects

## 🚀 Quick Start

### Prerequisites

- Python 3.11 or higher
- pip (Python package manager)
- Google OAuth credentials
- AI API key (Cerebras or GroqCloud)

### Installation

1. **Clone or navigate to the project directory**

   ```bash
   cd d:\Programing\FYP
   ```

2. **Create a virtual environment (recommended)**

   ```bash
   python -m venv venv

   # Windows
   .\venv\Scripts\activate

   # Linux/Mac
   source venv/bin/activate
   ```

3. **Install dependencies**

   ```bash
   pip install -r requirements.txt
   ```

4. **Configure environment variables**

   Copy the example environment file:

   ```bash
   copy .env.example .env
   ```

   Edit `.env` and add your credentials:

   ```env
   FLASK_SECRET_KEY=your-super-secret-key-here
   GOOGLE_CLIENT_ID=your-google-client-id.apps.googleusercontent.com
   GOOGLE_CLIENT_SECRET=your-google-client-secret
   AI_API_ENDPOINT=https://api.cerebras.ai/v1/chat/completions
   AI_API_KEY=your-ai-api-key
   AI_MODEL_NAME=llama3.1-70b
   FREE_TIER_LIMIT=100
   ```

5. **Run the application**

   ```bash
   python run.py
   ```

6. **Open your browser**

   Navigate to `http://localhost:5000`

## 🔧 Configuration

### Google OAuth Setup

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project or select existing one
3. Navigate to **APIs & Services** → **Credentials**
4. Click **Create Credentials** → **OAuth client ID**
5. Select **Web application**
6. Add authorized redirect URI: `http://localhost:5000/login/google/authorized`
7. Copy the Client ID and Client Secret to your `.env` file

### AI API Setup

#### Option 1: Cerebras

1. Sign up at [Cerebras Cloud](https://cloud.cerebras.ai/)
2. Generate an API key
3. Set in `.env`:
   ```env
   AI_API_ENDPOINT=https://api.cerebras.ai/v1/chat/completions
   AI_API_KEY=your-cerebras-api-key
   AI_MODEL_NAME=llama3.1-70b
   ```

#### Option 2: GroqCloud

1. Sign up at [GroqCloud](https://console.groq.com/)
2. Generate an API key
3. Set in `.env`:
   ```env
   AI_API_ENDPOINT=https://api.groq.com/openai/v1/chat/completions
   AI_API_KEY=your-groq-api-key
   AI_MODEL_NAME=llama-3.1-70b-versatile
   ```

## 📁 Project Structure

```
FYP/
├── app/
│   ├── __init__.py          # Flask app factory
│   ├── models.py             # Database models
│   ├── routes/
│   │   ├── auth.py           # Google OAuth routes
│   │   ├── chat.py           # Chat API endpoints
│   │   ├── integrations.py   # Integration settings
│   │   └── whatsapp_webhook.py # WhatsApp Meta Webhook
│   ├── services/
│   │   ├── ai_service.py     # AI API integration
│   │   ├── ecommerce_service.py # E-commerce logic
│   │   └── limiter.py        # Message limit service
│   ├── static/
│   │   ├── css/              # Split stylesheets (chat.css, settings.css, etc.)
│   │   └── js/               # Frontend logic (chat.js, settings.js)
│   └── templates/
│       ├── base.html         # Base template
│       ├── login.html        # Login page
│       ├── chat.html         # Chat interface
│       └── settings.html     # Integration settings
├── requirements.txt          # Python dependencies
├── .env.example              # Environment template
├── .env                      # Your configuration (git-ignored)
├── .gitignore                # Git ignore rules
├── run.py                    # Application entry point
└── README.md                 # This file
```

## 🔌 API Endpoints

### Authentication

| Method | Endpoint        | Description           |
| ------ | --------------- | --------------------- |
| GET    | `/login`        | Login page            |
| GET    | `/login/google` | Initiate Google OAuth |
| GET    | `/logout`       | Log out user          |
| GET    | `/api/user`     | Get current user info |

### Chat

| Method | Endpoint                  | Description                   |
| ------ | ------------------------- | ----------------------------- |
| POST   | `/api/chat`               | Send message, get AI response |
| GET    | `/api/messages`           | Get message history           |
| GET    | `/api/usage`              | Get usage statistics          |
| GET    | `/api/conversations`      | List conversation sessions    |
| GET    | `/api/conversations/<id>` | Get specific conversation     |

### Integrations

| Method          | Endpoint                      | Description                |
| --------------- | ----------------------------- | -------------------------- |
| GET             | `/api/integrations`           | Get all integrations       |
| POST            | `/api/integrations/token`     | Update Webhook Verify Token|
| GET/POST/DELETE | `/api/integrations/<provider>`| Manage provider settings   |
| GET/POST        | `/webhook`                    | WhatsApp Meta Webhook API  |

## 🎨 Screenshots

The application features a modern dark theme with:

- Animated gradient login page
- Glassmorphism chat interface
- Usage tracking sidebar
- Responsive settings page

## 📝 Usage Limits

- **Free Tier**: 100 messages per day
- Counter resets at midnight UTC
- Premium features coming soon!

## 🛠️ Development

### Running in Development Mode

```bash
python run.py
```

The server runs with debug mode enabled.

### Database

SQLite database is automatically created at `app/chat_agent.db` on first run.


## 🤝 Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## 📧 Support

For questions or support, please open an issue in the repository.

---
