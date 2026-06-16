# 📚 Mọt&Mèo - Nhà Sách Trực Tuyến

Ứng dụng web nhà sách trực tuyến hiện đại, được xây dựng với Flask, Supabase (pgvector + HNSW), tích hợp AI Google Gemini (chatbot tư vấn + tìm kiếm ngữ nghĩa "vibe search"), thanh toán QR theo chuẩn VietQR (tương thích MoMo, ZaloPay và mọi app ngân hàng), triển khai trên Render với CI/CD qua GitHub Actions. Docker chỉ được dùng để chạy và kiểm thử ở môi trường local trong quá trình phát triển.

---

## ✨ Tính năng

### 🛍️ Cửa hàng
- Trang chủ với sách nổi bật, sách mới, danh mục
- Danh sách sách với lọc theo danh mục, tìm kiếm, sắp xếp
- Trang chi tiết sách với đánh giá, gợi ý sách liên quan
- Giỏ hàng (session-based)
- Checkout + đặt hàng
- Theo dõi trạng thái đơn hàng

### 🤖 AI Features (Google Gemini)
- **Chatbot tư vấn sách** — hỏi AI để được gợi ý sách phù hợp, AI trả về kèm card sách (ảnh, giá, nút thêm vào giỏ) ngay trong khung chat
- **Tìm kiếm theo cảm xúc / "vibe search"** — mô tả tâm trạng bằng ngôn ngữ tự nhiên (VD: "muốn đọc gì nhẹ nhàng chiều mưa"), Gemini phân tích và tạo vector embedding, Supabase dùng pgvector + HNSW index để tìm sách có nội dung/không khí gần nhất theo cosine similarity
- **Tìm kiếm bằng hình ảnh** — upload ảnh bìa sách hoặc tranh minh họa, Gemini Vision phân tích thể loại/phong cách để gợi ý sách tương tự
- **Tóm tắt nội dung sách** — AI tóm tắt mô tả trong 3-4 câu
- **Phân tích đánh giá** — AI phân tích sentiment từ đánh giá độc giả
- **Search suggestions** — gợi ý tìm kiếm theo thời gian thực

### 💳 Thanh toán — QR theo chuẩn VietQR
| Phương thức | Mô tả |
|-------------|-------|
| 💵 COD | Thanh toán khi nhận hàng |
| 🏦 VietQR | Sinh mã QR chuyển khoản ngân hàng theo chuẩn VietQR (NAPAS) — quét được bằng **MoMo, ZaloPay** và hầu hết app ngân hàng tại Việt Nam |

> Vì VietQR là chuẩn QR liên ngân hàng dùng chung, đơn hàng được xác nhận thủ công qua đối soát (admin kiểm tra giao dịch) hoặc tự động nếu kết nối thêm dịch vụ webhook ngân hàng bên thứ ba (ví dụ Casso, SePay) — không bắt buộc để chạy demo.

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
- Quản lý & cập nhật trạng thái đơn hàng (bao gồm xác nhận thanh toán VietQR)
- Quản lý người dùng + phân quyền role (admin only)
- Kích hoạt / vô hiệu hóa tài khoản

---

## 🚀 Cài đặt & Chạy

### Yêu cầu
- Python 3.11+
- Tài khoản [Supabase](https://supabase.com) (đã bật extension `pgvector`)
- API key [Gemini](https://aistudio.google.com/)
- Thông tin tài khoản ngân hàng nhận thanh toán (để sinh mã VietQR)
- Docker & Docker Compose — **tùy chọn**, chỉ cần khi muốn chạy/test ở môi trường container hóa cục bộ (không dùng để chạy production)
- Tài khoản [Render](https://render.com) — để deploy production

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
SUPABASE_SERVICE_KEY=your-supabase-service-role-key

GEMINI_API_KEY=AIzaSy...

# Thông tin nhận thanh toán — dùng để sinh mã VietQR
VIETQR_BANK_BIN=your-bank-bin-code
VIETQR_ACCOUNT_NO=your-account-number
VIETQR_ACCOUNT_NAME=YOUR ACCOUNT NAME

APP_URL=http://localhost:5000
```

### 2. Tạo database Supabase

1. Đăng nhập [Supabase Dashboard](https://supabase.com)
2. Tạo project mới
3. Vào **SQL Editor** → chạy file `migrations/001_initial_schema.sql`
4. Chạy tiếp `migrations/002_semantic_search.sql` để bật extension `pgvector`, thêm cột `embedding vector(384)` và tạo HNSW index phục vụ tìm kiếm theo cảm xúc/ngữ nghĩa
5. Lấy `Project URL`, `anon public key` và `service_role key` từ **Settings → API**

### 3. Tạo tài khoản admin

```bash
python create_admin.py
```

### 4. Cài dependencies & chạy local

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

### 5. Seed dữ liệu & tạo embedding cho semantic search

```bash
# Thêm sách mẫu
python seed_data.py

# Tạo vector embedding cho toàn bộ sách (bắt buộc để tính năng
# "tìm theo cảm xúc" và "tìm bằng hình ảnh" hoạt động)
python generate_embeddings.py

# Chỉ tạo lại embedding cho 1 cuốn cụ thể
python generate_embeddings.py --book-id 5

# Tạo lại toàn bộ, ghi đè embedding cũ
python generate_embeddings.py --force
```

### 6. Chạy bằng Docker (chỉ dùng cho local dev/test)

```bash
docker-compose up -d --build
docker-compose logs -f web
docker-compose down
```

Truy cập: http://localhost — phục vụ kiểm thử cấu hình Nginx + Gunicorn trước khi deploy, **không dùng cách này để chạy production**.

### 7. Deploy lên Render (production)

1. Đăng nhập [Render Dashboard](https://render.com) → **New → Web Service** → kết nối repository GitHub
2. Build command: `pip install -r requirements.txt`
3. Start command: `gunicorn run:app`
4. Thêm các biến môi trường ở bước 1 vào phần **Environment** của service
5. Lấy **Deploy Hook URL** trong **Settings → Deploy Hook** của Render — dùng để GitHub Actions gọi triggering deploy tự động sau khi test pass (xem phần CI/CD)

---

## 🗂️ Cấu trúc dự án

```
bookstore/
├── app/
│   ├── __init__.py          # App factory, Supabase client
│   ├── models/
│   │   ├── user.py          # User model + auth
│   │   ├── book.py          # Book model
│   │   └── order.py         # Order model
│   ├── routes/
│   │   ├── auth.py          # Login, register, profile
│   │   ├── shop.py          # Storefront, cart, checkout
│   │   ├── admin.py         # Admin panel (RBAC)
│   │   ├── api.py           # AI APIs (chat, semantic & image search), search, cart count
│   │   └── payment.py       # Sinh mã VietQR, xác nhận đơn hàng
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
│   ├── 001_initial_schema.sql     # Schema chính: users, books, orders...
│   └── 002_semantic_search.sql    # pgvector, HNSW index, RPC tìm kiếm ngữ nghĩa
├── generate_embeddings.py   # Script tạo vector embedding cho sách (Gemini text-embedding-004)
├── .github/
│   └── workflows/
│       └── deploy.yml       # CI/CD: test → build → trigger deploy Render
├── Dockerfile                # Dùng cho local dev/test
├── docker-compose.yml        # Dùng cho local dev/test
├── nginx.conf
├── requirements.txt
├── run.py
└── .env.example
```

---

## 🔄 CI/CD với GitHub Actions + Render

Pipeline tự động:

```
Push to develop → Test → Build → Gọi Render Deploy Hook (staging)
Push to main    → Test → Build → Gọi Render Deploy Hook (production)
```

Render tự động build và khởi động lại service ngay khi Deploy Hook được gọi — không cần SSH hay quản lý server thủ công.

### GitHub Secrets cần thiết

| Secret | Mô tả |
|--------|-------|
| `SUPABASE_URL` | URL Supabase project |
| `SUPABASE_KEY` | Supabase anon key |
| `SUPABASE_SERVICE_KEY` | Supabase service role key (dùng cho test/seed trong CI) |
| `GEMINI_API_KEY` | Google Gemini API key |
| `RENDER_DEPLOY_HOOK_URL` | Deploy Hook của Render service production |
| `RENDER_DEPLOY_HOOK_URL_STAGING` | Deploy Hook của Render service staging *(nếu có)* |

---

## 🏦 Tích hợp thanh toán — VietQR

- Sinh mã QR chuyển khoản theo **chuẩn VietQR** (do NAPAS phát hành), được hầu hết ngân hàng và ví điện tử tại Việt Nam hỗ trợ quét, bao gồm **MoMo** và **ZaloPay**
- Mã QR được tạo từ thông tin: mã ngân hàng (BIN), số tài khoản, tên chủ tài khoản, số tiền và nội dung chuyển khoản (mã đơn hàng) — không cần đăng ký merchant account hay xin sandbox key như tích hợp trực tiếp cổng thanh toán
- Trang thanh toán hiển thị mã QR kèm đầy đủ thông tin chuyển khoản để người dùng tự nhập tay nếu cần
- Xác nhận đơn hàng theo 2 cách:
  - **Thủ công**: admin vào trang quản lý đơn hàng, kiểm tra sao kê và cập nhật trạng thái `paid`
  - **Tự động (tùy chọn)**: tích hợp thêm dịch vụ webhook ngân hàng của bên thứ ba (VD: Casso, SePay) để tự động bắt giao dịch và cập nhật trạng thái đơn hàng qua endpoint nội bộ

---

## 🔒 Bảo mật

- Mật khẩu mã hóa với Werkzeug (PBKDF2)
- CSRF protection (Flask-WTF)
- Rate limiting qua Nginx (khi chạy sau reverse proxy)
- Row Level Security (RLS) trên Supabase
- RBAC (Role-Based Access Control): admin / staff / customer
- Session-based cart (server-side)
- Security headers qua Nginx

---

## 📝 API Endpoints

| Method | Endpoint | Mô tả |
|--------|----------|-------|
| POST | `/api/ai/recommend` | AI gợi ý sách theo từ khóa |
| POST | `/api/ai/semantic-search` | Tìm sách theo cảm xúc/"vibe" qua vector embedding (pgvector + HNSW) |
| POST | `/api/ai/image-search` | Tìm sách bằng hình ảnh (Gemini Vision) |
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

MIT License © 2026 Mọt & Mèo
