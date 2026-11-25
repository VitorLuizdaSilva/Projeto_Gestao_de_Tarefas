
from django.contrib.auth.models import User, Group
from django.contrib.auth.password_validation import validate_password
from django.db import transaction
from rest_framework import serializers

from .models import (
    Perfil,
    Equipe,
    MembroEquipe,
    Tarefa,
)
from .api_permissions import papel


def sincronizar_grupo(usuario, novo_papel):
    """
    Mantém o grupo Django compatível com o papel salvo no Perfil.
    """
    grupos = {
        "SUPREMO": "Supremo",
        "GERENTE": "Gerente",
        "FUNCIONARIO": "Funcionario",
    }

    nomes_grupos = list(grupos.values())
    usuario.groups.remove(
        *Group.objects.filter(name__in=nomes_grupos)
    )

    nome_grupo = grupos.get(novo_papel)
    if nome_grupo:
        grupo, _ = Group.objects.get_or_create(name=nome_grupo)
        usuario.groups.add(grupo)


class UsuarioResumoSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = [
            "id",
            "username",
            "first_name",
            "last_name",
        ]


class EquipeSerializer(serializers.ModelSerializer):
    gerente = UsuarioResumoSerializer(read_only=True)

    gerente_id = serializers.PrimaryKeyRelatedField(
        source="gerente",
        queryset=User.objects.filter(is_active=True),
        write_only=True,
        required=False,
    )

    membros = serializers.SerializerMethodField()

    class Meta:
        model = Equipe
        fields = [
            "id",
            "nome",
            "descricao",
            "gerente",
            "gerente_id",
            "membros",
            "ativa",
            "criada_em",
        ]
        read_only_fields = ["gerente", "criada_em"]

    def get_membros(self, obj):
        usuarios = User.objects.filter(
            vinculos_equipes__equipe=obj,
            is_active=True,
        )
        return UsuarioResumoSerializer(
            usuarios,
            many=True,
        ).data


class TarefaSerializer(serializers.ModelSerializer):
    responsavel = UsuarioResumoSerializer(
        source="usuario",
        read_only=True,
    )

    responsavel_id = serializers.PrimaryKeyRelatedField(
        source="usuario",
        queryset=User.objects.filter(is_active=True),
        write_only=True,
        required=False,
    )

    equipe_nome = serializers.CharField(
        source="equipe.nome",
        read_only=True,
        default=None,
    )

    class Meta:
        model = Tarefa
        fields = [
            "id",
            "titulo",
            "descricao",
            "status",
            "urgencia",
            "equipe",
            "equipe_nome",
            "responsavel",
            "responsavel_id",
            "criada_por",
            "criada_em",
            "atualizada_em",
        ]
        read_only_fields = [
            "criada_por",
            "criada_em",
            "atualizada_em",
        ]


class MembroEquipeSerializer(serializers.ModelSerializer):
    usuario_nome = serializers.CharField(
        source="usuario.username",
        read_only=True,
    )

    usuario = serializers.PrimaryKeyRelatedField(
        queryset=User.objects.filter(
            is_active=True,
            perfil__papel="FUNCIONARIO",
        )
    )

    class Meta:
        model = MembroEquipe
        fields = [
            "id",
            "usuario",
            "usuario_nome",
            "pode_criar_tarefa",
            "pode_editar_tarefa",
            "pode_excluir_tarefa",
        ]



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
        role = papel(solicitante)

        papel_solicitado = attrs.get(
            "papel",
            Perfil.Papel.FUNCIONARIO,
        )

        if role == "GERENTE":
            if papel_solicitado != Perfil.Papel.FUNCIONARIO:
                raise serializers.ValidationError({
                    "papel": "Gerentes só podem cadastrar funcionários."
                })

        elif role == "SUPREMO":
            if papel_solicitado not in (
                Perfil.Papel.GERENTE,
                Perfil.Papel.FUNCIONARIO,
            ):
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


class UsuarioAtualSerializer(serializers.ModelSerializer):
    papel = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = [
            "id",
            "username",
            "email",
            "first_name",
            "last_name",
            "papel",
        ]

    def get_papel(self, obj):
        return papel(obj)


class UsuarioGerenciamentoSerializer(serializers.ModelSerializer):
    papel = serializers.ChoiceField(
        choices=Perfil.Papel.choices,
        required=False,
    )

    password = serializers.CharField(
        write_only=True,
        required=False,
        validators=[validate_password],
    )

    class Meta:
        model = User
        fields = [
            "id",
            "username",
            "email",
            "first_name",
            "last_name",
            "papel",
            "is_active",
            "password",
        ]
        read_only_fields = [
            "id",
            "username",
            "is_active",
        ]

    def validate_email(self, value):
        if value:
            duplicado = User.objects.filter(
                email__iexact=value,
            ).exclude(pk=self.instance.pk)

            if duplicado.exists():
                raise serializers.ValidationError(
                    "Este e-mail já está sendo utilizado."
                )

        return value

    @transaction.atomic
    def update(self, instance, validated_data):
        novo_papel = validated_data.pop(
            "papel",
            papel(instance),
        )

        password = validated_data.pop("password", None)

        for campo, valor in validated_data.items():
            setattr(instance, campo, valor)

        if password:
            instance.set_password(password)

        instance.save()

        perfil, _ = Perfil.objects.get_or_create(
            user=instance,
        )

        if perfil.papel != novo_papel:
            perfil.papel = novo_papel
            perfil.save(update_fields=["papel"])
            sincronizar_grupo(instance, novo_papel)

        return instance
