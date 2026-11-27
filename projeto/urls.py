from django.contrib import admin
from django.urls import include, path

urlpatterns = [
    path("admin/", admin.site.urls),
    path("", include("gestao_tarefas.urls")),
    path("api/", include("gestao_tarefas.api_urls")),
]
