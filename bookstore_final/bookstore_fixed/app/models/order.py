from app import supabase
import uuid
from datetime import datetime


class Order:
    STATUS_PENDING = 'pending'
    STATUS_PAID = 'paid'
    STATUS_PROCESSING = 'processing'
    STATUS_SHIPPED = 'shipped'
    STATUS_DELIVERED = 'delivered'
    STATUS_CANCELLED = 'cancelled'

    STATUS_LABELS = {
        'pending': ('Chờ thanh toán', 'warning'),
        'paid': ('Đã thanh toán', 'info'),
        'processing': ('Đang xử lý', 'primary'),
        'shipped': ('Đang giao', 'info'),
        'delivered': ('Đã giao', 'success'),
        'cancelled': ('Đã hủy', 'danger'),
    }

    def __init__(self, data):
        self.id = data.get('id')
        self.order_code = data.get('order_code')
        self.user_id = data.get('user_id')
        self.user_name = data.get('user_name', '')
        self.user_email = data.get('user_email', '')
        self.total_amount = data.get('total_amount', 0)
        self.status = data.get('status', 'pending')
        self.payment_method = data.get('payment_method', 'cod')
        self.payment_status = data.get('payment_status', 'unpaid')
        self.shipping_address = data.get('shipping_address', '')
        self.shipping_phone = data.get('shipping_phone', '')
        self.shipping_name = data.get('shipping_name', '')
        self.note = data.get('note', '')
        self.items = data.get('items', [])
        self.created_at = data.get('created_at')

    @property
    def status_label(self):
        return self.STATUS_LABELS.get(self.status, ('Không rõ', 'secondary'))

    @staticmethod
    def create(user_id, cart_items, shipping_info, payment_method, total):
        order_code = f"BS{datetime.now().strftime('%Y%m%d%H%M%S')}{str(uuid.uuid4())[:4].upper()}"
        try:
            order_result = supabase.table('orders').insert({
                'order_code': order_code,
                'user_id': user_id,
                'total_amount': total,
                'status': 'pending',
                'payment_method': payment_method,
                'payment_status': 'unpaid',
                'shipping_name': shipping_info.get('name'),
                'shipping_phone': shipping_info.get('phone'),
                'shipping_address': shipping_info.get('address'),
                'note': shipping_info.get('note', '')
            }).execute()

            if not order_result.data:
                return None

            order_id = order_result.data[0]['id']

            items_to_insert = []
            for item in cart_items:
                items_to_insert.append({
                    'order_id': order_id,
                    'book_id': item['book_id'],
                    'quantity': item['quantity'],
                    'price': item['price'],
                    'title': item['title']
                })

            supabase.table('order_items').insert(items_to_insert).execute()

            # Update stock
            for item in cart_items:
                supabase.rpc('decrement_stock', {
                    'book_id': item['book_id'],
                    'qty': item['quantity']
                }).execute()

            return Order(order_result.data[0])
        except Exception as e:
            print(f"Order create error: {e}")
            return None

    @staticmethod
    def get_by_id(order_id):
        try:
            order_result = supabase.table('orders').select('*').eq('id', order_id).single().execute()
            if order_result.data:
                order = order_result.data
                items_result = supabase.table('order_items').select('*, books(cover_image)').eq('order_id', order_id).execute()
                order['items'] = items_result.data or []
                return Order(order)
        except Exception:
            pass
        return None

    @staticmethod
    def get_by_user(user_id, page=1, per_page=10):
        offset = (page - 1) * per_page
        try:
            result = supabase.table('orders').select('*').eq('user_id', user_id).order('created_at', desc=True).range(offset, offset + per_page - 1).execute()
            return [Order(o) for o in (result.data or [])]
        except Exception:
            return []

    @staticmethod
    def get_all(page=1, per_page=20, status=None):
        offset = (page - 1) * per_page
        try:
            query = supabase.table('orders').select('*, users(full_name, email)')
            if status:
                query = query.eq('status', status)
            result = query.order('created_at', desc=True).range(offset, offset + per_page - 1).execute()
            orders = []
            for o in (result.data or []):
                if o.get('users'):
                    o['user_name'] = o['users']['full_name']
                    o['user_email'] = o['users']['email']
                orders.append(Order(o))
            return orders
        except Exception:
            return []

    def update_status(self, status):
        try:
            supabase.table('orders').update({'status': status}).eq('id', self.id).execute()
            self.status = status
            return True
        except Exception:
            return False

    @staticmethod
    def get_stats():
        try:
            total_result = supabase.table('orders').select('total_amount').eq('status', 'delivered').execute()
            revenue = sum(o['total_amount'] for o in (total_result.data or []))
            count_result = supabase.table('orders').select('id', count='exact').execute()
            pending_result = supabase.table('orders').select('id', count='exact').eq('status', 'pending').execute()
            return {
                'revenue': revenue,
                'total_orders': count_result.count or 0,
                'pending_orders': pending_result.count or 0,
            }
        except Exception:
            return {'revenue': 0, 'total_orders': 0, 'pending_orders': 0}
