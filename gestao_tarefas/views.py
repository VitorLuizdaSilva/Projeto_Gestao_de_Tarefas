from django.shortcuts import render
from django.contrib.auth.models import User, Group
from django.contrib import messages
# Create your views here.

def cadastro_user(request):
    if request.method == 'POST':
        username = request.POST['username']
        password = request.POST['password']
        email = request.POST['email']
        if User.objects.filter(username=username).exists() and User.objects.filter(email=email).exists():
            messages.error(request, 'Usuário ou email já existe')
            return render(request, 'cadastro.html')
        else:
            user = User.objects.create_user(username=username, password=password, email=email)
            user.save()
            messages.success(request, 'Usuário cadastrado com sucesso')
        return render(request, 'login.html')    
    else:
        return render(request, 'cadastro.html')

def login_user(request):
    if User.is_authenticated:
        if request.method == 'POST':
            return render(request, 'home.html')
        else:
            messages.error(request, 'Usuário ou senha inválidos')
            return render(request, 'login.html')
        
def home(request):
    if User.is_authenticated:
        return render(request, 'home.html')
    else:
        messages.error(request, 'Usuario não autenticado')
        return render(request, 'login.html')