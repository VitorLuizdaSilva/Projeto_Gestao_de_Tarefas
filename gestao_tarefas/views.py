from django.shortcuts import render, redirect
from django.contrib.auth.models import User, Group
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth import authenticate, login, logout
from django.contrib import messages
from .models import Tarefa, Perfil



def lista_tarefas(request):

    if not request.user.is_authenticated:
        return redirect('login')

  
    if request.user.groups.filter(name='Gerente').exists():

        tarefas = Tarefa.objects.all()

        return render(
            request,
            'lista_tarefas.html',
            {'tarefas': tarefas}
        )

 
    elif request.user.groups.filter(name='Funcionario').exists():

        tarefas = Tarefa.objects.filter(
            usuario=request.user
        )

        return render(
            request,
            'lista_tarefas.html',
            {'tarefas': tarefas}
        )

    else:

        messages.error(
            request,
            'Você não possui grupo.'
        )

        return render(request, 'lista_tarefas.html')



def cadastro_senha(request):

    if request.method == 'POST':

        form = UserCreationForm(request.POST)

        if form.is_valid():

            user = form.save()

            # adiciona automaticamente no grupo Funcionario
            group = Group.objects.get(name='Funcionario')
            user.groups.add(group)

            messages.success(
                request,
                'Usuário cadastrado com sucesso!'
            )

            return redirect('login')

    else:

        form = UserCreationForm()

    return render(
        request,
        'cadastro_user.html',
        {'form': form}
    )





# LOGIN
def login_user(request):

    if request.method == 'POST':

        username = request.POST.get('username')
        password = request.POST.get('password')

        user = authenticate(
            request,
            username=username,
            password=password
        )

        if user is not None:

            login(request, user)

            perfil, created = Perfil.objects.get_or_create(user=user)

            if perfil.senha_expirada():

                return redirect('cadastro_senha')

            return redirect('home')

        else:

            messages.error(
                request,
                'Usuário ou senha inválidos'
            )

            return redirect('login')

    return render(request, 'login.html')
# LOGOUT
def logout_user(request):

    logout(request)

    return redirect('login')


# ADICIONAR TAREFA

def add_tarefa(request):

    if request.method == 'POST':

        titulo = request.POST['titulo']
        descricao = request.POST['descricao']
        urgencia = request.POST['urgencia']

        if request.user.groups.filter(name='Gerente').exists():

            usuario_id = request.POST['usuario']
            usuario = User.objects.get(id=usuario_id)

        else:

            usuario = request.user

        Tarefa.objects.create(
            titulo=titulo,
            descricao=descricao,
            urgencia=urgencia,
            usuario=usuario
        )

        return redirect('home')

    else:

        usuarios = User.objects.all()

        is_gerente = request.user.groups.filter(
            name='Gerente'
        ).exists()

        return render(
            request,
            'add_tarefa.html',
            {
                'usuarios': usuarios,
                'is_gerente': is_gerente
            }
        )


# EDITAR TAREFA
def edit_tarefa(request, tarefa_id):

    tarefa = Tarefa.objects.get(id=tarefa_id)

    if request.method == 'POST':

        tarefa.titulo = request.POST['titulo']
        tarefa.descricao = request.POST['descricao']

        tarefa.status = request.POST['status']

        tarefa.urgencia = request.POST['urgencia']

        tarefa.usuario = request.user

        tarefa.save()

        return redirect('home')
    else:

        usuarios = User.objects.all()

        return render(
            request,
            'edit_tarefa.html',
            {
                'tarefa': tarefa,
                'usuarios': usuarios
            }
        )


# DELETAR TAREFA
def deletar_tarefa(request, tarefa_id):

    tarefa = Tarefa.objects.get(id=tarefa_id)

    tarefa.delete()

    return redirect('home')

def tarefa_detail(request, tarefa_id):

    tarefa = Tarefa.objects.get(id=tarefa_id)

    return render(
        request,
        'tarefa_detail.html',
        {'tarefa': tarefa}
    )

def home(request):

    if request.user.groups.filter(name='Gerente').exists():
        tarefas = Tarefa.objects.all()
    else:
        tarefas = Tarefa.objects.filter(usuario=request.user)

    context = {
        'total': tarefas.count(),
        'pendentes': tarefas.filter(status='PE').count(),
        'andamento': tarefas.filter(status='EA').count(),
        'concluidas': tarefas.filter(status='CO').count(),
    }

    return render(request, 'home.html', context)

def concluir_tarefa(request, tarefa_id):

    tarefa = Tarefa.objects.get(id=tarefa_id)

    tarefa.status = 'CO'

    tarefa.save()   

