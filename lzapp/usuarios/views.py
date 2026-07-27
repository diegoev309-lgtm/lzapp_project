from django.shortcuts import render, redirect
from django.contrib.auth import login, logout
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.contrib.auth.models import User
from django.contrib.auth.tokens import default_token_generator
from django.contrib.auth.forms import SetPasswordForm
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode
from django.utils.encoding import force_bytes

from .forms import RegistroForm, LoginForm
from dashboard.models import Perfil
from .utils import enviar_email_recuperacion_async  # ajusta el import según donde guardaste la función


def registro(request):

    if request.method == "POST":

        form = RegistroForm(request.POST)

        if form.is_valid():

            usuario = form.save()

            Perfil.objects.create(
                usuario=usuario,
                telefono=form.cleaned_data['telefono']
            )

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

            # Si es administrador
            if usuario.is_staff or usuario.is_superuser:
                return redirect('Inicio_dash')

            # Si es un usuario normal
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


def solicitar_reset_password(request):

    if request.method == "POST":

        email = request.POST.get('email', '').strip()

        try:
            usuario = User.objects.get(email=email)

            enviar_email_recuperacion_async(
                usuario.id,
                dominio=request.get_host(),
                protocolo='https' if request.is_secure() else 'http'
            )

        except User.DoesNotExist:
            # No revelamos si el email existe o no, por seguridad
            pass

        messages.success(request, "Si el correo está registrado, te enviamos un enlace para restablecer tu contraseña.")

        return redirect('login')

    return render(request, 'solicitar_reset.html')


def confirmar_reset_password(request, uidb64, token):

    try:
        uid = urlsafe_base64_decode(uidb64).decode()
        usuario = User.objects.get(pk=uid)

    except (TypeError, ValueError, OverflowError, User.DoesNotExist):
        usuario = None

    if usuario is not None and default_token_generator.check_token(usuario, token):

        if request.method == "POST":

            form = SetPasswordForm(usuario, request.POST)

            if form.is_valid():

                form.save()

                messages.success(request, "Tu contraseña se cambió correctamente. Ya puedes iniciar sesión.")

                return redirect('login')

            else:
                messages.error(request, "Revisa los datos del formulario.")

        else:
            form = SetPasswordForm(usuario)

        return render(request, 'confirmar_reset.html', {'form': form})

    else:
        return render(request, 'reset_invalido.html')