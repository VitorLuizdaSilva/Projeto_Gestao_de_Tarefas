from django.db import transaction
from django.db.models import Q, Count
from rest_framework import viewsets, permissions, generics
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.exceptions import TokenError
from rest_framework.permissions import AllowAny
from django.contrib.auth.password_validation import validate_password
from rest_framework import serializers
from django.conf import settings
from django.contrib.auth.models import User, Group
from rest_framework.views import APIView
from .api_permissions import papel,  PodeAcessarTarefa
from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from django.views.decorators.csrf import ensure_csrf_cookie, csrf_protect
from django.utils.decorators import method_decorator
from .models import (
    Equipe,
    MembroEquipe,
    Tarefa,
    HistoricoTarefa,
    Perfil
)
from .api_serializers import (
    EquipeSerializer,
    TarefaSerializer,
    MembroEquipeSerializer,
    CadastroSerializer,
    UsuarioAtualSerializer
)


class EquipeViewSet(viewsets.ModelViewSet):
    serializer_class = EquipeSerializer
    permission_classes = [permissions.IsAuthenticated]

    @transaction.atomic
    def destroy(self, request, *args, **kwargs):
        equipe = self.get_object()

        self._pode_administrar_membros(request, equipe)

        if equipe.tarefas.exists():
            raise ValidationError(
                'Não é possível excluir uma equipe que possui tarefas.'
            )

        equipe.delete()

        return Response(status=204)

    def get_queryset(self):
        user = self.request.user
        role = papel(user)

        if role == 'SUPREMO':
            return Equipe.objects.all()

        if role == 'GERENTE':
            return Equipe.objects.filter(
                gerente=user
            )

        if role == 'FUNCIONARIO':
            return Equipe.objects.filter(
                membros__usuario=user
            ).distinct()

        return Equipe.objects.none()

    @transaction.atomic
    def perform_create(self, serializer):
        user = self.request.user
        role = papel(user)

        if role not in ('SUPREMO', 'GERENTE'):
            raise PermissionDenied(
                'Somente Supremo ou Gerente pode criar equipes.'
            )

        gerente = serializer.validated_data.get('gerente')

        if role == 'SUPREMO':
            if not gerente or papel(gerente) != 'GERENTE':
                raise ValidationError({
                    'gerente_id': 'Informe um usuário com papel de Gerente.'
                })

            serializer.save(gerente=gerente)

        else:
            if gerente and gerente != user:
                raise PermissionDenied(
                    'Você só pode criar equipes sob sua própria gestão.'
                )

            serializer.save(gerente=user)

    @transaction.atomic
    def perform_update(self, serializer):
        equipe = serializer.instance
        user = self.request.user
        role = papel(user)

        novo_gerente = serializer.validated_data.get('gerente')

        if role == 'GERENTE':
            if equipe.gerente_id != user.id:
                raise PermissionDenied(
                    'Você não administra esta equipe.'
                )

            if novo_gerente and novo_gerente != user:
                raise PermissionDenied(
                    'Você não pode transferir a gestão da equipe.'
                )

            serializer.save(gerente=user)
            return

        if role != 'SUPREMO':
            raise PermissionDenied(
                'Você não tem permissão para editar equipes.'
            )

        if novo_gerente and papel(novo_gerente) != 'GERENTE':
            raise ValidationError({
                'gerente_id': 'O responsável precisa ter papel de Gerente.'
            })

        serializer.save()

    def _pode_administrar_membros(self, request, equipe):
        role = papel(request.user)

        autorizado = (
            role == 'SUPREMO'
            or (
                role == 'GERENTE'
                and equipe.gerente_id == request.user.id
            )
        )

        if not autorizado:
            raise PermissionDenied(
                'Somente o Supremo ou o gerente responsável '
                'pode administrar os membros.'
            )

    @action(detail=True, methods=['get', 'post'], url_path='membros')
    def membros(self, request, pk=None):
        equipe = self.get_object()

        if request.method == 'GET':
            role = papel(request.user)
            pode_visualizar = (
                role == 'SUPREMO'
                or (role == 'GERENTE' and equipe.gerente_id == request.user.id)
                or MembroEquipe.objects.filter(equipe=equipe, usuario=request.user).exists()
            )
            if not pode_visualizar:
                raise PermissionDenied('Você não pode visualizar os membros desta equipe.')

            membros = equipe.membros.select_related('usuario')

            serializer = MembroEquipeSerializer(
                membros,
                many=True
            )

            return Response(serializer.data)

        self._pode_administrar_membros(request, equipe)

        if not equipe.ativa:
            raise ValidationError(
                'Não é possível adicionar membros a uma equipe inativa.'
            )

        serializer = MembroEquipeSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        usuario = serializer.validated_data['usuario']

        if usuario.is_superuser or papel(usuario) != 'FUNCIONARIO':
            raise ValidationError(
                'Somente usuários com papel de Funcionário '
                'podem entrar na equipe.'
            )

        if MembroEquipe.objects.filter(
            equipe=equipe,
            usuario=usuario
        ).exists():
            raise ValidationError(
                'Este funcionário já pertence à equipe.'
            )

        serializer.save(equipe=equipe)

        return Response(serializer.data, status=201)

    @action(
        detail=True,
        methods=['patch', 'delete'],
        url_path='membros/(?P<membro_id>[^/.]+)'
    )
    def gerenciar_membro(self, request, pk=None, membro_id=None):
        equipe = self.get_object()

        self._pode_administrar_membros(request, equipe)

        membro = equipe.membros.filter(
            pk=membro_id
        ).first()

        if not membro:
            raise ValidationError(
                'Membro não encontrado nesta equipe.'
            )

        if request.method == 'DELETE':
            membro.delete()
            return Response(status=204)

        if 'usuario' in request.data:
            raise ValidationError(
                'Não é permitido alterar o funcionário vinculado à equipe.'
            )

        serializer = MembroEquipeSerializer(
            membro,
            data=request.data,
            partial=True
        )

        serializer.is_valid(raise_exception=True)
        serializer.save()

        return Response(serializer.data)


class TarefaViewSet(viewsets.ModelViewSet):
    serializer_class = TarefaSerializer
    permission_classes = [
        permissions.IsAuthenticated,
        PodeAcessarTarefa
    ]

    def get_queryset(self):
        user = self.request.user
        role = papel(user)

        qs = Tarefa.objects.select_related(
            'equipe',
            'usuario',
            'criada_por'
        )

        if role == 'SUPREMO':
            return qs

        if role == 'GERENTE':
            return qs.filter(
                Q(equipe__gerente=user)
                | (
                    Q(equipe__isnull=True)
                    & (
                        Q(usuario=user)
                        | Q(criada_por=user)
                    )
                )
            ).distinct()

        if role == 'FUNCIONARIO':
            return qs.filter(
                Q(equipe__membros__usuario=user)
                | (
                    Q(equipe__isnull=True)
                    & Q(usuario=user)
                )
            ).distinct()

        return Tarefa.objects.none()

    @transaction.atomic
    def perform_create(self, serializer):
        user = self.request.user
        role = papel(user)

        equipe = serializer.validated_data.get('equipe')
        responsavel = serializer.validated_data['usuario']

        if role not in ('SUPREMO', 'GERENTE', 'FUNCIONARIO'):
            raise PermissionDenied(
                'Usuário sem papel válido.'
            )

        if equipe:
            if not equipe.ativa:
                raise ValidationError({
                    'equipe': 'Não é possível criar tarefas em uma equipe inativa.'
                })

            if role == 'GERENTE':
                if equipe.gerente_id != user.id:
                    raise PermissionDenied(
                        'Você só pode criar tarefas em suas equipes.'
                    )

            elif role == 'FUNCIONARIO':
                membro = MembroEquipe.objects.filter(
                    equipe=equipe,
                    usuario=user
                ).first()

                if not membro or not membro.pode_criar_tarefa:
                    raise PermissionDenied(
                        'Você não tem permissão para criar tarefas nesta equipe.'
                    )

                if responsavel != user:
                    raise PermissionDenied(
                        'Você só pode atribuir tarefas a si mesmo.'
                    )

            # O responsável precisa pertencer à equipe.
            pertence = (
                responsavel == equipe.gerente
                or MembroEquipe.objects.filter(
                    equipe=equipe,
                    usuario=responsavel
                ).exists()
            )

            if not pertence:
                raise ValidationError({
                    'responsavel_id':
                        'O responsável precisa pertencer à equipe.'
                })

        elif role == 'FUNCIONARIO' and responsavel != user:
            raise PermissionDenied(
                'Você só pode atribuir tarefas a si mesmo.'
            )

        tarefa = serializer.save(criada_por=user)

        HistoricoTarefa.objects.create(
            tarefa=tarefa,
            autor=user,
            acao='Tarefa criada'
        )

    @transaction.atomic
    def perform_destroy(self, instance):
        HistoricoTarefa.objects.create(
            tarefa=instance,
            autor=self.request.user,
            acao='Tarefa excluída'
        )

        instance.delete()

    @transaction.atomic
    def perform_update(self, serializer):
        tarefa = serializer.instance
        user = self.request.user
        role = papel(user)

        equipe_anterior = tarefa.equipe

        equipe_nova = serializer.validated_data.get(
            'equipe',
            equipe_anterior
        )

        responsavel_novo = serializer.validated_data.get(
            'usuario',
            tarefa.usuario
        )

        # Impede alterações por usuários sem papel válido.
        if role not in ('SUPREMO', 'GERENTE', 'FUNCIONARIO'):
            raise PermissionDenied(
                'Usuário sem papel válido.'
            )

        # Funcionário não pode trocar o responsável da tarefa.
        if (
            role == 'FUNCIONARIO'
            and responsavel_novo != tarefa.usuario
        ):
            raise PermissionDenied(
                'Funcionários não podem alterar o responsável da tarefa.'
            )

        # Não permite transferir tarefas para equipes inativas.
        # Se a tarefa já está em equipe inativa, ela continua editável.
        if (
            equipe_nova
            and equipe_nova != equipe_anterior
            and not equipe_nova.ativa
        ):
            raise ValidationError({
                'equipe':
                    'Não é possível transferir tarefas para uma equipe inativa.'
            })

        # O responsável precisa pertencer à equipe de destino.
        if equipe_nova:
            pertence = (
                equipe_nova.gerente_id == responsavel_novo.id
                or MembroEquipe.objects.filter(
                    equipe=equipe_nova,
                    usuario=responsavel_novo
                ).exists()
            )

            if not pertence:
                raise ValidationError({
                    'responsavel_id':
                        'O responsável precisa pertencer à equipe.'
                })

        # Regras de transferência entre equipes.
        if equipe_nova != equipe_anterior:

            if role == 'SUPREMO':
                pass

            elif role == 'GERENTE':
                if (
                    equipe_nova is None
                    or equipe_nova.gerente_id != user.id
                ):
                    raise PermissionDenied(
                        'Você só pode transferir tarefas para suas próprias equipes.'
                    )

            elif role == 'FUNCIONARIO':
                if equipe_nova is None:
                    raise PermissionDenied(
                        'Você não pode transformar tarefas de equipe '
                        'em tarefas pessoais.'
                    )

                membro = MembroEquipe.objects.filter(
                    equipe=equipe_nova,
                    usuario=user,
                    pode_criar_tarefa=True
                ).first()

                if not membro:
                    raise PermissionDenied(
                        'Você não tem permissão para transferir tarefas '
                        'para esta equipe.'
                    )

        # Guarda os valores antigos para registrar o histórico.
        valores_anteriores = {
            'titulo': tarefa.titulo,
            'descricao': tarefa.descricao,
            'status': tarefa.status,
            'urgencia': tarefa.urgencia,
            'responsavel_id': tarefa.usuario_id,
            'equipe_id': tarefa.equipe_id,
        }

        valores_novos = {
            'titulo': serializer.validated_data.get(
                'titulo',
                tarefa.titulo
            ),
            'descricao': serializer.validated_data.get(
                'descricao',
                tarefa.descricao
            ),
            'status': serializer.validated_data.get(
                'status',
                tarefa.status
            ),
            'urgencia': serializer.validated_data.get(
                'urgencia',
                tarefa.urgencia
            ),
            'responsavel_id': responsavel_novo.id,
            'equipe_id': equipe_nova.id if equipe_nova else None,
        }

        mudancas = {
            campo: {
                'de': valores_anteriores[campo],
                'para': valores_novos[campo]
            }
            for campo in valores_anteriores
            if valores_anteriores[campo] != valores_novos[campo]
        }

        instance = serializer.save()

        if mudancas:
            HistoricoTarefa.objects.create(
                tarefa=instance,
                autor=user,
                acao='Tarefa atualizada',
                detalhes=mudancas
            )


    @action(detail=True, methods=['get'], url_path='historico')
    def historico(self, request, pk=None):
        tarefa = self.get_object()
        registros = tarefa.historico.select_related('autor').all()
        dados = [
            {
                'id': item.id,
                'acao': item.acao,
                'autor': item.autor.username if item.autor else 'Usuário removido',
                'criado_em': item.criado_em,
                'detalhes': item.detalhes,
            }
            for item in registros
        ]
        return Response(dados)


class UsuariosDisponiveisAPIView(generics.ListAPIView):
    permission_classes = [permissions.IsAuthenticated]

    def list(self, request, *args, **kwargs):
        from django.contrib.auth.models import User
        role = papel(request.user)
        if role not in ('SUPREMO', 'GERENTE'):
            raise PermissionDenied('Você não pode consultar a lista de usuários.')

        usuarios = User.objects.filter(is_active=True).select_related('perfil').order_by('username')
        if role == 'GERENTE':
            usuarios = usuarios.filter(perfil__papel='FUNCIONARIO')
        else:
            usuarios = usuarios.filter(perfil__papel__in=['GERENTE', 'FUNCIONARIO'])

        dados = [
            {
                'id': usuario.id,
                'username': usuario.username,
                'first_name': usuario.first_name,
                'last_name': usuario.last_name,
                'papel': papel(usuario),
            }
            for usuario in usuarios
        ]
        return Response(dados)


class DesempenhoViewSet(viewsets.ViewSet):
    permission_classes = [permissions.IsAuthenticated]

    def list(self, request):
        if papel(request.user) != 'SUPREMO':
            raise PermissionDenied(
                'Somente o Supremo pode consultar o desempenho global.'
            )

        equipes = Equipe.objects.select_related(
            'gerente'
        ).annotate(
            total=Count('tarefas'),
            pendentes=Count(
                'tarefas',
                filter=Q(tarefas__status='AF')
            ),
            em_andamento=Count(
                'tarefas',
                filter=Q(tarefas__status='EA')
            ),
            concluidas=Count(
                'tarefas',
                filter=Q(tarefas__status='CO')
            )
        )

        dados = [
            {
                'equipe_id': equipe.id,
                'equipe': equipe.nome,
                'gerente': equipe.gerente.username,
                'total': equipe.total,
                'pendentes': equipe.pendentes,
                'em_andamento': equipe.em_andamento,
                'concluidas': equipe.concluidas,
            }
            for equipe in equipes
        ]

        return Response(dados)




class CadastroSerializer(serializers.ModelSerializer):
    password = serializers.CharField(
        write_only=True,
        validators=[validate_password],
    )
    password2 = serializers.CharField(write_only=True)

    papel = serializers.ChoiceField(
        choices=Perfil.Papel.choices,
        required=False,
    )

    class Meta:
        model = User
        fields = [
            "id",
            "username",
            "email",
            "first_name",
            "last_name",
            "password",
            "password2",
            "papel",
        ]
        read_only_fields = ["id"]

    def validate(self, attrs):
        if attrs["password"] != attrs["password2"]:
            raise serializers.ValidationError({
                "password2": "As senhas não coincidem."
            })

        solicitante = self.context["request"].user
        role_solicitante = papel(solicitante)

        papel_solicitado = attrs.get(
            "papel",
            Perfil.Papel.FUNCIONARIO,
        )

        if role_solicitante == "GERENTE":
            if papel_solicitado != "FUNCIONARIO":
                raise serializers.ValidationError({
                    "papel": "Gerentes só podem cadastrar funcionários."
                })

        elif role_solicitante == "SUPREMO":
            if papel_solicitado not in ("GERENTE", "FUNCIONARIO"):
                raise serializers.ValidationError({
                    "papel": "Papel inválido."
                })

        else:
            raise serializers.ValidationError(
                "Você não pode cadastrar usuários."
            )

        attrs["papel"] = papel_solicitado
        return attrs

    @transaction.atomic
    def create(self, validated_data):
        validated_data.pop("password2")
        password = validated_data.pop("password")
        novo_papel = validated_data.pop(
            "papel",
            Perfil.Papel.FUNCIONARIO,
        )

        usuario = User(**validated_data)
        usuario.set_password(password)
        usuario.is_active = True
        usuario.save()

        perfil, _ = Perfil.objects.get_or_create(
            user=usuario,
            defaults={"papel": novo_papel},
        )

        perfil.papel = novo_papel
        perfil.save(update_fields=["papel"])

        sincronizar_grupo(usuario, novo_papel)

        return usuario



class LoginSerializer(TokenObtainPairSerializer):
    username_field = 'username'

@method_decorator(csrf_protect, name='dispatch')
class LoginAPIView(TokenObtainPairView):
    serializer_class = LoginSerializer
    permission_classes = [AllowAny]

    def post(self, request, *args, **kwargs):
        response = super().post(request, *args, **kwargs)

        refresh_token = response.data.pop('refresh')

        response.set_cookie(
            key='refresh_token',
            value=refresh_token,
            httponly=True,
            secure=not settings.DEBUG,
            samesite='Lax',
            max_age=86400,
            path='/api/auth/'
        )

        return response
    
@method_decorator(csrf_protect, name='dispatch')
class RefreshAPIView(TokenRefreshView):
    permission_classes = [permissions.AllowAny]

    def post(self, request, *args, **kwargs):
        refresh_token = request.COOKIES.get('refresh_token')

        if not refresh_token:
            return Response(
                {'detail': 'Refresh token não encontrado.'},
                status=401
            )

        serializer = self.get_serializer(
            data={'refresh': refresh_token}
        )

        serializer.is_valid(raise_exception=True)

        dados = serializer.validated_data
        novo_refresh = dados.pop('refresh', None)

        response = Response(dados)

        if novo_refresh:
            response.set_cookie(
                key='refresh_token',
                value=novo_refresh,
                httponly=True,
                secure=not settings.DEBUG,
                samesite='Lax',
                max_age=86400,
                path='/api/auth/'
            )

        return response
    
@method_decorator(csrf_protect, name='dispatch')
class LogoutAPIView(generics.GenericAPIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        refresh_token = request.COOKIES.get('refresh_token')

        response = Response(
            {'message': 'Logout realizado com sucesso.'},
            status=200
        )

        if refresh_token:
            try:
                token = RefreshToken(refresh_token)
                token.blacklist()
            except TokenError:
                pass

        response.delete_cookie(
            key='refresh_token',
            path='/api/auth/',
            samesite='Lax'
        )

        return response

class MeAPIView(generics.RetrieveAPIView):
    serializer_class = UsuarioAtualSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_object(self):
        return self.request.user

@ensure_csrf_cookie
def csrf_cookie(request):
    return JsonResponse({
        'detail': 'Cookie CSRF disponibilizado.'
    })



def sincronizar_grupo(usuario, novo_papel):
    nomes_grupos = {
        Perfil.Papel.SUPREMO: "Supremo",
        Perfil.Papel.GERENTE: "Gerente",
        Perfil.Papel.FUNCIONARIO: "Funcionario",
    }

    nome_grupo = nomes_grupos.get(novo_papel)

    if not nome_grupo:
        raise ValidationError({"papel": "Papel inválido."})

    grupo, _ = Group.objects.get_or_create(name=nome_grupo)

    usuario.groups.clear()
    usuario.groups.add(grupo)


def pode_gerenciar_usuario(solicitante, alvo):
    papel_solicitante = papel(solicitante)
    papel_alvo = papel(alvo)

    if papel_solicitante == "SUPREMO":
        return True

    if papel_solicitante == "GERENTE":
        return (
            papel_alvo == "FUNCIONARIO"
            and not alvo.is_superuser
        )

    return False


def quantidade_supremos_ativos():
    return User.objects.filter(
        is_active=True
    ).filter(
        # Usuários com perfil Supremo ou superusuários Django.
        # O distinct evita contar o mesmo usuário duas vezes.
        perfil__papel=Perfil.Papel.SUPREMO
    ).count() + User.objects.filter(
        is_active=True,
        is_superuser=True
    ).exclude(
        perfil__papel=Perfil.Papel.SUPREMO
    ).count()


class UsuariosAPIView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        role = papel(request.user)

        if role not in ("SUPREMO", "GERENTE"):
            raise PermissionDenied(
                "Você não pode consultar a lista de usuários."
            )

        usuarios = User.objects.select_related(
            "perfil"
        ).order_by("username")

        if role == "GERENTE":
            usuarios = usuarios.filter(
                perfil__papel=Perfil.Papel.FUNCIONARIO,
                is_superuser=False,
            )
        else:
            # O Supremo pode visualizar todos, inclusive outros
            # superusuários, sem poder rebaixar um superusuário.
            pass

        dados = []

        for usuario in usuarios:
            dados.append({
                "id": usuario.id,
                "username": usuario.username,
                "first_name": usuario.first_name,
                "last_name": usuario.last_name,
                "email": usuario.email,
                "papel": papel(usuario),
                "is_active": usuario.is_active,
                "is_superuser": usuario.is_superuser,
            })

        return Response(dados)


class UsuarioDetalheAPIView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    @transaction.atomic
    def patch(self, request, pk):
        alvo = get_object_or_404(
            User.objects.select_related("perfil"),
            pk=pk,
        )

        if not pode_gerenciar_usuario(request.user, alvo):
            raise PermissionDenied(
                "Você não pode editar este usuário."
            )

        if alvo.is_superuser:
            raise PermissionDenied(
                "Não é permitido editar uma conta de superusuário por esta tela."
            )

        dados_permitidos = {
            "first_name",
            "last_name",
            "email",
        }

        campos_invalidos = set(request.data.keys()) - (
            dados_permitidos | {"papel"}
        )

        if campos_invalidos:
            raise ValidationError({
                "detail": "Foram enviados campos não permitidos."
            })

        for campo in dados_permitidos:
            if campo in request.data:
                setattr(alvo, campo, request.data[campo])

        if "papel" in request.data:
            papel_solicitante = papel(request.user)
            novo_papel = request.data["papel"]

            if papel_solicitante != "SUPREMO":
                raise PermissionDenied(
                    "Somente o Supremo pode alterar papéis."
                )

            if novo_papel not in (
                Perfil.Papel.GERENTE,
                Perfil.Papel.FUNCIONARIO,
            ):
                raise ValidationError({
                    "papel": "Papel inválido."
                })

            perfil, _ = Perfil.objects.get_or_create(
                user=alvo,
                defaults={
                    "papel": Perfil.Papel.FUNCIONARIO
                },
            )

            perfil.papel = novo_papel
            perfil.save(update_fields=["papel"])

            sincronizar_grupo(alvo, novo_papel)

        alvo.save()

        return Response({
            "id": alvo.id,
            "username": alvo.username,
            "first_name": alvo.first_name,
            "last_name": alvo.last_name,
            "email": alvo.email,
            "papel": papel(alvo),
            "is_active": alvo.is_active,
        })


class UsuarioStatusAPIView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    @transaction.atomic
    def patch(self, request, pk):
        alvo = get_object_or_404(
            User.objects.select_related("perfil"),
            pk=pk,
        )

        if not pode_gerenciar_usuario(request.user, alvo):
            raise PermissionDenied(
                "Você não pode alterar o status deste usuário."
            )

        if alvo.is_superuser:
            raise PermissionDenied(
                "Não é permitido alterar o status de um superusuário por esta tela."
            )

        if "is_active" not in request.data:
            raise ValidationError({
                "is_active": "Informe o novo status do usuário."
            })

        novo_status = request.data["is_active"]

        if not isinstance(novo_status, bool):
            raise ValidationError({
                "is_active": "O status deve ser verdadeiro ou falso."
            })

        if alvo.pk == request.user.pk and not novo_status:
            raise ValidationError(
                "Você não pode desativar sua própria conta."
            )

        if not novo_status and papel(alvo) == "SUPREMO":
            if quantidade_supremos_ativos() <= 1:
                raise ValidationError(
                    "Não é possível desativar o último Supremo ativo."
                )

        alvo.is_active = novo_status
        alvo.save(update_fields=["is_active"])

        return Response({
            "id": alvo.id,
            "username": alvo.username,
            "is_active": alvo.is_active,
            "message": (
                "Usuário ativado."
                if novo_status
                else "Usuário desativado."
            ),
        })
