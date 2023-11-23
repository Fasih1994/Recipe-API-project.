"""
Test for recipe APIs
"""
from decimal import Decimal
import tempfile
import os

from PIL import Image

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from rest_framework import status
from rest_framework.test import APIClient

from core.models import (
    Recipe,
    Tag,
    Ingredient
)

from recipe.serializers import (
    RecipeSerializer,
    RecipeDetailSerializer,
)


RECIPE_URL = reverse('recipe:recipe-list')


def detail_url(recipe_id):
    """Create and return a recipe detail url"""
    return reverse('recipe:recipe-detail', args=[recipe_id])


def image_upload_url(recipe_id):
    """Create and return an image upload url"""
    return reverse('recipe:recipe-upload-image', args=[recipe_id])


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

    def test_create_recipe_with_new_tag(self):
        """Creating recipe with new tag"""
        payload = {
            'title': "Thai Prawn Curry",
            'time_minutes': 30,
            'price': Decimal('2.50'),
            "tags": [
                {'name': 'Thai'},
                {'name': 'Dinner'},
            ]
        }

        res = self.client.post(RECIPE_URL, payload, format='json')

        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        recipes = Recipe.objects.filter(user=self.user)

        self.assertEqual(recipes.count(), 1)

        recipe = recipes[0]

        self.assertEqual(recipe.tags.count(), 2)
        for tag in payload['tags']:
            exists = recipe.tags.filter(
                name=tag['name'],
                user=self.user
            ).exists()
            self.assertTrue(exists)

    def test_create_recipe_with_existing_tag(self):
        tag_asian = Tag.objects.create(user=self.user, name='Asian')

        payload = dict(
            title='Pongal',
            time_minutes=60,
            price=Decimal('4.50'),
            tags=[
                {"name": tag_asian.name},
                {"name": 'Breakfast'},
            ]
        )

        res = self.client.post(RECIPE_URL, payload, format='json')
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)

        recipes = Recipe.objects.filter(user=self.user)
        self.assertEqual(recipes.count(), 1)

        recipe = recipes[0]
        self.assertEqual(recipe.tags.count(), 2)
        self.assertIn(tag_asian, recipe.tags.all())

        for tag in payload['tags']:
            exists = recipe.tags.filter(
                name=tag['name'],
                user=self.user
            ).exists()
            self.assertTrue(exists)

    def test_create_tags_on_recipe_update(self):
        """Create tag on recipe update if not exists"""
        recipe = create_recipe(user=self.user)

        payload = {'tags': [{'name': 'lunch'}]}
        url = detail_url(recipe_id=recipe.id)
        res = self.client.patch(url, payload, format='json')

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        new_tag = Tag.objects.get(user=self.user, name='lunch')
        self.assertIn(new_tag, recipe.tags.all())

    def test_update_recipe_assign_tags(self):
        """assigning an existing tag when updating a recipe"""
        tag_asian = Tag.objects.create(user=self.user, name='Asian')
        recipe = create_recipe(user=self.user)
        recipe.tags.add(tag_asian)

        tag_lunch = Tag.objects.create(user=self.user, name='Lunch')
        payload = {'tags': [{'name': tag_lunch.name}]}
        url = detail_url(recipe_id=recipe.id)

        res = self.client.patch(url, payload, format='json')
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertIn(tag_lunch, recipe.tags.all())
        self.assertNotIn(tag_asian, recipe.tags.all())

    def test_clear_recipe_tag(self):
        """Clear recipe tags upon delete"""
        tag_asian = Tag.objects.create(user=self.user, name='Asian')
        recipe = create_recipe(user=self.user)
        recipe.tags.add(tag_asian)

        payload = {'tags': []}
        url = detail_url(recipe_id=recipe.id)
        res = self.client.patch(url, payload, format='json')

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(recipe.tags.count(), 0)

    def test_create_recipe_with_new_ingredient(self):
        """Test creating a recipe with new ingredients"""
        payload = {
            "title": "New Recipe",
            'time_minutes': 30,
            'price': Decimal('3.50'),
            'ingredients': [
                {'name': 'ingredient1'},
                {'name': 'ingredient2'},
            ]
        }

        res = self.client.post(RECIPE_URL, payload, format='json')
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        recipes = Recipe.objects.filter(user=self.user)
        self.assertEqual(recipes.count(), 1)

        recipe = recipes[0]
        self.assertEqual(recipe.ingredients.count(), 2)

        for ingredient in payload['ingredients']:
            exists = recipe.ingredients.filter(
                user=self.user,
                name=ingredient['name']
            ).exists()
            self.assertTrue(exists)

    def test_create_recipe_with_exisiting_ingredient(self):
        """Test create a recipe with existing ingredient"""
        ingredient = Ingredient.objects.create(user=self.user,
                                               name='Salt')
        payload = {
            'title': 'Salted Peanut',
            'time_minutes': 10,
            'price': Decimal('3.50'),
            'ingredients': [
                {'name': ingredient.name},
                {'name': 'Peanut'}
            ]
        }

        res = self.client.post(RECIPE_URL, payload, format='json')
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)

        recipes = Recipe.objects.filter(user=self.user)
        self.assertEqual(recipes.count(), 1)
        recipe = recipes[0]
        self.assertEqual(recipe.ingredients.count(), 2)
        self.assertIn(ingredient, recipe.ingredients.all())

        for ingredient in payload['ingredients']:
            exists = recipe.ingredients.filter(
                user=self.user,
                name=ingredient['name']
            ).exists()
            self.assertTrue(exists)

    def test_creating_ingredient_on_update(self):
        """Test creating ingredient on recipe update"""
        recipe = create_recipe(user=self.user)

        payload = {'ingredients': [{'name': 'salt'}]}
        url = detail_url(recipe.id)
        res = self.client.patch(url, payload, format='json')

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        ingredient = Ingredient.objects.get(
            user=self.user,
            name=payload['ingredients'][0]['name']
        )
        self.assertIn(ingredient, recipe.ingredients.all())

    def test_update_recipe_assign_ingredient(self):
        """Test assigning an existing ingredient on recipe update"""
        ingredient_salt = Ingredient.objects.create(user=self.user,
                                                    name='Salt')
        recipe = create_recipe(user=self.user)
        recipe.ingredients.add(ingredient_salt)

        payload = {'ingredients': [{'name': 'vinegor'}]}
        ingredient_vinegor = Ingredient.objects.create(
            user=self.user, name=payload['ingredients'][0]['name'])

        url = detail_url(recipe_id=recipe.id)
        res = self.client.patch(url, payload, format='json')

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertIn(ingredient_vinegor, recipe.ingredients.all())
        self.assertNotIn(ingredient_salt, recipe.ingredients.all())

    def test_clear_recipe_ingredients_on_update(self):
        """Clearing ingredients on recipe update"""
        ingredient = Ingredient.objects.create(
            user=self.user,
            name='Salt'
        )
        recipe = create_recipe(user=self.user)
        recipe.ingredients.add(ingredient)

        payload = {
            "ingredients": []
        }
        url = detail_url(recipe.id)
        res = self.client.patch(url, payload, format='json')

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(recipe.ingredients.count(), 0)

    def test_filter_by_tags(self):
        """Test filtering recipe by tags."""
        r1 = create_recipe(user=self.user, title='Thai vegetable Curry')
        r2 = create_recipe(user=self.user, title='Dal Chawal with Lawazmat')
        r3 = create_recipe(user=self.user, title='Fish and Chips')
        tag1 = Tag.objects.create(user=self.user, name='Vegan')
        tag2 = Tag.objects.create(user=self.user, name='Dal')

        r1.tags.add(tag1)
        r2.tags.add(tag2)

        params = {'tags': f'{tag1.id},{tag2.id}'}
        res = self.client.get(RECIPE_URL, params)

        s1 = RecipeSerializer(r1)
        s2 = RecipeSerializer(r2)
        s3 = RecipeSerializer(r3)

        self.assertIn(s1.data, res.data)
        self.assertIn(s2.data, res.data)
        self.assertNotIn(s3.data, res.data)

    def test_filter_by_ingredients(self):
        """Filtering recipes by ingredients"""
        r1 = create_recipe(user=self.user, title='Thai vegetable Curry')
        r2 = create_recipe(user=self.user, title='Dal Chawal with Lawazmat')
        r3 = create_recipe(user=self.user, title='Fish and Chips')

        in1 = Ingredient.objects.create(user=self.user, name='Yougert')
        in2 = Ingredient.objects.create(user=self.user, name='Rice')

        r1.ingredients.add(in1)
        r2.ingredients.add(in2)

        params = {'ingredients': f'{in1.id},{in2.id}'}

        res = self.client.get(RECIPE_URL, params)

        s1 = RecipeSerializer(r1)
        s2 = RecipeSerializer(r2)
        s3 = RecipeSerializer(r3)

        self.assertIn(s1.data, res.data)
        self.assertIn(s2.data, res.data)
        self.assertNotIn(s3.data, res.data)


class ImageUploadTest(TestCase):
    """Test for the image upload API"""

    def setUp(self):
        self.client = APIClient()
        self.user = get_user_model().objects.create_user(
            'user@example.com',
            'testPassq123'
        )
        self.client.force_authenticate(self.user)
        self.recipe = create_recipe(user=self.user)

    def tearDown(self) -> None:
        self.recipe.image.delete()

    def test_upload_image(self):
        """Test Uploading an image to the recipe"""
        url = image_upload_url(self.recipe.id)
        with tempfile.NamedTemporaryFile(suffix='.jpg') as image_file:
            img = Image.new('RGB', (10, 10))  # create a 10x10 black box image
            img.save(image_file, format='JPEG')
            image_file.seek(0)  # go back to beginning of file
            payload = {'image': image_file}
            res = self.client.post(url, payload, format='multipart')

        self.recipe.refresh_from_db()
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertIn('image', res.data)
        self.assertTrue(os.path.exists(self.recipe.image.path))

    def test_uploading_invalid_image(self):
        url = image_upload_url(self.recipe.id)
        payload = {'image': 'not an image'}
        res = self.client.post(url, payload, format='multipart')

        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
