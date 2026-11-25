from django.contrib import admin
from .models import Tarefa, Perfil, Equipe, MembroEquipe, HistoricoTarefa

@admin.register(Perfil)
class PerfilAdmin(admin.ModelAdmin):
    list_display = ('user', 'papel', 'data_troca_senha')
    list_filter = ('papel',)
    search_fields = ('user__username', 'user__email')

class MembroEquipeInline(admin.TabularInline):
    model = MembroEquipe
    extra = 0

@admin.register(Equipe)
class EquipeAdmin(admin.ModelAdmin):
    list_display = ('nome', 'gerente', 'ativa', 'criada_em')
    list_filter = ('ativa',)
    search_fields = ('nome', 'gerente__username')
    inlines = [MembroEquipeInline]

@admin.register(Tarefa)
class TarefaAdmin(admin.ModelAdmin):
    list_display = ('titulo', 'equipe', 'usuario', 'status', 'urgencia', 'atualizada_em')
    list_filter = ('status', 'urgencia', 'equipe')
    search_fields = ('titulo', 'usuario__username')

@admin.register(HistoricoTarefa)
class HistoricoTarefaAdmin(admin.ModelAdmin):
    list_display = ('tarefa', 'autor', 'acao', 'criado_em')
    readonly_fields = ('tarefa', 'autor', 'acao', 'criado_em', 'detalhes')
