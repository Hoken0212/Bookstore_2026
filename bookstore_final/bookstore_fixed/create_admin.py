#!/usr/bin/env python3
"""
Script tạo tài khoản admin đầu tiên cho BookStore.
Chạy: python create_admin.py
"""
import os
import sys
from dotenv import load_dotenv

load_dotenv()

from supabase import create_client

def create_admin():
    supabase_url = os.getenv('SUPABASE_URL')
    supabase_key = os.getenv('SUPABASE_KEY')

    if not supabase_url or not supabase_key:
        print("❌ Thiếu SUPABASE_URL hoặc SUPABASE_KEY trong file .env")
        sys.exit(1)

    supabase = create_client(supabase_url, supabase_key)

    print("=" * 50)
    print("  BookStore - Tạo tài khoản Admin")
    print("=" * 50)

    email = input("Email admin: ").strip().lower()
    full_name = input("Họ và tên: ").strip()
    password = input("Mật khẩu (tối thiểu 6 ký tự): ").strip()

    if not all([email, full_name, password]):
        print("❌ Vui lòng điền đầy đủ thông tin")
        sys.exit(1)

    if len(password) < 6:
        print("❌ Mật khẩu phải có ít nhất 6 ký tự")
        sys.exit(1)

    # Check existing
    try:
        existing = supabase.table('users').select('id').eq('email', email).execute()
        if existing.data:
            print(f"❌ Email {email} đã tồn tại trong database")
            sys.exit(1)
    except Exception as e:
        print(f"❌ Lỗi kết nối Supabase: {e}")
        sys.exit(1)

    # Hash password
    from werkzeug.security import generate_password_hash
    hashed = generate_password_hash(password)
    # Insert admin
    try:
        result = supabase.table('users').insert({
            'email': email,
            'password_hash': hashed,
            'full_name': full_name,
            'role': 'admin',
            'is_active': True
        }).execute()

        if result.data:
            print("\n✅ Tạo tài khoản admin thành công!")
            print(f"   Email: {email}")
            print(f"   Tên: {full_name}")
            print(f"   Role: admin")
            print(f"\n🔗 Đăng nhập tại: http://localhost:5000/auth/login")
            print(f"🔧 Admin panel:   http://localhost:5000/admin")
        else:
            print("❌ Không thể tạo tài khoản")
    except Exception as e:
        print(f"❌ Lỗi: {e}")
        sys.exit(1)

if __name__ == '__main__':
    create_admin()
