
from django.contrib import admin
from django.urls import path
from .views import home, alterar_senha, login_user, logout_user, add_tarefa, edit_tarefa, deletar_tarefa, lista_tarefas, concluir_tarefa
urlpatterns = [
    path('', login_user, name='login'),
    path('home/', home, name='home'),
    path('alterar_senha/', alterar_senha, name='alterar_senha'),
    path('logout/', logout_user, name='logout_user'),
    path('add_tarefa/', add_tarefa, name='add_tarefa'),
    path('edit_tarefa/<int:tarefa_id>/', edit_tarefa, name='edit_tarefa'),
    path('deletar_tarefa/<int:tarefa_id>/', deletar_tarefa, name='deletar_tarefa'),
    path('lista_tarefas/', lista_tarefas, name='lista_tarefas'),
    path('concluir_tarefa/<int:tarefa_id>/', concluir_tarefa, name='concluir_tarefa'),
]