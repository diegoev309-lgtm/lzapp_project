from django.shortcuts import render, redirect, get_object_or_404
from django.core.paginator import Paginator
from produccion.models import Produccion
from produccion.forms import ProduccionForm


def listar_producciones(request):
    lista_producciones = Produccion.objects.all().order_by("-id")
    paginator = Paginator(lista_producciones, 6)
    page = request.GET.get("page")
    producciones = paginator.get_page(page)

    return render(request, "listpc.html", {"producciones": producciones})


def crear_produccion(request):
    if request.method == 'POST':
        form = ProduccionForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect('listar_producciones')
    else:
        form = ProduccionForm()

    return render(request, 'formpc.html',{'form': form})