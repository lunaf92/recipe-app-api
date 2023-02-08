"""
Tests for the tags API
"""
from decimal import Decimal

from core.models import Recipe, Tag
from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from recipe.serializers import TagSerializer
from rest_framework import status
from rest_framework.test import APIClient

TAGS_URL = reverse("recipe:tag-list")


def tag_detail_url(tag_id):
    """Create and return tag detail"""
    return reverse("recipe:tag-detail", args=[tag_id])


def create_user(email="test@example.com", password="Test123"):
    return get_user_model().objects.create_user(email=email, password=password)


class PublicTagsApiTests(TestCase):
    """Test unauthenticated api requests"""

    def setUp(self) -> None:
        self.client = APIClient()

    def test_auth_required(self):
        """Test auth is required to continue"""
        res = self.client.get(TAGS_URL)

        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)


class PrivateTagsApiTests(TestCase):
    """Test authenticated api requests"""

    def setUp(self) -> None:
        self.user = create_user()
        self.client = APIClient()
        self.client.force_authenticate(user=self.user)

    def test_retrieve_tags(self):
        """Test retrieve a list  of tags"""
        Tag.objects.create(user=self.user, name="Vegan")
        Tag.objects.create(user=self.user, name="Dessert")

        res = self.client.get(TAGS_URL)

        tags = Tag.objects.all().order_by("-name")
        serializer = TagSerializer(tags, many=True)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data, serializer.data)

    def test_tags_limited_to_user(self):
        """Test retrieved tags are limited to the authenticated users only"""
        user2 = create_user(email="user2@example.com")

        Tag.objects.create(user=user2, name="Gluten Free")
        Tag.objects.create(user=user2, name="Starter")
        Tag.objects.create(user=self.user, name="Vegan")
        tag = Tag.objects.create(user=self.user, name="Dessert")
        res = self.client.get(TAGS_URL)

        tags = Tag.objects.all().filter(user=self.user).order_by("-name")
        serializer = TagSerializer(tags, many=True)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data, serializer.data)
        self.assertEqual(len(res.data), 2)
        self.assertEqual(res.data[1]["name"], tag.name)
        self.assertEqual(res.data[1]["id"], tag.id)

    def test_update_tag(self):
        """Tet update tag works"""
        tag = Tag.objects.create(user=self.user, name="Vegan")
        payload = {"name": "Meaty"}
        res = self.client.put(tag_detail_url(tag.id), payload)

        tag.refresh_from_db()

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data["name"], tag.name)
        self.assertEqual(tag.name, payload["name"])

    def test_delete_tag(self):
        """Tet delete tag works"""
        tag = Tag.objects.create(user=self.user, name="Vegan")

        res = self.client.delete(tag_detail_url(tag.id))

        self.assertEqual(res.status_code, status.HTTP_204_NO_CONTENT)

        tags = Tag.objects.filter(user=self.user)
        self.assertFalse(tags.exists())

    def test_tag_in_use_filter(self):
        """Testing that only the tags in use are returned"""
        t1 = Tag.objects.create(user=self.user, name="tag one")
        t2 = Tag.objects.create(user=self.user, name="tag two")
        t3 = Tag.objects.create(user=self.user, name="tag three")
        r1 = Recipe.objects.create(
            user=self.user,
            title="recipe one",
            price=Decimal("2.30"),
            time_minutes=30,
        )
        r2 = Recipe.objects.create(
            user=self.user,
            title="recipe two",
            price=Decimal("2.30"),
            time_minutes=30,
        )

        r1.tags.add(t1)
        r2.tags.add(t2)

        s1 = TagSerializer(t1)
        s2 = TagSerializer(t2)
        s3 = TagSerializer(t3)

        params = {"assigned_only": 1}
        res = self.client.get(TAGS_URL, params)
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertIn(s1.data, res.data)
        self.assertIn(s2.data, res.data)
        self.assertNotIn(s3.data, res.data)

    def test_tags_unique(self):
        """testing that filtering tags does not return duplicates"""
        t1 = Tag.objects.create(user=self.user, name="tag one")
        Tag.objects.create(user=self.user, name="tag two")
        r1 = Recipe.objects.create(
            user=self.user,
            title="recipe one",
            price=Decimal("2.30"),
            time_minutes=30,
        )
        r2 = Recipe.objects.create(
            user=self.user,
            title="recipe two",
            price=Decimal("2.30"),
            time_minutes=30,
        )

        r1.tags.add(t1)
        r2.tags.add(t1)

        params = {"assigned_only": 1}
        res = self.client.get(TAGS_URL, params)
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(len(res.data), 1)
