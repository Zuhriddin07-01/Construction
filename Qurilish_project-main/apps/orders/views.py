from django.db import models
from rest_framework import generics, permissions, status
from rest_framework.exceptions import PermissionDenied
from rest_framework.response import Response
from .models import Order
from .serializers import OrderSerializer

class OrderListCreateView(generics.ListCreateAPIView):
    serializer_class = OrderSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        if user.role == 'client':
            return Order.objects.filter(client=user)
        elif user.role == 'builder':
            # Quruvchi o'ziga biriktirilgan buyurtmalarni
            # va hali hech kimga biriktirilmagan (pending) buyurtmalarni ko'radi
            return Order.objects.filter(
                models.Q(builder=user) | models.Q(builder__isnull=True, status=Order.Status.PENDING)
            )
        return Order.objects.none()

    def perform_create(self, serializer):
        if self.request.user.role != 'client':
            raise PermissionDenied('Faqat mijozlar buyurtma bera oladi')
        serializer.save(client=self.request.user)


class OrderDetailView(generics.RetrieveUpdateAPIView):
    serializer_class = OrderSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        if user.role == 'client':
            return Order.objects.filter(client=user)
        elif user.role == 'builder':
            return Order.objects.filter(
                models.Q(builder=user) | models.Q(builder__isnull=True, status=Order.Status.PENDING)
            )
        return Order.objects.none()

    def patch(self, request, *args, **kwargs):
        order = self.get_object()
        new_status = request.data.get('status')
        allowed = ['accepted', 'rejected', 'in_work', 'done']

        if new_status not in allowed:
            return Response({'error': "Noto'g'ri status"}, status=400)

        user = request.user

        if new_status in ('accepted', 'rejected'):
            # Faqat quruvchi buyurtmani qabul qilishi/rad etishi mumkin
            if user.role != 'builder':
                return Response(
                    {'error': 'Faqat quruvchilar buyurtmani qabul qilishi/rad etishi mumkin'},
                    status=status.HTTP_403_FORBIDDEN,
                )
            if order.builder is not None and order.builder != user:
                return Response(
                    {'error': 'Bu buyurtma allaqachon boshqa quruvchiga biriktirilgan'},
                    status=status.HTTP_403_FORBIDDEN,
                )
            if new_status == 'accepted':
                order.builder = user

        elif new_status in ('in_work', 'done'):
            # Faqat shu buyurtmaga biriktirilgan quruvchi holatni o'zgartira oladi
            if user.role != 'builder' or order.builder != user:
                return Response(
                    {'error': 'Bu amalni faqat biriktirilgan quruvchi bajara oladi'},
                    status=status.HTTP_403_FORBIDDEN,
                )

        order.status = new_status
        order.save()
        return Response(OrderSerializer(order).data)
