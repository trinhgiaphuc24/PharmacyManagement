from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync
from datetime import datetime

class WebSocketService:
    def __init__(self):
        self.channel_layer = get_channel_layer()
    
    def send_order_created_notification(self, user_id, order_id, total):        
        async_to_sync(self.channel_layer.group_send)(f"user_{user_id}", {
            'type': 'order_created',
            'order_id': str(order_id),
            'message': f'Tạo đơn hàng thành công! Đơn hàng #{order_id}',
            'total': str(total),
            'timestamp': datetime.now().isoformat()
        })
    
    def send_staff_new_order_notification(self, order_id, customer_name, total):
        async_to_sync(self.channel_layer.group_send)("staff_notifications", {
            'type': 'new_order_notification',
            'order_id': str(order_id),
            'customer': customer_name,
            'total': str(total),
            'message': f'Đơn hàng mới #{order_id} từ {customer_name}',
            'timestamp': datetime.now().isoformat()
        })
    
    def send_order_status_update(self, user_id, order_id, old_status, new_status):
        status_labels = {
            'pending': 'Chờ xác nhận',
            'waiting_for_pickup': 'Chờ lấy hàng', 
            'waiting_for_delivery': 'Chờ giao hàng',
            'delivered': 'Đã giao',
            'canceled': 'Đã hủy'
        }

        async_to_sync(self.channel_layer.group_send)(f"user_{user_id}", {
            'type': 'order_status_update',
            'order_id': str(order_id),
            'old_status': old_status,
            'new_status': new_status, 
            'status_label': status_labels.get(new_status, new_status),
            'message': f'Đơn hàng #{order_id}: {status_labels.get(new_status, new_status)}',
            'timestamp': datetime.now().isoformat()
        })
 
websocket_service = WebSocketService()
