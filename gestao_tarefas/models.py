from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone


class Perfil(models.Model):
    class Papel(models.TextChoices):
        SUPREMO = "SUPREMO", "Supremo"
        GERENTE = "GERENTE", "Gerente"
        FUNCIONARIO = "FUNCIONARIO", "Funcionário"

    user = models.OneToOneField(User, on_delete=models.CASCADE)
    papel = models.CharField(max_length=12, choices=Papel.choices, default=Papel.FUNCIONARIO)
    data_troca_senha = models.DateTimeField(default=timezone.now)

    def senha_expirada(self):
        return timezone.now() >= self.data_troca_senha + timezone.timedelta(days=30)

    def atualizar_senha(self):
        self.data_troca_senha = timezone.now()
        self.save(update_fields=["data_troca_senha"])

    def __str__(self):
        return f"{self.user.username} ({self.get_papel_display()})"


class Equipe(models.Model):
    nome = models.CharField(max_length=100)
    descricao = models.TextField(blank=True)
    gerente = models.ForeignKey(User, on_delete=models.PROTECT, related_name="equipes_gerenciadas")
    criada_em = models.DateTimeField(auto_now_add=True)
    ativa = models.BooleanField(default=True)

    class Meta:
        ordering = ["nome"]
        verbose_name = "Equipe"
        verbose_name_plural = "Equipes"

    def __str__(self):
        return self.nome


class MembroEquipe(models.Model):
    equipe = models.ForeignKey(Equipe, on_delete=models.CASCADE, related_name="membros")
    usuario = models.ForeignKey(User, on_delete=models.CASCADE, related_name="vinculos_equipes")
    pode_criar_tarefa = models.BooleanField(default=False)
    pode_editar_tarefa = models.BooleanField(default=False)
    pode_excluir_tarefa = models.BooleanField(default=False)
    entrou_em = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [models.UniqueConstraint(fields=["equipe", "usuario"], name="uniq_membro_por_equipe")]

    def __str__(self):
        return f"{self.usuario.username} - {self.equipe.nome}"


class Tarefa(models.Model):
    NIVEL_URGENCIA = [("B", "Baixa"), ("M", "Média"), ("A", "Alta")]
    STATUS_CHOICES = [("AF", "A Fazer"), ("EA", "Em Andamento"), ("CO", "Concluído")]
    titulo = models.CharField(max_length=200)
    descricao = models.TextField()
    status = models.CharField(max_length=2, choices=STATUS_CHOICES, default="AF")
    urgencia = models.CharField(max_length=1, choices=NIVEL_URGENCIA, default="M")
    usuario = models.ForeignKey(User, on_delete=models.PROTECT, related_name="tarefas_atribuidas")
    equipe = models.ForeignKey(Equipe, on_delete=models.PROTECT, null=True, blank=True, related_name="tarefas")
    criada_por = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name="tarefas_criadas")
    criada_em = models.DateTimeField(auto_now_add=True)
    atualizada_em = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.titulo



class HistoricoTarefa(models.Model):
    tarefa = models.ForeignKey(
        Tarefa,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="historico"
    )

    # Identificação da tarefa mesmo depois da exclusão.
    tarefa_id_original = models.PositiveIntegerField(
        null=True,
        blank=True
    )

    tarefa_titulo = models.CharField(
        max_length=200,
        blank=True
    )

    autor = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True
    )

    acao = models.CharField(max_length=120)
    criado_em = models.DateTimeField(auto_now_add=True)
    detalhes = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ["-criado_em"]

    def save(self, *args, **kwargs):
        # Guarda os dados da tarefa na criação do histórico.
        if self._state.adding and self.tarefa:
            self.tarefa_id_original = self.tarefa.pk
            self.tarefa_titulo = self.tarefa.titulo

        super().save(*args, **kwargs)

    def __str__(self):
        titulo = self.tarefa_titulo or "Tarefa sem identificação"
        return f"{titulo}: {self.acao}"

