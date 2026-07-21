from django.shortcuts import render
from dashboard.models import Producto, Descuento, ReglaDescuentoAutomatico
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.views.decorators.http import require_POST
from .forms import DescuentoManualForm, ReglaDescuentoAutomaticoForm


def listar_descuentos(request):
    query = request.GET.get('q', '')
    productos = Producto.objects.filter(disponibilidad=True).prefetch_related('descuentos')
    if query:
        productos = productos.filter(nombre__icontains=query)

    reglas = ReglaDescuentoAutomatico.objects.all().order_by('-prioridad')

    return render(request, 'listdes.html', {
        'productos': productos,
        'reglas': reglas,
        'query': query,
    })


def aplicar_descuento(request, producto_id):
    producto = get_object_or_404(Producto, id=producto_id)
    if request.method == 'POST':
        form = DescuentoManualForm(request.POST)
        if form.is_valid():
            producto.descuentos.filter(activo=True).update(activo=False)
            descuento = form.save(commit=False)
            descuento.producto = producto
            descuento.origen = 'manual'
            descuento.save()
            messages.success(request, f'Descuento aplicado a "{producto.nombre}".')
            return redirect('listar_descuentos')
    else:
        form = DescuentoManualForm()
    return render(request, 'formdes.html', {'form': form, 'producto': producto})


def quitar_descuento(request, descuento_id):
    descuento = get_object_or_404(Descuento, id=descuento_id)
    if request.method == 'POST':
        descuento.activo = False
        descuento.save()
        messages.success(request, 'Descuento desactivado.')
        return redirect('listar_descuentos')
    return render(request, 'deletedes.html', {'descuento': descuento})


def toggle_regla_descuento(request, regla_id):
    regla = get_object_or_404(ReglaDescuentoAutomatico, id=regla_id)
    regla.activa = not regla.activa
    regla.save()
    return redirect('listar_descuentos')


def crear_regla_descuento(request):
    if request.method == 'POST':
        form = ReglaDescuentoAutomaticoForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'Regla automática creada.')
            return redirect('listar_descuentos')
    else:
        form = ReglaDescuentoAutomaticoForm()
    return render(request, 'createdes.html', {'form': form})

def editar_regla_descuento(request, regla_id):
    regla = get_object_or_404(ReglaDescuentoAutomatico, id=regla_id)
    if request.method == 'POST':
        form = ReglaDescuentoAutomaticoForm(request.POST, instance=regla)
        if form.is_valid():
            form.save()
            messages.success(request, f'Regla "{regla.nombre}" actualizada.')
            return redirect('listar_descuentos')
    else:
        form = ReglaDescuentoAutomaticoForm(instance=regla)
    return render(request, 'editdes.html', {'form': form, 'regla': regla})


def eliminar_regla_descuento(request, regla_id):
    regla = get_object_or_404(ReglaDescuentoAutomatico, id=regla_id)
    if request.method == 'POST':
        regla.delete()
        messages.success(request, 'Regla eliminada.')
        return redirect('listar_descuentos')
    return render(request, 'deleterdes.html', {'regla': regla})