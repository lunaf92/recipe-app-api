"""
Tests for the recipe API
"""
import os
import tempfile
from decimal import Decimal

from core.models import Ingredient, Recipe, Tag
from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from PIL import Image
from recipe.serializers import RecipeDetailSerializer, RecipeSerializer
from rest_framework import status
from rest_framework.test import APIClient

RECIPES_URL = reverse("recipe:recipe-list")


def detail_url(recipe_id):
    """Create and return a recipe detail url"""
    return reverse("recipe:recipe-detail", args=[recipe_id])


def image_upload_url(recipe_id):
    """Create and return an image upload URL."""
    return reverse("recipe:recipe-upload-image", args=[recipe_id])


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

    def test_update_user_returns_error(self):
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

    def test_create_recipe_with_new_tags(self):
        """Creating a recipe with new tags"""
        payload = {
            "title": "Sample recipe 1",
            "time_minutes": 30,
            "price": Decimal("2.50"),
            "tags": [{"name": "sample tag 1"}, {"name": "sample tag 2"}],
        }
        res = self.client.post(RECIPES_URL, payload, format="json")

        self.assertEqual(res.status_code, status.HTTP_201_CREATED)

        recipes = Recipe.objects.filter(user=self.user)
        self.assertEqual(recipes.count(), 1)

        recipe = recipes[0]
        self.assertEqual(recipe.tags.count(), 2)

        for tag in payload["tags"]:
            exist = recipe.tags.filter(
                name=tag["name"], user=self.user
            ).exists()
            self.assertTrue(exist)

    def test_create_recipe_with_existing_tags(self):
        """Creating a recipe with existing tags"""
        tag = Tag.objects.create(user=self.user, name="Sample tag 1")
        payload = {
            "title": "Sample recipe 1",
            "time_minutes": 30,
            "price": Decimal("2.50"),
            "tags": [{"name": "Sample tag 1"}, {"name": "sample tag 2"}],
        }
        res = self.client.post(RECIPES_URL, payload, format="json")

        self.assertEqual(res.status_code, status.HTTP_201_CREATED)

        recipes = Recipe.objects.filter(user=self.user)
        self.assertEqual(recipes.count(), 1)

        recipe = recipes[0]
        self.assertEqual(recipe.tags.count(), 2)

        self.assertIn(tag, recipe.tags.all())

        for tag in payload["tags"]:
            exist = recipe.tags.filter(
                name=tag["name"], user=self.user
            ).exists()
            self.assertTrue(exist)

    def test_create_tag_on_update(self):
        """create the tags when updating a recipe"""
        recipe = create_recipe(user=self.user)
        payload = {"tags": [{"name": "Lunch"}]}
        url = detail_url(recipe.id)
        res = self.client.patch(url, payload, format="json")

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        new_tag = Tag.objects.get(user=self.user, name="Lunch")
        self.assertIn(new_tag, recipe.tags.all())

    def test_update_recipe_assign_tag(self):
        """Test assigning an existing tag when updating a recipe,"""
        tag_one = Tag.objects.create(user=self.user, name="Sample tag 1")
        recipe = create_recipe(user=self.user)
        recipe.tags.add(tag_one)

        tag_two = Tag.objects.create(user=self.user, name="Sample tag 2")
        payload = {"tags": [{"name": "Sample tag 2"}]}

        url = detail_url(recipe.id)
        res = self.client.patch(url, payload, format="json")

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertIn(tag_two, recipe.tags.all())
        self.assertNotIn(tag_one, recipe.tags.all())

    def test_delete_recipe_tags(self):
        """Test clearing a recipe tags"""
        tag_one = Tag.objects.create(user=self.user, name="Sample tag 1")
        recipe = create_recipe(user=self.user)
        recipe.tags.add(tag_one)

        payload = {"tags": []}

        url = detail_url(recipe.id)
        res = self.client.patch(url, payload, format="json")

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(recipe.tags.count(), 0)

    def test_create_recipe_with_ingredients(self):
        """Test create recipe with ingredients ok"""

        payload = {
            "title": "Sample recipe 1",
            "time_minutes": 30,
            "price": Decimal("2.50"),
            "tags": [{"name": "sample tag 1"}, {"name": "sample tag 2"}],
            "ingredients": [
                {"name": "sample ingredient 1"},
                {"name": "sample ingredient 2"},
            ],
        }
        res = self.client.post(RECIPES_URL, payload, format="json")

        self.assertEqual(res.status_code, status.HTTP_201_CREATED)

        recipes = Recipe.objects.filter(user=self.user)
        self.assertEqual(recipes.count(), 1)

        recipe = recipes[0]
        self.assertEqual(recipe.ingredients.count(), 2)

        for ingredient in payload["ingredients"]:
            exist = recipe.ingredients.filter(
                name=ingredient["name"], user=self.user
            ).exists()
            self.assertTrue(exist)

    def test_create_recipe_with_existing_ingredients(self):
        """
        Test assigning existing ingredient to a recipe reuse
        """
        Ingredient.objects.create(user=self.user, name="eggs")

        payload = {
            "title": "Sample recipe 1",
            "time_minutes": 30,
            "price": Decimal("2.50"),
            "tags": [{"name": "sample tag 1"}, {"name": "sample tag 2"}],
            "ingredients": [
                {"name": "eggs"},
            ],
        }

        res = self.client.post(RECIPES_URL, payload, format="json")

        self.assertEqual(res.status_code, status.HTTP_201_CREATED)

        ingredients = Ingredient.objects.filter(user=self.user)
        recipe = Recipe.objects.filter(user=self.user)

        self.assertEqual(recipe.count(), 1)
        self.assertEqual(ingredients.count(), 1)
        self.assertEqual(recipe[0].ingredients.count(), 1)

        for ingredient in payload["ingredients"]:
            e = (
                recipe[0]
                .ingredients.filter(user=self.user, name=ingredient["name"])
                .exists()
            )
            self.assertTrue(e)

    def test_create_ingredients_on_update(self):
        """Test create the ingredient when updating recipe"""
        recipe = create_recipe(user=self.user)
        payload = {
            "ingredients": [
                {"name": "ingredient one"},
                {"name": "ingredient two"},
            ]
        }
        url = detail_url(recipe_id=recipe.id)
        res = self.client.patch(url, payload, format="json")
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        ingredient = Ingredient.objects.get(
            name="ingredient one", user=self.user
        )
        self.assertIn(ingredient, recipe.ingredients.all())

    def test_update_recipe_assign_ingredient(self):
        recipe = create_recipe(user=self.user)
        ingredient_one = Ingredient.objects.create(
            user=self.user, name="ingredient one"
        )
        recipe.ingredients.add(ingredient_one)

        self.assertIn(ingredient_one, recipe.ingredients.all())

        ingredient_two = Ingredient.objects.create(
            user=self.user, name="ingredient two"
        )
        payload = {
            "ingredients": [
                {"name": "ingredient two"},
            ]
        }

        url = detail_url(recipe_id=recipe.id)
        res = self.client.patch(url, payload, format="json")

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertNotIn(ingredient_one, recipe.ingredients.all())
        self.assertIn(ingredient_two, recipe.ingredients.all())

    def test_clear_ingredients(self):
        """Test that passing an empty array clears the ingredients"""
        recipe = create_recipe(user=self.user)
        ingredient = Ingredient.objects.create(user=self.user, name="one")
        recipe.ingredients.add(ingredient)
        self.assertEqual(recipe.ingredients.count(), 1)
        payload = {"ingredients": []}
        url = detail_url(recipe_id=recipe.id)
        res = self.client.patch(url, payload, format="json")

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(recipe.ingredients.count(), 0)

    def test_filter_by_tags(self):
        """Test that filtering tags works"""
        r1 = create_recipe(user=self.user, title="recipe1")
        r2 = create_recipe(user=self.user, title="recipe2")
        r3 = create_recipe(user=self.user, title="recipe3")
        t1 = Tag.objects.create(user=self.user, name="tag1")
        t2 = Tag.objects.create(user=self.user, name="tag2")

        r1.tags.add(t1)
        r2.tags.add(t2)

        params = {"tags": f"{t1.id}, {t2.id}"}
        res = self.client.get(RECIPES_URL, params)

        self.assertEqual(res.status_code, status.HTTP_200_OK)

        s1 = RecipeSerializer(r1)
        s2 = RecipeSerializer(r2)
        s3 = RecipeSerializer(r3)
        self.assertIn(s1.data, res.data)
        self.assertIn(s2.data, res.data)
        self.assertNotIn(s3.data, res.data)

    def test_filter_by_ingredients(self):
        """Test that filtering ingredients works"""
        r1 = create_recipe(user=self.user, title="recipe1")
        r2 = create_recipe(user=self.user, title="recipe2")
        r3 = create_recipe(user=self.user, title="recipe3")
        i1 = Ingredient.objects.create(user=self.user, name="ingredient1")
        i2 = Ingredient.objects.create(user=self.user, name="ingredient2")

        r1.ingredients.add(i1)
        r2.ingredients.add(i2)

        params = {"ingredients": f"{i1.id}, {i2.id}"}
        res = self.client.get(RECIPES_URL, params)

        self.assertEqual(res.status_code, status.HTTP_200_OK)

        s1 = RecipeSerializer(r1)
        s2 = RecipeSerializer(r2)
        s3 = RecipeSerializer(r3)
        self.assertIn(s1.data, res.data)
        self.assertIn(s2.data, res.data)
        self.assertNotIn(s3.data, res.data)


class ImageUploadTests(TestCase):
    """Tests for the image upload API."""

    def setUp(self) -> None:
        self.client = APIClient()
        self.user = get_user_model().objects.create_user(
            "user@example.com", "password123"
        )
        self.client.force_authenticate(self.user)
        self.recipe = create_recipe(user=self.user)

    def tearDown(self) -> None:
        self.recipe.image.delete()

    def test_upload_image(self):
        """Test uploading an image to a recipe"""
        url = image_upload_url(self.recipe.id)
        with tempfile.NamedTemporaryFile(suffix=".jpeg") as image_file:
            img = Image.new("RGB", (10, 10))
            img.save(image_file, format="JPEG")
            image_file.seek(0)
            payload = {"image": image_file}
            res = self.client.post(url, payload, format="multipart")

        self.recipe.refresh_from_db()
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertIn("image", res.data)
        self.assertTrue(os.path.exists(self.recipe.image.path))

    def test_upload_image_bad_request(self):
        """Test uploading an invalid image"""
        url = image_upload_url(self.recipe.id)
        payload = {"image": "not_an_image_file"}
        res = self.client.post(url, payload, format="multipart")

        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
