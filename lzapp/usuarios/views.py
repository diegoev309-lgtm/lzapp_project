from django.shortcuts import render, redirect
from django.contrib.auth import login, logout
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from .forms import RegistroForm, LoginForm
from dashboard.models import Perfil
from .tasks import enviar_email_bienvenida_async  # <-- NUEVO import

def registro(request):
    if request.method == "POST":
        form = RegistroForm(request.POST)
        if form.is_valid():
            usuario = form.save()
            Perfil.objects.create(
                usuario=usuario,
                telefono=form.cleaned_data['telefono'])

            enviar_email_bienvenida_async(usuario.id)  # <-- NUEVA línea: dispara el hilo en segundo plano

            messages.success(request, "Usuario registrado correctamente. Ya puedes iniciar sesión.")
            return redirect('login')
        else:
            messages.error(request, "Revisa los datos del formulario.")
    else:
        form = RegistroForm()
    return render(request, 'registro.html', {'form': form})

def iniciar_sesion(request):
    if request.method == "POST":
        form = LoginForm(request, data=request.POST)
        if form.is_valid():
            usuario = form.get_user()
            login(request, usuario)
            messages.success(request, f"Bienvenido, {usuario.username}.")
            return redirect('client')
        else:
            messages.error(request, "Usuario o contraseña incorrectos.")
    else:
        form = LoginForm()
    return render(request, 'login.html', {'form': form})

def cerrar_sesion(request):
    logout(request)
    messages.info(request, "Has cerrado sesión correctamente.")
    return redirect('login')

@login_required
def inicio(request):
    return render(request, 'inicio.html')