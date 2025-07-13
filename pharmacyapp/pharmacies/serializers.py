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