"""
Test for recipe APIs
"""
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from rest_framework import status
from rest_framework.test import APIClient

from core.models import Recipe

from recipe.serializers import (
    RecipeSerializer,
    RecipeDetailSerializer,
)


RECIPE_URL = reverse('recipe:recipe-list')


def detail_url(recipe_id):
    """Create and return a recipe detail url"""
    return reverse('recipe:recipe-detail', args=[recipe_id])


def create_recipe(user, **params) -> Recipe:
    """Create and return a sample recipe"""
    defaults = {
        'title': "Sample Recipe Title",
        'time_minutes': 22,
        "price": Decimal('5.25'),
        'description': 'Sample description',
        'link': 'http://example.com/recipe.pdf'
    }
    defaults.update(params)

    recipe = Recipe.objects.create(user=user, **defaults)
    return recipe


def create_user(**params):
    """Create and return a new user"""
    return get_user_model().objects.create_user(**params)


class PublicApiRecipeTest(TestCase):
    '''Test unauthenticated API requests'''

    def setUp(self) -> None:
        self.client = APIClient()

    def test_auth_required(self):
        """Test Auth is rquired to call APIs"""
        res = self.client.get(RECIPE_URL)
        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)


class PrivateRecipeApiTest(TestCase):
    """Test authenticated API requests"""

    def setUp(self) -> None:
        self.client = APIClient()
        self.user = create_user(
            email='user@example.com',
            password='testPass123')
        self.client.force_authenticate(user=self.user)

    def test_retirieve_recipes(self):
        """Test Retirieving a list of rcipes"""

        create_recipe(user=self.user)
        create_recipe(user=self.user)

        res = self.client.get(RECIPE_URL)
        recipes = Recipe.objects.all().order_by('-id')
        serializer = RecipeSerializer(recipes, many=True)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data, serializer.data)

    def test_resipe_list_limited_to_user(self):
        """Test List of Recipe is limited to authenticated user"""
        other_user = create_user(email='otheruser@example.com',
                                 password='pass1234')

        create_recipe(user=other_user)
        create_recipe(user=self.user)
        res = self.client.get(RECIPE_URL)
        recipes = Recipe.objects.filter(user=self.user)
        serializer = RecipeSerializer(recipes, many=True)
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data, serializer.data)

    def test_get_recipe_detail(self):
        """Test get recipe detail"""
        recpie = create_recipe(user=self.user)

        url = detail_url(recipe_id=recpie.id)
        res = self.client.get(url)

        serializer = RecipeDetailSerializer(recpie)
        self.assertEqual(res.data, serializer.data)

    def test_create_recipe(self):
        """Test creating recipe"""
        payload = {
            'title': "Sample Recipe Title",
            'time_minutes': 30,
            "price": Decimal('5.25')
        }
        res = self.client.post(RECIPE_URL, payload)  # api/recipes/recipe

        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        recipe = Recipe.objects.get(id=res.data['id'])

        for k, v in payload.items():
            self.assertEqual(getattr(recipe, k), v)
        self.assertEqual(recipe.user, self.user)

    def test_partial_update(self):
        """Test partial update recipe"""
        original_link = 'https://recipe.com/recipe.pdf'
        recipe = create_recipe(
            user=self.user,
            title='sample title',
            link=original_link,
        )

        payload = {
            "title": 'new title',
        }
        url = detail_url(recipe_id=recipe.id)
        res = self.client.patch(url, payload)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        recipe.refresh_from_db()

        self.assertEqual(recipe.title, payload['title'])
        self.assertEqual(recipe.link, original_link)
        self.assertEqual(recipe.user, self.user)

    def test_full_update(self):
        """Full update recipe"""
        recipe = create_recipe(user=self.user)
        payload = {
            'title': "Sample New Recipe Title",
            'time_minutes': 23,
            "price": Decimal('25.33'),
            'description': 'New description',
            'link': 'http://example.com/recipe1.pdf'
        }

        url = detail_url(recipe_id=recipe.id)
        res = self.client.put(url, payload)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        recipe.refresh_from_db()
        for k, v in payload.items():
            self.assertEqual(getattr(recipe, k), v)
        self.assertEqual(recipe.user, self.user)

    def test_update_user_returns_error(self):
        """changing recipe user return error"""
        new_user = create_user(email='user2@example.com',
                               password='testpass213')
        recipe = create_recipe(user=self.user)

        payload = {
            "user": new_user.id
        }
        url = detail_url(recipe_id=recipe.id)
        self.client.patch(url, payload)

        recipe.refresh_from_db()

        self.assertEqual(recipe.user, self.user)

    def test_delete_recipe(self):
        """Test Deleting a recipe from database is successful"""
        recipe = create_recipe(user=self.user)

        url = detail_url(recipe_id=recipe.id)
        res = self.client.delete(url)

        self.assertEqual(res.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(Recipe.objects.filter(id=recipe.id).exists())

    def test_recipe_other_users_recipe_error(self):
        """Test try to delete another users recipe gives error"""
        new_user = create_user(email='new_user@example.com',
                               password='testpass123')
        recipe = create_recipe(user=new_user)

        url = detail_url(recipe_id=recipe.id)
        res = self.client.delete(url)

        self.assertEqual(res.status_code, status.HTTP_404_NOT_FOUND)
        self.assertTrue(Recipe.objects.filter(id=recipe.id).exists())
