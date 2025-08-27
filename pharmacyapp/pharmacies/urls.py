from django.urls import path, include
from . import views
from .vnpay_views import VNPayReturnView, VNPayIPNView, create_vnpay_payment, check_payment_status
from rest_framework.routers import DefaultRouter
# Temporarily commented out for WebSocket testing
# from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView

router = DefaultRouter()
router.register('users',views.UserViewSet, basename='user')
router.register('medicine-genres', views.MedicineGenreViewSet, basename='medicine-genre')
router.register('produces', views.ProduceViewSet, basename='produce')
router.register('medicines', views.MedicineViewSet, basename='medicine')
router.register('medicine-images', views.MedicineImageViewSet, basename='medicine-image')
router.register('carts', views.CartViewSet, basename='cart')
router.register('cart-items', views.CartItemViewSet, basename='cart-item')
router.register('orders', views.OrderViewSet, basename='order')
router.register('shipping-fees', views.ShippingFeeViewSet, basename='shipping-fee')
# router.register('order-details', views.OrderDetailViewSet, basename='order-detail')


urlpatterns = [
    path('', include(router.urls)),
    path('chatbot/', views.ChatBotView.as_view(), name='chatbot'),
    path('vnpay/create-payment/', create_vnpay_payment, name='vnpay-create-payment'),
    path('vnpay/return/', VNPayReturnView.as_view(), name='vnpay-return'),
    path('vnpay/ipn/', VNPayIPNView.as_view(), name='vnpay-ipn'),
    path('vnpay/check-status/<int:order_id>/', check_payment_status, name='vnpay-check-status'),
    path('order-email/', views.order_email, name='order-email'),
]