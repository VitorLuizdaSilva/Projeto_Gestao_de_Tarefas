
from django.contrib.auth.models import User
from django.db import transaction

from rest_framework import generics, permissions
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.response import Response
from rest_framework.views import APIView
from django.shortcuts import get_object_or_404
from .api_permissions import papel
from .api_serializers import (
    CadastroSerializer,
    UsuarioGerenciamentoSerializer,
)
from .models import Perfil


class GerenciamentoUsuariosAPIView(generics.ListAPIView):
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = UsuarioGerenciamentoSerializer

    def get_queryset(self):
        usuario_atual = self.request.user
        role = papel(usuario_atual)

        if role not in ("SUPREMO", "GERENTE"):
            raise PermissionDenied(
                "Você não pode consultar usuários."
            )

        queryset = User.objects.select_related(
            "perfil"
        ).order_by("username")

        if role == "GERENTE":
            return queryset.filter(
                perfil__papel="FUNCIONARIO",
            )

        return queryset.filter(
            perfil__papel__in=[
                "GERENTE",
                "FUNCIONARIO",
            ],
        )


class CadastroUsuarioAPIView(generics.CreateAPIView):
    serializer_class = CadastroSerializer
    permission_classes = [permissions.IsAuthenticated]

    def perform_create(self, serializer):
        role = papel(self.request.user)

        if role not in ("SUPREMO", "GERENTE"):
            raise PermissionDenied(
                "Somente Supremo ou Gerente pode cadastrar usuários."
            )

        serializer.save()


class UsuarioDetalheAPIView(generics.RetrieveUpdateAPIView):
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = UsuarioGerenciamentoSerializer
    queryset = User.objects.select_related("perfil").all()
    http_method_names = ["get", "patch", "put", "head", "options"]

    def get_object(self):
        usuario_atual = self.request.user
        role = papel(usuario_atual)

        if role not in ("SUPREMO", "GERENTE"):
            raise PermissionDenied(
                "Você não pode gerenciar usuários."
            )

        alvo = get_object_or_404(
            self.get_queryset(),
            pk=self.kwargs["pk"],
        )

        papel_alvo = papel(alvo)

        if alvo.is_superuser:
            raise PermissionDenied(
                "Esta conta não pode ser gerenciada por esta tela."
            )

        if alvo.pk == usuario_atual.pk:
            raise PermissionDenied(
                "Você não pode alterar sua própria conta por esta tela."
            )

        if role == "GERENTE" and papel_alvo != "FUNCIONARIO":
            raise PermissionDenied(
                "Gerentes só podem gerenciar funcionários."
            )

        if role == "SUPREMO" and papel_alvo not in (
            "GERENTE",
            "FUNCIONARIO",
        ):
            raise PermissionDenied(
                "Este usuário não pode ser gerenciado por esta operação."
            )

        return alvo

    def perform_update(self, serializer):
        role_atual = papel(self.request.user)
        papel_novo = serializer.validated_data.get(
            "papel",
            papel(serializer.instance),
        )

        if role_atual == "GERENTE":
            if papel_novo != "FUNCIONARIO":
                raise PermissionDenied(
                    "Gerentes só podem manter funcionários como funcionários."
                )

        if role_atual == "SUPREMO":
            if papel_novo not in ("GERENTE", "FUNCIONARIO"):
                raise ValidationError({
                    "papel": "Papel inválido para esta operação."
                })

        serializer.save()


class StatusUsuarioAPIView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    @transaction.atomic
    def patch(self, request, pk):
        role = papel(request.user)

        if role not in ("SUPREMO", "GERENTE"):
            raise PermissionDenied(
                "Você não pode alterar o status de usuários."
            )

        usuario = get_object_or_404(
            User.objects.select_related("perfil"),
            pk=pk,
        )

        papel_alvo = papel(usuario)

        if usuario.pk == request.user.pk:
            raise PermissionDenied(
                "Você não pode desativar sua própria conta."
            )

        if usuario.is_superuser:
            raise PermissionDenied(
                "Esta conta não pode ser desativada por esta operação."
            )

        if role == "GERENTE" and papel_alvo != "FUNCIONARIO":
            raise PermissionDenied(
                "Gerentes só podem desativar funcionários."
            )

        if role == "SUPREMO" and papel_alvo not in (
            "GERENTE",
            "FUNCIONARIO",
        ):
            raise PermissionDenied(
                "Este usuário não pode ser desativado."
            )

        ativo = request.data.get("is_active")

        if not isinstance(ativo, bool):
            raise ValidationError({
                "is_active": "Informe true ou false."
            })

        usuario.is_active = ativo
        usuario.save(update_fields=["is_active"])

        return Response({
            "id": usuario.id,
            "username": usuario.username,
            "is_active": usuario.is_active,
            "message": (
                "Usuário ativado."
                if ativo
                else "Usuário desativado."
            ),
        })
