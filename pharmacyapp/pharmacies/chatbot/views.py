import uuid
import logging
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import AllowAny
from rest_framework import status
from pharmacies import serializers
# from .medicine_search import MedicineSearchService
from .openai_service import OpenAIService
from .rag_service import RAGMedicineService

logger = logging.getLogger(__name__)


class ChatBotView(APIView):
    permission_classes = [AllowAny]
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # self.medicine_search = MedicineSearchService()  # Fallback
        self.openai_service = OpenAIService()
        self.rag_service = RAGMedicineService()  # RAG service mới
    
    def post(self, request):
        """API endpoint cho chatbot tư vấn thuốc với RAG"""
        user_message = request.data.get('message', '').strip()
        session_id = request.data.get('session_id', str(uuid.uuid4()))
        use_rag = request.data.get('use_rag', True)  # Mặc định dùng RAG
        
        try:
            if use_rag:
                # Sử dụng RAG pipeline
                bot_response_data = self.rag_service.generate_rag_response(user_message)
            else:
                # Fallback về method cũ nếu cần
                bot_response_data = {
                    'response': 'Xin lỗi, chế độ tìm kiếm truyền thống tạm thời không khả dụng.',
                    'medicines': [],
                    'type': 'error',
                    'medicines_count': 0
                }
            
            bot_response = bot_response_data['response']
            
            # Format response để trả về frontend 
            response_data = {
                'user_message': user_message,
                'bot_response': bot_response,
                'session_id': session_id,
                'type': bot_response_data['type'],
                'response_type': bot_response_data['type'],
                'medicines_count': bot_response_data.get('medicines_count', 0),
                'message': bot_response,
                'search_method': 'RAG' if use_rag else 'Traditional'
            }
            
            # Thêm thông tin RAG nếu có
            if 'rag_info' in bot_response_data:
                response_data['rag_info'] = bot_response_data['rag_info']
            
            # CHỈ thêm thông tin thuốc nếu thực sự có medicines và không phải text_only
            if (bot_response_data.get('medicines') and 
                len(bot_response_data['medicines']) > 0 and 
                bot_response_data['type'] != 'text_only'):
                response_data['medicines'] = bot_response_data['medicines']
                
            return Response(response_data, status=status.HTTP_200_OK)
            
        except Exception as e:
            logger.error(f"ChatBot error: {str(e)}")
            return Response(
                {
                    'error': 'Xin lỗi, tôi gặp sự cố khi xử lý câu hỏi của bạn. Vui lòng thử lại sau.',
                    'user_message': user_message,
                    'bot_response': 'Hệ thống đang gặp sự cố, vui lòng liên hệ dược sĩ trực tiếp để được tư vấn.',
                    'session_id': session_id,
                    'type': 'error',
                    'search_method': 'Error'
                }, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    # def get(self, request):
    #     """Không lưu lịch sử chat - trả về empty"""
    #     return Response({'chats': [], 'message': 'Lịch sử chat không được lưu trữ'})
