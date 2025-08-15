from django.http import JsonResponse, HttpResponseRedirect
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from django.views import View
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from .models import Order, PaymentDetail
from .vnpay_service import VNPayService
from .email_service import EmailService
import json
import logging

logger = logging.getLogger(__name__)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def create_vnpay_payment(request):
    """
    Tạo URL thanh toán VNPay cho đơn hàng
    """
    try:
        order_id = request.data.get('order_id')
        
        if not order_id:
            return Response({'error': 'Order ID is required'}, status=status.HTTP_400_BAD_REQUEST)
        
        # Lấy thông tin đơn hàng
        try:
            order = Order.objects.get(id=order_id, user=request.user)
        except Order.DoesNotExist:
            return Response({'error': 'Order not found'}, status=status.HTTP_404_NOT_FOUND)
        
        # Kiểm tra xem đơn hàng đã thanh toán chưa
        if hasattr(order, 'payment_detail') and order.payment_detail.status == 'completed':
            return Response({'error': 'Order already paid'}, status=status.HTTP_400_BAD_REQUEST)
        
        # Tạo VNPay service
        vnpay = VNPayService()
        
        # Lấy IP client
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            client_ip = x_forwarded_for.split(',')[0]
        else:
            client_ip = request.META.get('REMOTE_ADDR', '127.0.0.1')
        
        # Tạo URL thanh toán
        payment_url = vnpay.create_payment_url(
            order_id=order.id,
            amount=order.total,
            order_desc=f"Thanh toan don hang #{order.id}",
            client_ip=client_ip
        )
        
        # Cập nhật payment detail status thành pending
        if hasattr(order, 'payment_detail'):
            order.payment_detail.status = 'pending'
            order.payment_detail.save()
        
        return Response({
            'payment_url': payment_url,
            'order_id': order.id,
            'amount': order.total
        })
        
    except Exception as e:
        logger.error(f"Error creating VNPay payment: {e}")
        return Response({'error': 'Internal server error'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@method_decorator(csrf_exempt, name='dispatch')
class VNPayReturnView(View):
    """
    Xử lý callback khi user quay lại từ VNPay
    """
    def get(self, request):
        vnpay_params = dict(request.GET.items())
        
        # Tạo VNPay service
        vnpay = VNPayService()
        
        # Xác thực phản hồi
        is_valid, message = vnpay.verify_payment_response(vnpay_params)
        
        if is_valid:
            # Lấy thông tin đơn hàng
            order_id = vnpay_params.get('vnp_TxnRef')
            
            try:
                order = Order.objects.get(id=order_id)
                
                # Cập nhật payment detail
                if hasattr(order, 'payment_detail'):
                    payment_detail = order.payment_detail
                    payment_detail.status = 'completed'
                    payment_detail.save()
                
                # Cập nhật trạng thái đơn hàng
                order.status = 'waiting_for_pickup'  # hoặc waiting_for_delivery
                order.save()
                
                # Gửi email thông báo đặt hàng và thanh toán thành công
                if order.user.email:
                    EmailService.send_order_success_email(order)
                
                # Redirect đến trang thành công
                return HttpResponseRedirect(f'http://localhost:3000/payment/success?order_id={order_id}')
                
            except Order.DoesNotExist:
                logger.error(f"Order {order_id} not found in VNPay return")
                return HttpResponseRedirect('http://localhost:3000/payment/error?reason=order_not_found')
        else:
            # Thanh toán thất bại
            order_id = vnpay_params.get('vnp_TxnRef')
            logger.error(f"VNPay payment failed for order {order_id}: {message}")
            return HttpResponseRedirect(f'http://localhost:3000/payment/error?reason=payment_failed&order_id={order_id}')


@method_decorator(csrf_exempt, name='dispatch')
class VNPayIPNView(View):
    """
    Xử lý IPN (Instant Payment Notification) từ VNPay
    """
    def post(self, request):
        vnpay_params = dict(request.POST.items())
        
        # Tạo VNPay service
        vnpay = VNPayService()
        
        # Xác thực phản hồi
        is_valid, message = vnpay.verify_payment_response(vnpay_params)
        
        if is_valid:
            order_id = vnpay_params.get('vnp_TxnRef')
            
            try:
                order = Order.objects.get(id=order_id)
                
                # Cập nhật payment detail
                if hasattr(order, 'payment_detail'):
                    payment_detail = order.payment_detail
                    payment_detail.status = 'completed'
                    payment_detail.save()
                
                # Cập nhật trạng thái đơn hàng
                order.status = 'waiting_for_pickup'
                order.save()
                
                logger.info(f"VNPay IPN: Order {order_id} payment completed")
                return JsonResponse({'RspCode': '00', 'Message': 'success'})
                
            except Order.DoesNotExist:
                logger.error(f"Order {order_id} not found in VNPay IPN")
                return JsonResponse({'RspCode': '01', 'Message': 'Order not found'})
        else:
            logger.error(f"VNPay IPN verification failed: {message}")
            return JsonResponse({'RspCode': '97', 'Message': 'Checksum failed'})


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def check_payment_status(request, order_id):
    """
    Kiểm tra trạng thái thanh toán của đơn hàng
    """
    try:
        order = Order.objects.get(id=order_id, user=request.user)
        
        payment_status = 'pending'
        if hasattr(order, 'payment_detail'):
            payment_status = order.payment_detail.status
        
        return Response({
            'order_id': order.id,
            'payment_status': payment_status,
            'order_status': order.status,
            'total': order.total
        })
        
    except Order.DoesNotExist:
        return Response({'error': 'Order not found'}, status=status.HTTP_404_NOT_FOUND)
