"""
Tests for the recipe API
"""
from decimal import Decimal

from core.models import Recipe
from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from recipe.serializers import RecipeDetailSerializer, RecipeSerializer
from rest_framework import status
from rest_framework.test import APIClient

RECIPES_URL = reverse("recipe:recipe-list")


def detail_url(recipe_id):
    """Create and return a recipe detail url"""
    return reverse("recipe:recipe-detail", args=[recipe_id])


def create_recipe(user, **params):
    """Create and return a sample recipe."""
    defaults = {
        "title": "Sample recipe title",
        "description": "Sample recipe description",
        "time_minutes": 22,
        "price": Decimal("5.25"),
        "link": "http://example.com/recipe.pdf",
    }
    defaults.update(params)

    recipe = Recipe.objects.create(user=user, **defaults)
    return recipe


def create_user(**params):
    """Create and return a new user"""
    return get_user_model().objects.create_user(**params)


class PublicRecipeApiTests(TestCase):
    """Test unauthenticated api requests"""

    def setUp(self) -> None:
        self.client = APIClient()

    def test_auth_required(self):
        """Test auth is required to continue"""
        res = self.client.get(RECIPES_URL)

        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)


class PrivateRecipeApiTests(TestCase):
    """Test authenticated api requests"""

    def setUp(self) -> None:
        self.user = create_user(
            email="test@example.com",
            password="testpass123",
            name="Test User",
        )
        self.client = APIClient()
        self.client.force_authenticate(user=self.user)

    def test_retrieve_recipes(self):
        """Test retrieving a list of recipes"""

        create_recipe(self.user)
        create_recipe(self.user)

        res = self.client.get(RECIPES_URL)

        recipes = Recipe.objects.all().order_by("-id")
        serializer = RecipeSerializer(recipes, many=True)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data, serializer.data)

    def test_retrieve_recipes_limited_to_user(self):
        """Test retrieving recipes are limited to current logged in user"""

        user_2 = create_user(
            email="user2@example.com",
            password="testpass123",
            name="Test User 2",
        )
        create_recipe(self.user)
        create_recipe(self.user)
        create_recipe(user_2)

        res = self.client.get(RECIPES_URL)

        recipes = Recipe.objects.filter(user=self.user).order_by("-id")
        serializer = RecipeSerializer(recipes, many=True)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data, serializer.data)

    def test_get_recipe_detail(self):
        """Test get a recipe detail"""
        recipe = create_recipe(user=self.user)

        url = detail_url(recipe_id=recipe.id)
        res = self.client.get(url)

        serializer = RecipeDetailSerializer(recipe)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data, serializer.data)

    def test_post_recipe_detail(self):
        """Test post a new recipe"""
        payload = {
            "title": "Sample recipe title",
            "description": "Sample recipe description",
            "time_minutes": 22,
            "price": Decimal("5.25"),
            "link": "http://example.com/recipe.pdf",
        }
        res = self.client.post(RECIPES_URL, payload)

        self.assertEqual(res.status_code, status.HTTP_201_CREATED)

        recipe = Recipe.objects.get(id=res.data["id"])
        for k, v in payload.items():
            self.assertEqual(getattr(recipe, k), v)
        self.assertEqual(recipe.user, self.user)

    def test_partial_update(self):
        """Test partial update in a recipe"""
        original = "http://example.com/recipe.pdf"
        payload = {
            "title": "Sample recipe title",
            "description": "Sample recipe description",
            "time_minutes": 22,
            "price": Decimal("5.25"),
            "link": original,
        }

        res = self.client.post(RECIPES_URL, payload)

        self.assertEqual(res.status_code, status.HTTP_201_CREATED)

        url = detail_url(res.data["id"])
        res = self.client.patch(url, {"title": "Updated title"})

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data["title"], "Updated title")
        self.assertEqual(res.data["link"], original)

    def test_full_update(self):
        """Test full update of recipe"""
        recipe = create_recipe(
            user=self.user,
            title="Sample title",
            link="http://some-link.com/recipe.pdf",
            description="Sample recipe description",
        )

        updated_payload = {
            "title": "Updated recipe title",
            "time_minutes": 55,
            "price": Decimal("5.55"),
            "link": "http://some-link.com/new-recipe.pdf",
            "description": "New recipe description",
        }

        url = detail_url(recipe_id=recipe.id)
        res = self.client.put(url, updated_payload)

        self.assertEqual(res.status_code, status.HTTP_200_OK)

        recipe.refresh_from_db()
        for k, v in updated_payload.items():
            self.assertEqual(getattr(recipe, k), v)

    def update_user_returns_error(self):
        """Test changing the recipe user results in an error"""
        new_user = create_user(email="test2@email.com", password="test123")
        recipe = create_recipe(
            user=self.user,
            title="Sample title",
            link="http://some-link.com/recipe.pdf",
            description="Sample recipe description",
        )

        updated_payload = {
            "user": new_user.id,
        }

        url = detail_url(recipe_id=recipe.id)
        res = self.client.patch(url, updated_payload)

        recipe.refresh_from_db()

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(recipe.user, self.user)

    def test_delete_recipe(self):
        """Test to see if delete works"""
        recipe = create_recipe(
            user=self.user,
            title="Sample title",
            link="http://some-link.com/recipe.pdf",
            description="Sample recipe description",
        )

        url = detail_url(recipe_id=recipe.id)
        res = self.client.delete(url)
        self.assertEqual(res.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(Recipe.objects.filter(id=recipe.id).exists())

    def test_recipe_delete_other_user_recipe_error(self):
        """Test delete other user recipe return error"""
        user2 = create_user(email="test2@email.com", password="test123")
        recipe = create_recipe(
            user=user2,
            title="Sample title",
            link="http://some-link.com/recipe.pdf",
            description="Sample recipe description",
        )

        url = detail_url(recipe_id=recipe.id)
        res = self.client.delete(url)
        self.assertEqual(res.status_code, status.HTTP_404_NOT_FOUND)
        self.assertTrue(Recipe.objects.filter(id=recipe.id).exists())
