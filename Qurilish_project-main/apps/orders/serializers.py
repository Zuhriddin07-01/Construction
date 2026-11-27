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

    def to_representation(self, instance):
        data = super().to_representation(instance)
        viewer_id = self.context.get('viewer_id')
        if viewer_id is not None and viewer_id not in (instance.client_id, instance.builder_id):
            data['address'] = ''
            data['client'] = None
            data['client_name'] = ''
        return data


class OrderStatusSerializer(serializers.Serializer):
    status = serializers.ChoiceField(choices=[
        Order.Status.ACCEPTED, Order.Status.REJECTED, Order.Status.IN_WORK, Order.Status.DONE,
    ])
