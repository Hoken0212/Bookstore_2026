import os
import re
import json
from flask import Blueprint, request, jsonify, session
from flask_login import current_user
from app.models.book import Book
from app import supabase
from google import genai
from google.genai import types
import time

api_bp = Blueprint('api', __name__)

ai_client  = genai.Client(api_key=os.getenv('GEMINI_API_KEY'))
MODEL_NAME = 'gemini-3.1-flash-lite'
EMBED_MODEL = 'gemini-embedding-001'
EMBED_DIM   = 384

MAX_IMAGE_BYTES = 8 * 1024 * 1024   # 8 MB
ALLOWED_MIME    = {'image/jpeg', 'image/png', 'image/webp', 'image/gif'}

def call_gemini_with_retry(system_prompt, user_input, retries=3):
    for i in range(retries):
        try:
            return ai_client.models.generate_content(
                model=MODEL_NAME,
                contents=user_input,
                config=types.GenerateContentConfig(
                    system_instruction=system_prompt,
                    max_output_tokens=1000,
                    response_mime_type="application/json",
                )
            )
        except Exception as e:
            if "503" in str(e) and i < retries - 1:
                time.sleep(2 ** i) # Đợi 1s, rồi 2s, rồi 4s...
                continue
            raise e
# ── Helpers ──────────────────────────────────────────────────────

def strip_markdown(text: str) -> str:
    if not text:
        return ""
    text = re.sub(r'^#+\s*', '', text, flags=re.MULTILINE)      # Xóa Header
    text = re.sub(r'^\s*[-•]\s+', '', text, flags=re.MULTILINE) # Xóa Bullet points
    text = re.sub(r'^\s*\d+\.\s+', '', text, flags=re.MULTILINE) # Xóa List số
    text = re.sub(r'`(.*?)`', r'\1', text)                       # Xóa Backtick code
    # Đã XÓA dòng r'__(.*?)__'
    return re.sub(r'\n{3,}', '\n\n', text).strip()               # Dọn khoảng trắng


def get_books_catalog_full() -> list[dict]:
    """Lấy catalog kèm description để AI matching tốt hơn"""
    try:
        r = supabase.table('books').select(
            'id, title, author, price, original_price, stock, cover_image, '
            'description, categories(name)'
        ).eq('is_active', True).execute()
        books = []
        for b in (r.data or []):
            if b.get('categories'):
                b['category_name'] = b['categories']['name']
            books.append(b)
        return books
    except Exception:
        return []


def fetch_books_by_ids(ids: list[int]) -> list[dict]:
    if not ids:
        return []
    try:
        r = supabase.table('books').select(
            'id, title, author, price, original_price, stock, cover_image, description'
        ).in_('id', ids).eq('is_active', True).execute()
        return r.data or []
    except Exception:
        return []


def find_alternatives(excluded_ids: list[int], limit: int = 2) -> list[dict]:
    try:
        r = supabase.table('books').select(
            'id, title, author, price, original_price, stock, cover_image'
        ).eq('is_active', True).gt('stock', 0).not_.in_(
            'id', excluded_ids
        ).order('review_count', desc=True).limit(limit).execute()
        return r.data or []
    except Exception:
        return []


def generate_query_embedding(text: str) -> list[float] | None:
    """Tạo embedding vector từ text người dùng"""
    try:
        result = ai_client.models.embed_content(
            model=EMBED_MODEL,
            contents=text,
            config=types.EmbedContentConfig(
                task_type='SEMANTIC_SIMILARITY',
                output_dimensionality=EMBED_DIM,
            )
        )
        return result.embeddings[0].values
    except Exception as e:
        print(f"Embedding error: {e}")
        return None


def expand_query_with_ai(user_input: str) -> str:
    """
    Dùng Gemini phân tích cảm xúc và mở rộng query tìm kiếm.
    VD: "stress, muốn sách nhẹ nhàng" → "tâm lý chữa lành, self-help thư giãn, cuộc sống bình yên"
    """
    prompt = (
        "Phân tích cảm xúc và nhu cầu đọc sách từ câu sau của người dùng.\n"
        "Trả về một đoạn mô tả ngắn (3-5 từ khóa/cụm từ) về thể loại và chủ đề sách PHÙ HỢP NHẤT.\n"
        "Chỉ trả về các từ khóa, không giải thích, không markdown.\n\n"
        f"Input: {user_input}"
    )
    try:
        r = ai_client.models.generate_content(
            model=MODEL_NAME,
            contents=prompt,
            config=types.GenerateContentConfig(max_output_tokens=200)
        )
        expanded = strip_markdown(r.text)
        # Kết hợp query gốc + mở rộng để embedding phong phú hơn
        return f"{user_input} {expanded}"
    except Exception:
        return user_input  # Fallback về query gốc


def analyze_image_with_gemini(
        image_bytes: bytes,
        mime_type: str,
        user_text: str = ''
) -> dict:
    """
    Phase 1: Gemini Vision phân tích ảnh và trả về structured JSON:
    {
      "image_type": "book_cover" | "artwork" | "sketch" | "character" | "scene" | "other",
      "identified_book": { "title": "...", "author": "..." } | null,
      "visual_description": "Mô tả visual style...",
      "genres": ["fantasy", "manga", "horror", ...],
      "themes": ["chiến tranh", "tình yêu", "phiêu lưu", ...],
      "mood": "dark / epic / cozy / tense / ...",
      "art_style": "anime / realistic / watercolor / sketch / ...",
      "search_keywords": ["từ khóa tìm kiếm", ...],
      "ai_message": "Mô tả ngắn về ảnh bằng tiếng Việt"
    }
    """
    extra_context = f'\nYêu cầu thêm của người dùng: "{user_text}"' if user_text else ''

    prompt = (
        "Phân tích hình ảnh này để tìm sách phù hợp cho người dùng.\n\n"

        "BƯỚC 1 - XÁC ĐỊNH LOẠI ẢNH:\n"
        "- book_cover: ảnh chụp/scan bìa sách\n"
        "- artwork: tranh minh họa, fan art, concept art\n"
        "- sketch: phác thảo, vẽ tay, nét vẽ đơn giản\n"
        "- character: nhân vật cụ thể (samurai, knight, wizard...)\n"
        "- scene: cảnh vật, phong cảnh có chủ đề\n"
        "- other: loại khác\n\n"

        "BƯỚC 2 - NẾU LÀ BÌA SÁCH:\n"
        "Cố gắng nhận diện tên sách và tác giả từ chữ trên bìa.\n\n"

        "BƯỚC 3 - PHÂN TÍCH VISUAL:\n"
        "Mô tả phong cách nghệ thuật, thể loại, chủ đề, không khí.\n\n"

        "BƯỚC 4 - TỪ KHÓA TÌM KIẾM:\n"
        "Tạo 3-6 từ khóa/cụm từ TIẾNG VIỆT để tìm sách tương tự "
        "(thể loại, chủ đề, không khí đọc).\n"
        f"{extra_context}\n\n"

        "TRẢ VỀ JSON HỢP LỆ DUY NHẤT (không có text ngoài JSON):\n"
        "{\n"
        '  "image_type": "...",\n'
        '  "identified_book": {"title": "...", "author": "..."} hoặc null,\n'
        '  "visual_description": "mô tả visual 1 câu tiếng Việt",\n'
        '  "genres": ["thể loại 1", "thể loại 2"],\n'
        '  "themes": ["chủ đề 1", "chủ đề 2"],\n'
        '  "mood": "không khí đọc",\n'
        '  "art_style": "phong cách nghệ thuật",\n'
        '  "search_keywords": ["từ khóa 1", "từ khóa 2", "từ khóa 3"],\n'
        '  "ai_message": "Nhận xét ngắn về ảnh và hướng tìm sách, 1-2 câu"\n'
        "}"
    )

    try:
        response = ai_client.models.generate_content(
            model=MODEL_NAME,
            contents=[
                types.Content(
                    role='user',
                    parts=[
                        types.Part.from_bytes(data=image_bytes, mime_type=mime_type),
                        types.Part.from_text(text=prompt),
                    ]
                )
            ],
            config=types.GenerateContentConfig(max_output_tokens=600)
        )

        raw = response.text.strip()
        raw = re.sub(r'^```(?:json)?\s*', '', raw, flags=re.MULTILINE)
        raw = re.sub(r'```\s*$', '', raw, flags=re.MULTILINE).strip()
        return json.loads(raw)

    except json.JSONDecodeError:
        # Trích keywords từ text nếu không parse được JSON
        return {
            'image_type': 'other',
            'identified_book': None,
            'visual_description': 'Hình ảnh thú vị',
            'genres': [],
            'themes': [],
            'mood': '',
            'art_style': '',
            'search_keywords': [],
            'ai_message': strip_markdown(response.text) if 'response' in dir() else 'Đang phân tích...'
        }
    except Exception as e:
        print(f"Vision analysis error: {e}")
        raise


def match_books_from_analysis(analysis: dict, catalog: list[dict]) -> list[int]:
    """
    Phase 2: Dùng AI kết hợp analysis + catalog để chọn book IDs phù hợp nhất.
    Trả về list[int] - danh sách ID sách khớp nhất.
    """
    # Nếu nhận diện được bìa sách cụ thể → tìm trong DB trước
    if analysis.get('identified_book'):
        ib = analysis['identified_book']
        title_hint = (ib.get('title') or '').lower()
        if title_hint:
            direct = [
                b['id'] for b in catalog
                if title_hint in b.get('title', '').lower()
            ]
            if direct:
                return direct[:3]

    # Tạo context cho AI matching
    books_ctx = []
    for b in catalog[:60]:   # giới hạn context size
        cat = b.get('category_name', '')
        desc_short = (b.get('description') or '')[:80]
        books_ctx.append(
            f"ID:{b['id']} | {b['title']} | {b['author']} | "
            f"{cat} | {desc_short}"
        )

    # Build matching prompt
    analysis_summary = (
        f"Loại ảnh: {analysis.get('image_type', 'unknown')}\n"
        f"Phong cách: {analysis.get('art_style', '')}\n"
        f"Thể loại: {', '.join(analysis.get('genres', []))}\n"
        f"Chủ đề: {', '.join(analysis.get('themes', []))}\n"
        f"Không khí: {analysis.get('mood', '')}\n"
        f"Từ khóa tìm kiếm: {', '.join(analysis.get('search_keywords', []))}"
    )

    prompt = (
            f"Dựa trên phân tích hình ảnh sau:\n{analysis_summary}\n\n"
            "Chọn 3-5 cuốn sách PHÙ HỢP NHẤT về phong cách, thể loại và chủ đề "
            "từ danh sách bên dưới.\n"
            "Ưu tiên sách có cùng thể loại (manga, fantasy, kinh dị...) hoặc cùng không khí đọc.\n"
            "Trả về JSON: {\"book_ids\": [id1, id2, id3]}\n"
            "Chỉ trả JSON, không text khác.\n\n"
            "DANH SÁCH SÁCH:\n" + "\n".join(books_ctx)
    )

    try:
        r = ai_client.models.generate_content(
            model=MODEL_NAME,
            contents=prompt,
            config=types.GenerateContentConfig(max_output_tokens=200)
        )
        raw = re.sub(r'^```(?:json)?\s*', '', r.text.strip(), flags=re.MULTILINE)
        raw = re.sub(r'```\s*$', '', raw.strip()).strip()
        data = json.loads(raw)
        return [int(i) for i in data.get('book_ids', [])]
    except Exception as e:
        print(f"Book matching error: {e}")
        # Fallback: keyword match
        keywords = analysis.get('search_keywords', []) + analysis.get('genres', [])
        matched = []
        for b in catalog:
            text = f"{b.get('title','')} {b.get('author','')} {b.get('category_name','')} {b.get('description','')}".lower()
            for kw in keywords:
                if kw.lower() in text:
                    matched.append(b['id'])
                    break
        return matched[:5]


def semantic_search_from_text(search_text: str, limit: int = 5) -> list[dict]:
    """Tìm kiếm HNSW bằng embedding của analysis text"""
    embedding = generate_query_embedding(search_text)
    if not embedding:
        return []
    try:
        result = supabase.rpc('search_books_semantic', {
            'query_embedding': embedding,
            'match_count': limit,
            'min_similarity': 0.20,
        }).execute()
        return result.data or []
    except Exception:
        return []


# ── ENDPOINT: Image Search ────────────────────────────────────────

@api_bp.route('/ai/image-search', methods=['POST'])
def image_search():
    """
    Multimodal search: nhận ảnh + text tùy chọn.

    Request: multipart/form-data
      - image: file ảnh (JPEG/PNG/WEBP/GIF, max 8MB)
      - text:  câu hỏi thêm (optional), VD: "tìm manga style này"

    Response:
    {
      "analysis": { image_type, visual_description, genres, ... },
      "ai_message": "Giải thích kết quả tìm kiếm",
      "books": [ book objects ],
      "similarity_scores": { book_id: pct },
      "search_method": "vision_semantic" | "vision_keyword" | "direct_match"
    }
    """
    # ── Validate input ──────────────────────────────────────────
    image_file = request.files.get('image')
    user_text  = request.form.get('text', '').strip()

    if not image_file:
        return jsonify({'error': 'Vui lòng tải lên một hình ảnh'}), 400

    mime_type = image_file.content_type or 'image/jpeg'
    if mime_type not in ALLOWED_MIME:
        return jsonify({
            'error': f'Định dạng ảnh không hỗ trợ. Chỉ nhận: JPEG, PNG, WEBP, GIF'
        }), 400

    image_bytes = image_file.read()
    if len(image_bytes) > MAX_IMAGE_BYTES:
        return jsonify({'error': 'Ảnh quá lớn, vui lòng chọn ảnh dưới 8MB'}), 400
    if len(image_bytes) < 100:
        return jsonify({'error': 'File ảnh không hợp lệ'}), 400

    # ── Phase 1: Vision analysis ────────────────────────────────
    try:
        analysis = analyze_image_with_gemini(image_bytes, mime_type, user_text)
    except Exception as e:
        print(f"Image search phase1 error: {e}")
        return jsonify({'error': 'Không thể phân tích ảnh. Vui lòng thử lại.'}), 500

    # ── Phase 2a: Thử HNSW semantic search trước ───────────────
    semantic_query = " ".join(filter(None, [
        " ".join(analysis.get('search_keywords', [])),
        " ".join(analysis.get('genres', [])),
        " ".join(analysis.get('themes', [])),
        analysis.get('mood', ''),
        analysis.get('art_style', ''),
    ]))

    semantic_results = []
    if semantic_query.strip():
        semantic_results = semantic_search_from_text(semantic_query, limit=5)

    # ── Phase 2b: AI matching từ catalog ───────────────────────
    catalog = get_books_catalog_full()
    matched_ids = match_books_from_analysis(analysis, catalog)

    # ── Merge kết quả: semantic + AI matching ──────────────────
    similarity_scores = {}
    final_books = []
    seen_ids = set()

    # Ưu tiên semantic results (có similarity score)
    for b in semantic_results:
        if b['id'] not in seen_ids and b.get('stock', 0) > 0:
            pct = round(b.get('similarity', 0) * 100, 1)
            similarity_scores[b['id']] = pct
            clean = {k: v for k, v in b.items() if k != 'similarity'}
            final_books.append(clean)
            seen_ids.add(b['id'])

    # Thêm từ AI matching nếu chưa đủ 4 kết quả
    if len(final_books) < 4 and matched_ids:
        extra = fetch_books_by_ids(
            [i for i in matched_ids if i not in seen_ids]
        )
        for b in extra:
            if b.get('stock', 0) > 0 and b['id'] not in seen_ids:
                final_books.append(b)
                seen_ids.add(b['id'])
                if len(final_books) >= 5:
                    break

    # Xác định phương pháp tìm kiếm
    if semantic_results:
        search_method = 'vision_semantic'
    elif matched_ids:
        search_method = 'vision_keyword'
    else:
        search_method = 'direct_match'

    # ── Phase 3: Sinh message giải thích kết quả ───────────────
    image_type_vn = {
        'book_cover': 'bìa sách',
        'artwork':    'tranh minh họa',
        'sketch':     'phác thảo',
        'character':  'nhân vật',
        'scene':      'cảnh vật',
        'other':      'hình ảnh',
    }.get(analysis.get('image_type', 'other'), 'hình ảnh')

    ai_message = analysis.get('ai_message', '')
    if not ai_message:
        if analysis.get('identified_book'):
            ib = analysis['identified_book']
            ai_message = f"Tôi nhận ra đây là bìa sách \"{ib.get('title', '')}\". "
        else:
            ai_message = f"Tôi nhận ra {image_type_vn} này "
            if analysis.get('art_style'):
                ai_message += f"theo phong cách {analysis['art_style']}"
            if analysis.get('genres'):
                ai_message += f", thể loại {', '.join(analysis['genres'][:2])}"
            ai_message += ". "

        if final_books:
            ai_message += f"Đây là {len(final_books)} cuốn sách có cùng vibe mà tôi tìm được:"
        else:
            ai_message += "Tôi chưa tìm được sách thật sự phù hợp trong kho — thử mô tả thêm bạn nhé!"

    return jsonify({
        'analysis': {
            'image_type':        analysis.get('image_type'),
            'visual_description': analysis.get('visual_description', ''),
            'genres':            analysis.get('genres', []),
            'themes':            analysis.get('themes', []),
            'mood':              analysis.get('mood', ''),
            'art_style':         analysis.get('art_style', ''),
            'identified_book':   analysis.get('identified_book'),
        },
        'ai_message':      ai_message,
        'books':           final_books,
        'similarity_scores': similarity_scores,
        'search_method':   search_method,
        'query_used':      semantic_query[:120] if semantic_query else '',
    })
# ── ENDPOINT 1: AI Recommend (Rich Product Cards) ────────────────

@api_bp.route('/ai/recommend', methods=['POST'])
def ai_recommend():
    data = request.json or {}
    user_input = data.get('message', '').strip()
    if not user_input:
        return jsonify({'error': 'Vui lòng nhập yêu cầu'}), 400

    catalog = get_books_catalog_full()
    if not catalog:
        return jsonify({'message': 'Cửa hàng chưa có sách nào.', 'books': []}), 200

    books_context_lines = []
    for b in catalog:
        stock_label = f"còn {b['stock']} cuốn" if b['stock'] > 0 else "HẾT HÀNG"
        books_context_lines.append(
            f"ID:{b['id']} | {b['title']} | {b['author']} | {b['price']:,.0f}đ | {stock_label}"
        )

    system_prompt = (
            "Bạn là trợ lý tư vấn sách của nhà sách BookStore.\n"
            "Nhiệm vụ: Phân tích yêu cầu của người dùng và chọn ra 1 đến 3 cuốn sách PHÙ HỢP NHẤT.\n\n"
            "QUY TẮC BẮT BUỘC:\n"
            "1. NGÔN NGỮ: LUÔN LUÔN phân tích và trả lời bằng CHÍNH NGÔN NGỮ mà người dùng đã sử dụng để hỏi (VD: Hỏi tiếng Anh -> Trả lời tiếng Anh, Hỏi tiếng Trung -> Trả lời tiếng Trung).\n"
            "2. CHỈ sử dụng thông tin và ID từ [DANH SÁCH SÁCH] bên dưới. Ưu tiên sách đang 'còn hàng'.\n"
            "3. Trong câu trả lời, LUÔN in đậm tên sách (VD: **Đắc Nhân Tâm**), in nghiêng tác giả và NÊU RÕ GIÁ TIỀN để khách hàng cân nhắc (VD: cuốn **Sapiens** của *Yuval Noah Harari* hiện có giá 150.000đ).\n"
            "4. KHÔNG trả về bất kỳ văn bản nào nằm ngoài cấu trúc JSON. Tuyệt đối KHÔNG dùng comment (//) bên trong JSON.\n\n"
            "ĐỊNH DẠNG JSON TRẢ VỀ (Tuân thủ tuyệt đối):\n"
            "{\n"
            '  "message": "Câu chào và lời khuyên thân thiện (1-3 câu văn xuôi tiếng Việt).",\n'
            '  "recommended_ids": [1, 5], \n'
            '  "out_of_stock_ids": []\n'
            "}\n\n"
            "Giải thích format:\n"
            "- recommended_ids: Mảng chứa các ID (số nguyên) của những sách bạn khuyên đọc.\n"
            "- out_of_stock_ids: Mảng chứa ID của những sách bạn khuyên đọc nhưng có trạng thái là 'HẾT HÀNG'. Nếu đều còn hàng thì để mảng rỗng [].\n\n"
            f"[DANH SÁCH SÁCH]\n" + "\n".join(books_context_lines)
    )

    try:
        response = ai_client.models.generate_content(
            model=MODEL_NAME,
            contents=user_input,
            config=types.GenerateContentConfig(
                system_instruction=system_prompt,
                max_output_tokens=1000,
            )
        )
        raw = re.sub(r'^```(?:json)?\s*', '', response.text.strip(), flags=re.MULTILINE)
        raw = re.sub(r'^```\s*', '', raw, flags=re.MULTILINE).strip()
        ai_data       = json.loads(raw)
        message       = strip_markdown(ai_data.get('message', 'Đây là gợi ý sách cho bạn:'))
        recommended   = [int(i) for i in ai_data.get('recommended_ids', [])]
        out_of_stock  = [int(i) for i in ai_data.get('out_of_stock_ids', [])]
    except Exception as e:
        print(f"AI recommend parse error: {e}")
        return jsonify({
            'message': strip_markdown(response.text) if 'response' in dir() else 'Xin lỗi, thử lại nhé!',
            'books': [], 'out_of_stock': [], 'alternatives': []
        }), 200

    in_stock_ids     = [i for i in recommended if i not in out_of_stock]
    in_stock_books   = fetch_books_by_ids(in_stock_ids)
    out_stock_books  = fetch_books_by_ids(out_of_stock) if out_of_stock else []
    alternatives     = []
    if out_of_stock:
        alternatives = find_alternatives(excluded_ids=recommended, limit=2)
        message += "\n\nMột số sách trong gợi ý đã hết hàng — tôi tìm thêm lựa chọn thay thế cho bạn!"

    return jsonify({
        'message': message,
        'books': in_stock_books,
        'out_of_stock': out_stock_books,
        'alternatives': alternatives,
        'search_type': 'keyword'
    })


# ── ENDPOINT 2: Semantic / Vibe Search ───────────────────────────

@api_bp.route('/ai/semantic-search', methods=['POST'])
def semantic_search():
    """
    Tìm kiếm theo cảm xúc / "vibe" bằng HNSW vector search.

    Flow:
      1. AI phân tích cảm xúc → mở rộng query
      2. Gemini embedding → vector 384 chiều
      3. Supabase HNSW RPC → books gần nhất
      4. AI sinh intro message phù hợp
    """
    data        = request.json or {}
    user_input  = data.get('message', '').strip()
    limit       = min(int(data.get('limit', 4)), 8)
    threshold   = float(data.get('threshold', 0.25))

    if not user_input:
        return jsonify({'error': 'Vui lòng nhập cảm xúc hoặc tâm trạng của bạn'}), 400

    # Step 1: AI mở rộng query để embedding phong phú hơn
    expanded_query = expand_query_with_ai(user_input)
    print(f"[Semantic] Original: '{user_input}' → Expanded: '{expanded_query}'")

    # Step 2: Tạo embedding vector
    embedding = generate_query_embedding(expanded_query)
    if embedding is None:
        # Fallback về keyword search nếu embedding lỗi
        return jsonify({
            'message': 'Không thể kết nối AI embedding. Vui lòng thử lại.',
            'books': [], 'search_type': 'semantic_failed'
        }), 500

    # Step 3: HNSW vector search trong Supabase
    try:
        result = supabase.rpc('search_books_semantic', {
            'query_embedding': embedding,
            'match_count': limit,
            'min_similarity': threshold,
        }).execute()
        books = result.data or []
    except Exception as e:
        print(f"[Semantic] HNSW search error: {e}")
        return jsonify({
            'message': 'Tính năng tìm kiếm ngữ nghĩa chưa sẵn sàng. Vui lòng chạy generate_embeddings.py trước.',
            'books': [], 'search_type': 'semantic_error'
        }), 200

    if not books:
        # Không tìm thấy → gợi ý sách phổ biến
        popular = supabase.table('books').select(
            'id, title, author, price, original_price, stock, cover_image'
        ).eq('is_active', True).gt('stock', 0).order(
            'review_count', desc=True
        ).limit(4).execute()

        return jsonify({
            'message': f'Tôi chưa tìm được sách khớp chính xác với cảm xúc của bạn, nhưng đây là những cuốn đang được yêu thích nhất tại BookStore:',
            'books': popular.data or [],
            'similarity_scores': [],
            'search_type': 'semantic_fallback'
        })

    # Step 4: AI tạo intro message dựa trên kết quả thực tế
    book_titles = ", ".join([b['title'] for b in books[:3]])
    intro_prompt = (
        f"Người dùng tìm sách với cảm xúc: '{user_input}'\n"
        f"Hệ thống tìm được các sách: {book_titles}\n\n"
        "Viết 1-2 câu giới thiệu kết quả tìm kiếm, đồng cảm với cảm xúc người dùng.\n"
        "QUAN TRỌNG: Phải viết bằng CHÍNH NGÔN NGỮ mà người dùng đã sử dụng trong câu cảm xúc của họ. Không dùng markdown, giọng văn ấm áp và chân thật."
    )
    try:
        intro_resp = ai_client.models.generate_content(
            model=MODEL_NAME,
            contents=intro_prompt,
            config=types.GenerateContentConfig(max_output_tokens=100)
        )
        message = strip_markdown(intro_resp.text)
    except Exception:
        message = f'Dựa trên cảm xúc của bạn, tôi tìm thấy {len(books)} cuốn sách có "vibe" phù hợp:'

    # Format scores đẹp hơn
    similarity_scores = {
        b['id']: round(b.get('similarity', 0) * 100, 1)
        for b in books
    }

    # Loại bỏ field 'similarity' khỏi books (frontend không cần raw value)
    clean_books = [{k: v for k, v in b.items() if k != 'similarity'} for b in books]

    return jsonify({
        'message': message,
        'books': clean_books,
        'similarity_scores': similarity_scores,
        'search_type': 'semantic',
        'query_analyzed': expanded_query,
    })


# ── ENDPOINT 3: Similar Books (dùng embedding của 1 cuốn sách) ───

@api_bp.route('/ai/similar-books/<int:book_id>', methods=['GET'])
def similar_books(book_id):
    """Tìm sách cùng 'vibe' với một cuốn cụ thể — dùng cho trang book detail"""
    try:
        result = supabase.rpc('find_similar_books', {
            'source_book_id': book_id,
            'match_count': 4,
        }).execute()
        books = result.data or []
        if not books:
            # Fallback: related by category
            source = supabase.table('books').select('category_id').eq('id', book_id).single().execute()
            if source.data:
                fallback = supabase.table('books').select(
                    'id, title, author, price, cover_image, stock'
                ).eq('category_id', source.data['category_id']).neq(
                    'id', book_id
                ).gt('stock', 0).limit(4).execute()
                return jsonify({'books': fallback.data or [], 'type': 'category'})
        return jsonify({'books': books, 'type': 'semantic'})
    except Exception as e:
        print(f"Similar books error: {e}")
        return jsonify({'books': [], 'type': 'error'})


# ── ENDPOINT 4: AI Summarize ─────────────────────────────────────

@api_bp.route('/ai/summarize/<int:book_id>', methods=['GET'])
def ai_summarize(book_id):
    book = Book.get_by_id(book_id)
    if not book or not book.description:
        return jsonify({'error': 'Không có mô tả sách'}), 404

    prompt = (
        "Bạn là một biên tập viên giàu kinh nghiệm của nhà sách BookStore.\n"
        "Nhiệm vụ: Tóm tắt phần mô tả sách dưới đây thành một đoạn giới thiệu thật hấp dẫn, súc tích để thu hút độc giả.\n\n"
        "QUY TẮC BẮT BUỘC:\n"
        "1. Độ dài: Viết CHÍNH XÁC từ 3 đến 4 câu văn hoàn chỉnh bằng tiếng Việt.\n"
        "2. Định dạng: Chỉ viết văn xuôi liền mạch. TUYỆT ĐỐI KHÔNG sử dụng bất kỳ ký tự Markdown nào (không dùng *, **, #, -, hoặc gạch đầu dòng).\n"
        "3. Ngữ pháp: Câu văn phải trọn vẹn, tuyệt đối không bị cắt ngang giữa chừng.\n\n"
        f"[MÔ TẢ GỐC CỦA SÁCH]:\n{book.description}"
    )
    try:
        r = ai_client.models.generate_content(
            model=MODEL_NAME,
            contents=prompt,
            config=types.GenerateContentConfig(max_output_tokens=300)
        )
        return jsonify({'summary': strip_markdown(r.text)})
    except Exception as e:
        print(f"Summarize error: {e}")
        return jsonify({'error': 'Không thể tóm tắt'}), 500


# ── ENDPOINT 5: Review Sentiment ─────────────────────────────────

@api_bp.route('/ai/review-sentiment/<int:book_id>', methods=['GET'])
def ai_review_sentiment(book_id):
    try:
        r = supabase.table('reviews').select('rating, comment').eq('book_id', book_id).execute()
        reviews = r.data or []
        if not reviews:
            return jsonify({'analysis': 'Chưa có đánh giá nào.'})
        reviews_text = "\n".join([f"Rating:{rv['rating']}/5 - {rv.get('comment','')}" for rv in reviews[:20]])
        prompt = (
            "Phân tích ngắn gọn các đánh giá sau, nêu điểm mạnh và yếu.\n"
            "Viết văn xuôi tiếng Việt, không dùng markdown.\n\n"
            f"{reviews_text}"
        )
        resp = ai_client.models.generate_content(
            model=MODEL_NAME, contents=prompt,
            config=types.GenerateContentConfig(max_output_tokens=300)
        )
        return jsonify({'analysis': strip_markdown(resp.text)})
    except Exception as e:
        return jsonify({'error': 'Không thể phân tích'}), 500


# ── Utilities ─────────────────────────────────────────────────────

@api_bp.route('/cart/count', methods=['GET'])
def cart_count():
    cart = session.get('cart', {})
    return jsonify({'count': sum(cart.values())})


@api_bp.route('/search/suggestions', methods=['GET'])
def search_suggestions():
    q = request.args.get('q', '').strip()
    if len(q) < 2:
        return jsonify([])
    try:
        r = supabase.table('books').select('id, title, author').or_(
            f'title.ilike.%{q}%,author.ilike.%{q}%'
        ).eq('is_active', True).limit(6).execute()
        return jsonify(r.data or [])
    except Exception:
        return jsonify([])