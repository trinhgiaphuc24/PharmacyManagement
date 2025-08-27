from django.contrib import admin
from django.urls import path
from django.shortcuts import render
from django.db.models import Count, Sum, Q
from django.db.models.functions import Extract
from django.utils import timezone
from .models import User, MedicineGenre, Produce, Medicine, MedicineImage, Cart, CartItem, Order, OrderDetail
import json

class MyPharmacyAdminSite(admin.AdminSite):
    site_header = 'Pharmacy Management Dashboard'
    site_title = 'Pharmacy Admin'
    index_title = 'Welcome to Pharmacy Admin Dashboard'
    index_template = 'admin/index.html'
    
    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path('stats/', self.admin_view(self.stats_view), name='stats'),
        ]
        return custom_urls + urls
    
    def index(self, request, extra_context=None):
        """Override index để thêm link thống kê"""
        from django.template.loader import render_to_string
        from django.utils.safestring import mark_safe
        
        extra_context = extra_context or {}
        extra_context['stats_url'] = '/admin/stats/'
        
        # Tạo HTML cho button thống kê và đưa vào context
        stats_html = '''
        <div class="module" style="background: linear-gradient(135deg, #f8f9fa, #e9ecef); padding: 25px; border-radius: 10px; margin: 25px 0; border-left: 5px solid #007cba; box-shadow: 0 2px 10px rgba(0, 0, 0, 0.1);">
            <h2 style="color: #007cba; margin-bottom: 10px; font-size: 24px;">Thống kê & Báo cáo</h2>
            <p style="color: #555; margin-bottom: 15px; font-size: 14px; line-height: 1.5;">Xem thống kê đơn hàng theo tháng, năm và trạng thái với biểu đồ trực quan</p>
            <a href="/admin/stats/" style="background: linear-gradient(135deg, #007cba, #005a87); color: white !important; padding: 12px 24px; border-radius: 6px; text-decoration: none; display: inline-block; margin: 15px 0; font-weight: bold; font-size: 16px; transition: all 0.3s ease; box-shadow: 0 2px 4px rgba(0, 124, 186, 0.3);">Xem thống kê đơn hàng</a>
        </div>
        '''
        
        extra_context['stats_button'] = mark_safe(stats_html)
        
        return super().index(request, extra_context)
    
    def stats_view(self, request):
        """View cho trang thống kê đơn hàng"""
        current_year = timezone.now().year
        selected_year = int(request.GET.get('year', current_year))
        
        # Thống kê đơn hàng theo tháng - chỉ tính đơn đã giao
        monthly_stats = (
            Order.objects
            .filter(createdAt__year=selected_year, status='delivered')
            .values('createdAt__month')
            .annotate(
                total_orders=Count('id'),
                total_revenue=Sum('total')
            )
            .order_by('createdAt__month')
        )
        
        # Thống kê theo trạng thái và tháng - chỉ 2 trạng thái
        status_stats = (
            Order.objects
            .filter(createdAt__year=selected_year, status__in=['delivered', 'canceled'])
            .values('createdAt__month', 'status')
            .annotate(count=Count('id'))
            .order_by('createdAt__month', 'status')
        )
        
        # Thống kê nơi nhận - chỉ đơn đã giao
        shipping_stats = (
            Order.objects
            .filter(createdAt__year=selected_year, status='delivered')
            .values('createdAt__month')
            .annotate(
                home_delivery=Count('id', filter=Q(online_order__shipping_method='home_delivery')),
                store_pickup=Count('id', filter=Q(online_order__shipping_method='store_pickup')),
                home_revenue=Sum('total', filter=Q(online_order__shipping_method='home_delivery')),
                store_revenue=Sum('total', filter=Q(online_order__shipping_method='store_pickup'))
            )
            .order_by('createdAt__month')
        )
        
        # Chuẩn bị dữ liệu cho biểu đồ
        months = list(range(1, 13))
        monthly_data = {month: {'total_orders': 0, 'total_revenue': 0} for month in months}
        
        for stat in monthly_stats:
            month = stat['createdAt__month']
            monthly_data[month] = {
                'total_orders': stat['total_orders'],
                'total_revenue': stat['total_revenue'] or 0
            }
        
        # Dữ liệu cho biểu đồ trạng thái - chỉ 2 trạng thái
        status_data = {}
        for stat in status_stats:
            month = stat['createdAt__month']
            status = stat['status']
            if month not in status_data:
                status_data[month] = {}
            status_data[month][status] = stat['count']
        
        # Dữ liệu cho biểu đồ nơi nhận
        shipping_data = {}
        for stat in shipping_stats:
            month = stat['createdAt__month']
            shipping_data[month] = {
                'home_delivery': stat['home_delivery'] or 0,
                'store_pickup': stat['store_pickup'] or 0,
                'home_revenue': stat['home_revenue'] or 0,
                'store_revenue': stat['store_revenue'] or 0
            }
        
        # Chuẩn bị dữ liệu JSON cho Chart.js
        chart_labels = [f"Tháng {month}" for month in months]
        chart_data = [monthly_data[month]['total_orders'] for month in months]
        revenue_data = [monthly_data[month]['total_revenue'] for month in months]
        
        # Danh sách các năm có dữ liệu
        data_years = list(
            Order.objects
            .dates('createdAt', 'year')
            .values_list('createdAt__year', flat=True)
            .distinct()
        )
        
        # Tạo danh sách các năm từ hiện tại về trước (5 năm gần nhất)
        year_range = range(current_year - 4, current_year + 1)  # 4 năm trước đến năm hiện tại
        all_years = set(year_range)  # Thêm các năm cơ bản
        all_years.update(data_years)  # Thêm các năm có dữ liệu
        
        # Chỉ giữ lại những năm <= năm hiện tại
        valid_years = [year for year in all_years if year <= current_year]
        
        # Sắp xếp từ mới nhất về cũ nhất
        available_years = sorted(valid_years, reverse=True)
        
        context = {
            'selected_year': selected_year,
            'available_years': available_years,
            'monthly_stats': json.dumps(monthly_data),
            'status_stats': json.dumps(status_data),
            'shipping_stats': json.dumps(shipping_data),
            'chart_labels': json.dumps(chart_labels),
            'chart_data': json.dumps(chart_data),
            'revenue_data': json.dumps(revenue_data),
            'months': months,
            'status_choices': json.dumps({'delivered': 'Đã giao', 'canceled': 'Đã hủy'}),
            'shipping_choices': json.dumps({'home_delivery': 'Giao hàng tại nhà', 'store_pickup': 'Nhận hàng tại cửa hàng'}),
        }
        
        return render(request, 'admin/stats.html', context)

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
