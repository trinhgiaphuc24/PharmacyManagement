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
from pharmacies.email_service import EmailService
from pharmacies.websocket_service import websocket_service
from rest_framework.response import Response
from rest_framework.decorators import action, api_view, permission_classes
from django.db.models import Q
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework import viewsets, generics, permissions, parsers, status
import requests
from datetime import datetime
from .models import Medicine
from .chatbot.views import ChatBotView
from .models import Order, ShippingFee
from .serializers import OrderSerializer, CreateOrderSerializer, ShippingFeeSerializer


class UserViewSet(viewsets.ViewSet, generics.CreateAPIView):
    queryset = User.objects.filter(is_active=True)
    serializer_class = serializers.UserSerializer
    parser_classes = [parsers.JSONParser, parsers.MultiPartParser]
    permission_classes = [AllowAny]

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


class MedicineGenreViewSet(viewsets.ViewSet, generics.ListAPIView):
    queryset = MedicineGenre.objects.all()
    serializer_class = serializers.MedicineGenreSerializer


class ProduceViewSet(viewsets.ViewSet, generics.ListAPIView):
    queryset = Produce.objects.all()
    serializer_class = serializers.ProduceSerializer


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

    

class MedicineImageViewSet(viewsets.ViewSet, generics.ListAPIView):
    queryset = MedicineImage.objects.all()
    serializer_class = serializers.MedicineImageSerializer


class CartViewSet(viewsets.ViewSet, generics.ListAPIView):
    serializer_class = serializers.CartSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Cart.objects.filter(user=self.request.user)

    @action(detail=False, methods=['get'], url_path='my-cart')
    def my_cart(self, request):
        cart, created = Cart.objects.get_or_create(user=request.user)
        serializer = self.get_serializer(cart)
        return Response(serializer.data)


class CartItemViewSet(viewsets.ViewSet, generics.ListAPIView):
    serializer_class = serializers.CartItemSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return CartItem.objects.filter(cart__user=self.request.user)

    def perform_create(self, serializer):
        cart, created = Cart.objects.get_or_create(user=self.request.user)
        medicine = serializer.validated_data['medicine']
        quantity = serializer.validated_data['quantity']
        total_price = quantity * medicine.price
        serializer.save(cart=cart, total_price=total_price)

    @action(detail=False, methods=['post'], url_path='add-to-cart')
    def add_to_cart(self, request):
        medicine_id = request.data.get('medicine')
        quantity = int(request.data.get('quantity', 1))
        
        if not medicine_id:
            return Response({'error': 'Medicine ID is required'}, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            medicine = Medicine.objects.get(id=medicine_id)
            cart, created = Cart.objects.get_or_create(user=request.user)
            
            # Kiểm tra xem sản phẩm đã có trong cart chưa
            cart_item, item_created = CartItem.objects.get_or_create(
                cart=cart,
                medicine=medicine,
                defaults={
                    'quantity': quantity,
                    'total_price': quantity * medicine.price
                }
            )
            
            if not item_created:
                # Nếu đã tồn tại, cập nhật số lượng và total_price
                cart_item.quantity += quantity
                cart_item.total_price = cart_item.quantity * medicine.price
                cart_item.save()
            
            serializer = self.get_serializer(cart_item)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
            
        except Medicine.DoesNotExist:
            return Response({'error': 'Medicine not found'}, status=status.HTTP_404_NOT_FOUND)

    @action(detail=True, methods=['patch'], url_path='update-quantity')
    def update_quantity(self, request, pk=None):
        """Cập nhật số lượng sản phẩm trong cart"""
        cart_item = self.get_object()
        new_quantity = request.data.get('quantity')
        
        if new_quantity is None:
            return Response({'error': 'Quantity is required'}, status=status.HTTP_400_BAD_REQUEST)
        
        new_quantity = int(new_quantity)
        if new_quantity <= 0:
            cart_item.delete()
            return Response({'message': 'Item removed from cart'}, status=status.HTTP_200_OK)
        
        cart_item.quantity = new_quantity
        cart_item.total_price = new_quantity * cart_item.medicine.price
        cart_item.save()
        
        serializer = self.get_serializer(cart_item)
        return Response(serializer.data)


class OrderViewSet(viewsets.ViewSet, generics.ListAPIView, generics.RetrieveAPIView):
    serializer_class = OrderSerializer
    permission_classes = [IsAuthenticated]
    pagination_class = paginators.OrderPagination
    
    def get_queryset(self):
        queryset = Order.objects.filter(user=self.request.user).order_by('-createdAt')
        
        order_id = self.request.query_params.get('order_id')
        if order_id:
            queryset = queryset.filter(id=order_id)
        
        status = self.request.query_params.get('status')
        if status:
            queryset = queryset.filter(status=status)
        
        start_date = self.request.query_params.get('start_date')
        if start_date:
            queryset = queryset.filter(date=start_date)
        
        return queryset
    
    @action(detail=False, methods=['get'], url_path='staff-all-orders')
    def staff_all_orders(self, request):
        if not request.user.userRole in ['staff']:
            return Response({
                'success': False,
                'message': 'Bạn không có quyền truy cập'
            }, status=status.HTTP_403_FORBIDDEN)
        
        queryset = Order.objects.all().order_by('-createdAt')
        
        order_id = request.query_params.get('order_id')
        if order_id:
            queryset = queryset.filter(id=order_id)
        
        status_filter = request.query_params.get('status')
        if status_filter:
            queryset = queryset.filter(status=status_filter)
        
        start_date = request.query_params.get('start_date')
        if start_date:
            queryset = queryset.filter(date=start_date)
        
        page = self.paginate_queryset(queryset)
        
        if page is not None:
            serializer = OrderSerializer(page, many=True, context={'request': request})
            return self.get_paginated_response({
                'success': True,
                'data': serializer.data
            })
        
        serializer = OrderSerializer(queryset, many=True, context={'request': request})
        return Response({
            'success': True,
            'data': serializer.data
        })
    
    def retrieve(self, request, pk=None):
        order = Order.objects.filter(pk=pk, user=request.user).first()
        serializer = self.get_serializer(order)
        return Response({
            'success': True,
            'data': serializer.data
        })
    
    @action(detail=False, methods=['post'], url_path='create-order')
    def create_order(self, request):
        serializer = CreateOrderSerializer(data=request.data, context={'request': request})
        
        if serializer.is_valid():
            try:
                order = serializer.save()
            
                websocket_service.send_order_created_notification(
                    user_id=request.user.id,
                    order_id=order.id,
                    total=order.total
                )
                
                customer_name = f"{request.user.first_name} {request.user.last_name}"
                websocket_service.send_staff_new_order_notification(
                    order_id=order.id,
                    customer_name=customer_name,
                    total=order.total
                )

                order_serializer = OrderSerializer(order, context={'request': request})
                return Response({
                    'success': True,
                    'message': 'Đơn hàng được tạo thành công',
                    'data': order_serializer.data
                }, status=status.HTTP_201_CREATED)
            except Exception as e:
                return Response({
                    'success': False,
                    'message': f'Lỗi tạo đơn hàng: {str(e)}'
                }, status=status.HTTP_400_BAD_REQUEST)
        
        return Response({
            'success': False,
            'message': 'Dữ liệu không hợp lệ',
            'errors': serializer.errors
        }, status=status.HTTP_400_BAD_REQUEST)
    
    
    @action(detail=False, methods=['get'], url_path='my-orders')
    def my_orders(self, request):
        orders = self.get_queryset()
        page = self.paginate_queryset(orders)
        
        if page is not None:
            serializer = OrderSerializer(page, many=True, context={'request': request})
            return self.get_paginated_response({
                'success': True,
                'data': serializer.data
            })
        
        serializer = OrderSerializer(orders, many=True, context={'request': request})
        return Response({
            'success': True,
            'data': serializer.data
        })
    
    @action(detail=True, methods=['patch'], url_path='cancel')
    def cancel_order(self, request, pk=None):
        order = Order.objects.filter(pk=pk, user=request.user).first()
        if order.status != 'pending' and order.status != 'waiting_for_pickup':
            return Response({
                'success': False,
                'message': 'Chỉ có thể hủy đơn hàng đang chờ xác nhận'
            }, status=status.HTTP_400_BAD_REQUEST)
        order.status = 'canceled'
        order.save()
        
        serializer = OrderSerializer(order, context={'request': request})
        return Response({
            'success': True,
            'message': 'Đơn hàng đã được hủy',
            'data': serializer.data
        })
    
    @action(detail=True, methods=['patch'], url_path='update-status')
    def update_status(self, request, pk=None):
        if not request.user.userRole in ['staff']:
            return Response({
                'success': False,
                'message': 'Bạn không có quyền cập nhật trạng thái đơn hàng'
            }, status=status.HTTP_403_FORBIDDEN)
        
        order = Order.objects.filter(pk=pk).first()
        
        new_status = request.data.get('status')
        if not new_status:
            return Response({
                'success': False,
                'message': 'Trạng thái mới là bắt buộc'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        old_status = order.status
        order.status = new_status
        order.save()
        
        # 📦 Gửi thông báo thay đổi trạng thái cho customer
        try:
            websocket_service.send_order_status_update(
                user_id=order.user.id,
                order_id=order.id,
                old_status=old_status,
                new_status=new_status
            )
        except Exception as ws_error:
            print(f"⚠️ WebSocket status notification error: {ws_error}")
        
        serializer = OrderSerializer(order, context={'request': request})
        return Response({
            'success': True,
            'message': 'Cập nhật trạng thái thành công',
            'data': serializer.data
        })
    
    @action(detail=True, methods=['patch'], url_path='update-shipping')
    def update_shipping(self, request, pk=None):
        try:
            order = Order.objects.filter(pk=pk, user=request.user).first()
            if not order:
                return Response({
                    'success': False,
                    'message': 'Không tìm thấy đơn hàng'
                }, status=status.HTTP_404_NOT_FOUND)
            
            # Only allow editing for pending or waiting orders
            if order.status not in ['pending', 'waiting_for_pickup']:
                return Response({
                    'success': False,
                    'message': 'Chỉ có thể chỉnh sửa đơn hàng đang chờ xử lý hoặc chờ lấy hàng'
                }, status=status.HTTP_400_BAD_REQUEST)
            
            # Get shipping information from request
            full_name = request.data.get('full_name')
            phone_number = request.data.get('phoneNumber')
            specific = request.data.get('specific')
            commune = request.data.get('commune')
            district = request.data.get('district')
            province = request.data.get('province')
            note = request.data.get('note')
            
            if not full_name or not phone_number:
                return Response({
                    'success': False,
                    'message': 'Vui lòng điền đầy đủ thông tin bắt buộc'
                }, status=status.HTTP_400_BAD_REQUEST)
            
            online_order = getattr(order, 'online_order', None)
            if online_order:
                ship_info, created = OnlineOrderShip.objects.get_or_create(
                    online_order=online_order,
                    defaults={
                        'full_name': full_name,
                        'phoneNumber': phone_number,
                        'specific': specific or '',
                        'commune': commune or '',
                        'district': district or '',
                        'province': province or '',
                        'note': note or ''
                    }
                )
                
                if not created:
                    ship_info.full_name = full_name
                    ship_info.phoneNumber = phone_number
                    ship_info.specific = specific or ''
                    ship_info.commune = commune or ''
                    ship_info.district = district or ''
                    ship_info.province = province or ''
                    ship_info.note = note or ''
                    ship_info.save()
            
            serializer = OrderSerializer(order, context={'request': request})
            return Response({
                'success': True,
                'message': 'Cập nhật thông tin giao hàng thành công',
                'data': serializer.data
            })
            
        except Exception as e:
            return Response({
                'success': False,
                'message': f'Lỗi cập nhật thông tin: {str(e)}'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    
    def remove_vietnamese_accents(self, text):
        if not text:
            return ""
        
        vietnamese_chars = {
            'à': 'a', 'á': 'a', 'ạ': 'a', 'ả': 'a', 'ã': 'a', 'â': 'a', 'ầ': 'a', 'ấ': 'a', 'ậ': 'a', 'ẩ': 'a', 'ẫ': 'a', 'ă': 'a', 'ằ': 'a', 'ắ': 'a', 'ặ': 'a', 'ẳ': 'a', 'ẵ': 'a',
            'è': 'e', 'é': 'e', 'ẹ': 'e', 'ẻ': 'e', 'ẽ': 'e', 'ê': 'e', 'ề': 'e', 'ế': 'e', 'ệ': 'e', 'ể': 'e', 'ễ': 'e',
            'ì': 'i', 'í': 'i', 'ị': 'i', 'ỉ': 'i', 'ĩ': 'i',
            'ò': 'o', 'ó': 'o', 'ọ': 'o', 'ỏ': 'o', 'õ': 'o', 'ô': 'o', 'ồ': 'o', 'ố': 'o', 'ộ': 'o', 'ổ': 'o', 'ỗ': 'o', 'ơ': 'o', 'ờ': 'o', 'ớ': 'o', 'ợ': 'o', 'ở': 'o', 'ỡ': 'o',
            'ù': 'u', 'ú': 'u', 'ụ': 'u', 'ủ': 'u', 'ũ': 'u', 'ư': 'u', 'ừ': 'u', 'ứ': 'u', 'ự': 'u', 'ử': 'u', 'ữ': 'u',
            'ỳ': 'y', 'ý': 'y', 'ỵ': 'y', 'ỷ': 'y', 'ỹ': 'y',
            'đ': 'd',
            'À': 'A', 'Á': 'A', 'Ạ': 'A', 'Ả': 'A', 'Ã': 'A', 'Â': 'A', 'Ầ': 'A', 'Ấ': 'A', 'Ậ': 'A', 'Ẩ': 'A', 'Ẫ': 'A', 'Ă': 'A', 'Ằ': 'A', 'Ắ': 'A', 'Ặ': 'A', 'Ẳ': 'A', 'Ẵ': 'A',
            'È': 'E', 'É': 'E', 'Ẹ': 'E', 'Ẻ': 'E', 'Ẽ': 'E', 'Ê': 'E', 'Ề': 'E', 'Ế': 'E', 'Ệ': 'E', 'Ể': 'E', 'Ễ': 'E',
            'Ì': 'I', 'Í': 'I', 'Ị': 'I', 'Ỉ': 'I', 'Ĩ': 'I',
            'Ò': 'O', 'Ó': 'O', 'Ọ': 'O', 'Ỏ': 'O', 'Õ': 'O', 'Ô': 'O', 'Ồ': 'O', 'Ố': 'O', 'Ộ': 'O', 'Ổ': 'O', 'Ỗ': 'O', 'Ơ': 'O', 'Ờ': 'O', 'Ớ': 'O', 'Ợ': 'O', 'Ở': 'O', 'Ỡ': 'O',
            'Ù': 'U', 'Ú': 'U', 'Ụ': 'U', 'Ủ': 'U', 'Ũ': 'U', 'Ư': 'U', 'Ừ': 'U', 'Ứ': 'U', 'Ự': 'U', 'Ử': 'U', 'Ữ': 'U',
            'Ỳ': 'Y', 'Ý': 'Y', 'Ỵ': 'Y', 'Ỷ': 'Y', 'Ỹ': 'Y',
            'Đ': 'D'
        }
        
        result = ""
        for char in text:
            result += vietnamese_chars.get(char, char)
        return result

    @action(detail=True, methods=['get'], url_path='export-pdf')
    def export_pdf(self, request, pk=None):
        """Export order as PDF"""
        try:
            # Get order for current user
            order = Order.objects.filter(pk=pk, user=request.user).first()
            if not order:
                return Response({
                    'success': False,
                    'message': 'Không tìm thấy đơn hàng'
                }, status=status.HTTP_404_NOT_FOUND)
            
            # Only allow PDF export for delivered orders
            if order.status != 'delivered':
                return Response({
                    'success': False,
                    'message': 'Chỉ có thể xuất hóa đơn cho đơn hàng đã giao'
                }, status=status.HTTP_400_BAD_REQUEST)
            
            from django.http import HttpResponse
            from reportlab.lib.pagesizes import A4
            from reportlab.pdfgen import canvas
            from reportlab.lib.units import mm
            from reportlab.pdfbase import pdfmetrics
            from reportlab.pdfbase.ttfonts import TTFont
            from io import BytesIO
            import unicodedata
            
            # Create PDF buffer
            buffer = BytesIO()
            
            # Create PDF canvas
            p = canvas.Canvas(buffer, pagesize=A4)
            width, height = A4
            
            # Use Times-Roman fonts for better Vietnamese support
            p.setFont("Times-Roman", 12)
            
            # Header
            p.setFillColorRGB(0.13, 0.55, 0.13)  # Green color
            p.rect(0, height - 40*mm, width, 40*mm, fill=1)
            
            p.setFillColorRGB(1, 1, 1)  # White text
            p.setFont("Times-Bold", 18)
            text = self.remove_vietnamese_accents("NHA THUOC GIA PHUC")
            text_width = p.stringWidth(text, "Times-Bold", 18)
            p.drawString((width - text_width) / 2, height - 18*mm, text)
            
            p.setFont("Times-Roman", 11)
            text = self.remove_vietnamese_accents("313 Hai Ba Trung, Q. Le Chan, TP. Hai Phong")
            text_width = p.stringWidth(text, "Times-Roman", 11)
            p.drawString((width - text_width) / 2, height - 28*mm, text)
            
            text = "Hotline: 1800 6821 | nhathuocgiaphuc.com"
            text_width = p.stringWidth(text, "Times-Roman", 11)
            p.drawString((width - text_width) / 2, height - 34*mm, text)
            
            # Invoice title
            p.setFillColorRGB(0, 0, 0)
            p.setFont("Times-Bold", 16)
            text = self.remove_vietnamese_accents("HOA DON BAN THUOC")
            text_width = p.stringWidth(text, "Times-Bold", 16)
            p.drawString((width - text_width) / 2, height - 50*mm, text)
            
            # Order info
            y_position = height - 65*mm
            p.setFont("Times-Roman", 11)
            
            order_date = order.date.strftime('%d/%m/%Y') if order.date else order.createdAt.strftime('%d/%m/%Y')
            p.drawString(20*mm, y_position, f"So hoa don: HD{str(order.id).zfill(4)}")
            p.drawRightString(width - 20*mm, y_position, f"Ngay lap: {order_date}")
            
            # Customer info section
            y_position -= 20*mm
            p.setFont("Times-Bold", 12)
            p.drawString(20*mm, y_position, self.remove_vietnamese_accents("THONG TIN KHACH HANG"))
            
            y_position -= 8*mm
            p.setFont("Times-Roman", 10)
            customer_name = f"{order.user.first_name} {order.user.last_name}".strip() if order.user else "Khach le"
            phone = getattr(order.user, 'phone_number', 'N/A') if order.user else 'N/A'
            email = getattr(order.user, 'email', 'N/A') if order.user else 'N/A'
            
            # Remove accents from customer info
            customer_name = self.remove_vietnamese_accents(customer_name)
            
            p.drawString(20*mm, y_position, f"Khach hang: {customer_name}")
            y_position -= 6*mm
            p.drawString(20*mm, y_position, f"Dien thoai: {phone}")
            y_position -= 6*mm
            p.drawString(20*mm, y_position, f"Email: {email}")
            
            # Order details section
            y_position -= 15*mm
            p.setFont("Times-Bold", 12)
            p.drawString(20*mm, y_position, self.remove_vietnamese_accents("THONG TIN DON HANG"))
            
            y_position -= 8*mm
            p.setFont("Times-Roman", 10)
            
            # Status and payment info
            status_map = {
                'pending': 'Cho xac nhan',
                'waiting_for_pickup': 'Cho lay hang',
                'shipping': 'Dang giao hang', 
                'delivered': 'Da giao',
                'canceled': 'Da huy'
            }
            payment_map = {
                'cod': 'Thanh toan khi nhan',
                'vnpay': 'VNPay'
            }
            
            p.drawString(20*mm, y_position, f"Trang thai: {status_map.get(order.status, order.status)}")
            y_position -= 6*mm
            p.drawString(20*mm, y_position, f"Phuong thuc thanh toan: {payment_map.get(order.paymentMethod, order.paymentMethod)}")
            
            # Table header
            y_position -= 20*mm
            p.setFillColorRGB(0.13, 0.55, 0.13)
            p.rect(20*mm, y_position - 10*mm, width - 40*mm, 10*mm, fill=1)
            
            p.setFillColorRGB(1, 1, 1)
            p.setFont("Times-Bold", 10)
            p.drawString(25*mm, y_position - 6*mm, "STT")
            p.drawString(40*mm, y_position - 6*mm, "Ten thuoc")
            p.drawString(120*mm, y_position - 6*mm, "SL")
            p.drawString(135*mm, y_position - 6*mm, "Don gia")
            p.drawString(165*mm, y_position - 6*mm, "Thanh tien")
            
            # Table content
            y_position -= 15*mm
            p.setFillColorRGB(0, 0, 0)
            p.setFont("Times-Roman", 9)
            
            subtotal = 0
            for index, item in enumerate(order.details.all()):
                if y_position < 50*mm:  # New page if needed
                    p.showPage()
                    y_position = height - 50*mm
                
                item_total = item.price * item.quantity
                subtotal += item_total
                
                # Alternating row colors
                if index % 2 == 0:
                    p.setFillColorRGB(0.97, 0.97, 0.97)
                    p.rect(20*mm, y_position - 4*mm, width - 40*mm, 10*mm, fill=1)
                
                p.setFillColorRGB(0, 0, 0)
                p.drawString(25*mm, y_position, f"{index + 1}")
                
                # Remove accents from medicine name
                medicine_name = item.medicine.name if item.medicine else "San pham"
                medicine_name = self.remove_vietnamese_accents(medicine_name)
                if len(medicine_name) > 40:
                    medicine_name = medicine_name[:37] + "..."
                p.drawString(40*mm, y_position, medicine_name)
                
                p.drawString(122*mm, y_position, f"{item.quantity}")
                p.drawRightString(155*mm, y_position, f"{int(item.price):,} VND")
                p.drawRightString(185*mm, y_position, f"{int(item_total):,} VND")
                
                y_position -= 10*mm
            
            # Summary section - match table width (20mm to width-20mm)
            y_position -= 15*mm
            
            # Summary background rectangle
            p.setFillColorRGB(0.95, 0.95, 0.95)
            p.rect(20*mm, y_position - 27*mm, width - 40*mm, 25*mm, fill=1)
            
            # Summary content
            p.setFillColorRGB(0, 0, 0)
            p.setFont("Times-Roman", 10)
            
            # Subtotal line
            y_position -= 8*mm
            p.drawString(25*mm, y_position, "Tam tinh:")
            p.drawRightString(width - 25*mm, y_position, f"{int(subtotal):,} VND")
            
            # Shipping fee line
            y_position -= 6*mm
            shipping_fee = 22000 if hasattr(order, 'online_order') and order.online_order.shipping_method == 'home_delivery' else 0
            p.drawString(25*mm, y_position, "Phi van chuyen:")
            p.drawRightString(width - 25*mm, y_position, "Mien phi" if shipping_fee == 0 else f"{shipping_fee:,} VND")
            
            # Total line with bold font and green color
            y_position -= 10*mm
            p.setFont("Times-Bold", 12)
            p.setFillColorRGB(0.13, 0.55, 0.13)
            p.drawString(25*mm, y_position, "TONG CONG:")
            p.drawRightString(width - 25*mm, y_position, f"{int(order.total):,} VND")
            
            
            # Footer with signature
            p.setFillColorRGB(0, 0, 0)
            p.setFont("Times-Roman", 10)
            signature_y = 50*mm
            current_date = order.createdAt.strftime('%d/%m/%Y') if order.createdAt else order.date.strftime('%d/%m/%Y')
            text = f"{current_date}"
            text_width = p.stringWidth(text, "Times-Roman", 10)
            p.drawString((width - text_width) / 2, signature_y, text)
            
            p.drawString(40*mm, signature_y - 15*mm, "Nguoi ban hang")
            p.drawRightString(width - 40*mm, signature_y - 15*mm, "Khach hang")
            
            # Footer message
            p.setFillColorRGB(0.5, 0.5, 0.5)
            p.setFont("Times-Italic", 9)
            text = self.remove_vietnamese_accents("Cam on quy khach da tin tuong va su dung dich vu cua chung toi!")
            text_width = p.stringWidth(text, "Times-Italic", 9)
            p.drawString((width - text_width) / 2, 25*mm, text)
            
            text = self.remove_vietnamese_accents("Moi thac mac xin lien he: 1800 6821 | nhathuocgiaphuc.com")
            text_width = p.stringWidth(text, "Times-Italic", 9)
            p.drawString((width - text_width) / 2, 20*mm, text)
            
            # Save PDF
            p.save()
            
            # Return PDF response
            buffer.seek(0)
            response = HttpResponse(buffer.getvalue(), content_type='application/pdf')
            response['Content-Disposition'] = f'attachment; filename="hoa-don-{order.id}.pdf"'
            
            return response
            
        except Exception as e:
            return Response({
                'success': False,
                'message': f'Lỗi xuất hóa đơn: {str(e)}'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class ShippingFeeViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = ShippingFee.objects.all()
    serializer_class = ShippingFeeSerializer
    permission_classes = [IsAuthenticated]


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def order_email(request):
    try:
        order_id = request.data.get('order_id')
        if not order_id:
            return Response({'error': 'Order ID is required'}, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            order = Order.objects.get(id=order_id, user=request.user)
        except Order.DoesNotExist:
            return Response({'error': 'Order not found'}, status=status.HTTP_404_NOT_FOUND)
        
        if not order.user.email:
            return Response({'error': 'User email not found'}, status=status.HTTP_400_BAD_REQUEST)
        
        success = EmailService.send_order_success_email(order)
        
        if success:
            return Response({'message': f'Email sent successfully to {order.user.email}'}, status=status.HTTP_200_OK)
        else:
            return Response({'error': 'Failed to send email'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
            
    except Exception as e:
        return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)