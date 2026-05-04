from django import forms
from django.contrib.auth.models import User
from django.contrib.auth.forms import UserCreationForm

class UsercadastroForm(UserCreationForm):
    email = forms.EmailField(label='', 
    widget=forms.EmailInput(
    attrs={'class': 'form-control', 'placeholder': 'Email'}))
    username = forms.CharField(label='', 
    widget=forms.TextInput(
    attrs={'class': 'form-control', 'placeholder': 'Username'}))
    
    class Meta:
        model = User
        fields = ['username', 'email', 'password1', 'password2']
       
    def __init__(self, *args, **kwargs):
        super(UsercadastroForm, self).__init__(*args, **kwargs)
        self.fields['username'].widget.attrs['class'] = 'form-control'
        self.fields['username'].widget.attrs['placeholder'] = 'User Name'
        self.fields['username'].label = ''
        self.fields['username'].help_text = '''
        <span class="form-text text-muted">
        <small>Requerido. 150 caracteres ou menos. Letras, dígitos e @/./+/-/_ apenas.</small>
        </span>'''
        
        self.fields['password1'].widget.attrs['class'] = 'form-control'
        self.fields['password1'].widget.attrs['placeholder'] = 'Password'
        self.fields['password1'].label = ''
        self.fields['password1'].help_text = '''
        <span class="form-text text-muted"> 
            <li>Sua senha deve ser única.</li>
            <li>Sua senha deve conter pelo menos 8 caracteres.</li>
            <li>Sua senha não pode ser totalmente numérica.</li>
        </span>'''
        
        self.fields['password2'].widget.attrs['class'] = 'form-control'
        self.fields['password2'].widget.attrs['placeholder'] = 'Confirm Password'
        self.fields['password2'].label = ''
        self.fields['password2'].help_text = '''
        <span class="form-text text-muted">
            <small>Digite a mesma senha para verificação.</small>
        </span>'''