# 📚 BookStore - Nhà Sách Trực Tuyến

Ứng dụng web nhà sách trực tuyến hiện đại, được xây dựng với Flask, Supabase, tích hợp AI Gemini, thanh toán MoMo & ZaloPay, và triển khai qua Docker + GitHub Actions.

---

## ✨ Tính năng

### 🛍️ Cửa hàng
- Trang chủ với sách nổi bật, sách mới, danh mục
- Danh sách sách với lọc theo danh mục, tìm kiếm, sắp xếp
- Trang chi tiết sách với đánh giá, gợi ý sách liên quan
- Giỏ hàng (session-based)
- Checkout + đặt hàng
- Theo dõi trạng thái đơn hàng

### 🤖 AI Features (Claude Gemni)
- **Chatbot tư vấn sách** — hỏi AI để được gợi ý sách phù hợp
- **Tóm tắt nội dung sách** — AI tóm tắt mô tả trong 3-4 câu
- **Phân tích đánh giá** — AI phân tích sentiment từ đánh giá độc giả
- **Search suggestions** — gợi ý tìm kiếm theo thời gian thực

### 💳 Thanh toán
| Phương thức | Mô tả |
|-------------|-------|
| 💵 COD | Thanh toán khi nhận hàng |
| 💜 MoMo | QR code / Deep link MoMo |
| 💚 ZaloPay | QR code ZaloPay |

### 👤 Tài khoản
- Đăng ký / Đăng nhập bằng email & password
- Hồ sơ cá nhân
- Lịch sử đơn hàng
- Đánh giá sách (1-5 sao + bình luận)

### 🔧 Admin Panel (`/admin`)

| Role | Quyền truy cập |
|------|----------------|
| `admin` | Toàn bộ: sách, đơn hàng, người dùng, phân quyền |
| `staff` | Sách, đơn hàng, danh mục |
| `customer` | Không có quyền admin |

**Tính năng admin:**
- Dashboard tổng quan (doanh thu, đơn hàng, sách, người dùng)
- CRUD sách đầy đủ
- Quản lý danh mục
- Quản lý & cập nhật trạng thái đơn hàng
- Quản lý người dùng + phân quyền role (admin only)
- Kích hoạt / vô hiệu hóa tài khoản

---

## 🚀 Cài đặt & Chạy

### Yêu cầu
- Python 3.11+
- Docker & Docker Compose
- Tài khoản [Supabase](https://supabase.com)
- API key [Gemini](https://aistudio.google.com/)

### 1. Clone & cấu hình môi trường

```bash
git clone https://github.com/your-org/bookstore.git
cd bookstore

# Sao chép file env mẫu
cp .env.example .env
```

Chỉnh sửa `.env`:
```env
SECRET_KEY=your-super-secret-key
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_KEY=your-supabase-anon-key
GEMINI_API_KEY=sk-ant-...
MOMO_PARTNER_CODE=...
MOMO_ACCESS_KEY=...
MOMO_SECRET_KEY=...
ZALOPAY_APP_ID=...
ZALOPAY_KEY1=...
ZALOPAY_KEY2=...
APP_URL=http://localhost:5000
```

### 2. Tạo database Supabase

1. Đăng nhập [Supabase Dashboard](https://supabase.com)
2. Tạo project mới
3. Vào **SQL Editor** → chạy file `migrations/001_initial_schema.sql`
4. Lấy `Project URL` và `anon public key` từ **Settings → API**

### 3. Tạo tài khoản admin

Chạy script tạo admin sau khi khởi động app:

```bash
python create_admin.py
```

Hoặc thêm trực tiếp vào Supabase SQL Editor:
```sql
INSERT INTO users (email, password_hash, full_name, role)
VALUES (
    'admin@bookstore.vn',
    '$2b$12$...', -- bcrypt hash của password
    'Administrator',
    'admin'
);
```

### 4. Chạy với Docker (khuyến nghị)

```bash
# Build và khởi động
docker-compose up -d --build

# Xem logs
docker-compose logs -f web

# Dừng
docker-compose down
```

Truy cập: http://localhost

### 5. Chạy local (development)

```bash
# Tạo virtual environment
python -m venv venv
source venv/bin/activate  # Linux/Mac
# venv\Scripts\activate   # Windows

# Cài dependencies
pip install -r requirements.txt

# Chạy app
python run.py
```

Truy cập: http://localhost:5000

---

## 🗂️ Cấu trúc dự án

```
bookstore/
├── app/
│   ├── __init__.py          # App factory, Supabase client
│   ├── models/
│   │   ├── user.py          # User model + bcrypt auth
│   │   ├── book.py          # Book model
│   │   └── order.py         # Order model
│   ├── routes/
│   │   ├── auth.py          # Login, register, profile
│   │   ├── shop.py          # Storefront, cart, checkout
│   │   ├── admin.py         # Admin panel (RBAC)
│   │   ├── api.py           # AI APIs, search, cart count
│   │   └── payment.py       # MoMo, ZaloPay, QR generation
│   ├── templates/
│   │   ├── base.html        # Layout chính + AI chatbot
│   │   ├── auth/            # Login, register, profile
│   │   ├── shop/            # Index, books, detail, cart...
│   │   └── admin/           # Dashboard, books, orders, users
│   └── static/
│       ├── css/
│       ├── js/
│       └── images/
├── migrations/
│   └── 001_initial_schema.sql
├── .github/
│   └── workflows/
│       └── deploy.yml       # CI/CD pipeline
├── Dockerfile
├── docker-compose.yml
├── nginx.conf
├── requirements.txt
├── run.py
└── .env.example
```

---

## 🔄 CI/CD với GitHub Actions

Pipeline tự động:

```
Push to develop → Test → Build → Deploy Staging
Push to main    → Test → Build → Deploy Production
```

### GitHub Secrets cần thiết

| Secret            | Mô tả                      |
|-------------------|----------------------------|
| `SUPABASE_URL`    | URL Supabase project       |
| `SUPABASE_KEY`    | Supabase anon key          |
| `GEMINI_API_KEY`  | Gemni Google API key       |
| `PROD_HOST`       | IP server production       |
| `PROD_USER`       | SSH user production        |
| `PROD_SSH_KEY`    | SSH private key production |
| `STAGING_HOST`    | IP server staging          |
| `STAGING_USER`    | SSH user staging           |
| `STAGING_SSH_KEY` | SSH private key staging    |

---

## 🏦 Tích hợp thanh toán

### MoMo
- Tích hợp qua MoMo Payment Gateway API v2
- Tạo QR code từ `payUrl` trả về
- Fallback: QR tĩnh với số điện thoại MoMo
- IPN endpoint: `POST /payment/ipn/momo`

### ZaloPay
- Tích hợp qua ZaloPay OpenAPI v2
- Tạo QR code từ `order_url`
- Callback: `GET /payment/callback/zalopay`

---

## 🔒 Bảo mật

- Mật khẩu mã hóa bcrypt
- CSRF protection (Flask-WTF)
- Rate limiting qua Nginx
- Row Level Security (RLS) trên Supabase
- RBAC (Role-Based Access Control): admin / staff / customer
- Session-based cart (server-side)
- Security headers qua Nginx

---

## 📝 API Endpoints

| Method | Endpoint | Mô tả |
|--------|----------|-------|
| POST | `/api/ai/recommend` | AI gợi ý sách |
| GET | `/api/ai/summarize/<id>` | AI tóm tắt sách |
| GET | `/api/ai/review-sentiment/<id>` | Phân tích đánh giá |
| GET | `/api/search/suggestions?q=` | Gợi ý tìm kiếm |
| GET | `/api/cart/count` | Số lượng giỏ hàng |

---

## 🤝 Đóng góp

1. Fork repo
2. Tạo branch: `git checkout -b feature/ten-tinh-nang`
3. Commit: `git commit -m "feat: thêm tính năng X"`
4. Push: `git push origin feature/ten-tinh-nang`
5. Tạo Pull Request vào `develop`

---

## 📄 License

MIT License © 2025 BookStore
