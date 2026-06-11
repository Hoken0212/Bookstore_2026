from flask import Blueprint, render_template, redirect, url_for, flash, request, jsonify
from flask_login import login_required, current_user
from functools import wraps
from app.models.book import Book
from app.models.user import User
from app.models.order import Order
from app import supabase
from app.models.generate_embeddings import generate_book_embedding_auto
import random

admin_bp = Blueprint('admin', __name__)

def admin_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if not current_user.is_authenticated or not current_user.is_admin:
            flash('Bạn không có quyền truy cập trang này.', 'danger')
            return redirect(url_for('shop.index'))
        return f(*args, **kwargs)
    return decorated


def staff_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if not current_user.is_authenticated or not current_user.is_staff:
            flash('Bạn không có quyền truy cập trang này.', 'danger')
            return redirect(url_for('shop.index'))
        return f(*args, **kwargs)
    return decorated


@admin_bp.route('/')
@admin_bp.route('/dashboard')
@login_required
@staff_required
def dashboard():
    stats = Order.get_stats()
    try:
        books_count = supabase.table('books').select('id', count='exact').eq('is_active', True).execute()
        users_count = supabase.table('users').select('id', count='exact').execute()
        stats['books'] = books_count.count or 0
        stats['users'] = users_count.count or 0
    except Exception:
        stats['books'] = 0
        stats['users'] = 0

    recent_orders = Order.get_all(per_page=5)
    return render_template('admin/dashboard.html', stats=stats, recent_orders=recent_orders)


# ---- BOOKS MANAGEMENT ----
@admin_bp.route('/books')
@login_required
@staff_required

def books():
    page = request.args.get('page', 1, type=int)
    search = request.args.get('q', '')
    books_list = Book.get_all(page=page, per_page=20, search=search)
    return render_template('admin/books.html', books=books_list, page=page, search=search)

def generate_random_isbn13(fake_vietnam_book=True):
    # 1. Ba số đầu cố định của thế giới (thường là 978 hoặc 979)
    prefix = "978"
    # 2. Mã quốc gia (Group Identifier)
    # Đặt cố định 604 nếu muốn giả lập sách Việt Nam cho đồng bộ DB của bạn
    group = "604" if fake_vietnam_book else str(random.randint(0, 9))
    # 3. Sinh ngẫu nhiên các số còn lại cho đủ 12 chữ số đầu tiên
    # (Bao gồm mã Nhà xuất bản và số thứ tự sách)
    needed_length = 12 - len(prefix) - len(group)
    remaining_digits = "".join(str(random.randint(0, 9)) for _ in range(needed_length))
    first_12 = f"{prefix}{group}{remaining_digits}"
    # 4. Thuật toán tính chữ số kiểm tra (Check Digit) cuối cùng của ISBN-13
    total = 0
    for idx, digit in enumerate(first_12):
        weight = 1 if idx % 2 == 0 else 3
        total += int(digit) * weight
    check_digit = (10 - (total % 10)) % 10
    # 5. Cắt chuỗi và định dạng dấu gạch ngang (-) cho đúng quy chuẩn hiển thị
    p1 = first_12[0:3]   # 978
    p2 = first_12[3:6]   # 604
    p3 = first_12[6:9]   # Mã NXB
    p4 = first_12[9:12]  # Mã Sách
    return f"{p1}-{p2}-{p3}-{p4}-{check_digit}"

@admin_bp.route('/books/create', methods=['GET', 'POST'])
@login_required
@staff_required
def create_book():
    categories = _get_categories()
    if request.method == 'POST':
        price_raw = request.form.get('price', '').strip()
        stock_raw = request.form.get('stock', '').strip()
        discount_raw = request.form.get('discount_percent', '').strip()

        price_val = float(price_raw) if price_raw else 0.0
        discount_val = float(discount_raw) if discount_raw else 0.0

        if discount_val > 0 and discount_val < 100:
            original_price_val = price_val / (1 - (discount_val / 100))
        else:
            original_price_val = 0.0

        # --- LOGIC TẠO EMBEDDING TỰ ĐỘNG ---
        cat_id_raw = request.form.get('category_id')
        cat_id = int(cat_id_raw) if cat_id_raw else None

        # Tìm tên thể loại từ danh sách categories để nạp cho AI
        category_name = next((c['name'] for c in categories if c['id'] == cat_id), '')

        # Gọi AI sinh Vector
        embedding_vector = generate_book_embedding_auto(
            title=request.form.get('title'),
            author=request.form.get('author'),
            category_name=category_name,
            publisher=request.form.get('publisher', ''),
            description=request.form.get('description', '')
        )
        # -----------------------------------

        data = {
            'title': request.form.get('title'),
            'author': request.form.get('author'),
            'isbn': generate_random_isbn13(),
            'price':  price_val,
            'original_price': original_price_val,
            'stock':  int(stock_raw) if stock_raw else 0,
            'description': request.form.get('description', ''),
            'cover_image': request.form.get('cover_image', ''),
            'category_id': cat_id,
            'publisher': request.form.get('publisher', ''),
            'publish_year': int(request.form.get('publish_year', 0)) or None,
            'pages': int(request.form.get('pages', 0)) or None,
            'language': request.form.get('language', 'Tiếng Việt'),
            'is_featured': request.form.get('is_featured') == 'on',
            'is_active': True,
            'embedding': embedding_vector  # Gắn Vector thẳng vào DB
        }

        book = Book.create(data)
        if book:
            flash('Thêm sách và tạo AI Embedding thành công!', 'success')
            return redirect(url_for('admin.books'))
        flash('Có lỗi khi thêm sách.', 'danger')

    return render_template('admin/book_form.html', book=None, categories=categories)

@admin_bp.route('/books/<int:book_id>/edit', methods=['GET', 'POST'])
@login_required
@staff_required
def edit_book(book_id):
    book = Book.get_by_id(book_id)
    if not book:
        flash('Không tìm thấy sách.', 'danger')
        return redirect(url_for('admin.books'))

    categories = _get_categories()
    if request.method == 'POST':
        price_raw = request.form.get('price', '').strip()
        stock_raw = request.form.get('stock', '').strip()
        discount_raw = request.form.get('discount_percent', '').strip()

        price_val = float(price_raw) if price_raw else 0.0
        discount_val = float(discount_raw) if discount_raw else 0.0

        if discount_val > 0 and discount_val < 100:
            original_price_val = price_val / (1 - (discount_val / 100))
        else:
            original_price_val = 0.0

        # --- LOGIC TẠO LẠI EMBEDDING TỰ ĐỘNG ---
        cat_id_raw = request.form.get('category_id')
        cat_id = int(cat_id_raw) if cat_id_raw else None

        category_name = next((c['name'] for c in categories if c['id'] == cat_id), '')

        embedding_vector = generate_book_embedding_auto(
            title=request.form.get('title'),
            author=request.form.get('author'),
            category_name=category_name,
            publisher=request.form.get('publisher', ''),
            description=request.form.get('description', '')
        )
        # ---------------------------------------

        updates = {
            'title': request.form.get('title'),
            'author': request.form.get('author'),
            'isbn': generate_random_isbn13(),
            'price':  price_val,
            'original_price': original_price_val,
            'stock':  int(stock_raw) if stock_raw else 0,
            'description': request.form.get('description', ''),
            'cover_image': request.form.get('cover_image', ''),
            'category_id': cat_id,
            'publisher': request.form.get('publisher', ''),
            'is_featured': request.form.get('is_featured') == 'on',
        }

        # Chỉ cập nhật cột embedding nếu API không bị lỗi trả về None
        if embedding_vector is not None:
            updates['embedding'] = embedding_vector

        book.update(**updates)
        flash('Cập nhật sách và làm mới AI Embedding thành công!', 'success')
        return redirect(url_for('admin.books'))

    return render_template('admin/book_form.html', book=book, categories=categories)

@admin_bp.route('/books/<int:book_id>/delete', methods=['POST'])
@login_required
@admin_required
def delete_book(book_id):
    book = Book.get_by_id(book_id)
    if book:
        book.delete()
        flash('Đã xóa sách.', 'success')
    return redirect(url_for('admin.books'))


# ---- ORDERS MANAGEMENT ----
@admin_bp.route('/orders')
@login_required
@staff_required
def orders():
    page = request.args.get('page', 1, type=int)
    status = request.args.get('status', '')
    orders_list = Order.get_all(page=page, per_page=20, status=status or None)
    return render_template('admin/orders.html', orders=orders_list, page=page, status=status)


@admin_bp.route('/orders/<int:order_id>')
@login_required
@staff_required
def order_detail(order_id):
    order = Order.get_by_id(order_id)
    if not order:
        flash('Không tìm thấy đơn hàng.', 'danger')
        return redirect(url_for('admin.orders'))
    return render_template('admin/order_detail.html', order=order)


@admin_bp.route('/orders/<int:order_id>/update-status', methods=['POST'])
@login_required
@staff_required
def update_order_status(order_id):
    order = Order.get_by_id(order_id)
    if order:
        status = request.form.get('status')
        if status in Order.STATUS_LABELS:
            order.update_status(status)
            flash('Cập nhật trạng thái đơn hàng thành công!', 'success')
    return redirect(url_for('admin.order_detail', order_id=order_id))


# ---- USERS MANAGEMENT (Admin only) ----
@admin_bp.route('/users')
@login_required
@admin_required
def users():
    page = request.args.get('page', 1, type=int)
    users_list = User.get_all(page=page)
    return render_template('admin/users.html', users=users_list, page=page)


@admin_bp.route('/users/<user_id>/update-role', methods=['POST'])
@login_required
@admin_required
def update_user_role(user_id):
    if str(user_id) == str(current_user.id):
        flash('Không thể thay đổi vai trò của chính mình.', 'danger')
        return redirect(url_for('admin.users'))
    role = request.form.get('role')
    if role in ['customer', 'staff', 'admin']:
        user = User.get_by_id(user_id)
        if user:
            user.update(role=role)
            flash(f'Đã cập nhật vai trò thành {role}.', 'success')
    return redirect(url_for('admin.users'))


@admin_bp.route('/users/<user_id>/toggle-active', methods=['POST'])
@login_required
@admin_required
def toggle_user_active(user_id):
    if str(user_id) == str(current_user.id):
        flash('Không thể vô hiệu hóa tài khoản của chính mình.', 'danger')
        return redirect(url_for('admin.users'))
    user = User.get_by_id(user_id)
    if user:
        user.update(is_active=not user.is_active_account)
        flash('Đã cập nhật trạng thái tài khoản.', 'success')
    return redirect(url_for('admin.users'))


# ---- CATEGORIES MANAGEMENT ----
@admin_bp.route('/categories')
@login_required
@staff_required
def categories():
    cats = _get_categories()
    return render_template('admin/categories.html', categories=cats)


@admin_bp.route('/categories/create', methods=['POST'])
@login_required
@staff_required
def create_category():
    name = request.form.get('name', '').strip()
    slug = request.form.get('slug', '').strip()
    if name:
        try:
            supabase.table('categories').insert({'name': name, 'slug': slug, 'is_active': True}).execute()
            flash('Thêm danh mục thành công!', 'success')
        except Exception:
            flash('Có lỗi khi thêm danh mục.', 'danger')
    return redirect(url_for('admin.categories'))


def _get_categories():
    try:
        result = supabase.table('categories').select('*').execute()
        return result.data or []
    except Exception:
        return []
