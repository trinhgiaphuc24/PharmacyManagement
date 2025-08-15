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
from rest_framework.response import Response
from rest_framework.decorators import action, api_view, permission_classes
from django.db.models import Q
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework import viewsets, generics, permissions, parsers, status
import requests
import logging
from datetime import datetime
from rest_framework import viewsets, generics
from rest_framework.decorators import action
from rest_framework.response import Response
from django.db.models import Q
from .models import Medicine
from . import serializers, paginators

# Import ChatBotView từ chatbot package
from .chatbot.views import ChatBotView
# logger = logging.getLogger(__name__)


class UserViewSet(viewsets.ViewSet, generics.CreateAPIView):
    queryset = User.objects.filter(is_active=True)
    serializer_class = serializers.UserSerializer
    parser_classes = [parsers.MultiPartParser]
    permission_classes = [AllowAny]  # Allow access without authentication for registration

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
    serializer_class = serializers.CartSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Cart.objects.filter(user=self.request.user)

    @action(detail=False, methods=['get'], url_path='my-cart')
    def my_cart(self, request):
        cart, created = Cart.objects.get_or_create(user=request.user)
        serializer = self.get_serializer(cart)
        return Response(serializer.data)


class CartItemViewSet(viewsets.ModelViewSet):
    serializer_class = serializers.CartItemSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        # Chỉ trả về cart items của user hiện tại
        return CartItem.objects.filter(cart__user=self.request.user)

    def perform_create(self, serializer):
        # Tự động gán cart của user hiện tại khi tạo cart item
        cart, created = Cart.objects.get_or_create(user=self.request.user)
        medicine = serializer.validated_data['medicine']
        quantity = serializer.validated_data['quantity']
        total_price = quantity * medicine.price
        serializer.save(cart=cart, total_price=total_price)

    @action(detail=False, methods=['post'], url_path='add-to-cart')
    def add_to_cart(self, request):
        """Thêm sản phẩm vào cart hoặc cập nhật số lượng nếu đã tồn tại"""
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


from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.shortcuts import get_object_or_404
from .models import Order, ShippingFee
from .serializers import OrderSerializer, CreateOrderSerializer, ShippingFeeSerializer


class OrderViewSet(viewsets.ModelViewSet):
    serializer_class = OrderSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        # Only return orders for the authenticated user
        queryset = Order.objects.filter(user=self.request.user).order_by('-createdAt')
        
        # Search by order ID
        order_id = self.request.query_params.get('order_id')
        if order_id:
            queryset = queryset.filter(id=order_id)
        
        # Filter by status
        status = self.request.query_params.get('status')
        if status:
            queryset = queryset.filter(status=status)
        
        # Filter by date (only start_date for simplicity)
        start_date = self.request.query_params.get('start_date')
        if start_date:
            queryset = queryset.filter(date=start_date)
        
        return queryset
    
    def retrieve(self, request, pk=None):
        """
        Override the default retrieve method to add custom response format
        """
        order = get_object_or_404(Order, pk=pk, user=request.user)
        serializer = self.get_serializer(order)
        return Response({
            'success': True,
            'data': serializer.data
        })
    
    @action(detail=False, methods=['post'], url_path='create-order')
    def create_order(self, request):
        """
        Tạo đơn hàng mới từ giỏ hàng
        """
        serializer = CreateOrderSerializer(data=request.data, context={'request': request})
        
        if serializer.is_valid():
            try:
                order = serializer.save()
                
                # Không gửi email ở đây, chỉ gửi khi thanh toán thành công
                # Email sẽ được gửi trong VNPayReturnView khi thanh toán thành công
                
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
    
    # @action(detail=True, methods=['get'])
    # def detail(self, request, pk=None):
    #     """
    #     Lấy chi tiết đơn hàng
    #     """
    #     order = get_object_or_404(Order, pk=pk, user=request.user)
    #     serializer = OrderSerializer(order, context={'request': request})
    #     return Response({
    #         'success': True,
    #         'data': serializer.data
    #     })
    
    @action(detail=False, methods=['get'], url_path='my-orders')
    def my_orders(self, request):
        """
        Lấy danh sách đơn hàng của user hiện tại
        """
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
        """
        Hủy đơn hàng (chỉ được phép hủy khi status = pending)
        """
        order = get_object_or_404(Order, pk=pk, user=request.user)
        
        if order.status != 'pending':
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


class ShippingFeeViewSet(viewsets.ReadOnlyModelViewSet):
    """
    ViewSet chỉ đọc cho ShippingFee
    """
    queryset = ShippingFee.objects.all()
    serializer_class = ShippingFeeSerializer
    permission_classes = [IsAuthenticated]


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def order_email(request):
    """
    API test gửi email đặt hàng thành công
    """
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
        
        # Gửi email
        success = EmailService.send_order_success_email(order)
        
        if success:
            return Response({'message': f'Email sent successfully to {order.user.email}'}, status=status.HTTP_200_OK)
        else:
            return Response({'error': 'Failed to send email'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
            
    except Exception as e:
        return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
