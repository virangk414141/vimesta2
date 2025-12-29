import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    # Flask Configuration
    SECRET_KEY = os.getenv('SECRET_KEY', 'vimesta-cloud-secret-key-2024')
    DEBUG = os.getenv('DEBUG', True)
    
    # Database Configuration
    SQLALCHEMY_DATABASE_URI = os.getenv('DATABASE_URL', 'sqlite:///vimesta.db')
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    # Telegram Bot Configuration
    TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN', '8142851465:AAEASmmPeQQIkTSKyRY7LogY-jket5Qra5E')
    TELEGRAM_BOT_USERNAME = 'Vimesta_bot'
    
    # PRIVATE STORAGE CHANNEL
    # Files will be uploaded here (hidden from users)
    # Set this to a private channel ID where bot is admin
    # Example: -1001234567890 (channel IDs start with -100)
    # If not set, will use bot's own chat (first person who starts bot becomes storage)
    STORAGE_CHANNEL_ID = os.getenv('STORAGE_CHANNEL_ID', None)
    
    # JWT Configuration
    JWT_SECRET_KEY = os.getenv('JWT_SECRET_KEY', 'vimesta-jwt-secret-2024')
    JWT_ACCESS_TOKEN_EXPIRES = 86400 * 7  # 7 days
    
    # File Upload Configuration
    MAX_CONTENT_LENGTH = 2 * 1024 * 1024 * 1024  # 2GB max file size
    UPLOAD_FOLDER = os.path.join(os.path.dirname(__file__), 'uploads')
    ALLOWED_EXTENSIONS = {'txt', 'pdf', 'png', 'jpg', 'jpeg', 'gif', 'mp4', 'mp3', 'doc', 'docx', 'xlsx', 'zip', 'rar', 'webp'}
    
    # CORS Configuration
    CORS_ORIGINS = ['*']
