"""
URL mappings for the user API.
"""
from django.urls import path

from .views import CreateTokenView, CreateUserView, ManageUserView

app_name = "user"

urlpatterns = [
    path("create/", CreateUserView.as_view(), name="create"),
    path("token/", CreateTokenView.as_view(), name="token"),
    path("self/", ManageUserView.as_view(), name="me"),
]