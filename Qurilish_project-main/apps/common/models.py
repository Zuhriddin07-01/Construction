from django.db import models
from django.conf import settings


class WorkPhoto(models.Model):
    """Quruvchi (builder) yuklagan bajarilgan ish namunasi rasmi."""
    worker = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='work_photos',
        limit_choices_to={'role': 'builder'},
    )
    title = models.CharField(max_length=100, blank=True)
    image = models.ImageField(upload_to='work_photos/%Y/%m/%d/')
    description = models.TextField(max_length=500, blank=True)
    location = models.CharField(max_length=200, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    views_count = models.IntegerField(default=0)

    def __str__(self):
        return f"{self.worker.get_full_name()} - {self.title or self.image.name}"

    class Meta:
        ordering = ['-created_at']


class WorkerReview(models.Model):
    """Mijoz tomonidan bajarilgan buyurtma bo'yicha quruvchiga qoldirilgan sharh."""
    order = models.OneToOneField(
        'orders.Order',
        on_delete=models.CASCADE,
        related_name='review',
    )
    worker = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='reviews_received',
        limit_choices_to={'role': 'builder'},
    )
    client = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='reviews_given',
    )
    rating = models.IntegerField(choices=[(i, i) for i in range(1, 6)])
    comment = models.TextField(max_length=500, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.client} -> {self.worker} - {self.rating}\u2605"

    class Meta:
        ordering = ['-created_at']
