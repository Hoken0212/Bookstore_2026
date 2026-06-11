import os
import json
from google import genai

_client = None


def get_client():
    global _client
    if _client is None:
        api_key = os.getenv('GEMINI_API_KEY')
        _client = genai.Client(api_key=api_key)
    return _client


def recommend_books(user_preferences: str, available_books: list) -> list:
    """AI-powered book recommendations based on user preferences"""
    client = get_client()
    
    books_text = "\n".join([
        f"- ID:{b['id']} | {b['title']} | {b.get('categories', {}).get('name', '')} | {b.get('description', '')[:100]}"
        for b in available_books[:50]
    ])
    
    prompt = f"""Bạn là trợ lý nhà sách thông minh. Dựa vào sở thích của người dùng, hãy gợi ý 5 cuốn sách phù hợp nhất.

Sở thích người dùng: {user_preferences}

Danh sách sách có sẵn:
{books_text}

Trả về JSON array gồm đúng 5 book IDs phù hợp nhất theo format: ["id1", "id2", "id3", "id4", "id5"]
Chỉ trả về JSON array, không có text khác."""

    try:
        message = client.messages.create(
            model="gemini-3.1-flash-lite",
            max_tokens=200,
            messages=[{"role": "user", "content": prompt}]
        )
        ids = json.loads(message.content[0].text.strip())
        return [b for b in available_books if b['id'] in ids][:5]
    except Exception:
        return available_books[:5]


def chat_assistant(message: str, context: dict = None) -> str:
    """AI chatbot for customer support"""
    client = get_client()
    
    system = """Bạn là trợ lý ảo của nhà sách Mọt & Mèo - một nhà sách trực tuyến uy tín tại Việt Nam.
Nhiệm vụ của bạn:
- Tư vấn sách cho khách hàng
- Giải đáp thắc mắc về đơn hàng, vận chuyển, thanh toán
- Giới thiệu sách mới và bestseller
- Hỗ trợ tìm sách theo chủ đề, tác giả
Luôn trả lời bằng tiếng Việt, thân thiện và chuyên nghiệp. Giữ câu trả lời ngắn gọn (dưới 150 từ)."""

    messages = [{"role": "user", "content": message}]
    if context and context.get('history'):
        messages = context['history'][-6:] + messages

    try:
        response = client.messages.create(
            model="gemini-3.1-flash-lite",
            max_tokens=300,
            system=system,
            messages=messages
        )
        return response.content[0].text
    except Exception as e:
        return "Xin lỗi, tôi đang gặp sự cố. Vui lòng thử lại sau hoặc liên hệ hotline 1800-xxxx."


def generate_book_description(title: str, author: str, category: str) -> str:
    """Auto-generate book description for admin"""
    client = get_client()
    
    try:
        message = client.messages.create(
            model="gemini-3.1-flash-lite",
            max_tokens=300,
            messages=[{
                "role": "user",
                "content": f"Viết mô tả hấp dẫn 150-200 từ bằng tiếng Việt cho cuốn sách: '{title}' của tác giả {author}, thể loại {category}. Chỉ trả về nội dung mô tả, không có tiêu đề."
            }]
        )
        return message.content[0].text
    except Exception:
        return ""


def analyze_review_sentiment(review_text: str) -> str:
    """Analyze review sentiment: positive/negative/neutral"""
    client = get_client()
    try:
        message = client.messages.create(
            model="gemini-3.1-flash-lite",
            max_tokens=10,
            messages=[{
                "role": "user",
                "content": f"Phân loại cảm xúc đánh giá này: '{review_text}'. Chỉ trả về 1 từ: positive, negative, hoặc neutral."
            }]
        )
        result = message.content[0].text.strip().lower()
        return result if result in ('positive', 'negative', 'neutral') else 'neutral'
    except Exception:
        return 'neutral'
