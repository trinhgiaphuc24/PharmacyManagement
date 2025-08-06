from django.contrib.auth.hashers import make_password
from pharmacies.models import *
from rest_framework import serializers
from rest_framework.serializers import ModelSerializer, SerializerMethodField


class UserSerializer(ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'password', 'phone_number', 'first_name', 'last_name', 'userRole', 'avatarUrl']

    def to_representation(self, instance):
        data = super().to_representation(instance)
        data['avatar'] = instance.avatarUrl.url if instance.avatarUrl else None
        return data

    def create(self, validated_data):
        data = validated_data.copy()
        u = User(**data)
        u.set_password(u.password)
        u.save()
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
    class Meta:
        model = CartItem
        fields = ['id', 'cart', 'medicine', 'quantity']


class CartSerializer(ModelSerializer):
    items = CartItemSerializer(many=True, read_only=True)
    class Meta:
        model = Cart
        fields = ['id', 'user', 'items']


class OrderDetailSerializer(ModelSerializer):
    class Meta:
        model = OrderDetail
        fields = ['id', 'order', 'medicine', 'quantity', 'price']


class OrderSerializer(ModelSerializer):
    details = OrderDetailSerializer(many=True, read_only=True)
    class Meta:
        model = Order
        fields = ['id', 'date', 'status', 'createdAt', 'address', 'paymentMethod', 'total', 'user', 'details']


class ChatHistorySerializer(ModelSerializer):
    class Meta:
        model = ChatHistory
        fields = ['id', 'user_message', 'bot_response', 'created_at']