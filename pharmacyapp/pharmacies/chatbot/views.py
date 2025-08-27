import uuid
import logging
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import AllowAny
from rest_framework import status
from pharmacies import serializers
from .medicine_search import MedicineSearchService
from .openai_service import OpenAIService

logger = logging.getLogger(__name__)


class ChatBotView(APIView):
    permission_classes = [AllowAny]
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.medicine_search = MedicineSearchService()
        self.openai_service = OpenAIService()
    
    def post(self, request):
        """API endpoint cho chatbot tư vấn thuốc với OpenAI"""
        user_message = request.data.get('message', '').strip()
        session_id = request.data.get('session_id', str(uuid.uuid4()))
        
        if not user_message:
            return Response(
                {'error': 'Vui lòng nhập câu hỏi của bạn'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            # Lấy context thuốc từ database
            medicine_context, medicines = self.medicine_search.get_medicine_context(user_message)
            
            # Tạo phản hồi bằng OpenAI
            bot_response_data = self.openai_service.generate_response(
                user_message, medicine_context, medicines
            )
            bot_response = bot_response_data['response']
            
            # Format response để trả về frontend 
            response_data = {
                'user_message': user_message,
                'bot_response': bot_response,
                'session_id': session_id,
                'timestamp': None,
                'type': bot_response_data['type'],
                'response_type': bot_response_data['type'],
                'medicines_count': bot_response_data.get('medicines_count', 0),
                'message': bot_response
            }
            
            # CHỈ thêm thông tin thuốc nếu thực sự có medicines và không phải text_only
            if (bot_response_data.get('medicines') and 
                len(bot_response_data['medicines']) > 0 and 
                bot_response_data['type'] != 'text_only'):
                response_data['medicines'] = bot_response_data['medicines']
            
            return Response(response_data, status=status.HTTP_200_OK)
            
        except Exception as e:
            return Response(
                {
                    'error': 'Xin lỗi, tôi gặp sự cố khi xử lý câu hỏi của bạn. Vui lòng thử lại sau.',
                    'user_message': user_message,
                    'bot_response': 'Hệ thống đang gặp sự cố, vui lòng liên hệ dược sĩ trực tiếp để được tư vấn.',
                    'session_id': session_id,
                    'type': 'error'
                }, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    # def get(self, request):
    #     """Không lưu lịch sử chat - trả về empty"""
    #     return Response({'chats': [], 'message': 'Lịch sử chat không được lưu trữ'})
