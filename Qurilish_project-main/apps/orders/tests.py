from django.contrib.auth import get_user_model
from rest_framework.test import APITestCase

from .models import Order


class OrderAccessTests(APITestCase):
    def setUp(self):
        user_model = get_user_model()
        self.owner = user_model.objects.create_user(username='client')
        self.builder = user_model.objects.create_user(username='builder', role='builder')
        self.order = Order.objects.create(
            client=self.owner, title='Painting', description='Paint one room', address='Private address',
        )
        self.url = f'/api/orders/{self.order.pk}/'

    def test_builder_claims_and_finishes_order(self):
        self.client.force_authenticate(self.builder)
        self.assertEqual(self.client.get(self.url).data['address'], '')
        self.assertEqual(self.client.patch(self.url, {'status': 'done'}).status_code, 400)
        accepted = self.client.patch(self.url, {'status': 'accepted'})
        self.assertEqual(accepted.status_code, 200)
        self.assertEqual(accepted.data['address'], 'Private address')
        self.assertEqual(self.client.patch(self.url, {'status': 'in_work'}).status_code, 200)
        self.assertEqual(self.client.patch(self.url, {'status': 'done'}).status_code, 200)
        self.assertEqual(self.client.patch(self.url, {'status': 'accepted'}).status_code, 400)

    def test_client_cannot_modify_order_through_put_or_set_status(self):
        self.client.force_authenticate(self.owner)
        self.assertEqual(self.client.put(self.url, {'title': 'Changed'}).status_code, 405)
        self.assertEqual(self.client.patch(self.url, {'status': 'accepted'}).status_code, 403)
        self.order.refresh_from_db()
        self.assertEqual(self.order.title, 'Painting')
