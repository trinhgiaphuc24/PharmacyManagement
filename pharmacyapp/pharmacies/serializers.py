from django.contrib.auth.hashers import make_password
from pharmacies.models import *
from rest_framework import serializers
from rest_framework.serializers import ModelSerializer, SerializerMethodField
from pharmacies.models import Cart


class UserSerializer(ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'password', 'phone_number', 'first_name', 'last_name', 'userRole']

    def create(self, validated_data):
        data = validated_data.copy()
        u = User(**data)
        u.set_password(u.password)
        u.save()
        Cart.objects.create(user=u)
        return u


class MedicineGenreSerializer(ModelSerializer):
    class Meta:
        model = MedicineGenre
        fields = ['id', 'name', 'imgMedicineGenreUrl', 'active']

    def to_representation(self, instance):
        data = super().to_representation(instance)
        data['imgMedicineGenreUrl'] = instance.imgMedicineGenreUrl.url if instance.imgMedicineGenreUrl else None
        return data


class ProduceSerializer(ModelSerializer):
    class Meta:
        model = Produce
        fields = ['id', 'name', 'active']


class MedicineImageSerializer(ModelSerializer):
    class Meta:
        model = MedicineImage
        fields = ['id', 'imgMedicineUrl', 'medicine']
    
    def to_representation(self, instance):
        data = super().to_representation(instance)
        data['imgMedicineUrl'] = instance.imgMedicineUrl.url if instance.imgMedicineUrl else None
        return data


class MedicineSerializer(ModelSerializer):
    medicineGenre = MedicineGenreSerializer(read_only=True)
    produce = ProduceSerializer(read_only=True)
    images = MedicineImageSerializer(many=True, read_only=True)

    class Meta:
        model = Medicine
        fields = [
            'id', 'name', 'description', 'ingredient', 'price', 'use', 'format', 'note', 'benefit',
            'createdAt', 'medicineGenre', 'produce', 'active', 'images'
        ]



class CartItemSerializer(ModelSerializer):
    medicine_name = serializers.CharField(source='medicine.name', read_only=True)
    medicine_price = serializers.FloatField(source='medicine.price', read_only=True)
    medicine_genre = serializers.CharField(source='medicine.medicineGenre.name', read_only=True)
    medicine_produce = serializers.CharField(source='medicine.produce.name', read_only=True)
    medicine_images = serializers.SerializerMethodField()
    
    class Meta:
        model = CartItem
        fields = ['id', 'cart', 'medicine', 'medicine_name', 'medicine_price', 'medicine_genre', 'medicine_produce', 'medicine_images', 'quantity', 'total_price']
        read_only_fields = ['total_price']

    def get_medicine_images(self, obj):
        # Sử dụng .url để convert CloudinaryResource thành string
        try:
            if obj.medicine.images.exists():
                return [{"imgMedicineUrl": img.imgMedicineUrl.url if img.imgMedicineUrl else None} for img in obj.medicine.images.all()]
            return []
        except Exception as e:
            print(f"Error getting medicine images: {e}")
            return []

    def create(self, validated_data):
        quantity = validated_data['quantity']
        medicine = validated_data['medicine']
        validated_data['total_price'] = quantity * medicine.price
        return super().create(validated_data)

    def update(self, instance, validated_data):
        if 'quantity' in validated_data:
            quantity = validated_data['quantity']
            validated_data['total_price'] = quantity * instance.medicine.price
        return super().update(instance, validated_data)


class CartSerializer(ModelSerializer):
    items = CartItemSerializer(many=True, read_only=True)
    total_cart_price = serializers.SerializerMethodField()
    total_items = serializers.SerializerMethodField()
    
    class Meta:
        model = Cart
        fields = ['id', 'user', 'items', 'total_cart_price', 'total_items']

    def get_total_cart_price(self, obj):
        return sum(item.total_price for item in obj.items.all())

    def get_total_items(self, obj):
        return sum(item.quantity for item in obj.items.all())


from rest_framework import serializers
from datetime import date
from django.db import transaction
from .models import Order, OrderDetail, OnlineOrder, OnlineOrderShip, PaymentDetail, ShippingFee, Medicine, CartItem


class ShippingFeeSerializer(serializers.ModelSerializer):
    class Meta:
        model = ShippingFee
        fields = ['id', 'price']


class OrderDetailSerializer(serializers.ModelSerializer):
    medicine_name = serializers.CharField(source='medicine.name', read_only=True)
    medicine_image = serializers.SerializerMethodField()
    
    class Meta:
        model = OrderDetail
        fields = ['id', 'quantity', 'price', 'medicine', 'medicine_name', 'medicine_image']
    
    def get_medicine_image(self, obj):
        if obj.medicine and obj.medicine.images.exists():
            # Lấy ảnh đầu tiên từ MedicineImage
            first_image = obj.medicine.images.first()
            if first_image and first_image.imgMedicineUrl:
                request = self.context.get('request')
                if request:
                    return request.build_absolute_uri(first_image.imgMedicineUrl.url)
                return first_image.imgMedicineUrl.url
        return None


class PaymentDetailSerializer(serializers.ModelSerializer):
    class Meta:
        model = PaymentDetail
        fields = ['id', 'createAt', 'amount', 'status', 'method']


class OnlineOrderShipSerializer(serializers.ModelSerializer):
    class Meta:
        model = OnlineOrderShip
        fields = ['id', 'full_name', 'phoneNumber', 'province', 'district', 'commune', 'specific', 'note']


class OnlineOrderSerializer(serializers.ModelSerializer):
    ship_info = OnlineOrderShipSerializer(read_only=True)
    
    class Meta:
        model = OnlineOrder
        fields = ['id', 'shipping_method', 'ship_info']


class OrderSerializer(serializers.ModelSerializer):
    details = OrderDetailSerializer(many=True, read_only=True)
    online_order = OnlineOrderSerializer(read_only=True)
    payment_detail = PaymentDetailSerializer(read_only=True)
    user_name = serializers.CharField(source='user.first_name', read_only=True)
    
    class Meta:
        model = Order
        fields = [
            'id', 'date', 'status', 'createdAt', 'paymentMethod', 'total', 
            'user', 'user_name', 'shipping_fee', 'details', 'online_order', 'payment_detail'
        ]


class CreateOrderSerializer(serializers.Serializer):
    # Delivery type: "pickup" hoặc "delivery"
    delivery_type = serializers.ChoiceField(choices=['pickup', 'delivery'])
    
    # Payment method
    payment_method = serializers.ChoiceField(choices=['cod', 'vnpay'])
    
    # Selected cart items
    selected_items = serializers.ListField(
        child=serializers.IntegerField(),
        help_text="Danh sách ID của cart items được chọn"
    )
    
    # Shipping info (chỉ cần khi delivery_type = "delivery")
    shipping_info = serializers.DictField(required=False, allow_null=True)
    
    def validate(self, data):
        # Validate shipping info if delivery type is "delivery"
        if data['delivery_type'] == 'delivery':
            shipping_info = data.get('shipping_info')
            if not shipping_info:
                raise serializers.ValidationError("Thông tin giao hàng là bắt buộc khi chọn giao hàng tận nơi")
            
            required_fields = ['full_name', 'phone', 'province', 'district', 'ward', 'address']
            for field in required_fields:
                if not shipping_info.get(field):
                    raise serializers.ValidationError(f"Trường {field} là bắt buộc trong thông tin giao hàng")
        
        return data
    
    @transaction.atomic
    def create(self, validated_data):
        user = self.context['request'].user
        delivery_type = validated_data['delivery_type']
        payment_method = validated_data['payment_method']
        selected_items_ids = validated_data['selected_items']
        shipping_info = validated_data.get('shipping_info')
        
        # Get selected cart items
        cart_items = CartItem.objects.filter(
            id__in=selected_items_ids,
            cart__user=user
        ).select_related('medicine')
        
        if not cart_items.exists():
            raise serializers.ValidationError("Không tìm thấy sản phẩm trong giỏ hàng")
        
        # Calculate total
        total = sum(item.quantity * item.medicine.price for item in cart_items)
        
        # Get shipping fee (default to 0 for pickup, can be calculated for delivery)
        shipping_fee = None
        if delivery_type == 'delivery':
            # You can implement shipping fee calculation logic here
            # For now, we'll use a default shipping fee if exists
            shipping_fee = ShippingFee.objects.first()
            if shipping_fee:
                total += shipping_fee.price
        
        # Map payment method
        payment_method_mapping = {
            'cod': 'cod',  # THANH_TOAN_KHI_NHAN_HANG
            'vnpay': 'vnpay'  # THANH_TOAN_QUA_VNPAY
        }
        
        # Create Order
        order = Order.objects.create(
            date=date.today(),
            paymentMethod=payment_method_mapping.get(payment_method, 'cod'),
            total=total,
            user=user,
            shipping_fee=shipping_fee
        )
        
        # Create OrderDetails
        for cart_item in cart_items:
            OrderDetail.objects.create(
                order=order,
                medicine=cart_item.medicine,
                quantity=cart_item.quantity,
                price=cart_item.medicine.price
            )
        
        # Create OnlineOrder
        shipping_method = 'store_pickup' if delivery_type == 'pickup' else 'home_delivery'
        online_order = OnlineOrder.objects.create(
            order=order,
            shipping_method=shipping_method
        )
        
        # Create OnlineOrderShip if delivery
        if delivery_type == 'delivery' and shipping_info:
            OnlineOrderShip.objects.create(
                online_order=online_order,
                full_name=shipping_info['full_name'],
                phoneNumber=shipping_info['phone'],
                province=shipping_info['province'],
                district=shipping_info['district'],
                commune=shipping_info['ward'],
                specific=shipping_info['address'],
                note=shipping_info.get('note', '')
            )
        
        # Create PaymentDetail
        PaymentDetail.objects.create(
            order=order,
            amount=str(total),
            status='pending' if payment_method == 'vnpay' else 'completed',
            method=payment_method_mapping.get(payment_method, 'cod')
        )
        
        # Remove cart items after successful order
        cart_items.delete()
        
        return order


class ChatHistorySerializer(ModelSerializer):
    class Meta:
        model = ChatHistory
        fields = ['id', 'user_message', 'bot_response', 'created_at']