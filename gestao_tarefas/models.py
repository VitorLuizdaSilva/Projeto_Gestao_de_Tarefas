from django.db import models
from django.contrib.auth.models import User
# Create your models here.
class Tarefa(models.Model):
    titulo = models.CharField(max_length=200)
    descricao = models.TextField()
    status = models.BooleanField(default=False)
    usuario = models.ForeignKey(User, on_delete=models.CASCADE)


