from django.db.models import Avg, Count
from rest_framework import serializers
from django.contrib.auth import get_user_model
from ..models import WorkPhoto, WorkerReview

User = get_user_model()


class WorkerListSerializer(serializers.ModelSerializer):
    full_name = serializers.CharField(source='get_full_name')
    avg_rating = serializers.FloatField(read_only=True)
    total_orders = serializers.IntegerField(read_only=True)

    class Meta:
        model = User
        fields = [
            'id', 'full_name',
            'avg_rating', 'total_orders',
        ]


class WorkerDetailSerializer(serializers.ModelSerializer):
    """Bitta quruvchi profili — to'liq ma'lumot"""
    full_name = serializers.CharField(source='get_full_name')
    avg_rating = serializers.FloatField(read_only=True)
    total_orders = serializers.IntegerField(read_only=True)

    class Meta:
        model = User
        fields = [
            'id', 'full_name', 'avatar',
            'bio', 'created_at', 'avg_rating', 'total_orders',
        ]


class WorkPhotoSerializer(serializers.ModelSerializer):
    class Meta:
        model = WorkPhoto
        fields = [
            'id', 'worker', 'title', 'image',
            'description', 'location', 'created_at', 'views_count',
        ]
        read_only_fields = ['worker', 'created_at', 'views_count']


class ReviewSerializer(serializers.ModelSerializer):
    client_name = serializers.CharField(source='client.get_full_name', read_only=True)

    class Meta:
        model = WorkerReview
        fields = [
            'id', 'order', 'worker', 'client', 'client_name',
            'rating', 'comment', 'created_at',
        ]
        read_only_fields = ['worker', 'client', 'created_at']

class ReviewInputSerializer(serializers.Serializer):
    order = serializers.IntegerField(min_value=1, max_value=2**63 - 1)
    rating = serializers.IntegerField(min_value=1, max_value=5)
    comment = serializers.CharField(max_length=500, required=False, allow_blank=True, default='')


class WorkerReviewsSerializer(serializers.Serializer):
    worker_id = serializers.IntegerField()
    worker_name = serializers.CharField()
    reviews = ReviewSerializer(many=True)
