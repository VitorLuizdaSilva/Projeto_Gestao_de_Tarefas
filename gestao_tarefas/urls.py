
from django.contrib import admin
from django.urls import path
from views import home, cadastro_user, login_user
urlpatterns = [
    path('admin/', admin.site.urls),
    path('home/', home, name='home'),
    path('login/', login_user, name='login_user'),
    path('cadastro_user/', cadastro_user, name='cadastro_user'),
]
