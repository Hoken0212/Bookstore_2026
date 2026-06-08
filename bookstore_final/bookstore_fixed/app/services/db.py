import os
from supabase import create_client, Client

_client: Client = None

def get_client() -> Client:
    global _client
    if _client is None:
        url = os.getenv('SUPABASE_URL')
        key = os.getenv('SUPABASE_KEY')
        _client = create_client(url, key)
    return _client

def get_service_client() -> Client:
    url = os.getenv('SUPABASE_URL')
    key = os.getenv('SUPABASE_SERVICE_KEY', os.getenv('SUPABASE_KEY'))
    return create_client(url, key)

# ── Users ─────────────────────────────────────────────
def get_user_by_email(email: str):
    db = get_client()
    res = db.table('users').select('*').eq('email', email).execute()
    return res.data[0] if res.data else None

def get_user_by_id(user_id: str):
    db = get_client()
    res = db.table('users').select('*').eq('id', user_id).execute()
    return res.data[0] if res.data else None

def create_user(data: dict):
    db = get_service_client()
    return db.table('users').insert(data).execute()

def update_user(user_id: str, data: dict):
    db = get_service_client()
    return db.table('users').update(data).eq('id', user_id).execute()

def get_all_users(limit=50, offset=0, search=None):
    db = get_service_client()
    q = db.table('users').select('*')
    if search:
        q = q.ilike('full_name', f'%{search}%')
    return q.order('created_at', desc=True).range(offset, offset+limit-1).execute()

# ── Books ─────────────────────────────────────────────
def get_books(limit=12, offset=0, category_id=None, search=None, sort='created_at', featured=False):
    db = get_client()
    q = db.table('books').select('*, categories(name, slug)').eq('is_active', True)
    if category_id:
        q = q.eq('category_id', category_id)
    if search:
        q = q.ilike('title', f'%{search}%')
    if featured:
        q = q.eq('is_featured', True)
    q = q.order(sort, desc=True).range(offset, offset+limit-1)
    return q.execute()

def get_book_by_slug(slug: str):
    db = get_client()
    res = db.table('books').select('*, categories(name,slug)').eq('slug', slug).execute()
    return res.data[0] if res.data else None

def get_book_by_id(book_id: str):
    db = get_service_client()
    res = db.table('books').select('*, categories(name,slug)').eq('id', book_id).execute()
    return res.data[0] if res.data else None

def create_book(data: dict):
    db = get_service_client()
    return db.table('books').insert(data).execute()

def update_book(book_id: str, data: dict):
    db = get_service_client()
    return db.table('books').update(data).eq('id', book_id).execute()

def delete_book(book_id: str):
    db = get_service_client()
    return db.table('books').update({'is_active': False}).eq('id', book_id).execute()

def count_books(category_id=None, search=None):
    db = get_client()
    q = db.table('books').select('id', count='exact').eq('is_active', True)
    if category_id:
        q = q.eq('category_id', category_id)
    if search:
        q = q.ilike('title', f'%{search}%')
    res = q.execute()
    return res.count or 0

def get_all_books_admin(limit=20, offset=0, search=None):
    db = get_service_client()
    q = db.table('books').select('*, categories(name)')
    if search:
        q = q.ilike('title', f'%{search}%')
    return q.order('created_at', desc=True).range(offset, offset+limit-1).execute()

# ── Categories ────────────────────────────────────────
def get_categories():
    db = get_client()
    return db.table('categories').select('*').order('name').execute().data

def create_category(data: dict):
    db = get_service_client()
    return db.table('categories').insert(data).execute()

def update_category(cat_id: str, data: dict):
    db = get_service_client()
    return db.table('categories').update(data).eq('id', cat_id).execute()

def delete_category(cat_id: str):
    db = get_service_client()
    return db.table('categories').delete().eq('id', cat_id).execute()

# ── Orders ────────────────────────────────────────────
def create_order(data: dict):
    db = get_service_client()
    return db.table('orders').insert(data).execute()

def get_orders_by_user(user_id: str):
    db = get_service_client()
    return db.table('orders').select('*, order_items(*, books(title, cover_image, price))').eq('user_id', user_id).order('created_at', desc=True).execute()

def get_all_orders(limit=50, offset=0, status=None):
    db = get_service_client()
    q = db.table('orders').select('*, users(full_name,email)')
    if status:
        q = q.eq('status', status)
    return q.order('created_at', desc=True).range(offset, offset+limit-1).execute()

def get_order_by_id(order_id: str):
    db = get_service_client()
    res = db.table('orders').select('*, users(full_name,email,phone), order_items(*, books(title,cover_image,price))').eq('id', order_id).execute()
    return res.data[0] if res.data else None

def update_order_status(order_id: str, status: str):
    db = get_service_client()
    return db.table('orders').update({'status': status}).eq('id', order_id).execute()

def create_order_items(items: list):
    db = get_service_client()
    return db.table('order_items').insert(items).execute()

# ── Reviews ───────────────────────────────────────────
def create_review(data: dict):
    db = get_service_client()
    return db.table('reviews').insert(data).execute()

def get_reviews_by_book(book_id: str):
    db = get_client()
    return db.table('reviews').select('*, users(full_name, avatar_url)').eq('book_id', book_id).order('created_at', desc=True).execute()

def get_all_reviews_admin():
    db = get_service_client()
    return db.table('reviews').select('*, users(full_name), books(title)').order('created_at', desc=True).execute()

def delete_review(review_id: str):
    db = get_service_client()
    return db.table('reviews').delete().eq('id', review_id).execute()

# ── Dashboard Stats ───────────────────────────────────
def get_dashboard_stats():
    db = get_service_client()
    total_books = db.table('books').select('id', count='exact').eq('is_active', True).execute().count or 0
    total_users = db.table('users').select('id', count='exact').execute().count or 0
    total_orders = db.table('orders').select('id', count='exact').execute().count or 0
    revenue = db.table('orders').select('total_amount').eq('status', 'completed').execute()
    total_revenue = sum(o['total_amount'] for o in revenue.data) if revenue.data else 0
    pending = db.table('orders').select('id', count='exact').eq('status', 'pending').execute().count or 0
    recent_orders = db.table('orders').select('*, users(full_name)').order('created_at', desc=True).limit(10).execute()
    return {
        'total_books': total_books,
        'total_users': total_users,
        'total_orders': total_orders,
        'total_revenue': total_revenue,
        'pending_orders': pending,
        'recent_orders': recent_orders.data or []
    }
