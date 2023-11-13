"""
Tests for the tags API
"""
from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from rest_framework import status
from rest_framework.test import APIClient

from core.models import Tag

from recipe.serializers import TagSerializer


TAGS_URL = reverse('recipe:tag-list')


def detaile_tag_url(tag_id):
    """Create and return a tag detail url"""
    return reverse('recipe:tag-detail', args=[tag_id])


def create_uesr(email='sample@example.com', password='testPas123'):
    return get_user_model().objects.create_user(email=email, password=password)


class PublicTagAPITest(TestCase):
    """Test unauthenticated API Request"""

    def setUp(self):
        self.client = APIClient()

    def test_auth_required(self):
        """Auth is required for retrieving tags"""
        res = self.client.get(TAGS_URL)

        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)


class PrivatAPITagTest(TestCase):
    """Test Authenticated API Requests"""

    def setUp(self):
        self.user = create_uesr()
        self.client = APIClient()
        self.client.force_authenticate(user=self.user)

    def test_retrieve_tags(self):
        """Test Retreving tags"""
        Tag.objects.create(user=self.user, name='Vegan')
        Tag.objects.create(user=self.user, name='Desert')

        res = self.client.get(TAGS_URL)

        tags = Tag.objects.all().order_by('-name')
        serialzer = TagSerializer(tags, many=True)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data, serialzer.data)

    def test_tags_limited_to_user(self):
        """Test Retreving tags"""
        user2 = create_uesr('user22@example.com', 'testPass1234')
        Tag.objects.create(user=user2, name='Desert')
        Tag.objects.create(user=user2, name='Fruity')
        tag = Tag.objects.create(user=self.user, name='Vegan')

        res = self.client.get(TAGS_URL)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(len(res.data), 1)
        self.assertEqual(res.data[0]['name'], tag.name)
        self.assertEqual(res.data[0]['id'], tag.id)

    def test_tag_update(self):
        """Test Updating Tags"""
        tag = Tag.objects.create(user=self.user, name='After Dinner')

        payload = {"name": 'Dessert'}
        url = detaile_tag_url(tag_id=tag.id)

        res = self.client.patch(url, payload)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        tag.refresh_from_db()

        self.assertEqual(tag.name, payload['name'])

    def test_delete_tag(self):
        """Deleteing a tag"""
        tag = Tag.objects.create(user=self.user, name='Frutiy')
        url = detaile_tag_url(tag.id)

        res = self.client.delete(url)
        self.assertEqual(res.status_code, status.HTTP_204_NO_CONTENT)

        tags = Tag.objects.filter(user=self.user)
        self.assertFalse(tags.exists())
