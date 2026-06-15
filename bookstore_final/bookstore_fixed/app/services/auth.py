import bcrypt
import uuid
from datetime import datetime
from app.services.db import get_user_by_email, create_user, get_user_by_id


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()


def check_password(password: str, hashed: str) -> bool:
    return bcrypt.checkpw(password.encode(), hashed.encode())


def register_user(full_name: str, email: str, password: str, phone: str = None):
    existing = get_user_by_email(email)
    if existing:
        return None, "Email đã được sử dụng rồi"

    user_data = {
        'id': str(uuid.uuid4()),
        'full_name': full_name,
        'email': email,
        'password_hash': hash_password(password),
        'phone': phone,
        'role': 'customer',
        'is_active': True,
        'created_at': datetime.utcnow().isoformat()
    }
    result = create_user(user_data)
    if result.data:
        return result.data[0], None
    return None, "Lỗi tạo tài khoản"


def login_user(email: str, password: str):
    user = get_user_by_email(email)
    if not user:
        return None, "Email không tồn tại"
    if not user.get('is_active'):
        return None, "Tài khoản đã bị khóa"
    if not check_password(password, user['password_hash']):
        return None, "Mật khẩu không đúng"
    return user, None


class UserSession:
    """Lightweight user object for session management"""
    def __init__(self, user_dict):
        self.id = user_dict['id']
        self.email = user_dict['email']
        self.full_name = user_dict['full_name']
        self.role = user_dict.get('role', 'customer')
        self.avatar_url = user_dict.get('avatar_url', '')
        self.is_active = user_dict.get('is_active', True)
        self.is_authenticated = True
        self.is_anonymous = False

    def get_id(self):
        return str(self.id)

    def is_admin(self):
        return self.role in ('admin', 'staff')

    def is_super_admin(self):
        return self.role == 'admin'
