from django.shortcuts import render, redirect, get_object_or_404
from producto.models import Producto
from producto.forms import ProductoForm
from django.contrib import messages


def listar_productos(request):
    productos = Producto.objects.all()
    return render(request, "listpt.html", {"productos": productos})


def crear_producto(request):
    if request.method == "POST":
        form = ProductoForm(request.POST, request.FILES)
        if form.is_valid():
            form.save()
            return redirect('listar_productos')
    else:
        form = ProductoForm()

    return render(request, 'formpt.html', {'form': form})


def editar_producto(request, id):
    producto = get_object_or_404(Producto, id=id)

    if request.method == "POST":
        form = ProductoForm(
            request.POST,
            request.FILES,
            instance=producto
        )

        if form.is_valid():
            form.save()
            return redirect('listar_productos')
    else:
        form = ProductoForm(instance=producto)

    return render(request, 'formpt.html', {'form': form})


def eliminar_producto(request, id):
    producto = get_object_or_404(Producto, id=id)

    if request.method == "POST":
        producto.delete()
        return redirect('listar_productos')

    return render(request, "deletept.html", {"producto": producto})