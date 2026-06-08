import os
from dotenv import load_dotenv
from supabase import create_client
from google import genai
from google.genai import types

load_dotenv()

# Cấu hình
SUPABASE_URL = os.getenv('SUPABASE_URL')
SUPABASE_KEY = os.getenv('SUPABASE_SERVICE_KEY') or os.getenv('SUPABASE_KEY')
GEMINI_API_KEY = os.getenv('GEMINI_API_KEY')

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
ai = genai.Client(api_key=GEMINI_API_KEY)

def test_semantic_search(query_text: str):
    print(f"\n🔍 Đang tìm kiếm cho câu: '{query_text}'")

    # 1. Biến câu hỏi thành Vector 384 chiều (Dùng model 005 giống lúc nạp)
    response = ai.models.embed_content(
        model='gemini-embedding-001',
        contents=query_text,
        config=types.EmbedContentConfig(
            task_type='RETRIEVAL_QUERY', # Chỉ định đây là query để tìm kiếm
            output_dimensionality=384,
        )
    )
    query_embedding = response.embeddings[0].values

    # 2. Gọi hàm RPC trên Supabase để so sánh Vector
    result = supabase.rpc(
        'search_books_semantic',
        {
            'query_embedding': query_embedding,
            'match_threshold': 0.1, # Ngưỡng tối thiểu (chọn thấp để test)
            'match_count': 3        # Trả về top 3 cuốn giống nhất
        }
    ).execute()

    # 3. In kết quả
    books = result.data
    if not books:
        print("❌ Không tìm thấy sách nào phù hợp.")
        return

    print("✅ Đã tìm thấy top 3 sách phù hợp nhất:\n")
    for b in books:
        # In ra tên sách và độ tương đồng (Càng gần 1.0 càng giống)
        print(f"📚 {b['title']} (Tác giả: {b['author']})")
        print(f"   Độ khớp (Similarity): {b['similarity']:.4f}\n")

if __name__ == '__main__':
    # BẠN HÃY THỬ SỬA NHỮNG CÂU SAU ĐỂ TEST SỰ KỲ DIỆU CỦA AI:

    # Test 1: Tìm theo cảm xúc / Vibe (Không chứa từ khóa cụ thể)
    test_semantic_search("Mình muốn học cách giao tiếp tốt hơn và thu phục lòng người")

    # Test 2: Tìm theo chủ đề trừu tượng
    test_semantic_search("Có sách nào nói về lịch sử con người từ thời đồ đá không?")

    # Test 3: Tìm theo tình huống
    test_semantic_search("Làm sao để code cho gọn gàng và dễ đọc?")