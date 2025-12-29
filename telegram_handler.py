import os
import json
import time
import threading
import requests
from config import Config

class TelegramHandler:
    def __init__(self):
        self.bot_token = Config.TELEGRAM_BOT_TOKEN
        self.api_base = f"https://api.telegram.org/bot{self.bot_token}"
        
        # Phone to Telegram ID mapping
        self.phone_mapping_file = os.path.join(os.path.dirname(__file__), 'phone_mapping.json')
        self.phone_to_telegram = self._load_phone_mapping()
        
        # Storage channel ID - use first registered user or config
        self.storage_channel_id = self._get_initial_storage_channel()
        
        # Track last update ID for polling
        self.last_update_id = 0
        
        # Start polling in background
        self.polling_thread = threading.Thread(target=self._poll_updates, daemon=True)
        self.polling_thread.start()
        print("✅ Telegram Bot polling started!")
        if self.storage_channel_id:
            print(f"📦 Storage channel: {self.storage_channel_id}")
    
    def _get_initial_storage_channel(self):
        if Config.STORAGE_CHANNEL_ID:
            return int(Config.STORAGE_CHANNEL_ID)
        if self.phone_to_telegram:
            first_user = list(self.phone_to_telegram.values())[0]
            return first_user.get('telegram_id')
        return None
    
    def _load_phone_mapping(self):
        if os.path.exists(self.phone_mapping_file):
            try:
                with open(self.phone_mapping_file, 'r') as f:
                    return json.load(f)
            except:
                return {}
        return {}
    
    def _save_phone_mapping(self):
        with open(self.phone_mapping_file, 'w') as f:
            json.dump(self.phone_to_telegram, f)
    
    def _normalize_phone(self, phone):
        phone = ''.join(filter(lambda x: x.isdigit() or x == '+', str(phone)))
        if phone.startswith('+'):
            return phone
        if phone.startswith('91') and len(phone) > 10:
            return '+' + phone
        if len(phone) == 10:
            return '+91' + phone
        return '+' + phone
    
    def get_telegram_id_by_phone(self, phone):
        phone = self._normalize_phone(phone)
        return self.phone_to_telegram.get(phone)
    
    def register_phone(self, phone, telegram_id, first_name=''):
        phone = self._normalize_phone(phone)
        self.phone_to_telegram[phone] = {
            'telegram_id': telegram_id,
            'first_name': first_name
        }
        self._save_phone_mapping()
        print(f"📱 Registered: {phone} -> {telegram_id}")
        
        if not self.storage_channel_id:
            self.storage_channel_id = telegram_id
            print(f"📦 Storage: {telegram_id}")
    
    def get_storage_channel(self):
        if not self.storage_channel_id:
            self.storage_channel_id = self._get_initial_storage_channel()
        return self.storage_channel_id
    
    def _poll_updates(self):
        while True:
            try:
                url = f"{self.api_base}/getUpdates"
                params = {
                    'offset': self.last_update_id + 1,
                    'timeout': 30,
                    'allowed_updates': json.dumps(['message'])
                }
                response = requests.get(url, params=params, timeout=35)
                if response.status_code == 200:
                    data = response.json()
                    if data.get('ok') and data.get('result'):
                        for update in data['result']:
                            self.last_update_id = update['update_id']
                            self._handle_update(update)
            except Exception as e:
                print(f"Polling error: {e}")
                time.sleep(5)
    
    def _handle_update(self, update):
        if 'message' not in update:
            return
        
        message = update['message']
        chat_id = message['chat']['id']
        
        if 'contact' in message:
            contact = message['contact']
            phone = contact.get('phone_number', '')
            first_name = contact.get('first_name', '')
            self.register_phone(phone, chat_id, first_name)
            self.send_message(chat_id, "✅ <b>Verified!</b>\nNow login on Vimesta Cloud.")
            return
        
        if 'text' in message:
            text = message['text']
            if text.startswith('/start'):
                self._send_contact_request(
                    chat_id,
                    "🚀 <b>Vimesta Cloud</b>\n\nShare your phone to continue 👇"
                )
    
    def _send_contact_request(self, chat_id, text):
        url = f"{self.api_base}/sendMessage"
        keyboard = {
            'keyboard': [[{'text': '📱 Share Phone', 'request_contact': True}]],
            'resize_keyboard': True,
            'one_time_keyboard': True
        }
        try:
            requests.post(url, data={
                'chat_id': chat_id,
                'text': text,
                'parse_mode': 'HTML',
                'reply_markup': json.dumps(keyboard)
            })
        except:
            pass
    
    def send_message(self, chat_id, text, silent=False):
        url = f"{self.api_base}/sendMessage"
        try:
            data = {'chat_id': chat_id, 'text': text, 'parse_mode': 'HTML'}
            if silent:
                data['disable_notification'] = True
            response = requests.post(url, data=data)
            if response.status_code == 200:
                result = response.json()
                return {'success': result.get('ok', False), 'message_id': result.get('result', {}).get('message_id')}
            return {'success': False, 'error': response.text}
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    def upload_file_hidden(self, file_path, filename, user_telegram_id, user_phone):
        """
        Upload file to HIDDEN storage (for Vimesta Cloud)
        Then send brief notification to user and DELETE it
        """
        storage_id = self.get_storage_channel()
        
        if not storage_id:
            return {'success': False, 'error': 'No storage configured'}
        
        # 1. Upload to HIDDEN storage (permanent, for cloud)
        url = f"{self.api_base}/sendDocument"
        file_caption = f"📁 {filename}\n👤 {user_phone}"
        
        try:
            with open(file_path, 'rb') as f:
                files = {'document': (filename, f)}
                data = {
                    'chat_id': storage_id,
                    'caption': file_caption,
                    'disable_notification': True
                }
                response = requests.post(url, files=files, data=data, timeout=300)
            
            if response.status_code != 200:
                return {'success': False, 'error': f"Storage upload failed"}
            
            result = response.json()
            if not result.get('ok'):
                return {'success': False, 'error': result.get('description', 'Upload failed')}
            
            storage_message = result['result']
            document = storage_message.get('document', {})
            
            # 2. Send brief notification to user's chat (will be deleted)
            if user_telegram_id and user_telegram_id != storage_id:
                notify_result = self.send_message(
                    user_telegram_id,
                    f"☁️ <b>Uploaded to Cloud!</b>\n📁 {filename}",
                    silent=True
                )
                
                # 3. Delete notification after 2 seconds (in background)
                if notify_result.get('success') and notify_result.get('message_id'):
                    def delete_later():
                        time.sleep(2)
                        self.delete_message(user_telegram_id, notify_result['message_id'])
                    
                    threading.Thread(target=delete_later, daemon=True).start()
            
            return {
                'success': True,
                'message_id': storage_message['message_id'],
                'file_id': document.get('file_id'),
                'file_size': document.get('file_size', 0),
                'storage_channel': storage_id
            }
            
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    def send_file_to_storage(self, file_path, filename, user_phone, caption=None):
        """Legacy method - redirect to new hidden upload"""
        user_data = self.get_telegram_id_by_phone(user_phone)
        user_telegram_id = user_data.get('telegram_id') if user_data else None
        return self.upload_file_hidden(file_path, filename, user_telegram_id, user_phone)
    
    def send_file_sync(self, chat_id, file_path, filename, caption=None):
        url = f"{self.api_base}/sendDocument"
        try:
            with open(file_path, 'rb') as f:
                files = {'document': (filename, f)}
                data = {'chat_id': chat_id, 'caption': caption or filename, 'disable_notification': True}
                response = requests.post(url, files=files, data=data, timeout=300)
            if response.status_code == 200:
                result = response.json()
                if result.get('ok'):
                    msg = result['result']
                    doc = msg.get('document', {})
                    return {'success': True, 'message_id': msg['message_id'], 'file_id': doc.get('file_id')}
            return {'success': False, 'error': response.text}
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    def get_file_url(self, file_id):
        url = f"{self.api_base}/getFile"
        try:
            response = requests.get(url, params={'file_id': file_id})
            if response.status_code == 200:
                result = response.json()
                if result.get('ok'):
                    file_path = result['result']['file_path']
                    return {'success': True, 'url': f"https://api.telegram.org/file/bot{self.bot_token}/{file_path}"}
            return {'success': False, 'error': response.text}
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    def delete_message(self, chat_id, message_id):
        url = f"{self.api_base}/deleteMessage"
        try:
            response = requests.post(url, data={'chat_id': chat_id, 'message_id': message_id})
            return {'success': response.status_code == 200}
        except:
            return {'success': False}


telegram_handler = TelegramHandler()
