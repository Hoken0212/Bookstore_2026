import os
from google import genai
from google.genai import types
import time
import re

# Khởi tạo client một lần duy nhất
ai = genai.Client(api_key=os.getenv('GEMINI_API_KEY'))

EMBED_MODEL = 'gemini-embedding-001'
EMBED_DIM = 384

def strip_html_tags(text):
    """Xóa các thẻ HTML (như <p>, <b>) nếu có trong description"""
    clean = re.compile('<.*?>')
    return re.sub(clean, '', text)

def make_book_text(book: dict) -> str:
    parts = []
    if book.get('title'): parts.append(f"Tên sách: {book['title']}")
    if book.get('author'): parts.append(f"Tác giả: {book['author']}")
    if book.get('category_name'): parts.append(f"Thể loại: {book['category_name']}")
    if book.get('publisher'): parts.append(f"Nhà xuất bản: {book['publisher']}")
    if book.get('language'): parts.append(f"Ngôn ngữ: {book['language']}")
    if book.get('publish_year'): parts.append(f"Năm xuất bản: {book['publish_year']}")

    if book.get('description'):
        # Xóa HTML rác và giữ lại tới 4000 ký tự (AI đủ sức đọc)
        desc = strip_html_tags(book['description'])[:4000]
        parts.append(f"Nội dung: {desc}")

    return "\n".join(parts)

def embed_text(text: str, max_retries=3) -> list[float] | None:
    """Thêm cơ chế tự động gọi lại (Retry) khi API gặp lỗi mạng"""
    for attempt in range(max_retries):
        try:
            result = ai.models.embed_content(
                model=EMBED_MODEL,
                contents=text,
                config=types.EmbedContentConfig(
                    task_type='SEMANTIC_SIMILARITY',
                    output_dimensionality=EMBED_DIM,
                )
            )
            return result.embeddings[0].values
        except Exception as e:
            print(f"  ⚠️ Lỗi API (Lần {attempt + 1}/{max_retries}): {e}")
            if attempt < max_retries - 1:
                time.sleep(2) # Nghỉ 2 giây rồi thử lại
            else:
                return None

def get_books(book_id: int | None, force: bool) -> list[dict]:
    """Sử dụng Pagination để vượt qua giới hạn 1000 dòng của Supabase"""
    all_books = []
    limit = 1000
    offset = 0

    while True:
        # Bổ sung lấy thêm 'language' và 'publish_year'
        query = supabase.table('books').select(
            'id, title, author, description, publisher, language, publish_year, categories(name)'
        ).eq('is_active', True)

        if book_id:
            query = query.eq('id', book_id)
        elif not force:
            query = query.is_('embedding', 'null')

        # Gắn Range để phân trang
        query = query.range(offset, offset + limit - 1)
        result = query.execute()

        data = result.data or []
        for b in data:
            if b.get('categories'):
                b['category_name'] = b['categories']['name']
            all_books.append(b)

        # Nếu data trả về ít hơn limit nghĩa là đã lặp hết DB hoặc là đang tìm 1 cuốn (book_id)
        if len(data) < limit:
            break

        offset += limit

    return all_books

def generate_book_embedding_auto(title, author, category_name, publisher, description):
    """
    Hàm cầu nối dùng cho trang Admin gọi vào khi thêm/sửa sách
    """
    # Tạo một dictionary giả lập giống với dữ liệu từ Supabase
    book_data = {
        'title': title,
        'author': author,
        'category_name': category_name,
        'publisher': publisher,
        'description': description
    }

    # 1. Dùng hàm make_book_text có sẵn để gom chữ
    text_to_embed = make_book_text(book_data)

    if not text_to_embed.strip():
        return None

    # 2. Dùng hàm embed_text có sẵn để gọi AI
    return embed_text(text_to_embed)