from django.shortcuts import render, redirect, get_object_or_404
from django.core.paginator import Paginator
from producto.models import Producto
from producto.forms import ProductoForm
from django.contrib import messages
from django.db.models import F



def listar_productos(request):
    lista_producto = Producto.objects.all().order_by("-id")
    productos_bajo_stock = Producto.objects.filter(stock_actual__lt=F('stock_minimo'))
    paginator = Paginator(lista_producto, 6)
    page = request.GET.get("page")
    productos = paginator.get_page(page)

    return render(request, "listpt.html", {"productos": productos,"productos_bajo_stock": productos_bajo_stock,})


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