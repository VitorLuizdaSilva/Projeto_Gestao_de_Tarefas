
from django.urls import path
from rest_framework.routers import DefaultRouter

from .api_views import (
    EquipeViewSet,
    TarefaViewSet,
    DesempenhoViewSet,
    LoginAPIView,
    RefreshAPIView,
    LogoutAPIView,
    MeAPIView,
    csrf_cookie,
)

from .api_user_management import (
    GerenciamentoUsuariosAPIView,
    CadastroUsuarioAPIView,
    UsuarioDetalheAPIView,
    StatusUsuarioAPIView,
)

router = DefaultRouter()

router.register(
    "equipes",
    EquipeViewSet,
    basename="api-equipes",
)

router.register(
    "tarefas",
    TarefaViewSet,
    basename="api-tarefas",
)

router.register(
    "desempenho",
    DesempenhoViewSet,
    basename="api-desempenho",
)

urlpatterns = [
    path(
        "auth/cadastro/",
        CadastroUsuarioAPIView.as_view(),
        name="api-cadastro",
    ),
    path(
        "usuarios/",
        GerenciamentoUsuariosAPIView.as_view(),
        name="api-usuarios",
    ),
    path(
        "usuarios/<int:pk>/",
        UsuarioDetalheAPIView.as_view(),
        name="api-usuario-detalhe",
    ),
    path(
        "usuarios/<int:pk>/status/",
        StatusUsuarioAPIView.as_view(),
        name="api-usuario-status",
    ),
    path(
        "auth/login/",
        LoginAPIView.as_view(),
        name="api-login",
    ),
    path(
        "auth/refresh/",
        RefreshAPIView.as_view(),
        name="api-refresh",
    ),
    path(
        "auth/logout/",
        LogoutAPIView.as_view(),
        name="api-logout",
    ),
    path(
        "auth/me/",
        MeAPIView.as_view(),
        name="api-me",
    ),
    path(
        "auth/csrf/",
        csrf_cookie,
        name="api-csrf",
    ),
    *router.urls,
]
