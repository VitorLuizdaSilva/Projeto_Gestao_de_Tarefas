from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone

# Create your models here.
from django.db import models
from django.contrib.auth.models import User

class Tarefa(models.Model):

    NIVEL_URGENCIA = [
        ('B', 'Baixa'),
        ('M', 'Média'),
        ('A', 'Alta'),
    ]
    STATUS_CHOICES = [
        ('AF', 'A Fazer'),
        ('EA', 'Em Andamento'),
        ('CO', 'Concluído'),
    ]
    titulo = models.CharField(max_length=200)
    descricao = models.TextField()
    status = models.CharField(
        max_length=2,
        choices=STATUS_CHOICES,
        default='AF'
    )

    urgencia = models.CharField(
        max_length=1,
        choices=NIVEL_URGENCIA,
        default='M'
    )

    usuario = models.ForeignKey(
        User,
        on_delete=models.CASCADE
    )

    def __str__(self):
        return self.titulo
    
class Perfil(models.Model):

    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE
    )

    data_troca_senha = models.DateTimeField(
        default=timezone.now
    )

    def senha_expirada(self):

        return timezone.now() >= (
            self.data_troca_senha +
            timezone.timedelta(days=30)
        )