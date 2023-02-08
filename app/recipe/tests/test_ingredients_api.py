"""
Tests for the ingredients API
"""
from decimal import Decimal

from core.models import Ingredient, Recipe
from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from recipe.serializers import IngredientSerializer
from rest_framework import status
from rest_framework.test import APIClient

INGREDIENTS_URL = reverse("recipe:ingredient-list")


def detail_url(ingredient_id):
    """Create and return an ingredient detail url"""
    return reverse("recipe:ingredient-detail", args=[ingredient_id])


def create_user(email="test@user.com", password="test123"):
    """Create and return a new user"""
    return get_user_model().objects.create_user(email, password)


class PublicRecipeApiTests(TestCase):
    """Test unauthenticated api requests"""

    def setUp(self) -> None:
        self.client = APIClient()

    def test_auth_required(self):
        """Test auth is required to continue"""
        res = self.client.get(INGREDIENTS_URL)

        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)


class PrivateRecipeApiTests(TestCase):
    """Test authenticated api requests"""

    def setUp(self):
        self.client = APIClient()
        self.user = create_user()
        self.client.force_authenticate(user=self.user)

    def test_list_ingredients(self):
        """test that list of ingredients works"""
        Ingredient.objects.create(user=self.user, name="egg")
        Ingredient.objects.create(user=self.user, name="olives")
        Ingredient.objects.create(user=self.user, name="sugar")
        res = self.client.get(INGREDIENTS_URL)

        ingredients = Ingredient.objects.all().order_by("-name")
        serializer = IngredientSerializer(ingredients, many=True)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data, serializer.data)

    def test_list_ingredients_self_user(self):
        """test that list of ingredients works only for the logged in user"""
        user2 = create_user(email="test2@example.com")

        Ingredient.objects.create(user=user2, name="egg")
        Ingredient.objects.create(user=user2, name="olives")
        Ingredient.objects.create(user=self.user, name="sugar")
        Ingredient.objects.create(user=self.user, name="tea")
        res = self.client.get(INGREDIENTS_URL)

        ingredients = (
            Ingredient.objects.all().filter(user=self.user).order_by("-name")
        )
        serializer = IngredientSerializer(ingredients, many=True)
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data, serializer.data)
        self.assertEqual(len(res.data), 2)

    def test_update_ingredients(self):
        ingredient = Ingredient.objects.create(user=self.user, name="egg")
        payload = {"name": "kiwi"}
        res = self.client.patch(detail_url(ingredient.id), payload)
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        ingredient.refresh_from_db()
        self.assertEqual(res.data["name"], payload["name"])
        self.assertEqual(ingredient.name, payload["name"])
        self.assertEqual(ingredient.id, res.data["id"])

    def test_delete_ingredients(self):
        ingredient = Ingredient.objects.create(user=self.user, name="egg")

        res = self.client.delete(
            detail_url(ingredient.id),
        )
        self.assertEqual(res.status_code, status.HTTP_204_NO_CONTENT)

        ingredients = Ingredient.objects.filter(user=self.user)
        self.assertFalse(ingredients.exists())

    def test_list_ingredients_assigned_to_recipes(self):
        """Test filter ingredients in use only"""
        i1 = Ingredient.objects.create(user=self.user, name="ingredient 1")
        i2 = Ingredient.objects.create(user=self.user, name="ingredient 2")
        i3 = Ingredient.objects.create(user=self.user, name="ingredient 3")
        r1 = Recipe.objects.create(
            user=self.user,
            title="Recipe one",
            time_minutes=50,
            price=Decimal("2.50"),
        )
        r2 = Recipe.objects.create(
            user=self.user,
            title="Recipe two",
            time_minutes=50,
            price=Decimal("2.50"),
        )
        r1.ingredients.add(i1)
        r2.ingredients.add(i2)

        params = {"assigned_only": 1}
        res = self.client.get(INGREDIENTS_URL, params)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        s1 = IngredientSerializer(i1)
        s2 = IngredientSerializer(i2)
        s3 = IngredientSerializer(i3)
        self.assertIn(s1.data, res.data)
        self.assertIn(s2.data, res.data)
        self.assertNotIn(s3.data, res.data)

    def test_filtered_ingredients_unique(self):
        i1 = Ingredient.objects.create(user=self.user, name="ingredient 1")
        Ingredient.objects.create(user=self.user, name="ingredient 2")

        r1 = Recipe.objects.create(
            user=self.user,
            title="Recipe one",
            time_minutes=50,
            price=Decimal("2.50"),
        )
        r2 = Recipe.objects.create(
            user=self.user,
            title="Recipe two",
            time_minutes=50,
            price=Decimal("2.50"),
        )
        r1.ingredients.add(i1)
        r2.ingredients.add(i1)

        params = {"assigned_only": 1}
        res = self.client.get(INGREDIENTS_URL, params)
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(len(res.data), 1)
