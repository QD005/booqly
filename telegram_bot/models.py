from django.db import models

class TelegramUser(models.Model):
    user_id = models.BigIntegerField(unique=True, db_index=True)
    username = models.CharField(max_length=255, blank=True, null=True)
    first_name = models.CharField(max_length=255, blank=True, null=True)
    last_name = models.CharField(max_length=255, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    class Meta:
        ordering = ['-created_at']
    def __str__(self):
        return f"{self.first_name or 'User'} ({self.user_id})"

class Conversation(models.Model):
    DIRECTIONS = [('incoming', 'Incoming'), ('outgoing', 'Outgoing')]
    user = models.ForeignKey(TelegramUser, on_delete=models.CASCADE, related_name='conversations')
    message = models.TextField()
    direction = models.CharField(max_length=20, choices=DIRECTIONS)
    created_at = models.DateTimeField(auto_now_add=True)
    class Meta:
        ordering = ['-created_at']

class Product(models.Model):
    external_id = models.CharField(max_length=100, unique=True, db_index=True)
    name = models.CharField(max_length=500)
    price = models.CharField(max_length=50)
    rating = models.FloatField(null=True, blank=True)
    image_url = models.URLField(max_length=2000,blank=True, null=True)
    product_url = models.URLField(max_length=2000,blank=True, null=True)
    features = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    class Meta:
        ordering = ['-created_at']
    def __str__(self):
        return self.name[:60]

class Order(models.Model):
    STATUS_CHOICES = [('pending', 'Pending'), ('completed', 'Completed'), ('failed', 'Failed'), ('cancelled', 'Cancelled')]
    user = models.ForeignKey(TelegramUser, on_delete=models.CASCADE, related_name='orders')
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='orders')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    payment_id = models.CharField(max_length=255, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    class Meta:
        ordering = ['-created_at']
    def __str__(self):
        return f"Order #{self.id} - {self.status}"
