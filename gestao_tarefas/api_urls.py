from django.urls import path
from rest_framework.routers import DefaultRouter

from .api_views import (
    EquipeViewSet,
    TarefaViewSet,
    DesempenhoViewSet,
    CadastroAPIView,
    LoginAPIView,
    RefreshAPIView,
    LogoutAPIView,
    MeAPIView,
    csrf_cookie,
    UsuariosDisponiveisAPIView
)

router = DefaultRouter()

router.register('equipes', EquipeViewSet, basename='api-equipes')
router.register('tarefas', TarefaViewSet, basename='api-tarefas')
router.register('desempenho', DesempenhoViewSet, basename='api-desempenho')

urlpatterns = [
    path('auth/cadastro/', CadastroAPIView.as_view(), name='api-cadastro'),
    path('usuarios/', UsuariosDisponiveisAPIView.as_view(), name='api-usuarios'),
    path('auth/login/', LoginAPIView.as_view(), name='api-login'),
    path('auth/refresh/', RefreshAPIView.as_view(), name='api-refresh'),
    path('auth/logout/', LogoutAPIView.as_view(), name='api-logout'),
    *router.urls,
    path('auth/me/', MeAPIView.as_view(), name='api-me'),
    path('auth/csrf/', csrf_cookie, name='api-csrf'),
]