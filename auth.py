import jwt
import hashlib
import hmac
from datetime import datetime, timedelta
from functools import wraps
from flask import request, jsonify, current_app
from models import db, User, Session

def generate_token(user_id, telegram_id):
    """Generate JWT token for authenticated user"""
    payload = {
        'user_id': user_id,
        'telegram_id': telegram_id,
        'exp': datetime.utcnow() + timedelta(seconds=current_app.config['JWT_ACCESS_TOKEN_EXPIRES']),
        'iat': datetime.utcnow()
    }
    token = jwt.encode(payload, current_app.config['JWT_SECRET_KEY'], algorithm='HS256')
    return token


def verify_token(token):
    """Verify JWT token and return payload"""
    try:
        payload = jwt.decode(token, current_app.config['JWT_SECRET_KEY'], algorithms=['HS256'])
        return payload
    except jwt.ExpiredSignatureError:
        return None
    except jwt.InvalidTokenError:
        return None


def verify_telegram_auth(auth_data):
    """Verify Telegram Login Widget authentication data"""
    bot_token = current_app.config['TELEGRAM_BOT_TOKEN']
    
    # Create data check string
    check_hash = auth_data.pop('hash', None)
    if not check_hash:
        return False
    
    # Sort data alphabetically and create check string
    data_check_arr = [f"{key}={value}" for key, value in sorted(auth_data.items())]
    data_check_string = '\n'.join(data_check_arr)
    
    # Create secret key from bot token
    secret_key = hashlib.sha256(bot_token.encode()).digest()
    
    # Calculate hash
    calculated_hash = hmac.new(secret_key, data_check_string.encode(), hashlib.sha256).hexdigest()
    
    # Verify hash matches
    if calculated_hash != check_hash:
        return False
    
    # Check if auth_date is not too old (max 1 day)
    auth_date = int(auth_data.get('auth_date', 0))
    if datetime.utcnow().timestamp() - auth_date > 86400:
        return False
    
    return True


def token_required(f):
    """Decorator to require valid JWT token for API endpoints"""
    @wraps(f)
    def decorated(*args, **kwargs):
        token = None
        
        # Get token from Authorization header
        if 'Authorization' in request.headers:
            auth_header = request.headers['Authorization']
            if auth_header.startswith('Bearer '):
                token = auth_header.split(' ')[1]
        
        if not token:
            return jsonify({'error': 'Token is missing', 'success': False}), 401
        
        # Verify token
        payload = verify_token(token)
        if not payload:
            return jsonify({'error': 'Token is invalid or expired', 'success': False}), 401
        
        # Get user from database
        user = User.query.get(payload['user_id'])
        if not user:
            return jsonify({'error': 'User not found', 'success': False}), 401
        
        # Pass user to the decorated function
        return f(user, *args, **kwargs)
    
    return decorated


def create_session(user, token, request):
    """Create a new session record"""
    session = Session(
        user_id=user.id,
        jwt_token=token,
        ip_address=request.remote_addr,
        user_agent=request.user_agent.string[:500] if request.user_agent else None,
        expires_at=datetime.utcnow() + timedelta(seconds=current_app.config['JWT_ACCESS_TOKEN_EXPIRES'])
    )
    db.session.add(session)
    db.session.commit()
    return session


def invalidate_session(token):
    """Invalidate a session"""
    session = Session.query.filter_by(jwt_token=token, is_active=True).first()
    if session:
        session.is_active = False
        db.session.commit()
        return True
    return False
