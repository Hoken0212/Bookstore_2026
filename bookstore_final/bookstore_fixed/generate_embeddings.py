#!/usr/bin/env python3
"""
generate_embeddings.py
======================
Tạo vector embedding cho toàn bộ sách trong database.
Dùng Google Gemini gemini-embedding-001 (output 384 dims).

Chạy: python generate_embeddings.py
      python generate_embeddings.py --book-id 5   # chỉ 1 cuốn
      python generate_embeddings.py --force        # overwrite existing
"""
import os
import sys
import time
import argparse
from dotenv import load_dotenv

load_dotenv()

from supabase import create_client
from google import genai
from google.genai import types

# ── Config ────────────────────────────────────────────────────────
SUPABASE_URL    = os.getenv('SUPABASE_URL', '')
SUPABASE_KEY    = os.getenv('SUPABASE_SERVICE_KEY') or os.getenv('SUPABASE_KEY', '')
GEMINI_API_KEY  = os.getenv('GEMINI_API_KEY', '')
EMBED_MODEL     = 'gemini-embedding-001'
EMBED_DIM       = 384     # phải khớp với vector(384) trong Supabase
BATCH_DELAY     = 0.5     # giây giữa mỗi API call tránh rate limit

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
ai       = genai.Client(api_key=GEMINI_API_KEY)


def make_book_text(book: dict) -> str:
    """
    Tạo text đại diện cho cuốn sách để embed.
    Kết hợp nhiều trường để embedding phong phú hơn.
    """
    parts = []
    if book.get('title'):
        parts.append(f"Tên sách: {book['title']}")
    if book.get('author'):
        parts.append(f"Tác giả: {book['author']}")
    if book.get('category_name'):
        parts.append(f"Thể loại: {book['category_name']}")
    if book.get('publisher'):
        parts.append(f"Nhà xuất bản: {book['publisher']}")
    if book.get('description'):
        # Giới hạn 500 ký tự để tránh token quá dài
        desc = book['description'][:500]
        parts.append(f"Nội dung: {desc}")
    return "\n".join(parts)


def embed_text(text: str) -> list[float] | None:
    """Gọi Gemini embedding API, trả về list 384 floats"""
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
        print(f"  ❌ Embedding error: {e}")
        return None


def store_embedding(book_id: int, embedding: list[float]) -> bool:
    """Lưu embedding vector vào Supabase"""
    try:
        supabase.table('books').update(
            {'embedding': embedding}
        ).eq('id', book_id).execute()
        return True
    except Exception as e:
        print(f"  ❌ Store error: {e}")
        return False


def get_books(book_id: int | None, force: bool) -> list[dict]:
    """Lấy danh sách sách cần embed"""
    query = supabase.table('books').select(
        'id, title, author, description, publisher, categories(name)'
    ).eq('is_active', True)

    if book_id:
        query = query.eq('id', book_id)
    elif not force:
        # Chỉ lấy sách chưa có embedding
        query = query.is_('embedding', 'null')

    result = query.execute()
    books = []
    for b in (result.data or []):
        if b.get('categories'):
            b['category_name'] = b['categories']['name']
        books.append(b)
    return books


def main():
    parser = argparse.ArgumentParser(description='Generate book embeddings')
    parser.add_argument('--book-id', type=int, help='Chỉ embed 1 cuốn sách cụ thể')
    parser.add_argument('--force', action='store_true', help='Overwrite existing embeddings')
    args = parser.parse_args()

    if not GEMINI_API_KEY:
        print("❌ Thiếu GEMINI_API_KEY trong .env")
        sys.exit(1)
    if not SUPABASE_URL:
        print("❌ Thiếu SUPABASE_URL trong .env")
        sys.exit(1)

    print("📚 BookStore — Generate Semantic Embeddings")
    print(f"   Model: {EMBED_MODEL} | Dimensions: {EMBED_DIM}")
    print("─" * 50)

    books = get_books(args.book_id, args.force)

    if not books:
        print("✅ Tất cả sách đã có embedding! (Dùng --force để tạo lại)")
        return

    print(f"📊 Sẽ tạo embedding cho {len(books)} cuốn sách\n")

    success = 0
    failed  = 0

    for i, book in enumerate(books, 1):
        title = book.get('title', 'N/A')
        bid   = book['id']

        print(f"[{i:>2}/{len(books)}] {title[:50]}", end=' ', flush=True)

        text = make_book_text(book)
        if not text.strip():
            print("⚠️  Không có text để embed, bỏ qua")
            failed += 1
            continue

        embedding = embed_text(text)
        if embedding is None:
            print("❌ Lỗi tạo embedding")
            failed += 1
            continue

        if store_embedding(bid, embedding):
            print(f"✅ ({EMBED_DIM}d)")
            success += 1
        else:
            print("❌ Lỗi lưu DB")
            failed += 1

        # Rate limit: tránh bị throttle
        if i < len(books):
            time.sleep(BATCH_DELAY)

    print("\n" + "─" * 50)
    print(f"✨ Hoàn thành! Thành công: {success} | Lỗi: {failed}")
    print(f"\n🔍 Giờ bạn có thể thử semantic search tại chatbot!")


if __name__ == '__main__':
    main()