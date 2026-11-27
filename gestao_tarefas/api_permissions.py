from rest_framework.permissions import BasePermission, SAFE_METHODS

from .models import MembroEquipe


def papel(user):
    if not user.is_authenticated:
        return None

    if user.is_superuser:
        return 'SUPREMO'

    perfil = getattr(user, 'perfil', None)

    if perfil:
        return perfil.papel

    # Compatibilidade com usuários antigos sem Perfil.
    if user.groups.filter(name='Supremo').exists():
        return 'SUPREMO'

    if user.groups.filter(name='Gerente').exists():
        return 'GERENTE'

    if user.groups.filter(name='Funcionario').exists():
        return 'FUNCIONARIO'

    return None


class PodeGerenciarEquipe(BasePermission):
    def has_object_permission(self, request, view, obj):
        role = papel(request.user)

        return (
            role == 'SUPREMO'
            or (
                role == 'GERENTE'
                and obj.gerente_id == request.user.id
            )
        )


class PodeAcessarTarefa(BasePermission):

    def has_object_permission(self, request, view, obj):
        user = request.user
        role = papel(user)

        # Supremo tem acesso global.
        if role == 'SUPREMO':
            return True

        # Tarefa vinculada a uma equipe.
        if obj.equipe_id:

            # Gerente responsável pela equipe.
            if (
                role == 'GERENTE'
                and obj.equipe.gerente_id == user.id
            ):
                return True

            # Somente Funcionários podem acessar como membros.
            if role != 'FUNCIONARIO':
                return False

            membro = MembroEquipe.objects.filter(
                equipe_id=obj.equipe_id,
                usuario=user
            ).first()

            if not membro:
                return False

            # Membros podem visualizar tarefas da equipe.
            if request.method in SAFE_METHODS:
                return True

            # Exclusão exige permissão específica.
            if request.method == 'DELETE':
                return membro.pode_excluir_tarefa

            # Edição exige permissão específica.
            if request.method in ('PUT', 'PATCH'):
                return membro.pode_editar_tarefa

            return False

        # Tarefas sem equipe.
        if role == 'GERENTE':
            return (
                obj.usuario_id == user.id
                or obj.criada_por_id == user.id
            )

        if role == 'FUNCIONARIO':
            return obj.usuario_id == user.id

        return False