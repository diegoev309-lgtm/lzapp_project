import json

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, logout
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_POST
from django.contrib import messages
from django.contrib.auth.models import User
from django.contrib.auth.tokens import default_token_generator
from django.contrib.auth.forms import SetPasswordForm
from django.utils.http import urlsafe_base64_decode
from django.utils import timezone
from django.http import JsonResponse
from django.db.models import Count
from datetime import timedelta
from dashboard.models import Venta, Perfil, PerfilEmple
from .utils import enviar_email_recuperacion_async
from .forms import (RegistroForm,LoginForm,UserUpdateForm,PerfilUpdateForm,RegistroEmpleadoForm)
from django.core.paginator import Paginator


def registro(request):
    if request.method == "POST":
        form = RegistroForm(request.POST)
        if form.is_valid():
            usuario = form.save()
            Perfil.objects.create(usuario=usuario,telefono=form.cleaned_data['telefono'])

            messages.success(request,"Usuario registrado correctamente. Ya puedes iniciar sesión.")

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


@login_required
def configuracion(request):
    # Si el usuario no tiene Perfil todavía, se crea uno vacío
    perfil, _ = Perfil.objects.get_or_create(usuario=request.user)
    if request.method == "POST":
        user_form = UserUpdateForm(request.POST, instance=request.user)
        perfil_form = PerfilUpdateForm(request.POST, instance=perfil)
        if user_form.is_valid() and perfil_form.is_valid():
            user_form.save()
            perfil_form.save()

            messages.success(request,"Tus datos se actualizaron correctamente.")

            return redirect('configuracion')

        else:
            messages.error(request, "Revisa los datos del formulario.")
    else:
        user_form = UserUpdateForm(instance=request.user)
        perfil_form = PerfilUpdateForm(instance=perfil)

    return render(request, 'configuracion.html', {'user_form': user_form,'perfil_form': perfil_form,})


# -----------------------------
# RECUPERAR CONTRASEÑA
# -----------------------------


def solicitar_reset_password(request):
    if request.method == "POST":
        email = request.POST.get('email', '').strip()

        # Usamos filter() para evitar MultipleObjectsReturned
        usuarios = User.objects.filter(email=email)
        if usuarios.exists():

            # Tomamos el primer usuario encontrado
            usuario = usuarios.first()
            enviar_email_recuperacion_async(usuario.id,dominio=request.get_host(),
            protocolo='https' if request.is_secure() else 'http')

        # No revelamos si el correo existe o no
        messages.success(request,"Si el correo está registrado, te enviamos un enlace para restablecer tu contraseña.")

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
                messages.success(request,"Tu contraseña se cambió correctamente. Ya puedes iniciar sesión.")

                return redirect('login')

            else:
                messages.error(request, "Revisa los datos del formulario.")
        else:
            form = SetPasswordForm(usuario)

        return render(request, 'confirmar_reset.html', {'form': form})
    else:
        return render(request, 'reset_invalido.html')


# =====================================
# PANEL USUARIO DEL DASHBOARD
# =====================================

def Usuario(request):
    return render(request, "usuarios.html")

# -----------------------------
# REGISTRO DE EMPLEADOS
# -----------------------------

def registro_empleado(request):
    if request.method == 'POST':
        form = RegistroEmpleadoForm(request.POST)
        if form.is_valid():
            usuario = form.save()
            PerfilEmple.objects.create(empleado=usuario,telefono=form.cleaned_data.get('telefono'),rol='empleado')
            messages.success(request, 'Empleado registrado correctamente.')

            return redirect('usuarios')
    else:
        form = RegistroEmpleadoForm()

    return render(request, 'registro_empleado.html', {'form': form})

# -----------------------------
# LISTA DE USUARIOS
# -----------------------------

@login_required
def lista_usuarios(request):
    usuarios = User.objects.select_related('perfil').filter(perfilemple__isnull=True)
    empleados = User.objects.select_related('perfilemple').filter(perfilemple__isnull=False)

    return render(request, 'usuarios.html', {'usuarios': usuarios,'empleados': empleados,})

# -----------------------------
# EDITAR USUARIO
# -----------------------------

@login_required
def editar_usuario(request, id):
    usuario = get_object_or_404(User, id=id)
    if request.method == 'POST':
        usuario.username = request.POST.get('username')
        usuario.email = request.POST.get('email')
        usuario.save()
        messages.success(request, 'Usuario actualizado correctamente.')

        return redirect('usuarios')

    return render(request,'editar_usuario.html',{'usuario': usuario})

# -----------------------------
# ELIMINAR USUARIO
# -----------------------------

@login_required
@require_POST
def eliminar_usuario(request, id):
    usuario = get_object_or_404(User, id=id)

    # Evitar que el administrador se elimine a sí mismo
    if usuario == request.user:
        messages.error(request,'No puedes eliminar tu propia cuenta.')

        return redirect('Usuario')

    nombre = usuario.username
    usuario.delete()
    messages.success(request,f'El usuario "{nombre}" fue eliminado correctamente.')

    return redirect('Usuario')


# -----------------------------
# HELPER: TOP COMPRADORES
# -----------------------------
def _top_compradores(limite=5):
    """
    Devuelve un queryset de Users anotados con 'total_compras',
    ordenados de mayor a menor, solo los que tienen al menos 1 compra.
    """
    return (
        User.objects
        .annotate(total_compras=Count('ventas'))
        .filter(total_compras__gt=0)
        .order_by('-total_compras')[:limite]
    )


# -----------------------------
# LISTADO DE USUARIOS
# -----------------------------

@login_required
def Usuarios(request):
    usuarios_qs = (User.objects.select_related('perfil','perfilemple').all().order_by('id'))

    filtro_rol = request.GET.get('rol')

    # ---------- Filtros ----------
    if filtro_rol == 'empleado':
        usuarios_qs = usuarios_qs.filter(perfilemple__isnull=False)

    elif filtro_rol == 'usuario':
        usuarios_qs = usuarios_qs.filter(perfilemple__isnull=True)

    # ---------- Estadísticas: cantidad, activos, inactivos ----------
    total_usuarios = User.objects.filter(perfilemple__isnull=True).count()
    total_empleados = User.objects.filter(perfilemple__isnull=False).count()

    usuarios_activos = User.objects.filter(is_active=True).count()
    usuarios_inactivos = User.objects.filter(is_active=False).count()

    # ---------- Top usuarios que más han comprado ----------
    top_compradores = _top_compradores(limite=5)

    # ---------- Registros por mes ----------
    hoy = timezone.now()
    meses_labels = []
    meses_data = []

    for i in range(5, -1, -1):
        mes_ref = hoy - timedelta(days=30 * i)
        inicio_mes = mes_ref.replace(
            day=1,
            hour=0,
            minute=0,
            second=0,
            microsecond=0
        )

        if inicio_mes.month == 12:
            fin_mes = inicio_mes.replace(
                year=inicio_mes.year + 1,
                month=1
            )

        else:
            fin_mes = inicio_mes.replace(month=inicio_mes.month + 1)

        cantidad = User.objects.filter(
            date_joined__gte=inicio_mes,
            date_joined__lt=fin_mes
        ).count()

        meses_labels.append(inicio_mes.strftime('%b'))
        meses_data.append(cantidad)

    # ---------- Paginación ----------
    paginator = Paginator(usuarios_qs, 8)
    pagina = request.GET.get('page')
    usuarios_pagina = paginator.get_page(pagina)

    # ---------- Tendencia de registros (usa meses_data ya calculado arriba) ----------
    nuevos_este_mes = meses_data[-1] if meses_data else 0
    nuevos_mes_anterior = meses_data[-2] if len(meses_data) > 1 else 0
    diferencia_mes = nuevos_este_mes - nuevos_mes_anterior

    # ---------- Contexto ----------
    context = {
        'usuarios': usuarios_pagina,
        'filtro_rol': filtro_rol,
        'total_usuarios': total_usuarios,
        'total_empleados': total_empleados,
        'usuarios_activos': usuarios_activos,
        'usuarios_inactivos': usuarios_inactivos,
        'top_compradores': top_compradores,
        'nuevos_este_mes': nuevos_este_mes,
        'diferencia_mes': diferencia_mes,

        # Para ApexCharts
        'meses_labels': json.dumps(meses_labels),
        'meses_data': json.dumps(meses_data),
    }

    return render(request,'usuarios.html',context)


# -----------------------------
# API DE ESTADÍSTICAS DE USUARIOS
# -----------------------------

@login_required
def api_estadisticas_usuarios(request):
    """
    Endpoint JSON con las estadísticas de usuarios:
    - total de usuarios
    - usuarios activos / inactivos
    - top usuarios que más han comprado

    GET /api/estadisticas-usuarios/
    GET /api/estadisticas-usuarios/?top=10  (para cambiar el límite del ranking)
    """
    total_usuarios = User.objects.count()
    usuarios_activos = User.objects.filter(is_active=True).count()
    usuarios_inactivos = User.objects.filter(is_active=False).count()

    try:
        limite_top = int(request.GET.get('top', 5))
    except (TypeError, ValueError):
        limite_top = 5
    limite_top = max(1, min(limite_top, 50))  # tope de seguridad

    top_compradores_qs = _top_compradores(limite=limite_top)
    top_compradores = [
        {
            'id': u.id,
            'username': u.username,
            'email': u.email,
            'total_compras': u.total_compras,
        }
        for u in top_compradores_qs
    ]

    data = {
        'total_usuarios': total_usuarios,
        'usuarios_activos': usuarios_activos,
        'usuarios_inactivos': usuarios_inactivos,
        'top_compradores': top_compradores,
    }

    return JsonResponse(data)