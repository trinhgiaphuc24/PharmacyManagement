from django.contrib.auth.hashers import make_password
from pharmacies.models import *
from rest_framework import serializers
from rest_framework.serializers import ModelSerializer, SerializerMethodField
from pharmacies.models import Cart, CartItem, Medicine, Order, OrderDetail, OnlineOrder, OnlineOrderShip, PaymentDetail, ShippingFee, User
from datetime import date
from django.db import transaction
import uuid


class UserSerializer(ModelSerializer):
    current_password = serializers.CharField(write_only=True, required=False)

    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'password', 'phone_number', 'first_name', 'last_name', 'userRole', 'current_password']

        extra_kwargs = {
            'password': {'write_only': True, 'required': False}
        }

    def create(self, validated_data):
        data = validated_data.copy()
        u = User(**data)
        u.set_password(u.password)
        u.save()
        if u.userRole != 'staff':
            Cart.objects.create(user=u)
        return u
    
    def update(self, user, validated_data):
        current_password = validated_data.pop('current_password', None)
        password = validated_data.pop('password', None)

        if password and current_password:
            if not user.check_password(current_password):
                raise serializers.ValidationError({'current_password': 'Mật khẩu hiện tại không đúng'})
            user.set_password(password)
        
        for attr, value in validated_data.items():
            setattr(user, attr, value)
        
        user.save()
        return user


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
            'createdAt', 'medicineGenre', 'produce', 'active', 'images', 'quantity'
        ]



class CartItemSerializer(ModelSerializer):
    medicine_name = serializers.CharField(source='medicine.name', read_only=True)
    medicine_price = serializers.FloatField(source='medicine.price', read_only=True)
    medicine_genre = serializers.CharField(source='medicine.medicineGenre.name', read_only=True)
    medicine_produce = serializers.CharField(source='medicine.produce.name', read_only=True)
    medicine_stock = serializers.IntegerField(source='medicine.quantity', read_only=True)
    medicine_images = serializers.SerializerMethodField()
    
    class Meta:
        model = CartItem
        fields = ['id', 'cart', 'medicine', 'medicine_name', 'medicine_price', 'medicine_genre', 'medicine_produce', 'medicine_stock', 'medicine_images', 'quantity', 'total_price']
        read_only_fields = ['total_price']

    def get_medicine_images(self, obj):
        # Sử dụng .url để convert CloudinaryResource thành string
        if obj.medicine.images.exists():
            return [{"imgMedicineUrl": img.imgMedicineUrl.url if img.imgMedicineUrl else None} for img in obj.medicine.images.all()]
        return []
    
    def create(self, validated_data):
        cart = validated_data.get('cart')
        if cart and cart.user.userRole == 'staff':
            raise serializers.ValidationError("Staff không được phép sử dụng giỏ hàng")
        
        quantity = validated_data['quantity']
        medicine = validated_data['medicine']

        if medicine.quantity < quantity:
            raise serializers.ValidationError(f"Không đủ hàng cho thuốc {medicine.name}. Còn lại: {medicine.quantity}")
        
        validated_data['total_price'] = quantity * medicine.price
        return super().create(validated_data)

    def update(self, instance, validated_data):
        if 'quantity' in validated_data:
            quantity = validated_data['quantity']
            if instance.medicine.quantity < quantity:
                raise serializers.ValidationError(f"Không đủ hàng cho thuốc {instance.medicine.name}. Còn lại: {instance.medicine.quantity}")
            
            validated_data['total_price'] = quantity * instance.medicine.price
        return super().update(instance, validated_data)


class CartSerializer(ModelSerializer):
    items = CartItemSerializer(many=True, read_only=True)
    
    class Meta:
        model = Cart
        fields = ['id', 'user', 'items']
    
    def to_representation(self, instance):
        if hasattr(instance, 'items'):
            instance.items.all().select_related('medicine', 'medicine__medicineGenre', 'medicine__produce').prefetch_related('medicine__images')
        return super().to_representation(instance)


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
    user_name = serializers.SerializerMethodField()
    phone_number = serializers.CharField(source='user.phone_number', read_only=True)
    email = serializers.EmailField(source='user.email', read_only=True)
    delivery_type = serializers.ChoiceField(choices=['store_pickup', 'home_delivery'], write_only=True, required=False)
    payment_method = serializers.ChoiceField(choices=['cod', 'vnpay'], write_only=True, required=False)
    selected_items = serializers.ListField(child=serializers.IntegerField(),write_only=True,required=False)
    buy_now_items = serializers.ListField(
        child=serializers.DictField(child=serializers.CharField()),
        write_only=True,
        required=False,
        help_text="List of items for buy now: [{'medicine_id': '1', 'quantity': '2'}]"
    )
    shipping_info = serializers.DictField(write_only=True, required=False, allow_null=True)

    class Meta:
        model = Order
        fields = [
            'id', 'date', 'status', 'createdAt', 'paymentMethod', 'total', 
            'user', 'user_name', 'shipping_fee', 'details', 'online_order', 'payment_detail', 'phone_number', 'email',
            'delivery_type', 'payment_method', 'selected_items', 'buy_now_items', 'shipping_info'
        ]
        extra_kwargs = {
            'date': {'required': False},
            'total': {'required': False},
            'user': {'required': False},
            'status': {'required': False},
            'paymentMethod': {'required': False},
        }

    def get_user_name(self, obj):
        if obj.user:
            return f"{obj.user.first_name} {obj.user.last_name}".strip()
        return ""
    
    @transaction.atomic
    def create(self, validated_data):
        delivery_type = validated_data.pop('delivery_type')
        payment_method = validated_data.pop('payment_method')
        selected_items_ids = validated_data.pop('selected_items', [])
        buy_now_items = validated_data.pop('buy_now_items', [])
        shipping_info = validated_data.pop('shipping_info')
        user = self.context['request'].user
        order_items = []
        
        if selected_items_ids:
            cart_items = CartItem.objects.filter(id__in=selected_items_ids, cart__user=user).select_related('medicine')
            
            for cart_item in cart_items:
                if cart_item.medicine.quantity < cart_item.quantity:
                    raise serializers.ValidationError(f"Không đủ hàng cho thuốc {cart_item.medicine.name}. Còn lại: {cart_item.medicine.quantity}")
                
                order_items.append({
                    'medicine': cart_item.medicine,
                    'quantity': cart_item.quantity,
                    'price': cart_item.medicine.price
                })
        
        if buy_now_items:
            for item in buy_now_items:
                medicine_id = item.get('medicine_id')
                quantity = int(item.get('quantity', 1))
                
                try:
                    medicine = Medicine.objects.get(id=medicine_id)
                except Medicine.DoesNotExist:
                    raise serializers.ValidationError(f"Thuốc với ID {medicine_id} không tồn tại")
                
                if medicine.quantity < quantity:
                    raise serializers.ValidationError(f"Không đủ hàng cho thuốc {medicine.name}. Còn lại: {medicine.quantity}")
                
                order_items.append({
                    'medicine': medicine,
                    'quantity': quantity,
                    'price': medicine.price
                })
        
        if not order_items:
            raise serializers.ValidationError("Phải có ít nhất một sản phẩm trong đơn hàng")
        
        total = sum(item['quantity'] * item['price'] for item in order_items)
        if delivery_type == 'home_delivery':
            shipping_fee = ShippingFee.objects.first()
            total += shipping_fee.price
        else:
            shipping_fee = None
        payment_method_mapping = {'cod': 'cod','vnpay': 'vnpay'}
        
        order = Order.objects.create(
            date=date.today(),
            paymentMethod=payment_method_mapping.get(payment_method, 'cod'),
            total=total,
            user=user,
            shipping_fee=shipping_fee
        )
        
        for item in order_items:
            OrderDetail.objects.create(
                order=order,
                medicine=item['medicine'],
                quantity=item['quantity'],
                price=item['price']
            )
            item['medicine'].quantity -= item['quantity']
            item['medicine'].save()
        
        shipping_method = delivery_type
        online_order = OnlineOrder.objects.create(
            order=order,
            shipping_method=shipping_method
        )
        
        if delivery_type == 'home_delivery' and shipping_info:
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
        
        PaymentDetail.objects.create(
            order=order,
            amount=str(total),
            status='pending' if payment_method == 'vnpay' else 'completed',
            method=payment_method_mapping.get(payment_method, 'cod')
        )
        
        if selected_items_ids:
            CartItem.objects.filter(id__in=selected_items_ids, cart__user=user).delete()
        
        return order


class StaffDirectSaleSerializer(serializers.Serializer):
    customer_name = serializers.CharField(max_length=255)
    phone_number = serializers.CharField(max_length=15)
    medicines = serializers.ListField(child=serializers.DictField(child=serializers.CharField()))
    
    def validate(self, data):
        medicines_data = data.get('medicines', [])
        if not medicines_data:
            raise serializers.ValidationError("Phải có ít nhất một thuốc trong đơn hàng")
        for item in medicines_data:
            medicine_id = item.get('medicine_id')
            quantity = item.get('quantity', 1)
            medicine = Medicine.objects.get(id=medicine_id)
            
            if medicine.quantity < int(quantity):
                raise serializers.ValidationError(f"Không đủ hàng cho thuốc {medicine.name}. Còn lại: {medicine.quantity}")
            
            item['medicine_obj'] = medicine
            item['quantity'] = int(quantity) 
        return data
    
    @transaction.atomic
    def create(self, validated_data):
        customer_name = validated_data['customer_name']
        phone_number = validated_data['phone_number']
        medicines_data = validated_data['medicines']
        
        offline_customer = User.objects.create(
            username=str(uuid.uuid4()),
            first_name='',
            last_name=customer_name,
            phone_number=phone_number,
            userRole='cus_off',
            email=None,
            is_active=True
        )
        
        total = sum(item['medicine_obj'].price * item['quantity'] for item in medicines_data)
        
        order = Order.objects.create(
            date=date.today(),
            paymentMethod='cod',
            total=total,
            user=offline_customer,
            status='delivered',
            shipping_fee=None
        )
        
        for item in medicines_data:
            medicine = item['medicine_obj']
            quantity = item['quantity']
            
            # Create order detail
            OrderDetail.objects.create(
                order=order,
                medicine=medicine,
                quantity=quantity,
                price=medicine.price
            )
            
            # Update medicine stock
            medicine.quantity -= quantity
            medicine.save()
        
        PaymentDetail.objects.create(
            order=order,
            amount=str(total),
            status='completed',
            method='cod'
        )
        
        return {
            'order': order,
            'customer': offline_customer
        }




