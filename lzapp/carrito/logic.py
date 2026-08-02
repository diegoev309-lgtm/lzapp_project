from django.utils import timezone

class Carro:
    def __init__(self,request):
        self.request=request
        self.session=request.session
        carro=self.session.get("carro")

        if not carro:
            carro=self.session["carro"]={}

        self.carro=carro

    def agregar(self, producto, premio=None):
        producto_id = str(producto.id)
        item_existente = self.carro.get(producto_id)

        if premio:
            # Reclamar premio: SIEMPRE deja 1 sola unidad con el precio
            # de descuento, sin importar si ya había cantidad acumulada.
            # El botón "+" normal (sin premio) no debe volver a pasar
            # por aquí para este mismo producto (ver bloque de abajo).
            self.carro[producto_id] = {
                "producto_id": producto_id,
                "nombre": producto.nombre,
                "precio": str(premio.precio_con_descuento),
                "precio_original": str(premio.precio_original),
                "cantidad": 1,
                "imagen": producto.imagen.url if producto.imagen else "",
                "es_premio": True,
                "codigo_premio": premio.codigo,
            }
            self.guardar_carro()
            return

        if item_existente and item_existente.get("es_premio"):
            # Ya es un premio reclamado: el "+" normal del widget no debe
            # sumarle más unidades (el descuento aplica a una sola).
            return

        if not item_existente:
            self.carro[producto_id]={
                "producto_id":producto_id,
                "nombre":producto.nombre,
                "precio":str(producto.precio),
                "cantidad":1,
                "imagen":producto.imagen.url if producto.imagen else ""
            }
        else:
            item_existente["cantidad"] += 1
        self.guardar_carro()
    
    def guardar_carro(self):
        self.session["carro"]=self.carro
        self.session.modified=True
    
    def eliminar(self,producto):
        producto_id=str(producto.id)
        if producto_id in self.carro:
            del self.carro[producto_id]
            self.guardar_carro()

    def restar(self,producto):
        for key,value in self.carro.items():
            if key==str(producto.id):
                value["cantidad"]=value["cantidad"]-1
                if value["cantidad"]<1:
                    self.eliminar(producto)
                break
        self.guardar_carro()

    def limpiar_carro(self):
        self.session["carro"]={}
        self.session.modified=True

def limpiar_premios_invalidos_del_carrito(request):
    """
    Revisa cada ítem del carrito marcado como premio (es_premio=True) y
    lo elimina si el DescuentoAsignado correspondiente ya no es válido
    (usado, vencido, o no le pertenece al usuario actual). Se llama en
    cada carga de la página del carrito para no dejar precios de
    descuento "flotando" en la sesión indefinidamente.
    """
    from dashboard.models import DescuentoAsignado  # import local: evita ciclo de imports
    carro = request.session.get('carro', {})
    cambiado = False
    for pid in list(carro.keys()):
        item = carro[pid]
        if item.get('es_premio'):
            valido = False
            if request.user.is_authenticated:
                valido = DescuentoAsignado.objects.filter(
                    codigo=item.get('codigo_premio'),
                    usuario=request.user,
                    usado=False,
                    fecha_expiracion__gte=timezone.now(),
                ).exists()
            if not valido:
                del carro[pid]
                cambiado = True
    if cambiado:
        request.session['carro'] = carro
        request.session.modified = True

def premio_ya_en_carrito(request, codigo):
    """
    True si este código de premio ya fue reclamado y está en el carrito
    actual. Se usa para NO repetir la animación/tarjeta de "ganaste" en
    el home si el usuario ya le dio clic a "Reclamar premio".
    """
    if not codigo:
        return False
    carro = request.session.get('carro', {})
    return any(
        item.get('es_premio') and item.get('codigo_premio') == codigo
        for item in carro.values()
    )