from rest_framework import serializers
from .models import Order


class OrderSerializer(serializers.ModelSerializer):
    client_name = serializers.CharField(source='client.get_full_name', read_only=True)
    builder_name = serializers.CharField(source='builder.get_full_name', read_only=True, default=None)

    class Meta:
        model = Order
        fields = [
            'id', 'client', 'client_name', 'builder', 'builder_name',
            'title', 'description', 'address',
            'budget', 'status', 'created_at', 'updated_at',
        ]
        read_only_fields = ['client', 'builder', 'status', 'created_at', 'updated_at']