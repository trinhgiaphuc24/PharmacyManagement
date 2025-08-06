import uuid
import re
from threading import activeCount
from django.core.mail import send_mail
from django.db import transaction
from django.utils.decorators import method_decorator
from django.views import View
from django.views.decorators.csrf import csrf_exempt
import json
from django.http import JsonResponse
from django.db.models import Count
from rest_framework.filters import OrderingFilter
from rest_framework.views import APIView
from pharmacies.models import *
from pharmacies import serializers, paginators, perms
from rest_framework.response import Response
from rest_framework.decorators import action
from django.db.models import Q
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework import viewsets, generics, permissions, parsers, status
import requests
import logging
from datetime import datetime

logger = logging.getLogger(__name__)


class UserViewSet(viewsets.ViewSet, generics.CreateAPIView):
    queryset = User.objects.filter(is_active=True)
    serializer_class = serializers.UserSerializer
    parser_classes = [parsers.MultiPartParser]

    @action(methods=['GET', 'PUT'], url_path='current-user', detail=False, permission_classes=[IsAuthenticated])
    def current_user(self, request):
        user = request.user
        if request.method == 'GET':
            return Response(serializers.UserSerializer(user).data)
        elif request.method == 'PUT':
            serializer = self.get_serializer(user, data=request.data, partial=True)
            if serializer.is_valid():
                serializer.save()
                return Response(serializer.data, status=status.HTTP_200_OK)
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class MedicineGenreViewSet(viewsets.ModelViewSet):
    queryset = MedicineGenre.objects.all()
    serializer_class = serializers.MedicineGenreSerializer


class ProduceViewSet(viewsets.ModelViewSet):
    queryset = Produce.objects.all()
    serializer_class = serializers.ProduceSerializer


from rest_framework import viewsets, generics
from rest_framework.decorators import action
from rest_framework.response import Response
from django.db.models import Q
from .models import Medicine
from . import serializers, paginators

class MedicineViewSet(viewsets.ViewSet, generics.ListAPIView, generics.RetrieveAPIView):
    queryset = Medicine.objects.all()
    serializer_class = serializers.MedicineSerializer
    pagination_class = paginators.MedicinePagination

    def get_queryset(self):
        queryset = self.queryset

        q = self.request.query_params.get('q')
        if q:
            queryset = queryset.filter(Q(name__icontains=q))

        genre = self.request.query_params.get('medicineGenre')
        if genre:
            queryset = queryset.filter(medicineGenre__id=genre)

        produce = self.request.query_params.get('produce')
        if produce:
            queryset = queryset.filter(produce__name=produce)

        min_price = self.request.query_params.get('min_price')
        max_price = self.request.query_params.get('max_price')
        if min_price:
            queryset = queryset.filter(price__gte=min_price)
        if max_price:
            queryset = queryset.filter(price__lte=max_price)

        return queryset

    @action(detail=True, methods=['get'], url_path='detail')
    def detail(self, request, pk=None):
        medicine = self.get_object()
        serializer = self.get_serializer(medicine)
        return Response(serializer.data)

    


class MedicineImageViewSet(viewsets.ModelViewSet):
    queryset = MedicineImage.objects.all()
    serializer_class = serializers.MedicineImageSerializer


class CartViewSet(viewsets.ModelViewSet):
    queryset = Cart.objects.all()
    serializer_class = serializers.CartSerializer


class CartItemViewSet(viewsets.ModelViewSet):
    queryset = CartItem.objects.all()
    serializer_class = serializers.CartItemSerializer


class OrderViewSet(viewsets.ModelViewSet):
    queryset = Order.objects.all()
    serializer_class = serializers.OrderSerializer


class OrderDetailViewSet(viewsets.ModelViewSet):
    queryset = OrderDetail.objects.all()
    serializer_class = serializers.OrderDetailSerializer


class ChatBotView(APIView):
    permission_classes = [AllowAny]
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        try:
            from openai import OpenAI
            self.api_key = "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"
            self.client = OpenAI(api_key=self.api_key)
            self.openai_available = True
        except Exception as e:
            self.client = None
            self.openai_available = False
            logger.error(f"Failed to initialize OpenAI: {e}")
    
    def get_medicine_context(self, question):
        """Lấy thông tin thuốc từ database dựa trên MedicineGenre và keywords"""
        try:
            question_lower = question.lower()
            
            # Mapping từ khóa → MedicineGenre ID
            genre_mapping = {
                # Gan
                'gan': [11],
                'liver': [11], 
                'bảo vệ gan': [11],
                'giải độc gan': [11],
                'tăng cường gan': [11],
                'milk thistle': [11],
                'si-liver': [11],
                'dr. liver': [11],
                
                # Thận - Tiết niệu  
                'thận': [6],
                'niệu': [6],
                'tiểu tiện': [6],
                'bổ thận': [6],
                'kidney': [6],
                
                # Tim mạch
                'tim': [9],
                'tim mạch': [9],
                'huyết áp': [9],
                'cholesterol': [9],
                'co enzyme': [9],
                'hato gold': [9],
                'lipitas': [9],
                
                # Cơ - Xương - Khớp
                'xương': [4],
                'khớp': [4],
                'xương khớp': [4],
                'đau khớp': [4],
                'viêm khớp': [4],
                'fastum': [4],
                'salonpas': [4],
                'nhất nhất': [4],
                
                # Tiêu hóa
                'đau bụng': [12],
                'tiêu hóa': [12],
                'dạ dày': [12],
                'táo bón': [12],
                'tiêu chảy': [12],
                'omeprazole': [12],
                'antacid': [12],
                
                # Tai - Mũi - Họng
                'ho': [3],
                'cảm cúm': [3],
                'viêm họng': [3],
                'cảm lạnh': [3],
                'mũi': [3],
                'tai': [3],
                
                # Mắt
                'mắt': [2],
                'nhỏ mắt': [2],
                'khô mắt': [2],
                'mỏi mắt': [2],
                
                # Kí sinh trùng
                'giun': [5],
                'sán': [5],
                'tẩy giun': [5],
                'kí sinh trùng': [5],
                'azoltel': [5],
                'fugacar': [5],
                'alzental': [5],
                
                # SỨC KHỎE SINH SẢN - CHỈ KHI HỎI CỤ THỂ
                'sinh sản': [1],
                'âm đạo': [1],
                'viêm âm đạo': [1],
                'phụ khoa': [1],
                'kinh nguyệt': [1],
                'deginal': [1],
                'agimycob': [1],
                'ích mẫu': [1],
                'mãn kinh': [1],
                
                # Đau đầu, sốt (có thể thuộc nhiều genre)
                'đau đầu': [4, 12, 10],  # Cơ-Xương-Khớp, Tiêu hóa, Vitamin
                'sốt': [3, 10],  # Tai-Mũi-Họng, Vitamin
                'paracetamol': [3, 4, 10],
                'aspirin': [4, 9],
                'ibuprofen': [4, 3],
                
                # Vitamin và bổ sung dinh dưỡng
                'vitamin': [10],
                'khoáng chất': [10],
                'thiếu sắt': [10],
                'thiếu vitamin': [10],
                'canxi': [10],
                'calcium': [10],
                'sắt': [10],
                'iron': [10],
                'bổ sung': [10]
            }
            
            # Tìm genre phù hợp
            matching_genres = set()
            matched_keywords = []
            
            for keyword, genres in genre_mapping.items():
                if keyword in question_lower:
                    matching_genres.update(genres)
                    matched_keywords.append(keyword)
            
            medicines = Medicine.objects.none()
            
            if matching_genres:
                # Tìm thuốc theo genre
                medicines = Medicine.objects.filter(
                    medicineGenre_id__in=matching_genres
                ).select_related('medicineGenre', 'produce').prefetch_related('images')
                
                # Nếu có quá nhiều kết quả, lọc thêm bằng keyword
                if medicines.count() > 3:
                    refined_query = Q()
                    for keyword in matched_keywords:
                        refined_query |= (
                            Q(name__icontains=keyword) |
                            Q(benefit__icontains=keyword) |
                            Q(use__icontains=keyword)
                        )
                    
                    refined_medicines = medicines.filter(refined_query)[:3]
                    if refined_medicines.exists():
                        medicines = refined_medicines
                    else:
                        medicines = medicines[:3]
                else:
                    medicines = medicines[:5]
            
            # Fallback: tìm theo tên thuốc nếu không match genre
            if not medicines.exists():
                # Tìm theo tên thuốc chính xác
                medicines = Medicine.objects.filter(
                    name__icontains=question
                ).exclude(
                    medicineGenre_id=1  # Loại trừ thuốc sinh sản khỏi fallback
                ).select_related('medicineGenre', 'produce').prefetch_related('images')[:3]
                
                if not medicines.exists():
                    # Tìm theo từng từ - LOẠI TRỪ thuốc sinh sản và CHỈ TÌM TỪ DÀI
                    words = question.split()
                    
                    # Loại bỏ các từ phổ biến không có ý nghĩa
                    excluded_words = {
                        'thuốc', 'của', 'cho', 'với', 'và', 'là', 'có', 'tôi', 'bị', 'về',
                        'trong', 'để', 'được', 'như', 'hay', 'hoặc', 'nào', 'gì', 'thế',
                        'này', 'đó', 'một', 'các', 'những', 'chống', 'mạnh', 'tốt', 'giải',
                        'random', 'text', 'here', 'đường', 'sinh', 'morphine', 'insulin',
                        'kháng', 'không', 'tồn', 'tại', 'strong', 'antibiotic', 'sắt',
                        'thiếu', 'thụt', 'ướt', 'khô', 'cảm', 'ơn'
                    }
                    
                    significant_words = [
                        word.lower() for word in words 
                        if len(word) > 4 and word.lower() not in excluded_words
                    ]
                    
                    for word in significant_words:
                        medicines = Medicine.objects.filter(
                            Q(name__icontains=word) |
                            Q(benefit__icontains=word) |
                            Q(use__icontains=word)
                        ).exclude(
                            medicineGenre_id=1  # Loại trừ thuốc sinh sản khỏi fallback
                        ).select_related('medicineGenre', 'produce').prefetch_related('images')[:3]
                        if medicines.exists():
                            break
                    
                    # Nếu vẫn không tìm thấy, thử với từ 4 ký tự NHƯNG phải exact match và không phải từ excluded
                    if not medicines.exists():
                        words_4_chars = [
                            word.lower() for word in words 
                            if len(word) == 4 and word.lower() not in excluded_words
                        ]
                        for word in words_4_chars:
                            # Tìm exact match trong tên (không phải substring)
                            medicines = Medicine.objects.filter(
                                name__iregex=r'\b' + word + r'\b'
                            ).exclude(
                                medicineGenre_id=1
                            ).select_related('medicineGenre', 'produce').prefetch_related('images')[:3]
                            if medicines.exists():
                                break
            
            # Format thông tin thuốc
            context = "THÔNG TIN THUỐC CÓ SẴN:\n\n"
            medicine_list = []
            
            for i, med in enumerate(medicines, 1):
                context += f"THUỐC {i}: {med.name}\n"
                context += f"- Loại: {med.medicineGenre.name if med.medicineGenre else 'Không phân loại'}\n"
                context += f"- Giá: {med.price:,.0f} VND\n"
                context += f"- Công dụng: {med.benefit or 'Không có thông tin'}\n"
                context += f"- Cách dùng: {med.use or 'Không có thông tin'}\n"
                context += f"- Nhà sản xuất: {med.produce.name if med.produce else 'Không rõ'}\n\n"
                
                # Lấy hình ảnh thuốc nếu có
                medicine_images = []
                if hasattr(med, 'images'):
                    medicine_images = [img.imgMedicineUrl.url for img in med.images.all() if img.imgMedicineUrl]
                
                medicine_list.append({
                    'id': med.id,
                    'name': med.name,
                    'genre': med.medicineGenre.name if med.medicineGenre else 'Không phân loại',
                    'price': f"{med.price:,.0f} VND",
                    'formatted_price': f"{med.price:,.0f} VND",
                    'benefit': med.benefit,
                    'use': med.use,
                    'description': med.benefit or 'Không có thông tin',
                    'format': med.medicineGenre.name if med.medicineGenre else 'Không phân loại',
                    'producer': med.produce.name if med.produce else 'Không rõ',
                    'images': medicine_images
                })
            
            return context, medicine_list
            
        except Exception as e:
            logger.error(f"Error getting medicine context: {e}")
            return "Không tìm thấy thông tin thuốc.\n", []
    
    def generate_openai_response(self, user_question):
        """Tạo phản hồi bằng OpenAI API"""
        try:
            if not self.openai_available:
                return {
                    'response': 'Xin lỗi, hệ thống AI tư vấn đang bảo trì. Vui lòng liên hệ dược sĩ trực tiếp.',
                    'medicines': [],
                    'type': 'error',
                    'medicines_count': 0
                }
            
            # Lấy context từ database
            context, medicines = self.get_medicine_context(user_question)
            
            # Kiểm tra xem có thuốc nào được tìm thấy không
            if medicines:
                # Có thuốc liên quan - chỉ tư vấn về thuốc có sẵn
                medicine_names = [med['name'] for med in medicines]
                prompt = f"""Bạn là dược sĩ chuyên nghiệp. Khách hàng hỏi: "{user_question}"

Thuốc có sẵn trong nhà thuốc:
{context}

QUY TẮC QUAN TRỌNG:
- CHỈ tư vấn về những thuốc có trong danh sách trên
- KHÔNG đề cập thuốc nào khác ngoài danh sách
- Tập trung vào công dụng, cách dùng, giá cả của thuốc có sẵn
- Đưa ra lời khuyên cụ thể về thuốc phù hợp nhất

Trả lời chuyên nghiệp, không sử dụng emoji."""

                return {
                    'response': self._call_openai_api(prompt),
                    'medicines': medicines,
                    'type': 'openai_response',
                    'medicines_count': len(medicines)
                }
            else:
                # Không có thuốc phù hợp trong kho - CHỈ TRẢ VỀ TEXT, KHÔNG CÓ MEDICINES
                prompt = f"""Bạn là dược sĩ chuyên nghiệp. Khách hàng hỏi: "{user_question}"

Hiện tại nhà thuốc không có thuốc cụ thể nào phù hợp với yêu cầu này.

Hãy trả lời:
- Nếu là lời chào: chào lại thân thiện
- Nếu hỏi thuốc không có: xin lỗi và khuyên tham khảo dược sĩ hoặc bác sĩ
- Nếu hỏi triệu chứng: tư vấn chung và khuyên đến cơ sở y tế

KHÔNG đề cập bất kỳ tên thuốc cụ thể nào. Trả lời ngắn gọn, không emoji."""

                return {
                    'response': self._call_openai_api(prompt),
                    'medicines': [],  # Không có thuốc nào
                    'type': 'text_only',  # Loại phản hồi chỉ có text
                    'medicines_count': 0
                }
            
        except Exception as e:
            logger.error(f"OpenAI API error: {str(e)}")
            return {
                'response': f'Xin lỗi, tôi gặp sự cố khi xử lý câu hỏi của bạn. Vui lòng thử lại sau hoặc liên hệ dược sĩ trực tiếp.',
                'medicines': [],
                'type': 'error',
                'medicines_count': 0
            }
    
    def _call_openai_api(self, prompt):
        """Gọi OpenAI API và trả về response"""
        try:
            response = self.client.chat.completions.create(
                model="gpt-3.5-turbo",
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
            
            # Loại bỏ emoji nếu có (fallback)
            import re
            ai_response = re.sub(r'[^\w\s\u00C0-\u024F\u1E00-\u1EFF.,!?;:()\-]', '', ai_response, flags=re.UNICODE)
            
            return ai_response
            
        except Exception as e:
            logger.error(f"OpenAI API call error: {str(e)}")
            return "Xin lỗi, tôi gặp sự cố khi xử lý câu hỏi của bạn. Vui lòng thử lại sau."
    
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
            # Tạo phản hồi bằng OpenAI
            bot_response_data = self.generate_openai_response(user_message)
            bot_response = bot_response_data['response']
            
            # Lưu lịch sử chat
            user = request.user if request.user.is_authenticated else None
            chat_history = ChatHistory.objects.create(
                user=user,
                user_message=user_message,
                bot_response=bot_response,
                session_id=session_id if not user else None
            )
            
            # Format response để trả về frontend
            response_data = {
                'chat_id': chat_history.id,
                'user_message': user_message,
                'bot_response': bot_response,
                'session_id': session_id,
                'timestamp': chat_history.created_at.isoformat(),
                'type': bot_response_data['type'],
                'response_type': bot_response_data['type'],  # Thêm cho frontend
                'medicines_count': bot_response_data.get('medicines_count', 0),
                'message': bot_response  # Thêm message cho StructuredMessage
            }
            
            # CHỈ thêm thông tin thuốc nếu thực sự có medicines và không phải text_only
            if (bot_response_data.get('medicines') and 
                len(bot_response_data['medicines']) > 0 and 
                bot_response_data['type'] != 'text_only'):
                response_data['medicines'] = bot_response_data['medicines']
            
            return Response(response_data, status=status.HTTP_200_OK)
            
        except Exception as e:
            logger.error(f"Chatbot error: {str(e)}")
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
    
    def get(self, request):
        """Lấy lịch sử chat của user hoặc session"""
        session_id = request.query_params.get('session_id')
        
        if request.user.is_authenticated:
            # User đã đăng nhập - lấy lịch sử theo user
            chat_history = ChatHistory.objects.filter(user=request.user).order_by('-created_at')[:20]
        elif session_id:
            # Anonymous user - lấy lịch sử theo session_id
            chat_history = ChatHistory.objects.filter(session_id=session_id).order_by('-created_at')[:20]
        else:
            return Response({'chats': []})
        
        serializer = serializers.ChatHistorySerializer(chat_history, many=True)
        return Response({'chats': serializer.data})