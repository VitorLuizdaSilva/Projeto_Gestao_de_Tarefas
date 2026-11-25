from rest_framework import serializers
from django.contrib.auth.models import User, Group
from .models import Equipe, MembroEquipe, Tarefa
from django.contrib.auth.password_validation import validate_password
from .api_permissions import papel
from django.db import transaction


from .models import Perfil

class UsuarioResumoSerializer(serializers.ModelSerializer):

    class Meta:
        model = User
        fields = [
            'id',
            'username',
            'first_name',
            'last_name'
        ]


class EquipeSerializer(serializers.ModelSerializer):
    gerente = UsuarioResumoSerializer(read_only=True)

    gerente_id = serializers.PrimaryKeyRelatedField(
        source='gerente',
        queryset=User.objects.all(),
        write_only=True,
        required=False
    )

    membros = serializers.SerializerMethodField()

    class Meta:
        model = Equipe
        fields = [
            'id',
            'nome',
            'descricao',
            'gerente',
            'gerente_id',
            'membros',
            'ativa',
            'criada_em'
        ]

        read_only_fields = [
            'gerente',
            'criada_em'
        ]

    def get_membros(self, obj):
        usuarios = [
            membro.usuario
            for membro in obj.membros.select_related('usuario')
        ]

        return UsuarioResumoSerializer(
            usuarios,
            many=True
        ).data


class TarefaSerializer(serializers.ModelSerializer):
    responsavel = UsuarioResumoSerializer(
        source='usuario',
        read_only=True
    )

    responsavel_id = serializers.PrimaryKeyRelatedField(
        source='usuario',
        queryset=User.objects.all(),
        write_only=True
    )

    equipe_nome = serializers.CharField(
        source='equipe.nome',
        read_only=True
    )

    class Meta:
        model = Tarefa
        fields = [
            'id',
            'titulo',
            'descricao',
            'status',
            'urgencia',
            'equipe',
            'equipe_nome',
            'responsavel',
            'responsavel_id',
            'criada_por',
            'criada_em',
            'atualizada_em'
        ]

        read_only_fields = [
            'criada_por',
            'criada_em',
            'atualizada_em'
        ]


class MembroEquipeSerializer(serializers.ModelSerializer):
    usuario_nome = serializers.CharField(
        source='usuario.username',
        read_only=True
    )

    class Meta:
        model = MembroEquipe
        fields = [
            'id',
            'usuario',
            'usuario_nome',
            'pode_criar_tarefa',
            'pode_editar_tarefa',
            'pode_excluir_tarefa'
        ]

class CadastroSerializer(serializers.ModelSerializer):
    password = serializers.CharField(
        write_only=True,
        validators=[validate_password]
    )

    password2 = serializers.CharField(write_only=True)

    class Meta:
        model = User
        fields = ['username', 'email', 'password', 'password2']

    def validate(self, attrs):
        if attrs['password'] != attrs['password2']:
            raise serializers.ValidationError({
                'password2': 'As senhas não coincidem.'
            })

        return attrs

    @transaction.atomic
    def create(self, validated_data):
        validated_data.pop('password2')
        password = validated_data.pop('password')

        user = User(**validated_data)
        user.set_password(password)
        user.save()

        Perfil.objects.get_or_create(
            user=user,
            defaults={'papel': Perfil.Papel.FUNCIONARIO}
        )

        grupo, _ = Group.objects.get_or_create(
            name='Funcionario'
        )
        user.groups.add(grupo)

        return user

class UsuarioAtualSerializer(serializers.ModelSerializer):
    papel = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'first_name', 'last_name', 'papel']

    def get_papel(self, obj):
        return papel(obj)