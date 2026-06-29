from django.shortcuts import render, redirect, get_object_or_404
from produccion.models import Produccion
from produccion.forms import ProduccionForm


def listar_producciones(request):
    producciones = Produccion.objects.select_related('producto').all()
    return render(request, 'listpc.html',
                  {'producciones': producciones})


def crear_produccion(request):
    if request.method == 'POST':
        form = ProduccionForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect('listar_producciones')
    else:
        form = ProduccionForm()

    return render(request, 'formpc.html',{'form': form})