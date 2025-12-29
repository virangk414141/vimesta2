# Vimesta Cloud

🚀 **Unlimited Free Cloud Storage** powered by Telegram

Vimesta Cloud is a web-based cloud storage platform that uses Telegram's infrastructure to provide users with unlimited free storage. Upload, manage, and share your files through a beautiful web interface.

## ✨ Features

- **Unlimited Storage** - No storage limits, ever
- **2GB Per File** - Upload large files up to 2GB each
- **Secure** - Files stored in your Telegram account
- **Beautiful UI** - Modern dark theme with glassmorphism
- **Drag & Drop** - Easy file uploads
- **File Sharing** - Generate shareable links
- **Folder Organization** - Keep files organized
- **Cross-Platform** - Access from any device

## 🛠️ Technology Stack

| Component | Technology |
|-----------|------------|
| Frontend | HTML5, CSS3, Vanilla JavaScript |
| Backend | Python 3.10+, Flask |
| Database | SQLite |
| Bot API | python-telegram-bot v20+ |
| Auth | JWT tokens |

## 📁 Project Structure

```
vimesta Cloud/
├── backend/
│   ├── app.py              # Flask API server
│   ├── config.py           # Configuration
│   ├── models.py           # Database models
│   ├── auth.py             # JWT authentication
│   ├── telegram_handler.py # Telegram Bot integration
│   └── requirements.txt    # Python dependencies
├── frontend/
│   ├── index.html          # Landing page
│   ├── dashboard.html      # User dashboard
│   ├── css/
│   │   └── style.css       # Main stylesheet
│   └── js/
│       ├── app.js          # Main app logic
│       └── upload.js       # File upload handler
└── README.md
```

## 🚀 Quick Start

### Prerequisites

- Python 3.10 or higher
- pip (Python package manager)
- A web browser

### Installation

1. **Clone or download the project**

2. **Install backend dependencies**
   ```bash
   cd "vimesta Cloud/backend"
   pip install -r requirements.txt
   ```

3. **Start the backend server**
   ```bash
   python app.py
   ```
   Server will start at `http://localhost:5000`

4. **Open the frontend**
   
   Open `frontend/index.html` in your web browser
   
   Or use a local server:
   ```bash
   cd "vimesta Cloud/frontend"
   python -m http.server 8080
   ```
   Then visit `http://localhost:8080`

## 🔧 Configuration

Edit `backend/config.py` to configure:

```python
# Telegram Bot Token
TELEGRAM_BOT_TOKEN = 'your-bot-token-here'

# JWT Secret Key (change in production)
JWT_SECRET_KEY = 'your-secret-key'

# Database URL
SQLALCHEMY_DATABASE_URI = 'sqlite:///vimesta.db'
```

## 📡 API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/auth/telegram` | Login with Telegram |
| GET | `/api/auth/verify` | Verify JWT token |
| POST | `/api/files/upload` | Upload file |
| GET | `/api/files/list` | List user's files |
| GET | `/api/files/{id}/download` | Download file |
| DELETE | `/api/files/{id}` | Delete file |
| POST | `/api/files/{id}/share` | Create share link |
| POST | `/api/folders/create` | Create folder |
| GET | `/api/folders/list` | List folders |
| GET | `/api/user/profile` | Get user profile |
| GET | `/api/user/storage` | Get storage stats |

## 🔐 How It Works

1. **User Login** - Users authenticate with their Telegram ID
2. **File Upload** - Files are uploaded through the web interface
3. **Telegram Storage** - Backend sends files to user's Telegram "Saved Messages"
4. **Metadata Storage** - File metadata (name, size, Telegram file_id) stored in database
5. **File Retrieval** - Downloads fetched from Telegram using stored file_id

## 🎨 Screenshots

### Landing Page
- Modern hero section with animated card
- Feature highlights
- Pricing plans

### Dashboard
- File grid view
- Drag-and-drop upload
- Folder organization
- Storage statistics

## 🤝 Telegram Bot

Your Telegram bot: [@Vimesta_bot](https://t.me/Vimesta_bot)

The bot sends welcome messages and stores files in users' "Saved Messages".

## ⚠️ Important Notes

- **File Size Limit**: Telegram allows files up to 2GB
- **Token Security**: Never expose your bot token publicly
- **Rate Limits**: Telegram has API rate limits, uploads are queued
- **Privacy**: Files stored in user's own Telegram account

## 📄 License

MIT License - feel free to use and modify!

## 🙏 Credits

- Telegram Bot API
- Flask Framework
- Inter Font (Google Fonts)

---

Made with ❤️ for unlimited cloud storage
