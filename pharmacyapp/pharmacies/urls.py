from django.urls import path, include
from . import views
from rest_framework.routers import DefaultRouter
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView

router = DefaultRouter()
router.register('users',views.UserViewSet, basename='user')
router.register('medicine-genres', views.MedicineGenreViewSet, basename='medicine-genre')
router.register('produces', views.ProduceViewSet, basename='produce')
router.register('medicines', views.MedicineViewSet, basename='medicine')
router.register('medicine-images', views.MedicineImageViewSet, basename='medicine-image')
router.register('carts', views.CartViewSet, basename='cart')
router.register('cart-items', views.CartItemViewSet, basename='cart-item')
router.register('orders', views.OrderViewSet, basename='order')
router.register('order-details', views.OrderDetailViewSet, basename='order-detail')


urlpatterns = [
    path('', include(router.urls)),
    path('chatbot/', views.ChatBotView.as_view(), name='chatbot'),
    # path('api/token/', TokenObtainPairView.as_view(), name='token_obtain_pair'),
    # path('send-email/', send_email, name='send_email'),
    # path('chat/', views.ChatView.as_view(), name='chat'),
]