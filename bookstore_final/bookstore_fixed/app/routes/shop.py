from flask import Blueprint, render_template, redirect, url_for, flash, request, session, jsonify
from flask_login import login_required, current_user
from app.models.book import Book
from app.models.order import Order
from app import supabase

shop_bp = Blueprint('shop', __name__)


def get_categories():
    try:
        result = supabase.table('categories').select('*').eq('is_active', True).execute()
        return result.data or []
    except Exception:
        return []


@shop_bp.route('/')
def index():
    featured_books = Book.get_featured(8)
    new_books = Book.get_all(per_page=8, sort='newest')
    categories = get_categories()
    return render_template('shop/index.html',
                           featured_books=featured_books,
                           new_books=new_books,
                           categories=categories)


@shop_bp.route('/books')
def books():
    page = request.args.get('page', 1, type=int)
    per_page = 12
    category_id = request.args.get('category', type=int)
    search = request.args.get('q', '').strip()
    sort = request.args.get('sort', 'newest')
    categories = get_categories()

    books_list = Book.get_all(page=page, per_page=per_page,
                              category_id=category_id, search=search, sort=sort)
    total = Book.count(category_id=category_id, search=search)
    total_pages = (total + per_page - 1) // per_page

    return render_template('shop/books.html',
                           books=books_list,
                           categories=categories,
                           current_category=category_id,
                           search=search,
                           sort=sort,
                           page=page,
                           total_pages=total_pages,
                           total=total)


@shop_bp.route('/books/<int:book_id>')
def book_detail(book_id):
    book = Book.get_by_id(book_id)
    if not book:
        flash('Không tìm thấy sách.', 'danger')
        return redirect(url_for('shop.books'))

    # Get related books
    related = Book.get_all(per_page=4, category_id=book.category_id)
    related = [b for b in related if b.id != book.id][:4]

    # Get reviews
    try:
        reviews_result = supabase.table('reviews').select('*, users(full_name)').eq('book_id', book_id).order('created_at', desc=True).limit(10).execute()
        reviews = reviews_result.data or []
    except Exception:
        reviews = []

    return render_template('shop/book_detail.html', book=book, related=related, reviews=reviews)


@shop_bp.route('/cart')
def cart():
    cart = session.get('cart', {})
    cart_items = []
    total = 0
    for book_id, qty in cart.items():
        book = Book.get_by_id(int(book_id))
        if book:
            subtotal = book.price * qty
            cart_items.append({'book': book, 'quantity': qty, 'subtotal': subtotal})
            total += subtotal
    return render_template('shop/cart.html', cart_items=cart_items, total=total)


@shop_bp.route('/cart/add/<int:book_id>', methods=['POST'])
def add_to_cart(book_id):
    book = Book.get_by_id(book_id)
    if not book:
        return jsonify({'success': False, 'error': 'Không tìm thấy sách'})

    # 1. Chặn ngay lập tức nếu sách đã hết hàng
    if book.stock <= 0:
        return jsonify({'success': False, 'error': 'Sản phẩm này hiện đã hết hàng'})

    qty = request.form.get('quantity', 1, type=int)
    cart = session.get('cart', {})
    key = str(book_id)

    current_qty = cart.get(key, 0)
    new_qty = current_qty + qty

    # 2. Báo lỗi cho người dùng nếu họ cố thêm số lượng vượt quá tồn kho
    if new_qty > book.stock:
        return jsonify({
            'success': False,
            'error': f'Chỉ còn {book.stock} cuốn trong kho, bạn đang có {current_qty} cuốn trong giỏ.'
        })

    # 3. Nếu hợp lệ thì mới cập nhật giỏ hàng
    cart[key] = new_qty
    session['cart'] = cart
    session.modified = True

    total_items = sum(cart.values())
    return jsonify({
        'success': True,
        'message': f'Đã thêm "{book.title}" vào giỏ',
        'cart_count': total_items
    })


@shop_bp.route('/cart/remove/<int:book_id>', methods=['POST'])
def remove_from_cart(book_id):
    cart = session.get('cart', {})
    cart.pop(str(book_id), None)
    session['cart'] = cart
    session.modified = True
    return redirect(url_for('shop.cart'))


@shop_bp.route('/cart/update', methods=['POST'])
def update_cart():
    cart = session.get('cart', {})
    for key in list(cart.keys()):
        qty = request.form.get(f'qty_{key}', type=int)
        if qty and qty > 0:
            cart[key] = qty
        elif qty == 0:
            cart.pop(key, None)
    session['cart'] = cart
    session.modified = True
    return redirect(url_for('shop.cart'))


@shop_bp.route('/checkout', methods=['GET', 'POST'])
@login_required
def checkout():
    cart = session.get('cart', {})
    if not cart:
        flash('Giỏ hàng trống!', 'warning')
        return redirect(url_for('shop.cart'))

    cart_items = []
    total = 0
    for book_id, qty in cart.items():
        book = Book.get_by_id(int(book_id))
        if book:
            subtotal = book.price * qty
            cart_items.append({
                'book_id': book.id, 'title': book.title,
                'price': book.price, 'quantity': qty,
                'subtotal': subtotal, 'cover': book.cover_image
            })
            total += subtotal

    if request.method == 'POST':
        shipping_info = {
            'name': request.form.get('shipping_name'),
            'phone': request.form.get('shipping_phone'),
            'address': request.form.get('shipping_address'),
            'note': request.form.get('note', '')
        }
        payment_method = request.form.get('payment_method', 'cod')

        order = Order.create(current_user.id, cart_items, shipping_info, payment_method, total)
        if order:
            session.pop('cart', None)
            session.modified = True
            if payment_method in ['momo', 'zalopay']:
                return redirect(url_for('payment.process', order_id=order.id, method=payment_method))
            flash(f'Đặt hàng thành công! Mã đơn hàng: {order.order_code}', 'success')
            return redirect(url_for('shop.order_detail', order_id=order.id))
        else:
            flash('Có lỗi khi đặt hàng. Vui lòng thử lại.', 'danger')

    return render_template('shop/checkout.html', cart_items=cart_items, total=total)


@shop_bp.route('/orders')
@login_required
def orders():
    page = request.args.get('page', 1, type=int)
    orders_list = Order.get_by_user(current_user.id, page=page)
    return render_template('shop/orders.html', orders=orders_list, page=page)


@shop_bp.route('/orders/<int:order_id>')
@login_required
def order_detail(order_id):
    order = Order.get_by_id(order_id)
    if not order or (order.user_id != current_user.id and not current_user.is_staff):
        flash('Không tìm thấy đơn hàng.', 'danger')
        return redirect(url_for('shop.orders'))
    return render_template('shop/order_detail.html', order=order)


@shop_bp.route('/review/<int:book_id>', methods=['POST'])
@login_required
def add_review(book_id):
    rating = request.form.get('rating', type=int)
    comment = request.form.get('comment', '').strip()
    if not rating or not (1 <= rating <= 5):
        flash('Đánh giá không hợp lệ.', 'danger')
        return redirect(url_for('shop.book_detail', book_id=book_id))
    try:
        supabase.table('reviews').upsert({
            'user_id': current_user.id,
            'book_id': book_id,
            'rating': rating,
            'comment': comment
        }).execute()
        flash('Cảm ơn bạn đã đánh giá!', 'success')
    except Exception:
        flash('Không thể gửi đánh giá. Vui lòng thử lại.', 'danger')
    return redirect(url_for('shop.book_detail', book_id=book_id))
