from django.contrib import admin
from .models import TelegramUser, Conversation, Product, Order

@admin.register(TelegramUser)
class TelegramUserAdmin(admin.ModelAdmin):
    list_display = ['user_id', 'username', 'first_name', 'created_at']
    search_fields = ['user_id', 'username', 'first_name']

@admin.register(Conversation)
class ConversationAdmin(admin.ModelAdmin):
    list_display = ['user', 'direction', 'created_at']
    list_filter = ['direction']

@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ['name', 'price', 'rating', 'created_at']
    search_fields = ['name', 'external_id']

@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ['id', 'user', 'product', 'status', 'created_at']
    list_filter = ['status']
    search_fields = ['payment_id']
