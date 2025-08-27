# WebSocket Real-time Notification System

## Tổng quan
Hệ thống WebSocket cho phép gửi thông báo realtime khi:
- Customer đặt hàng thành công → Thông báo cho customer và staff
- Staff thay đổi trạng thái đơn hàng → Thông báo cho customer

## Kiến trúc

### Backend (Django + Channels)
```
Django Views → WebSocket Service → Channel Layer → WebSocket Consumer → Frontend
```

### Components

#### 1. WebSocket Consumers (`consumers.py`)
- **NotificationConsumer**: Xử lý connection từ customer
- **StaffNotificationConsumer**: Xử lý connection từ staff

#### 2. WebSocket Service (`websocket_service.py`)
- **send_order_created_notification()**: Thông báo đơn hàng mới
- **send_order_status_update()**: Thông báo thay đổi trạng thái
- **send_staff_new_order_notification()**: Thông báo cho staff

#### 3. Authentication Middleware (`middleware.py`)
- **JWTAuthMiddleware**: Authenticate JWT token trong WebSocket

## Cài đặt & Cấu hình

### 1. Dependencies
```bash
pip install channels[daphne] channels-redis
```

### 2. Redis Setup
**Windows:**
```bash
# Download Redis từ https://github.com/microsoftarchive/redis/releases
# Hoặc dùng Docker:
docker run -d -p 6379:6379 redis:alpine
```

**Linux/Mac:**
```bash
sudo apt install redis-server
# hoặc
brew install redis
```

### 3. Django Settings (`settings.py`)
```python
INSTALLED_APPS = [
    'daphne',  # Phải ở đầu
    # ... other apps
    'channels',
]

ASGI_APPLICATION = 'pharmacyapp.asgi.application'

CHANNEL_LAYERS = {
    'default': {
        'BACKEND': 'channels_redis.core.RedisChannelLayer',
        'CONFIG': {
            "hosts": [('127.0.0.1', 6379)],
        },
    },
}
```

### 4. ASGI Configuration (`asgi.py`)
```python
from pharmacies.middleware import JWTAuthMiddlewareStack

application = ProtocolTypeRouter({
    "http": django_asgi_app,
    "websocket": AllowedHostsOriginValidator(
        JWTAuthMiddlewareStack(
            URLRouter(pharmacies.routing.websocket_urlpatterns)
        )
    ),
})
```

## API Endpoints

### WebSocket Endpoints
- `ws://localhost:8000/ws/notifications/` - Customer notifications
- `ws://localhost:8000/ws/staff-notifications/` - Staff notifications

### Authentication
WebSocket connection cần JWT token:
```javascript
// Qua query parameter
ws://localhost:8000/ws/notifications/?token=your_jwt_token

// Hoặc qua header
const socket = new WebSocket('ws://localhost:8000/ws/notifications/');
socket.headers = {
    'Authorization': 'Bearer your_jwt_token'
};
```

## Message Types

### Client → Server

#### Ping Message
```json
{
    "type": "ping",
    "timestamp": "2025-08-25T10:00:00Z"
}
```

#### Subscribe to Order
```json
{
    "type": "subscribe_order",
    "order_id": 123
}
```

### Server → Client

#### Connection Established
```json
{
    "type": "connection_established",
    "message": "Kết nối thành công cho user username"
}
```

#### Order Created
```json
{
    "type": "order_created",
    "order_id": "123",
    "message": "Đơn hàng #123 đã được tạo thành công",
    "total": "500000",
    "timestamp": "2025-08-25T10:00:00Z"
}
```

#### Order Status Update
```json
{
    "type": "order_status_update",
    "order_id": "123",
    "old_status": "pending",
    "new_status": "waiting_for_delivery",
    "status_label": "Đang giao hàng đến bạn",
    "message": "Đơn hàng #123 đã được cập nhật: Đang giao hàng đến bạn",
    "timestamp": "2025-08-25T10:00:00Z"
}
```

#### Staff New Order
```json
{
    "type": "new_order",
    "order_id": "123",
    "customer": "Nguyễn Văn A",
    "total": "500000",
    "message": "Đơn hàng mới #123 từ Nguyễn Văn A",
    "timestamp": "2025-08-25T10:00:00Z"
}
```

## Frontend Integration (React)

### 1. WebSocket Connection
```javascript
class WebSocketService {
    constructor() {
        this.socket = null;
        this.reconnectAttempts = 0;
        this.maxReconnectAttempts = 5;
        this.reconnectInterval = 3000;
    }

    connect(token) {
        const wsUrl = `ws://localhost:8000/ws/notifications/?token=${token}`;
        
        this.socket = new WebSocket(wsUrl);
        
        this.socket.onopen = (event) => {
            console.log('WebSocket connected');
            this.reconnectAttempts = 0;
        };
        
        this.socket.onmessage = (event) => {
            const data = JSON.parse(event.data);
            this.handleMessage(data);
        };
        
        this.socket.onclose = (event) => {
            console.log('WebSocket disconnected');
            this.handleReconnect();
        };
        
        this.socket.onerror = (error) => {
            console.error('WebSocket error:', error);
        };
    }

    handleMessage(data) {
        switch(data.type) {
            case 'order_created':
                this.showNotification('Đặt hàng thành công!', data.message);
                break;
                
            case 'order_status_update':
                this.showNotification('Cập nhật đơn hàng', data.message);
                break;
                
            case 'connection_established':
                console.log('Connection established:', data.message);
                break;
                
            default:
                console.log('Unknown message type:', data);
        }
    }

    showNotification(title, message) {
        // Hiển thị notification trong UI
        // Có thể dùng toast, modal, hoặc notification component
        if ('Notification' in window) {
            new Notification(title, {
                body: message,
                icon: '/pharmacy-icon.png'
            });
        }
    }

    handleReconnect() {
        if (this.reconnectAttempts < this.maxReconnectAttempts) {
            this.reconnectAttempts++;
            setTimeout(() => {
                console.log(`Reconnecting... (${this.reconnectAttempts}/${this.maxReconnectAttempts})`);
                this.connect();
            }, this.reconnectInterval);
        }
    }

    disconnect() {
        if (this.socket) {
            this.socket.close();
        }
    }

    sendPing() {
        if (this.socket && this.socket.readyState === WebSocket.OPEN) {
            this.socket.send(JSON.stringify({
                type: 'ping',
                timestamp: new Date().toISOString()
            }));
        }
    }
}
```

### 2. React Hook
```javascript
import { useEffect, useRef } from 'react';

export const useWebSocket = (token) => {
    const ws = useRef(null);

    useEffect(() => {
        if (token) {
            ws.current = new WebSocketService();
            ws.current.connect(token);

            // Ping every 30 seconds to keep connection alive
            const pingInterval = setInterval(() => {
                ws.current.sendPing();
            }, 30000);

            return () => {
                clearInterval(pingInterval);
                ws.current.disconnect();
            };
        }
    }, [token]);

    return ws.current;
};
```

### 3. Sử dụng trong Component
```javascript
import React, { useEffect } from 'react';
import { useWebSocket } from './hooks/useWebSocket';

const NotificationCenter = () => {
    const token = localStorage.getItem('access_token');
    const ws = useWebSocket(token);

    useEffect(() => {
        // Request notification permission
        if ('Notification' in window && Notification.permission === 'default') {
            Notification.requestPermission();
        }
    }, []);

    return (
        <div>
            {/* Notification UI components */}
        </div>
    );
};
```

## Chạy hệ thống

### 1. Start Redis
```bash
redis-server
```

### 2. Start Django với Daphne
```bash
# Development
python manage.py runserver

# Production với Daphne
daphne -p 8000 pharmacyapp.asgi:application
```

### 3. Test WebSocket
```bash
python test_websocket.py
```

## Troubleshooting

### 1. Channel Layer Issues
```python
# Test channel layer
python manage.py shell
>>> from channels.layers import get_channel_layer
>>> channel_layer = get_channel_layer()
>>> print(channel_layer)
```

### 2. Redis Connection
```bash
redis-cli ping
# Should return: PONG
```

### 3. WebSocket Authentication
- Kiểm tra JWT token hợp lệ
- Verify middleware đã được config đúng
- Check CORS settings cho WebSocket

### 4. Common Errors

#### "Channel layer is not configured"
- Cài đặt Redis
- Cấu hình CHANNEL_LAYERS trong settings
- Restart Django server

#### "Connection rejected 4001"
- JWT token không hợp lệ hoặc expired
- User chưa được authenticate

#### "Connection rejected 4003"
- User không có quyền staff (cho staff notifications)

## Monitoring & Logging

### Django Logging
```python
LOGGING = {
    'version': 1,
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
        },
    },
    'loggers': {
        'pharmacies.consumers': {
            'handlers': ['console'],
            'level': 'INFO',
        },
        'pharmacies.websocket_service': {
            'handlers': ['console'],
            'level': 'INFO',
        },
    },
}
```

### Redis Monitoring
```bash
redis-cli monitor
```

## Security Considerations

1. **Authentication**: Luôn verify JWT token
2. **Authorization**: Kiểm tra user permissions
3. **Rate Limiting**: Implement connection limits
4. **CORS**: Cấu hình origins cho WebSocket
5. **SSL**: Sử dụng WSS trong production

## Production Deployment

### 1. Nginx Configuration
```nginx
location /ws/ {
    proxy_pass http://backend;
    proxy_http_version 1.1;
    proxy_set_header Upgrade $http_upgrade;
    proxy_set_header Connection "upgrade";
    proxy_set_header Host $host;
    proxy_set_header X-Real-IP $remote_addr;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    proxy_set_header X-Forwarded-Proto $scheme;
}
```

### 2. Redis Cluster
```python
CHANNEL_LAYERS = {
    'default': {
        'BACKEND': 'channels_redis.core.RedisChannelLayer',
        'CONFIG': {
            "hosts": [
                ('redis-server-1', 6379),
                ('redis-server-2', 6379),
            ],
        },
    },
}
```
