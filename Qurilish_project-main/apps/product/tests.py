from django.contrib.auth import get_user_model
from rest_framework.test import APITestCase

from .models import Product


class CatalogTests(APITestCase):
    def setUp(self):
        user_model = get_user_model()
        self.customer = user_model.objects.create_user(username='client')
        self.builder = user_model.objects.create_user(username='builder', role='builder')
        self.product = Product.objects.create(builder=self.builder, title='Paint', description='One room')
        self.client.force_authenticate(self.customer)

    def test_catalog_write_permissions(self):
        self.assertEqual(self.client.post('/api/products/', {
            'title': 'Drywall', 'description': 'One room',
        }).status_code, 403)
        response = self.client.patch(f'/api/products/{self.product.pk}/', {'title': 'Other'})
        self.assertEqual(response.status_code, 403)

    def test_rating_validation_and_missing_product(self):
        path = f'/api/products/{self.product.pk}/rate/'
        self.assertEqual(self.client.post(path, {'rating': 'bad'}).status_code, 400)
        self.assertEqual(self.client.post(path, {'rating': 4}).status_code, 200)
        self.assertEqual(self.client.post('/api/products/9999/rate/', {'rating': 4}).status_code, 404)
