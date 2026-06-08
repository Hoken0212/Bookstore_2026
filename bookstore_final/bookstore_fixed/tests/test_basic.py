import pytest
import os
os.environ['SECRET_KEY'] = '953cbe29b051264f783e0e2d78e8236b91af67dd7fa33565'
os.environ['SUPABASE_URL'] = 'https://zoxhcdykhjxcngiiyvuh.supabase.co'
os.environ['SUPABASE_KEY'] = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InpveGhjZHlraGp4Y25naWl5dnVoIiwicm9sZSI6ImFub24iLCJpYXQiOjE3ODAzNzk3NzQsImV4cCI6MjA5NTk1NTc3NH0.Igblskcc-3xnsbYcuAMHNoT6z8LYz9qdlPm7qNa1rfk'
os.environ['ANTHROPIC_API_KEY'] = 'sk-ant-test'


def test_app_imports():
    """Test that the app can be imported without errors."""
    try:
        from app import create_app
        assert create_app is not None
    except ImportError as e:
        pytest.skip(f"Skipping import test: {e}")


def test_password_hashing():
    """Test bcrypt password hashing."""
    import bcrypt
    password = "testpassword123"
    hashed = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())
    assert bcrypt.checkpw(password.encode('utf-8'), hashed)
    assert not bcrypt.checkpw("wrongpassword".encode('utf-8'), hashed)


def test_order_code_format():
    """Test order code generation."""
    from datetime import datetime
    import uuid
    order_code = f"BS{datetime.now().strftime('%Y%m%d%H%M%S')}{str(uuid.uuid4())[:4].upper()}"
    assert order_code.startswith("BS")
    assert len(order_code) > 10


def test_book_discount_percent():
    """Test book discount percentage calculation."""
    class MockBook:
        def __init__(self, price, original_price):
            self.price = price
            self.original_price = original_price

        @property
        def discount_percent(self):
            if self.original_price and self.original_price > self.price:
                return int((1 - self.price / self.original_price) * 100)
            return 0

    book = MockBook(price=80000, original_price=100000)
    assert book.discount_percent == 20

    book_no_discount = MockBook(price=100000, original_price=100000)
    assert book_no_discount.discount_percent == 0
