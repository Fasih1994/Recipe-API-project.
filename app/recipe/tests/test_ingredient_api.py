"""
Testing Ingerdient API
"""
from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from rest_framework import status
from rest_framework.test import APIClient

from core.models import Ingredient

from recipe.serializers import IngredientSerializer


INGREDIENT_URL = reverse("recipe:ingredient-list")


def detail_url(ingredient_id):
    """Create and return ingredient detail URL"""
    return reverse('recipe:ingredient-detail', args=[ingredient_id])


def create_user(email='user@example.com',
                password='testpass123'):
    return get_user_model().objects.create_user(email=email,
                                                password=password)


class PublicIngredientAPITest(TestCase):
    """Test unauthenticated user"""

    def setUp(self):
        self.client = APIClient()

    def test_auth_required(self):
        res = self.client.get(INGREDIENT_URL)
        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)


class PrivateIngredientAPITest(TestCase):
    """Test Authenticated API Requests"""

    def setUp(self):
        self.user = create_user()
        self.client = APIClient()
        self.client.force_authenticate(self.user)

    def test_retrive_ingredients(self):
        """Test retrieving list of ingredients"""
        Ingredient.objects.create(user=self.user, name='Banana')
        Ingredient.objects.create(user=self.user, name='Milk')

        res = self.client.get(INGREDIENT_URL)

        ingredients = Ingredient.objects.all().order_by('-name')
        serializer = IngredientSerializer(ingredients, many=True)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data, serializer.data)

    def test_ingredients_limited_to_user(self):
        """Test ingredients are limited to authenticated user"""
        user2 = create_user('user2@example.com', 'testpass123')
        Ingredient.objects.create(user=user2, name='Salt')

        ingredient = Ingredient.objects.create(user=self.user, name='Banana')

        res = self.client.get(INGREDIENT_URL)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(len(res.data), 1)
        self.assertEqual(res.data[0]['name'], ingredient.name)
        self.assertEqual(res.data[0]['id'], ingredient.id)

    def test_update_ingredient(self):
        """Test update an ingredient"""
        ingredient = Ingredient.objects.create(user=self.user, name='Sugar')
        payload = {
            "name": "Sucral"
        }
        url = detail_url(ingredient.id)

        res = self.client.patch(url, payload)
        self.assertEqual(res.status_code, status.HTTP_200_OK)

        ingredient.refresh_from_db()
        self.assertEqual(ingredient.name, payload['name'])

    def test_delete_ingredient(self):
        """Test Delete an ingredient"""
        ingredient = Ingredient.objects.create(user=self.user,
                                               name='New Ingredient')

        url = detail_url(ingredient.id)
        res = self.client.delete(url)

        self.assertEqual(res.status_code, status.HTTP_204_NO_CONTENT)

        ingredients = Ingredient.objects.filter(user=self.user)
        self.assertFalse(ingredients.exists())
