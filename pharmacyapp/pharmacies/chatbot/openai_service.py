import logging
import os
import re
from openai import OpenAI
from dotenv import load_dotenv
load_dotenv()

logger = logging.getLogger(__name__)


class OpenAIService:
    def __init__(self):
        self.client = None
        self.openai_available = False
        self.api_key = os.getenv("OPENAI_API_KEY") 
        self.client = OpenAI(api_key=self.api_key)
        self.openai_available = True
    
    def create_prompt_with_medicines(self, user_question, context):
        return f"""Bạn là dược sĩ chuyên nghiệp. Khách hàng hỏi: "{user_question}"

                    Thuốc có sẵn trong nhà thuốc:
                    {context}

                    QUY TẮC QUAN TRỌNG:
                    - CHỈ tư vấn về những thuốc có trong danh sách trên
                    - KHÔNG đề cập thuốc nào khác ngoài danh sách
                    - Tập trung vào công dụng, cách dùng, giá cả của thuốc có sẵn
                    - Đưa ra lời khuyên cụ thể về thuốc phù hợp nhất
                    - BẮT BUỘC phải có đầy đủ 4 phần dưới đây

                    BẮT BUỘC PHẢI TRẢ LỜI THEO FORMAT SAU (TUYỆT ĐỐI KHÔNG ĐƯỢC THAY ĐỔI):

                    **Giới thiệu và công dụng:**
                    [Viết 2-3 câu giới thiệu thuốc và liệt kê công dụng chính]

                    **Cách sử dụng:**
                    [Hướng dẫn cách sử dụng thuốc chi tiết]

                    **Giá cả:**
                    [Thông tin giá thuốc cụ thể]

                    **Lưu ý quan trọng:**
                    [Các lưu ý an toàn khi sử dụng thuốc]

                    CRITICAL: 
                    - Bạn PHẢI bắt đầu mỗi section bằng **Tên section:** (có hai dấu sao trước và sau, có dấu hai chấm)
                    - PHẢI có đầy đủ 4 phần: Giới thiệu và công dụng, Cách sử dụng, Giá cả, Lưu ý quan trọng
                    - KHÔNG được bỏ sót bất kỳ phần nào
                    - KHÔNG được sử dụng markdown khác, chỉ được dùng **text:** cho header section
                    - Không emoji, không bullet points trong header"""
    
    def create_prompt_without_medicines(self, user_question):
        return f"""Bạn là dược sĩ chuyên nghiệp. Khách hàng hỏi: "{user_question}"

                    Hiện tại nhà thuốc không có thuốc cụ thể nào phù hợp với yêu cầu này.

                    Hãy trả lời:
                    - Nếu là lời chào: chào lại thân thiện
                    - Nếu hỏi thuốc không có: xin lỗi và khuyên tham khảo dược sĩ hoặc bác sĩ
                    - Nếu hỏi triệu chứng: tư vấn chung và khuyên đến cơ sở y tế

                    KHÔNG đề cập bất kỳ tên thuốc cụ thể nào. Trả lời ngắn gọn, không emoji."""
    
    def call_openai_api(self, prompt):
        """Gọi OpenAI API và trả về response"""
        # try:
        #     if not self.openai_available:
        #         return "Xin lỗi, hệ thống AI tư vấn đang bảo trì. Vui lòng liên hệ dược sĩ trực tiếp."
            
        response = self.client.chat.completions.create(
                model="gpt-4-turbo",
                messages=[
                    {
                        "role": "system", 
                        "content": "Bạn là dược sĩ chuyên nghiệp, tư vấn thuốc an toàn và có trách nhiệm. KHÔNG sử dụng emoji trong phản hồi."
                    },
                    {
                        "role": "user", 
                        "content": prompt
                    }
                ],
                max_tokens=500,
                temperature=0.7
            )
            
        ai_response = response.choices[0].message.content.strip()
            
            # # Loại bỏ emoji nếu có (fallback)
            # ai_response = re.sub(r'[^\w\s\u00C0-\u024F\u1E00-\u1EFF.,!?;:()\-]', '', ai_response, flags=re.UNICODE)
            
        return ai_response
            
        # except Exception as e:
        #     logger.error(f"OpenAI API call error: {str(e)}")
        #     return "Xin lỗi, tôi gặp sự cố khi xử lý câu hỏi của bạn. Vui lòng thử lại sau."
    
    def generate_response(self, user_question, medicine_context, medicines):
        """Generate response cho chatbot"""
        # try:
            # if not self.openai_available:
            #     return {
            #         'response': 'Xin lỗi, hệ thống AI tư vấn đang bảo trì. Vui lòng liên hệ dược sĩ trực tiếp.',
            #         'medicines': [],
            #         'type': 'error',
            #         'medicines_count': 0
            #     }
            
        if medicines:
                # Có thuốc liên quan
                prompt = self.create_prompt_with_medicines(user_question, medicine_context)
                return {
                    'response': self.call_openai_api(prompt),
                    'medicines': medicines,
                    'type': 'openai_response',
                    'medicines_count': len(medicines)
                }
        else:
                # Không có thuốc phù hợp
                prompt = self.create_prompt_without_medicines(user_question)
                return {
                    'response': self.call_openai_api(prompt),
                    'medicines': [],
                    'type': 'text_only',
                    'medicines_count': 0
                }
                
        # except Exception as e:
        #     logger.error(f"OpenAI API error: {str(e)}")
        #     return {
        #         'response': 'Xin lỗi, tôi gặp sự cố khi xử lý câu hỏi của bạn. Vui lòng thử lại sau hoặc liên hệ dược sĩ trực tiếp.',
        #         'medicines': [],
        #         'type': 'error',
        #         'medicines_count': 0
        #     }
