# Chatbot Module Structure

## Tổng quan
ChatBotView đã được refactor thành module riêng biệt để dễ quản lý và bảo trì.

## Cấu trúc thư mục
```
pharmacies/
├── chatbot/
│   ├── __init__.py
│   ├── views.py           # ChatBotView chính
│   ├── medicine_search.py # Service tìm kiếm thuốc
│   └── openai_service.py  # Service xử lý OpenAI API
├── views.py               # Import ChatBotView từ chatbot package
└── ...
```

## Các file trong chatbot module

### 1. `views.py`
- **Chức năng**: Main view xử lý HTTP requests cho chatbot
- **Class**: `ChatBotView`
- **Methods**:
  - `post()`: Xử lý tin nhắn từ user
  - `get()`: Lấy lịch sử chat

### 2. `medicine_search.py`
- **Chức năng**: Service tìm kiếm thuốc trong database
- **Class**: `MedicineSearchService`
- **Methods**:
  - `search_exact_match()`: Tìm theo tên chính xác
  - `search_by_genre()`: Tìm theo genre mapping
  - `search_fallback()`: Tìm kiếm dự phòng
  - `format_medicine_data()`: Format dữ liệu thuốc
  - `get_medicine_context()`: Main method tìm kiếm

### 3. `openai_service.py`
- **Chức năng**: Service xử lý OpenAI API
- **Class**: `OpenAIService`
- **Methods**:
  - `create_prompt_with_medicines()`: Tạo prompt khi có thuốc
  - `create_prompt_without_medicines()`: Tạo prompt khi không có thuốc
  - `call_openai_api()`: Gọi OpenAI API
  - `generate_response()`: Main method tạo response

## Lợi ích của việc refactor

### 1. **Separation of Concerns**
- Mỗi file chỉ chịu trách nhiệm cho một nhiệm vụ cụ thể
- Dễ debug và maintain hơn

### 2. **Code Reusability**
- Các service có thể được sử dụng ở những nơi khác
- Dễ dàng unit test từng component

### 3. **Scalability**
- Dễ thêm features mới
- Có thể thay đổi implementation mà không ảnh hưởng đến các parts khác

### 4. **Maintainability**
- Code ngắn gọn, dễ đọc
- Dễ tìm và fix bugs

## Cách sử dụng

### Import trong views.py chính:
```python
from .chatbot.views import ChatBotView
```

### Sử dụng riêng biệt (nếu cần):
```python
from pharmacies.chatbot.medicine_search import MedicineSearchService
from pharmacies.chatbot.openai_service import OpenAIService

# Tìm kiếm thuốc
medicine_service = MedicineSearchService()
context, medicines = medicine_service.get_medicine_context("paracetamol")

# Tạo response từ OpenAI
openai_service = OpenAIService()
response = openai_service.generate_response("question", context, medicines)
```

## API không thay đổi
- Endpoint vẫn là `/chatbot/`
- Request/Response format không đổi
- Frontend không cần thay đổi gì

## Future Enhancements
1. **Caching**: Thêm Redis cache cho medicine search
2. **Async**: Convert sang async views cho performance tốt hơn
3. **ML Integration**: Thêm ML models cho better intent recognition
4. **Analytics**: Thêm logging và analytics cho user interactions
