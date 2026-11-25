from django.shortcuts import render


def login_page(request):
    return render(request, "login.html")


def cadastro_page(request):
    return render(request, "cadastro.html")


def home_page(request):
    return render(request, "home.html")
