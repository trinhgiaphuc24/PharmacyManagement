from django.contrib import admin
from .models import User, MedicineGenre, Produce, Medicine, MedicineImage, Cart, CartItem, Order, OrderDetail, ChatHistory

class MyPharmacyAdminSite(admin.AdminSite):
    site_header = 'Pharmacy Management Dashboard'
    site_title = 'Pharmacy Admin'
    index_title = 'Welcome to Pharmacy Admin Dashboard'

admin_site = MyPharmacyAdminSite(name='pharmacy')

@admin.register(User, site=admin_site)
class UserAdmin(admin.ModelAdmin):
    list_display = ('username', 'email', 'first_name', 'last_name', 'userRole', 'is_active', 'createdAt')
    search_fields = ('username', 'email', 'first_name', 'last_name')
    list_filter = ('userRole', 'is_active', 'createdAt')
    ordering = ('-createdAt',)

@admin.register(MedicineGenre, site=admin_site)
class MedicineGenreAdmin(admin.ModelAdmin):
    list_display = ('name', 'active')
    search_fields = ('name',)
    list_filter = ('active',)

@admin.register(Produce, site=admin_site)
class ProduceAdmin(admin.ModelAdmin):
    list_display = ('name', 'active')
    search_fields = ('name',)
    list_filter = ('active',)

@admin.register(Medicine, site=admin_site)
class MedicineAdmin(admin.ModelAdmin):
    list_display = ('name', 'price', 'use', 'medicineGenre', 'produce', 'active', 'createdAt')
    search_fields = ('name', 'use')
    list_filter = ('medicineGenre', 'produce', 'active')
    ordering = ('-createdAt',)

@admin.register(MedicineImage, site=admin_site)
class MedicineImageAdmin(admin.ModelAdmin):
    list_display = ('medicine', 'imgMedicineUrl')
    search_fields = ('medicine__name',)

@admin.register(Cart, site=admin_site)
class CartAdmin(admin.ModelAdmin):
    list_display = ('user',)
    search_fields = ('user__username',)

@admin.register(CartItem, site=admin_site)
class CartItemAdmin(admin.ModelAdmin):
    list_display = ('cart', 'medicine', 'quantity')
    search_fields = ('cart__user__username', 'medicine__name')

@admin.register(Order, site=admin_site)
class OrderAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'date', 'status', 'total', 'paymentMethod', 'createdAt')
    search_fields = ('user__username', 'address')
    list_filter = ('status', 'paymentMethod', 'date')
    ordering = ('-createdAt',)

@admin.register(OrderDetail, site=admin_site)
class OrderDetailAdmin(admin.ModelAdmin):
    list_display = ('order', 'medicine', 'quantity', 'price')
    search_fields = ('order__user__username', 'medicine__name')


@admin.register(ChatHistory, site=admin_site)
class ChatHistoryAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'user_message_preview', 'created_at')
    list_filter = ('created_at',)
    search_fields = ('user__username', 'user_message', 'bot_response')
    readonly_fields = ('created_at',)
    ordering = ('-created_at',)
    
    def user_message_preview(self, obj):
        return obj.user_message[:100] + "..." if len(obj.user_message) > 100 else obj.user_message
    user_message_preview.short_description = 'Tin nhắn người dùng'
