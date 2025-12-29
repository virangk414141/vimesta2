import os
import uuid
import hashlib
import random
import mimetypes
from datetime import datetime, timedelta
from flask import Flask, request, jsonify, redirect
from flask_cors import CORS
from werkzeug.utils import secure_filename

from config import Config
from models import db, init_db, User, File
from auth import generate_token, token_required, create_session
from telegram_handler import telegram_handler

# Initialize Flask app
app = Flask(__name__)
app.config.from_object(Config)

# CORS
CORS(app, resources={r"/api/*": {"origins": "*"}}, supports_credentials=True)

# Initialize database
init_db(app)

# Upload folder
os.makedirs(Config.UPLOAD_FOLDER, exist_ok=True)

# OTP Storage
otp_storage = {}

# File URL Cache
file_url_cache = {}
CACHE_DURATION = 3600


def generate_otp():
    return str(random.randint(100000, 999999))


def normalize_phone(phone):
    phone = ''.join(filter(lambda x: x.isdigit() or x == '+', str(phone)))
    if phone.startswith('+91'):
        return phone
    if phone.startswith('91') and len(phone) > 10:
        return '+91' + phone[2:]
    if len(phone) == 10:
        return '+91' + phone
    return '+91' + phone[-10:] if len(phone) >= 10 else phone


def get_file_type(filename):
    ext = filename.lower().split('.')[-1] if '.' in filename else ''
    if ext in ['jpg', 'jpeg', 'png', 'gif', 'bmp', 'webp', 'svg', 'ico']:
        return 'image'
    elif ext in ['mp4', 'avi', 'mkv', 'mov', 'webm', 'flv', '3gp']:
        return 'video'
    elif ext in ['mp3', 'wav', 'ogg', 'flac', 'm4a', 'aac']:
        return 'audio'
    elif ext in ['pdf', 'doc', 'docx', 'txt', 'xlsx', 'xls', 'pptx', 'ppt', 'csv']:
        return 'document'
    return 'other'


def format_file_size(size_bytes):
    for unit in ['B', 'KB', 'MB', 'GB']:
        if size_bytes < 1024:
            return f"{size_bytes:.1f} {unit}"
        size_bytes /= 1024
    return f"{size_bytes:.1f} TB"


def get_cached_file_url(file_id):
    now = datetime.now().timestamp()
    if file_id in file_url_cache:
        cached = file_url_cache[file_id]
        if now - cached['time'] < CACHE_DURATION:
            return cached['url']
    result = telegram_handler.get_file_url(file_id)
    if result['success']:
        file_url_cache[file_id] = {'url': result['url'], 'time': now}
        return result['url']
    return None


# ==================== AUTH ====================

@app.route('/api/auth/request-otp', methods=['POST'])
def request_otp():
    try:
        data = request.json
        if not data or not data.get('phone'):
            return jsonify({'success': False, 'error': 'Phone required'}), 400
        
        phone = normalize_phone(data['phone'])
        telegram_data = telegram_handler.get_telegram_id_by_phone(phone)
        
        if not telegram_data:
            return jsonify({
                'success': False,
                'error': 'phone_not_linked',
                'message': 'Open @Vimesta_bot on Telegram and share phone number.',
                'bot_link': 'https://t.me/Vimesta_bot?start=login'
            }), 400
        
        telegram_id = telegram_data['telegram_id']
        otp = generate_otp()
        
        otp_storage[phone] = {
            'otp': otp,
            'expires': datetime.now() + timedelta(minutes=5),
            'attempts': 0,
            'telegram_id': telegram_id
        }
        
        result = telegram_handler.send_message(
            telegram_id,
            f"🔐 <b>Verification Code</b>\n\n<code>{otp}</code>\n\nExpires in 5 minutes."
        )
        
        if result['success']:
            return jsonify({'success': True, 'message': 'OTP sent!'})
        return jsonify({'success': False, 'error': 'Failed to send OTP'}), 500
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/auth/verify-otp', methods=['POST'])
def verify_otp():
    try:
        data = request.json
        if not data:
            return jsonify({'success': False, 'error': 'No data'}), 400
        
        phone = normalize_phone(data.get('phone', ''))
        otp = data.get('otp', '')
        
        if not phone or not otp:
            return jsonify({'success': False, 'error': 'Phone and OTP required'}), 400
        
        if phone not in otp_storage:
            return jsonify({'success': False, 'error': 'OTP expired'}), 400
        
        stored = otp_storage[phone]
        
        if datetime.now() > stored['expires']:
            del otp_storage[phone]
            return jsonify({'success': False, 'error': 'OTP expired'}), 400
        
        if stored['attempts'] >= 3:
            del otp_storage[phone]
            return jsonify({'success': False, 'error': 'Too many attempts'}), 400
        
        if stored['otp'] != otp:
            stored['attempts'] += 1
            return jsonify({'success': False, 'error': f'Invalid OTP. {3-stored["attempts"]} left.'}), 400
        
        telegram_id = stored['telegram_id']
        del otp_storage[phone]
        
        user = User.query.filter_by(phone_number=phone).first()
        
        if not user:
            telegram_data = telegram_handler.get_telegram_id_by_phone(phone)
            first_name = telegram_data.get('first_name', 'User') if telegram_data else 'User'
            user = User(telegram_id=telegram_id, phone_number=phone, first_name=first_name)
            db.session.add(user)
            db.session.commit()
        else:
            user.last_login = datetime.now()
            user.telegram_id = telegram_id
            db.session.commit()
        
        token = generate_token(user.id, telegram_id)
        create_session(user, token, request)
        
        return jsonify({'success': True, 'message': 'Login successful!', 'token': token, 'user': user.to_dict()})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/auth/verify', methods=['GET'])
@token_required
def verify_auth(user):
    return jsonify({'success': True, 'user': user.to_dict()})


# ==================== FILES ====================

@app.route('/api/files/upload', methods=['POST'])
@token_required
def upload_file(user):
    try:
        if 'file' not in request.files:
            return jsonify({'success': False, 'error': 'No file'}), 400
        
        file = request.files['file']
        if file.filename == '':
            return jsonify({'success': False, 'error': 'No file'}), 400
        
        original_filename = file.filename
        secure_name = secure_filename(original_filename) or f"file_{uuid.uuid4().hex[:8]}"
        unique_filename = f"{uuid.uuid4()}_{secure_name}"
        file_path = os.path.join(Config.UPLOAD_FOLDER, unique_filename)
        
        file.save(file_path)
        file_size = os.path.getsize(file_path)
        
        result = telegram_handler.send_file_to_storage(
            file_path=file_path,
            filename=original_filename,
            user_phone=user.phone_number or str(user.telegram_id)
        )
        
        if not result['success']:
            os.remove(file_path)
            return jsonify({'success': False, 'error': result.get('error', 'Upload failed')}), 500
        
        file_type = get_file_type(original_filename)
        mime_type, _ = mimetypes.guess_type(original_filename)
        
        file_record = File(
            user_id=user.id,
            telegram_file_id=result['file_id'],
            telegram_message_id=result.get('message_id'),
            original_filename=original_filename,
            file_size=file_size,
            file_type=file_type,
            mime_type=mime_type
        )
        db.session.add(file_record)
        user.storage_used += file_size
        db.session.commit()
        
        os.remove(file_path)
        
        preview_url = None
        if file_type == 'image' and result.get('file_id'):
            preview_url = get_cached_file_url(result['file_id'])
        
        file_dict = file_record.to_dict()
        file_dict['preview_url'] = preview_url
        
        return jsonify({'success': True, 'file': file_dict})
    except Exception as e:
        if 'file_path' in locals() and os.path.exists(file_path):
            os.remove(file_path)
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/files/list', methods=['GET'])
@token_required
def list_files(user):
    try:
        file_type = request.args.get('type')
        query = File.query.filter_by(user_id=user.id)
        
        if file_type:
            query = query.filter_by(file_type=file_type)
        
        files = query.order_by(File.upload_date.desc()).all()
        
        files_list = []
        for f in files:
            fd = f.to_dict()
            if f.file_type == 'image' and f.telegram_file_id:
                fd['preview_url'] = get_cached_file_url(f.telegram_file_id)
            files_list.append(fd)
        
        return jsonify({'success': True, 'files': files_list, 'count': len(files)})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/files/<file_id>/download', methods=['GET'])
@token_required
def download_file(user, file_id):
    try:
        file_record = File.query.filter_by(id=file_id, user_id=user.id).first()
        
        if not file_record:
            return jsonify({'success': False, 'error': 'Not found'}), 404
        
        if not file_record.telegram_file_id:
            return jsonify({'success': False, 'error': 'File data missing'}), 500
        
        download_url = get_cached_file_url(file_record.telegram_file_id)
        
        if not download_url:
            result = telegram_handler.get_file_url(file_record.telegram_file_id)
            if result['success']:
                download_url = result['url']
            else:
                return jsonify({'success': False, 'error': 'Could not get download URL'}), 500
        
        file_record.download_count += 1
        db.session.commit()
        
        return jsonify({'success': True, 'download_url': download_url, 'filename': file_record.original_filename})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/files/<file_id>', methods=['DELETE'])
@token_required
def delete_file(user, file_id):
    try:
        file_record = File.query.filter_by(id=file_id, user_id=user.id).first()
        
        if not file_record:
            return jsonify({'success': False, 'error': 'Not found'}), 404
        
        storage_channel = telegram_handler.get_storage_channel()
        if file_record.telegram_message_id and storage_channel:
            telegram_handler.delete_message(storage_channel, file_record.telegram_message_id)
        
        if file_record.telegram_file_id in file_url_cache:
            del file_url_cache[file_record.telegram_file_id]
        
        user.storage_used = max(0, user.storage_used - file_record.file_size)
        db.session.delete(file_record)
        db.session.commit()
        
        return jsonify({'success': True, 'message': 'Deleted'})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/files/<file_id>/share', methods=['POST'])
@token_required
def share_file(user, file_id):
    try:
        file_record = File.query.filter_by(id=file_id, user_id=user.id).first()
        
        if not file_record:
            return jsonify({'success': False, 'error': 'Not found'}), 404
        
        if not file_record.public_link_hash:
            file_record.public_link_hash = hashlib.sha256(
                f"{file_id}{datetime.now().isoformat()}{random.random()}".encode()
            ).hexdigest()[:16]
        
        file_record.is_public = True
        db.session.commit()
        
        return jsonify({'success': True, 'share_link': f"/share/{file_record.public_link_hash}"})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


# ==================== USER ====================

@app.route('/api/user/profile', methods=['GET'])
@token_required
def get_profile(user):
    return jsonify({'success': True, 'user': user.to_dict()})


@app.route('/api/user/storage', methods=['GET'])
@token_required
def get_storage_stats(user):
    try:
        files = File.query.filter_by(user_id=user.id).all()
        
        by_type = {}
        for f in files:
            ft = f.file_type or 'other'
            if ft not in by_type:
                by_type[ft] = {'count': 0, 'size': 0}
            by_type[ft]['count'] += 1
            by_type[ft]['size'] += f.file_size
        
        return jsonify({
            'success': True,
            'storage': {
                'total_files': len(files),
                'total_size': user.storage_used,
                'total_size_formatted': format_file_size(user.storage_used),
                'by_type': by_type
            }
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


# ==================== PUBLIC ====================

@app.route('/share/<hash>', methods=['GET'])
def public_file(hash):
    try:
        file_record = File.query.filter_by(public_link_hash=hash, is_public=True).first()
        if not file_record:
            return jsonify({'success': False, 'error': 'Not found'}), 404
        
        url = get_cached_file_url(file_record.telegram_file_id)
        if not url:
            return jsonify({'success': False, 'error': 'File unavailable'}), 500
        
        file_record.download_count += 1
        db.session.commit()
        
        return jsonify({
            'success': True,
            'file': {'filename': file_record.original_filename, 'size': file_record.file_size, 'download_url': url}
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/health', methods=['GET'])
def health():
    return jsonify({'success': True, 'status': 'healthy', 'version': '3.1.0'})


@app.route('/')
def index():
    return jsonify({'message': 'Vimesta Cloud API v3.1', 'status': 'running'})


if __name__ == '__main__':
    print("""
    ╔════════════════════════════════════════════════════════╗
    ║        🚀 VIMESTA CLOUD API v3.1 (No Folders) 🚀       ║
    ║                                                        ║
    ║  ✅ Phone-Only Auth  ✅ Hidden Storage                 ║
    ║  ✅ URL Caching      ✅ Files Only (No Folders)        ║
    ║                                                        ║
    ║  API: http://localhost:5000                            ║
    ╚════════════════════════════════════════════════════════╝
    """)
    app.run(debug=True, host='0.0.0.0', port=5000, threaded=True)
