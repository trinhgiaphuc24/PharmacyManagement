from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.utils.html import strip_tags
from django.conf import settings
from .models import Order
import logging

logger = logging.getLogger(__name__)

class EmailService:
    @staticmethod
    def send_order_success_email(order):
        """
        Gửi email thông báo đặt hàng thành công
        """
        try:
            # Kiểm tra xem email đã được gửi chưa (dựa trên log hoặc cache)
            cache_key = f"email_sent_order_{order.id}"
            from django.core.cache import cache
            
            if cache.get(cache_key):
                logger.info(f"Email already sent for order #{order.id}, skipping...")
                return True
            
            subject = f'Xác nhận đơn hàng #{order.id} - PharmacyApp'
            
            # Lấy thông tin giao hàng
            shipping_info = "N/A"
            shipping_name = "N/A"
            shipping_phone = "N/A"
            
            if hasattr(order, 'online_order') and hasattr(order.online_order, 'ship_info'):
                ship_info = order.online_order.ship_info
                shipping_name = ship_info.full_name
                shipping_phone = ship_info.phoneNumber
                shipping_info = f"{ship_info.province}, {ship_info.district}, {ship_info.commune}, {ship_info.specific}"
            
            # Tạo nội dung email HTML
            html_content = f"""
            <!DOCTYPE html>
            <html>
            <head>
                <meta charset="utf-8">
                <title>Xác nhận đơn hàng</title>
                <style>
                    body {{ font-family: Arial, sans-serif; line-height: 1.6; }}
                    .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
                    .header {{ background-color: #007bff; color: white; padding: 20px; text-align: center; }}
                    .content {{ padding: 20px; }}
                    .order-info {{ background-color: #f8f9fa; padding: 15px; margin: 15px 0; border-radius: 5px; }}
                    .item {{ border-bottom: 1px solid #dee2e6; padding: 10px 0; }}
                    .item:last-child {{ border-bottom: none; }}
                    .total {{ font-weight: bold; color: #007bff; }}
                    .footer {{ background-color: #6c757d; color: white; padding: 15px; text-align: center; margin-top: 20px; }}
                </style>
            </head>
            <body>
                <div class="container">
                    <div class="header">
                        <h1>Đặt hàng thành công!</h1>
                    </div>
                    
                    <div class="content">
                        <p>Xin chào <strong>{order.user.get_full_name() or order.user.username}</strong>,</p>
                        
                        <p>Cảm ơn bạn đã đặt hàng tại PharmacyApp. Đơn hàng của bạn đã được xác nhận và đang được xử lý.</p>
                        
                        <div class="order-info">
                            <h3>Thông tin đơn hàng</h3>
                            <p><strong>Mã đơn hàng:</strong> #{order.id}</p>
                            <p><strong>Ngày đặt:</strong> {order.createdAt.strftime('%d/%m/%Y %H:%M')}</p>
                            <p><strong>Trạng thái:</strong> {"Đang chờ xử lý" if order.status == "pending" else "Đã xác nhận" if order.status == "confirmed" else order.status}</p>
                        </div>
                        
                        <div class="order-info">
                            <h3>Thông tin giao hàng</h3>
                            <p><strong>Người nhận:</strong> {shipping_name}</p>
                            <p><strong>Số điện thoại:</strong> {shipping_phone}</p>
                            <p><strong>Địa chỉ:</strong> {shipping_info}</p>
                        </div>
                        
                        <div class="order-info">
                            <h3>Chi tiết sản phẩm</h3>
            """
            
            # Thêm thông tin sản phẩm
            total = 0
            for item in order.details.all():
                item_total = item.price * item.quantity
                total += item_total
                html_content += f"""
                            <div class="item">
                                <p><strong>{item.medicine.name}</strong></p>
                                <p>Giá: {item.price:,.0f} VNĐ x {item.quantity} = {item_total:,.0f} VNĐ</p>
                            </div>
                """
            
            # Phí vận chuyển
            shipping_fee = order.shipping_fee.price if order.shipping_fee else 0
            total_amount = total + shipping_fee
            
            html_content += f"""
                        </div>
                        
                        <div class="order-info">
                            <h3>Tổng tiền</h3>
                            <p>Tạm tính: {total:,.0f} VNĐ</p>
                            <p>Phí vận chuyển: {shipping_fee:,.0f} VNĐ</p>
                            <p class="total">Tổng cộng: {total_amount:,.0f} VNĐ</p>
                        </div>
                        
                        <p>Chúng tôi sẽ liên hệ với bạn sớm nhất để xác nhận và giao hàng.</p>
                        <p>Nếu có bất kỳ thắc mắc nào, vui lòng liên hệ với chúng tôi qua hotline: <strong>1900-xxxx</strong></p>
                        
                        <p>Trân trọng,<br><strong>Đội ngũ PharmacyApp</strong></p>
                    </div>
                    
                    <div class="footer">
                        <p>&copy; 2025 PharmacyApp. Tất cả quyền được bảo lưu.</p>
                    </div>
                </div>
            </body>
            </html>
            """
            
            # Tạo phiên bản text plain từ HTML
            text_content = strip_tags(html_content)
            
            # Tạo email
            email = EmailMultiAlternatives(
                subject=subject,
                body=text_content,
                from_email=settings.DEFAULT_FROM_EMAIL,
                to=[order.user.email]
            )
            
            # Attach HTML content
            email.attach_alternative(html_content, "text/html")
            
            # Gửi email
            email.send()
            
            # Đánh dấu email đã được gửi (cache trong 24 giờ)
            cache.set(cache_key, True, 86400)  # 24 hours
            
            logger.info(f"Order success email sent to {order.user.email} for order #{order.id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to send order success email for order #{order.id}: {str(e)}")
            return False

    @staticmethod
    def send_payment_success_email(order):
        """
        Gửi email thông báo thanh toán thành công
        """
        try:
            subject = f'Thanh toán thành công - Đơn hàng #{order.id} - PharmacyApp'
            
            # Lấy thông tin giao hàng
            shipping_info = "N/A"
            shipping_name = "N/A"
            shipping_phone = "N/A"
            
            if hasattr(order, 'online_order') and hasattr(order.online_order, 'ship_info'):
                ship_info = order.online_order.ship_info
                shipping_name = ship_info.full_name
                shipping_phone = ship_info.phoneNumber
                shipping_info = f"{ship_info.province}, {ship_info.district}, {ship_info.commune}, {ship_info.specific}"
            
            # Tạo nội dung email HTML
            html_content = f"""
            <!DOCTYPE html>
            <html>
            <head>
                <meta charset="utf-8">
                <title>Thanh toán thành công</title>
                <style>
                    body {{ font-family: Arial, sans-serif; line-height: 1.6; }}
                    .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
                    .header {{ background-color: #28a745; color: white; padding: 20px; text-align: center; }}
                    .content {{ padding: 20px; }}
                    .order-info {{ background-color: #f8f9fa; padding: 15px; margin: 15px 0; border-radius: 5px; }}
                    .item {{ border-bottom: 1px solid #dee2e6; padding: 10px 0; }}
                    .item:last-child {{ border-bottom: none; }}
                    .total {{ font-weight: bold; color: #28a745; }}
                    .footer {{ background-color: #6c757d; color: white; padding: 15px; text-align: center; margin-top: 20px; }}
                    .success-icon {{ font-size: 48px; color: #28a745; text-align: center; margin: 20px 0; }}
                </style>
            </head>
            <body>
                <div class="container">
                    <div class="header">
                        <h1>✅ Thanh toán thành công!</h1>
                    </div>
                    
                    <div class="content">
                        <div class="success-icon">🎉</div>
                        
                        <p>Xin chào <strong>{order.user.get_full_name() or order.user.username}</strong>,</p>
                        
                        <p>Cảm ơn bạn đã thanh toán! Đơn hàng #{order.id} của bạn đã được thanh toán thành công và đang được chuẩn bị giao hàng.</p>
                        
                        <div class="order-info">
                            <h3>Thông tin đơn hàng</h3>
                            <p><strong>Mã đơn hàng:</strong> #{order.id}</p>
                            <p><strong>Ngày thanh toán:</strong> {order.payment_detail.createAt.strftime('%d/%m/%Y %H:%M') if order.payment_detail else order.createdAt.strftime('%d/%m/%Y %H:%M')}</p>
                            <p><strong>Trạng thái:</strong> {"Đang chuẩn bị hàng" if order.status == "waiting_for_pickup" else "Đang giao hàng" if order.status == "shipping" else order.status}</p>
                        </div>
                        
                        <div class="order-info">
                            <h3>Thông tin giao hàng</h3>
                            <p><strong>Người nhận:</strong> {shipping_name}</p>
                            <p><strong>Số điện thoại:</strong> {shipping_phone}</p>
                            <p><strong>Địa chỉ:</strong> {shipping_info}</p>
                        </div>
                        
                        <div class="order-info">
                            <h3>Chi tiết sản phẩm</h3>
            """
            
            # Thêm thông tin sản phẩm
            total = 0
            for item in order.details.all():
                item_total = item.price * item.quantity
                total += item_total
                html_content += f"""
                            <div class="item">
                                <p><strong>{item.medicine.name}</strong></p>
                                <p>Giá: {item.price:,.0f} VNĐ x {item.quantity} = {item_total:,.0f} VNĐ</p>
                            </div>
                """
            
            # Phí vận chuyển
            shipping_fee = order.shipping_fee.price if order.shipping_fee else 0
            total_amount = total + shipping_fee
            
            html_content += f"""
                        </div>
                        
                        <div class="order-info">
                            <h3>Thông tin thanh toán</h3>
                            <p>Tạm tính: {total:,.0f} VNĐ</p>
                            <p>Phí vận chuyển: {shipping_fee:,.0f} VNĐ</p>
                            <p class="total">Tổng đã thanh toán: {total_amount:,.0f} VNĐ</p>
                            <p><strong>Phương thức:</strong> VNPay</p>
                        </div>
                        
                        <p>Đơn hàng của bạn đang được chuẩn bị và sẽ được giao trong thời gian sớm nhất. Chúng tôi sẽ thông báo đến bạn khi hàng được giao.</p>
                        <p>Nếu có bất kỳ thắc mắc nào, vui lòng liên hệ với chúng tôi qua hotline: <strong>1900-xxxx</strong></p>
                        
                        <p>Trân trọng,<br><strong>Đội ngũ PharmacyApp</strong></p>
                    </div>
                    
                    <div class="footer">
                        <p>&copy; 2025 PharmacyApp. Tất cả quyền được bảo lưu.</p>
                    </div>
                </div>
            </body>
            </html>
            """
            
            # Tạo phiên bản text plain từ HTML
            text_content = strip_tags(html_content)
            
            # Tạo email
            email = EmailMultiAlternatives(
                subject=subject,
                body=text_content,
                from_email=settings.DEFAULT_FROM_EMAIL,
                to=[order.user.email]
            )
            
            # Attach HTML content
            email.attach_alternative(html_content, "text/html")
            
            # Gửi email
            email.send()
            
            logger.info(f"Payment success email sent to {order.user.email} for order #{order.id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to send payment success email for order #{order.id}: {str(e)}")
            return False
