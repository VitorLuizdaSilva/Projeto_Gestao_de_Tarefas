from django.apps import AppConfig


from django.apps import AppConfig

class GestaoTarefasConfig(AppConfig):

    default_auto_field = 'django.db.models.BigAutoField'
    name = 'gestao_tarefas'

    def ready(self):

        import gestao_tarefas.signals
