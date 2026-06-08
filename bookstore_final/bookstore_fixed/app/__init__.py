import os
from flask import Flask
from flask_login import LoginManager
from dotenv import load_dotenv
from supabase import create_client, Client

load_dotenv()

login_manager = LoginManager()
supabase: Client = None


def create_app():
    app = Flask(__name__)
    app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'dev-secret-key')
    app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024

    global supabase
    supabase = create_client(
        os.getenv('SUPABASE_URL', ''),
        os.getenv('SUPABASE_SERVICE_KEY') or os.getenv('SUPABASE_KEY', '')
    )

    login_manager.init_app(app)
    login_manager.login_view = 'auth.login'
    login_manager.login_message = 'Vui lòng đăng nhập để tiếp tục.'
    login_manager.login_message_category = 'info'

    from app.models.user import User

    @login_manager.user_loader
    def load_user(user_id):
        return User.get_by_id(user_id)

    from app.routes.auth import auth_bp
    from app.routes.shop import shop_bp
    from app.routes.admin import admin_bp
    from app.routes.api import api_bp
    from app.routes.payment import payment_bp

    app.register_blueprint(auth_bp, url_prefix='/auth')
    app.register_blueprint(shop_bp, url_prefix='/')
    app.register_blueprint(admin_bp, url_prefix='/admin')
    app.register_blueprint(api_bp, url_prefix='/api')
    app.register_blueprint(payment_bp, url_prefix='/payment')

    @app.route('/health')
    def health():
        return {'status': 'ok'}, 200

    @app.errorhandler(404)
    def not_found(e):
        return {'error': 'Not found'}, 404

    @app.errorhandler(500)
    def server_error(e):
        return {'error': 'Server error'}, 500

    return app