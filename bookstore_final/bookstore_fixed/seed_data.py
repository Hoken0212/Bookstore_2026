#!/usr/bin/env python3
"""
Script seed dữ liệu mẫu cho BookStore.
Chạy: python seed_data.py
"""
import os
import sys
from dotenv import load_dotenv

load_dotenv()

from supabase import create_client

supabase = create_client(
    os.getenv('SUPABASE_URL', ''),
    os.getenv('SUPABASE_SERVICE_KEY') or os.getenv('SUPABASE_KEY', '')
)

SAMPLE_BOOKS = [
    {
        "title": "Đắc Nhân Tâm",
        "author": "Dale Carnegie",
        "isbn": "978-604-77-4965-9",
        "price": 79000,
        "original_price": 108000,
        "stock": 120,
        "category_id": 5,
        "publisher": "NXB Tổng hợp TPHCM",
        "publish_year": 2023,
        "pages": 320,
        "language": "Tiếng Việt",
        "is_featured": True,
        "cover_image": "https://salt.tikicdn.com/cache/w1200/ts/product/45/05/fd/fc814b4d928829a578d90e7a3e7ea74d.jpg",
        "description": "Đắc Nhân Tâm là cuốn sách nổi tiếng nhất, bán chạy nhất và có ảnh hưởng nhất của mọi thời đại. Tác phẩm đã giúp hàng triệu người thay đổi cuộc đời và đạt được thành công trong cuộc sống lẫn sự nghiệp.",
    },
    {
        "title": "Nhà Giả Kim",
        "author": "Paulo Coelho",
        "isbn": "978-604-2-30-448-5",
        "price": 69000,
        "original_price": 88000,
        "stock": 85,
        "category_id": 1,
        "publisher": "NXB Hội Nhà Văn",
        "publish_year": 2022,
        "pages": 228,
        "language": "Tiếng Việt",
        "is_featured": True,
        "cover_image": "https://salt.tikicdn.com/cache/w1200/ts/product/45/d8/96/6904a81393c86ef4fecb5e26b494eb9e.jpg",
        "description": "Nhà Giả Kim kể về cuộc hành trình của Santiago, một cậu bé chăn cừu người Andalucia với ước mơ tìm đến kho báu ở chân những kim tự tháp Ai Cập.",
    },
    {
        "title": "Tư Duy Nhanh Và Chậm",
        "author": "Daniel Kahneman",
        "isbn": "978-604-2-23-672-8",
        "price": 155000,
        "original_price": 198000,
        "stock": 45,
        "category_id": 5,
        "publisher": "NXB Thế Giới",
        "publish_year": 2023,
        "pages": 636,
        "language": "Tiếng Việt",
        "is_featured": True,
        "cover_image": "https://salt.tikicdn.com/cache/w1200/ts/product/7b/b3/5b/399f2532c38ee1b0e7c37369e22fcae1.jpg",
        "description": "Cuốn sách tiết lộ cơ chế hoạt động của tư duy con người với hai hệ thống: Hệ thống 1 - nhanh, trực giác và cảm xúc; Hệ thống 2 - chậm, có chủ ý và logic.",
    },
    {
        "title": "Sapiens: Lược Sử Loài Người",
        "author": "Yuval Noah Harari",
        "isbn": "978-604-77-3200-2",
        "price": 185000,
        "original_price": 239000,
        "stock": 60,
        "category_id": 4,
        "publisher": "NXB Tri Thức",
        "publish_year": 2022,
        "pages": 560,
        "language": "Tiếng Việt",
        "is_featured": True,
        "cover_image": "https://salt.tikicdn.com/cache/w1200/ts/product/36/f2/be/89b62a350a93af7b0caccbb5c0aec2e8.jpg",
        "description": "Sapiens dẫn dắt chúng ta qua toàn bộ lịch sử loài người, từ nguồn gốc của loài Homo Sapiens đến thế giới ngày nay, xem xét các quyết định quan trọng đã định hình nên xã hội loài người.",
    },
    {
        "title": "Atomic Habits - Thói Quen Nguyên Tử",
        "author": "James Clear",
        "isbn": "978-604-2-24-989-6",
        "price": 109000,
        "original_price": 139000,
        "stock": 95,
        "category_id": 5,
        "publisher": "NXB Lao Động",
        "publish_year": 2023,
        "pages": 380,
        "language": "Tiếng Việt",
        "is_featured": True,
        "cover_image": "https://salt.tikicdn.com/cache/w1200/ts/product/fd/b4/d6/b5b8d7c443e49ac91e2d53cf4be4e5a9.jpg",
        "description": "Atomic Habits cung cấp cho bạn một khuôn khổ đã được kiểm chứng để cải thiện – mỗi ngày một chút.",
    },
    {
        "title": "Người Giàu Có Nhất Thành Babylon",
        "author": "George S. Clason",
        "isbn": "978-604-2-18-552-7",
        "price": 65000,
        "original_price": 85000,
        "stock": 75,
        "category_id": 2,
        "publisher": "NXB Lao Động - Xã Hội",
        "publish_year": 2022,
        "pages": 256,
        "language": "Tiếng Việt",
        "is_featured": False,
        "cover_image": "https://salt.tikicdn.com/cache/w1200/ts/product/2c/40/58/4e0e4db9e0dc6d2aa8c14f41a5fdb77c.jpg",
        "description": "Quyển sách này chứa đựng những bài học tài chính vô giá được truyền đạt qua những câu chuyện hấp dẫn, sinh động từ thành phố Babylon cổ đại.",
    },
    {
        "title": "Dune - Xứ Cát",
        "author": "Frank Herbert",
        "isbn": "978-604-2-30-001-2",
        "price": 195000,
        "original_price": 249000,
        "stock": 30,
        "category_id": 1,
        "publisher": "NXB Trẻ",
        "publish_year": 2021,
        "pages": 788,
        "language": "Tiếng Việt",
        "is_featured": False,
        "cover_image": "https://salt.tikicdn.com/cache/w1200/ts/product/d6/53/08/2ee5f0af7d7b6cb50e8b2fc6f16d7226.jpg",
        "description": "Dune là tác phẩm khoa học viễn tưởng vĩ đại nhất mọi thời đại, kể về cuộc phiêu lưu của chàng trai trẻ Paul Atreides trên hành tinh sa mạc Arrakis.",
    },
    {
        "title": "Clean Code - Code Sạch",
        "author": "Robert C. Martin",
        "isbn": "978-604-2-25-001-3",
        "price": 220000,
        "original_price": 280000,
        "stock": 40,
        "category_id": 3,
        "publisher": "NXB Khoa học Kỹ thuật",
        "publish_year": 2022,
        "pages": 464,
        "language": "Tiếng Việt",
        "is_featured": True,
        "cover_image": "https://salt.tikicdn.com/cache/w1200/ts/product/e8/a3/73/28fc5b59dafe3eef7b70b5e4fb73bfc2.jpg",
        "description": "Hướng dẫn thực tiễn cho các lập trình viên viết code sạch, dễ đọc, dễ bảo trì và dễ mở rộng.",
    },
]


def seed_books():
    print("🌱 Bắt đầu seed dữ liệu sách...")
    success = 0
    for book in SAMPLE_BOOKS:
        try:
            result = supabase.table('books').insert({**book, 'is_active': True}).execute()
            if result.data:
                print(f"  ✅ {book['title']}")
                success += 1
        except Exception as e:
            print(f"  ⚠️  {book['title']}: {e}")

    print(f"\n✨ Đã thêm {success}/{len(SAMPLE_BOOKS)} cuốn sách")


if __name__ == '__main__':
    seed_books()
