from django.shortcuts import render, redirect
from django.contrib import messages
from django.contrib.auth.hashers import make_password, check_password

from .models import Usuario
from .forms import RegistroForm


def registro(request):

    if request.method == "POST":

        form = RegistroForm(request.POST)

        print(request.POST)          
        print(form.errors)          

        if form.is_valid():

            usuario = form.save(commit=False)

            usuario.contraseña = make_password(
                form.cleaned_data["contraseña"]
            )

            usuario.save()

            print("Usuario guardado correctamente")

            return redirect("login")

    else:
        form = RegistroForm()

    return render(request, "registro.html", {
        "form": form
    })

def login(request):

    if request.method == "POST":

        correo = request.POST["correo"]
        contraseña = request.POST["contraseña"]

        try:

            usuario = Usuario.objects.get(correo=correo)

            if check_password(contraseña, usuario.contraseña):

                request.session["usuario_id"] = usuario.id
                request.session["nombre"] = usuario.nombre

                return redirect("client")

            else:

                messages.error(request, "Contraseña incorrecta.")

        except Usuario.DoesNotExist:

            messages.error(request, "El usuario no existe.")

    return render(request, "login.html")


def logout(request):

    request.session.flush()

    return redirect("user")