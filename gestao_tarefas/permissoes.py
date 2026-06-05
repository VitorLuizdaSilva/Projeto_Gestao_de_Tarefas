from django.contrib.auth.models import Group, Permission


Group.objects.get_or_create(name='Gerente')
Group.objects.get_or_create(name='Funcionario')

for grupo_nome in ['Gerente', 'Funcionario']:
    grupo = Group.objects.get(name=grupo_nome)

    grupo.permissions.add(
        Permission.objects.get(codename='add_tarefa'),
        Permission.objects.get(codename='change_tarefa'),
        Permission.objects.get(codename='view_tarefa'),
        Permission.objects.get(codename='delete_tarefa'),
    )

