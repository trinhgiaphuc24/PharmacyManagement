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
from django.db.models import Count, Sum
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
from datetime import datetime, date
from .models import Medicine
from .chatbot.views import ChatBotView
from .models import Order, ShippingFee
from .serializers import UserSerializer, OrderSerializer, ShippingFeeSerializer, StaffDirectSaleSerializer


class UserViewSet(viewsets.ViewSet, generics.CreateAPIView):
    queryset = User.objects.filter(is_active=True)
    serializer_class = serializers.UserSerializer
    parser_classes = [parsers.JSONParser, parsers.MultiPartParser]
    permission_classes = [AllowAny]

    @action(methods=['GET', 'PATCH'], url_path='current-user', detail=False, permission_classes=[IsAuthenticated])
    def current_user(self, request):
        user = request.user
        if request.method == 'GET':
            return Response(serializers.UserSerializer(user).data)
        elif request.method == 'PATCH':
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

    def partial_update(self, request, pk=None):
        if request.user.userRole != 'staff':
            return Response({'success': False, 'message': 'Chỉ staff mới có quyền cập nhật số lượng thuốc'}, status=status.HTTP_403_FORBIDDEN)

        try:
            medicine = Medicine.objects.get(pk=pk)
            new_quantity = request.data.get('quantity')
            
            if new_quantity is None:
                return Response({
                    'success': False,
                    'message': 'Số lượng là bắt buộc'
                }, status=status.HTTP_400_BAD_REQUEST)
            
            try:
                new_quantity = int(new_quantity)
                if new_quantity < 0:
                    return Response({
                        'success': False,
                        'message': 'Số lượng không được âm'
                    }, status=status.HTTP_400_BAD_REQUEST)
            except ValueError:
                return Response({
                    'success': False,
                    'message': 'Số lượng phải là số nguyên'
                }, status=status.HTTP_400_BAD_REQUEST)
            
            old_quantity = medicine.quantity
            medicine.quantity = new_quantity
            medicine.save()
            
            return Response({
                'success': True,
                'message': f'Cập nhật số lượng thành công: {old_quantity} → {new_quantity}',
                'data': {
                    'id': medicine.id,
                    'name': medicine.name,
                    'old_quantity': old_quantity,
                    'new_quantity': new_quantity
                }
            })
            
        except Medicine.DoesNotExist:
            return Response({
                'success': False,
                'message': 'Không tìm thấy thuốc'
            }, status=status.HTTP_404_NOT_FOUND)

    def get_queryset(self):
        queryset = self.queryset
        q = self.request.query_params.get('q')
        if q:
            queryset = queryset.filter(Q(name__icontains=q))
        medicine_id = self.request.query_params.get('medicine_id')
        if medicine_id:
            queryset = queryset.filter(id=medicine_id)
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

    @action(detail=False, methods=['get'], url_path='best-selling')
    def best_selling(self, request):
        best_selling_medicines = Medicine.objects.filter(orderDetails__order__status='delivered').annotate(total_sold=Sum('orderDetails__quantity')).order_by('-total_sold')[:10]
        medicines_data = []
        for medicine in best_selling_medicines:
            medicine_data = self.get_serializer(medicine).data
            medicine_data['total_sold'] = medicine.total_sold
            medicines_data.append(medicine_data)
        return Response({'success': True, 'data': medicines_data})
    

class MedicineImageViewSet(viewsets.ViewSet, generics.ListAPIView):
    queryset = MedicineImage.objects.all()
    serializer_class = serializers.MedicineImageSerializer


class ShippingFeeViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = ShippingFee.objects.all()
    serializer_class = ShippingFeeSerializer
    permission_classes = [IsAuthenticated]


class CartViewSet(viewsets.ViewSet, generics.ListAPIView):
    serializer_class = serializers.CartSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        if self.request.user.userRole == 'staff':
            return Cart.objects.none()
        return Cart.objects.filter(user=self.request.user)

    @action(detail=False, methods=['get'], url_path='my-cart')
    def my_cart(self, request):
        if request.user.userRole == 'staff':
            return Response(status=status.HTTP_403_FORBIDDEN)
        
        cart = Cart.objects.select_related('user').prefetch_related(
            'items__medicine',
            'items__medicine__medicineGenre', 
            'items__medicine__produce',
            'items__medicine__images'
        ).get(user=request.user)
        
        serializer = self.get_serializer(cart)
        return Response(serializer.data)


class CartItemViewSet(viewsets.ViewSet, generics.ListAPIView):
    serializer_class = serializers.CartItemSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        if self.request.user.userRole == 'staff':
            return CartItem.objects.none()
        return CartItem.objects.filter(cart__user=self.request.user)

    def perform_create(self, serializer):
        if self.request.user.userRole == 'staff':
            raise serializers.ValidationError("Staff không được phép sử dụng giỏ hàng")
        cart = Cart.objects.get(user=self.request.user)
        medicine = serializer.validated_data['medicine']
        quantity = serializer.validated_data['quantity']
        total_price = quantity * medicine.price
        serializer.save(cart=cart, total_price=total_price)

    @action(detail=False, methods=['post'], url_path='add-to-cart')
    def add_to_cart(self, request):
        if request.user.userRole == 'staff':
            return Response(status=status.HTTP_403_FORBIDDEN)
        medicine_id = request.data.get('medicine')
        quantity = int(request.data.get('quantity', 1))
        medicine = Medicine.objects.get(id=medicine_id)
        
        if medicine.quantity < quantity:
            return Response({
                'success': False,
                'message': f'Không đủ hàng cho thuốc {medicine.name}. Còn lại: {medicine.quantity}'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        cart = Cart.objects.get(user=request.user)
        cart_item, item_created = CartItem.objects.get_or_create(
            cart=cart,
            medicine=medicine,
            defaults={
                'quantity': quantity,
                'total_price': quantity * medicine.price
            }
        )
        if not item_created:
            new_quantity = cart_item.quantity + quantity
            
            if medicine.quantity < new_quantity:
                return Response({
                    'success': False,
                    'message': f'Không đủ hàng cho thuốc {medicine.name}. Còn lại: {medicine.quantity}, trong giỏ: {cart_item.quantity}'
                }, status=status.HTTP_400_BAD_REQUEST)
            
            cart_item.quantity = new_quantity
            cart_item.total_price = cart_item.quantity * medicine.price
            cart_item.save()
        serializer = self.get_serializer(cart_item)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=['patch'], url_path='update-quantity')
    def update_quantity(self, request, pk=None):
        cart_item = self.get_object()
        new_quantity = request.data.get('quantity')
        new_quantity = int(new_quantity)
        if new_quantity <= 0:
            cart_item.delete()
            return Response({'message': 'Item removed from cart'}, status=status.HTTP_200_OK)
        
        if cart_item.medicine.quantity < new_quantity:
            return Response({
                'success': False,
                'message': f'Không đủ hàng cho thuốc {cart_item.medicine.name}. Còn lại: {cart_item.medicine.quantity}'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        cart_item.quantity = new_quantity
        cart_item.total_price = new_quantity * cart_item.medicine.price
        cart_item.save()
        serializer = self.get_serializer(cart_item)
        return Response(serializer.data)
    
    def destroy(self, request, pk=None):
        cart_item = CartItem.objects.get(pk=pk, cart__user=request.user)
        cart_item.delete()
        return Response({'message': 'Item removed from cart successfully'}, status=status.HTTP_200_OK)


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
            return Response({'success': False,'message': 'Bạn không có quyền truy cập'}, status=status.HTTP_403_FORBIDDEN)
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
        serializer = OrderSerializer(page, many=True, context={'request': request})
        return self.get_paginated_response({
            'success': True,
            'data': serializer.data
        })
        
        # serializer = OrderSerializer(queryset, many=True, context={'request': request})
        # return Response({
        #     'success': True,
        #     'data': serializer.data
        # })
    
    def retrieve(self, request, pk=None):
        order = Order.objects.filter(pk=pk, user=request.user).first()
        serializer = self.get_serializer(order)
        return Response({'success': True,'data': serializer.data})
    
    @action(detail=False, methods=['post'], url_path='create-order')
    def create_order(self, request):
        serializer = OrderSerializer(data=request.data, context={'request': request})
        
        if serializer.is_valid():
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
    
        websocket_service.send_order_status_update(
            user_id=order.user.id,
            order_id=order.id,
            old_status=old_status,
            new_status=new_status
        )
        
        serializer = OrderSerializer(order, context={'request': request})
        return Response({
            'success': True,
            'message': 'Cập nhật trạng thái thành công',
            'data': serializer.data
        })
    
    @action(detail=True, methods=['patch'], url_path='update-shipping')
    def update_shipping(self, request, pk=None):
        order = Order.objects.filter(pk=pk, user=request.user).first()
        if order.status not in ['pending', 'waiting_for_pickup']:
            return Response({'success': False,'message': 'Chỉ có thể chỉnh sửa đơn hàng đang chờ xử lý hoặc chờ lấy hàng'}, status=status.HTTP_400_BAD_REQUEST)
        full_name = request.data.get('full_name')
        phone_number = request.data.get('phoneNumber')
        specific = request.data.get('specific')
        commune = request.data.get('commune')
        district = request.data.get('district')
        province = request.data.get('province')
        note = request.data.get('note')
        online_order = getattr(order, 'online_order', None)
        if online_order and hasattr(online_order, 'ship_info'):
            ship_info = online_order.ship_info
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
    
    @action(detail=False, methods=['post'], url_path='staff-direct-sale')
    def staff_direct_sale(self, request):
        if request.user.userRole != 'staff':
            return Response({'success': False,'message': 'Chỉ staff mới có quyền bán trực tiếp'}, status=status.HTTP_403_FORBIDDEN)
        serializer = StaffDirectSaleSerializer(data=request.data)
        if serializer.is_valid():
            result = serializer.save()
            order = result['order']
            customer = result['customer']
            order_serializer = OrderSerializer(order, context={'request': request})
            return Response({
                'success': True,
                'message': 'Bán hàng trực tiếp thành công',
                'data': {
                    'order': order_serializer.data,
                    'customer': {
                        'id': customer.id,
                        'name': customer.last_name,
                        'phone': customer.phone_number
                    }
                }
            }, status=status.HTTP_201_CREATED)
        else:
            return Response({
                'success': False,
                'message': 'Dữ liệu không hợp lệ',
                'errors': serializer.errors
            }, status=status.HTTP_400_BAD_REQUEST)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def order_email(request):
    order_id = request.data.get('order_id')
    order = Order.objects.get(id=order_id, user=request.user)
        
    if not order.user.email:
        return Response({'error': 'User email not found'}, status=status.HTTP_400_BAD_REQUEST)
        
    success = EmailService.send_order_success_email(order)
        
    if success:
        return Response({'message': f'Email sent successfully to {order.user.email}'}, status=status.HTTP_200_OK)
    else:
        return Response({'error': 'Failed to send email'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)