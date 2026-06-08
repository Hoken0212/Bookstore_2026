from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from app import supabase


class User(UserMixin):
    def __init__(self, data):
        self.id = data.get('id')
        self.email = data.get('email')
        self.full_name = data.get('full_name')
        self.phone = data.get('phone')
        self.role = data.get('role', 'customer')
        self.avatar_url = data.get('avatar_url', '')
        self.is_active_account = data.get('is_active', True)
        self.created_at = data.get('created_at')

    def get_id(self):
        return str(self.id)

    @property
    def is_admin(self):
        return self.role == 'admin'

    @property
    def is_staff(self):
        return self.role in ['admin', 'staff']

    @staticmethod
    def get_by_id(user_id):
        try:
            result = supabase.table('users').select('*').eq('id', user_id).single().execute()
            if result.data:
                return User(result.data)
        except Exception:
            pass
        return None

    @staticmethod
    def get_by_email(email):
        try:
            result = supabase.table('users').select('*').eq('email', email).single().execute()
            if result.data:
                return User(result.data)
        except Exception:
            pass
        return None

    @staticmethod
    def create(email, password, full_name, phone='', role='customer'):
        hashed = generate_password_hash(password)
        try:
            result = supabase.table('users').insert({
                'email': email,
                'password_hash': hashed,
                'full_name': full_name,
                'phone': phone,
                'role': role,
                'is_active': True
            }).execute()
            if result.data:
                return User(result.data[0]), None
        except Exception as e:
            return None, str(e)
        return None, 'Không thể tạo tài khoản'

    @staticmethod
    def verify_password(email, password):
        try:
            result = supabase.table('users').select('*').eq('email', email).single().execute()
            if result.data:
                stored_hash = result.data.get('password_hash', '')
                if check_password_hash(stored_hash, password):
                    return User(result.data)
        except Exception:
            pass
        return None

    @staticmethod
    def get_all(page=1, per_page=20):
        offset = (page - 1) * per_page
        try:
            result = supabase.table('users').select('*').order('created_at', desc=True).range(offset, offset + per_page - 1).execute()
            return [User(u) for u in result.data] if result.data else []
        except Exception:
            return []

    def update(self, **kwargs):
        try:
            result = supabase.table('users').update(kwargs).eq('id', self.id).execute()
            return result.data is not None
        except Exception:
            return False