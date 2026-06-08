from flask import Blueprint, render_template, redirect, url_for, flash, request, session
from flask_login import login_user, logout_user, login_required, current_user
from app.models.user import User

auth_bp = Blueprint('auth', __name__)


@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('shop.index'))

    if request.method == 'POST':
        email = request.form.get('email', '').strip().lower()
        password = request.form.get('password', '')
        remember = request.form.get('remember') == 'on'

        if not email or not password:
            flash('Vui lòng nhập đầy đủ thông tin.', 'danger')
            return render_template('auth/login.html')

        user = User.verify_password(email, password)
        if user:
            if not user.is_active_account:
                flash('Tài khoản của bạn đã bị vô hiệu hóa.', 'danger')
                return render_template('auth/login.html')
            login_user(user, remember=remember)
            next_page = request.args.get('next')
            flash(f'Chào mừng trở lại, {user.full_name}!', 'success')
            if next_page:
                return redirect(next_page)
            if user.is_admin:
                return redirect(url_for('admin.dashboard'))
            return redirect(url_for('shop.index'))
        else:
            flash('Email hoặc mật khẩu không đúng.', 'danger')

    return render_template('auth/login.html')


@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('shop.index'))

    if request.method == 'POST':
        email = request.form.get('email', '').strip().lower()
        password = request.form.get('password', '')
        confirm_password = request.form.get('confirm_password', '')
        full_name = request.form.get('full_name', '').strip()
        phone = request.form.get('phone', '').strip()

        errors = []
        if not all([email, password, full_name]):
            errors.append('Vui lòng điền đầy đủ thông tin bắt buộc.')
        if len(password) < 6:
            errors.append('Mật khẩu phải có ít nhất 6 ký tự.')
        if password != confirm_password:
            errors.append('Mật khẩu xác nhận không khớp.')
        if User.get_by_email(email):
            errors.append('Email này đã được đăng ký.')

        if errors:
            for error in errors:
                flash(error, 'danger')
            return render_template('auth/register.html')

        user, error = User.create(email, password, full_name, phone)
        if user:
            login_user(user)
            flash('Đăng ký thành công! Chào mừng bạn đến với BookStore.', 'success')
            return redirect(url_for('shop.index'))
        else:
            flash(f'Lỗi: {error}', 'danger')

    return render_template('auth/register.html')


@auth_bp.route('/logout')
@login_required
def logout():
    logout_user()
    flash('Bạn đã đăng xuất.', 'info')
    return redirect(url_for('shop.index'))


@auth_bp.route('/profile', methods=['GET', 'POST'])
@login_required
def profile():
    if request.method == 'POST':
        full_name = request.form.get('full_name', '').strip()
        phone = request.form.get('phone', '').strip()
        current_user.update(full_name=full_name, phone=phone)
        flash('Cập nhật thông tin thành công!', 'success')
        return redirect(url_for('auth.profile'))
    return render_template('auth/profile.html')