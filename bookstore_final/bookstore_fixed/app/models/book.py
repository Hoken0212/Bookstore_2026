from app import supabase


class Book:
    def __init__(self, data):
        self.id = data.get('id')
        self.title = data.get('title')
        self.author = data.get('author')
        self.isbn = data.get('isbn')
        self.price = data.get('price', 0)
        self.original_price = data.get('original_price', 0)
        self.stock = data.get('stock', 0)
        self.description = data.get('description', '')
        self.cover_image = data.get('cover_image') or '/static/images/no-cover.png'
        self.category_id = data.get('category_id')
        self.category_name = data.get('category_name', '')
        self.publisher = data.get('publisher', '')
        self.publish_year = data.get('publish_year')
        self.pages = data.get('pages')
        self.language = data.get('language', 'Tiếng Việt')
        self.rating = data.get('rating', 0)
        self.review_count = data.get('review_count', 0)
        self.is_featured = data.get('is_featured', False)
        self.is_active = data.get('is_active', True)
        self.created_at = data.get('created_at')

    @property
    def discount_percent(self):
        if self.original_price and self.original_price > self.price:
            return int((1 - self.price / self.original_price) * 100)
        return 0

    @staticmethod
    def get_all(page=1, per_page=12, category_id=None, search=None, sort='newest'):
        offset = (page - 1) * per_page
        try:
            query = supabase.table('books').select(
                '*, categories(name)'
            ).eq('is_active', True)

            if category_id:
                query = query.eq('category_id', category_id)
            if search:
                query = query.or_(f'title.ilike.%{search}%,author.ilike.%{search}%')

            if sort == 'price_asc':
                query = query.order('price', desc=False)
            elif sort == 'price_desc':
                query = query.order('price', desc=True)
            elif sort == 'popular':
                query = query.order('review_count', desc=True)
            else:
                query = query.order('created_at', desc=True)

            result = query.range(offset, offset + per_page - 1).execute()
            books = []
            for b in (result.data or []):
                if b.get('categories'):
                    b['category_name'] = b['categories']['name']
                books.append(Book(b))
            return books
        except Exception:
            return []

    @staticmethod
    def get_by_id(book_id):
        try:
            result = supabase.table('books').select('*, categories(name)').eq('id', book_id).single().execute()
            if result.data:
                data = result.data
                if data.get('categories'):
                    data['category_name'] = data['categories']['name']
                return Book(data)
        except Exception:
            pass
        return None

    @staticmethod
    def get_featured(limit=8):
        try:
            result = supabase.table('books').select('*, categories(name)').eq('is_featured', True).eq('is_active', True).limit(limit).execute()
            books = []
            for b in (result.data or []):
                if b.get('categories'):
                    b['category_name'] = b['categories']['name']
                books.append(Book(b))
            return books
        except Exception:
            return []

    @staticmethod
    def create(data):
        try:
            result = supabase.table('books').insert(data).execute()
            return Book(result.data[0]) if result.data else None
        except Exception as e:
            return None

    def update(self, **kwargs):
        try:
            result = supabase.table('books').update(kwargs).eq('id', self.id).execute()
            return result.data is not None
        except Exception:
            return False

    def delete(self):
        try:
            supabase.table('books').update({'is_active': False}).eq('id', self.id).execute()
            return True
        except Exception:
            return False

    @staticmethod
    def count(category_id=None, search=None):
        try:
            query = supabase.table('books').select('id', count='exact').eq('is_active', True)
            if category_id:
                query = query.eq('category_id', category_id)
            if search:
                query = query.or_(f'title.ilike.%{search}%,author.ilike.%{search}%')
            result = query.execute()
            return result.count or 0
        except Exception:
            return 0
