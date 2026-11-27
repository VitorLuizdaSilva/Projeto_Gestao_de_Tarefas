from django.urls import path
from . import views

urlpatterns = [
    path("", views.login_page, name="login"),
    path("cadastro/", views.cadastro_page, name="cadastro"),
    path("home/", views.home_page, name="home"),
]
