"""
Tests for models.
"""
from decimal import Decimal

from core import models
from django.contrib.auth import get_user_model
from django.test import TestCase


def create_user(email="test@example.com", password="pass123"):
    """Create and return a user"""
    return get_user_model().objects.create_user(email, password)


class ModelTest(TestCase):
    def test_create_user_with_email_successful(self):
        """
        Test that creating a user with an email is successful
        """
        email = "test@example.com"
        password = "123456"
        user = get_user_model().objects.create_user(
            email=email, password=password
        )
        self.assertEqual(user.email, email)
        self.assertTrue(user.check_password(password))

    def test_new_user_email_normalized(self):
        """
        Test email is normalized for new users
        """
        sample_email = [
            ["test1@EXAMPLE.com", "test1@example.com"],
            ["Test2@Example.com", "Test2@example.com"],
            ["TEST3@EXAMPLE.COM", "TEST3@example.com"],
            ["test4@example.COM", "test4@example.com"],
        ]
        for email, expected in sample_email:
            user = get_user_model().objects.create_user(email, "pass123")
            self.assertEqual(user.email, expected)

    def test_new_user_without_email_raises_error(self):
        """
        Test that creating an user without email address raises an error
        """
        with self.assertRaises(ValueError):
            get_user_model().objects.create_user("", "123")

    def test_create_new_superuser(self):
        """Test creating a superuser"""
        user = get_user_model().objects.create_superuser(
            "test@example.com", "pass123"
        )
        self.assertEqual(user.is_superuser, True)
        self.assertEqual(user.is_staff, True)

    def test_new_superuser_without_password_raises_error(self):
        """
        Test that creating an user without password address raises an error
        """
        with self.assertRaises(ValueError):
            get_user_model().objects.create_superuser("test@example.com", "")

    def test_create_recipe(self):
        """Test creating a recipe is sucessful"""
        user = get_user_model().objects.create_user(
            "test@emaple.com", "pass123"
        )
        recipe = models.Recipe.objects.create(
            user=user,
            title="Sample recipe name",
            time_minutes=5,
            price=Decimal("5.50"),
            description="sample recipe description",
        )

        self.assertEqual(str(recipe), recipe.title)

    def test_create_recipe_tag(self):
        """Test create tag is succesful"""
        user = create_user()

        tag = models.Tag.objects.create(user=user, name="something")

        self.assertEqual(str(tag), tag.name)
