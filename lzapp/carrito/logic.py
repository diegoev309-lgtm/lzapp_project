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
            if producto.stock_actual < 1:
                return {"ok": False, "error": f'"{producto.nombre}" está agotado.'}

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
            return {"ok": True}

        if item_existente and item_existente.get("es_premio"):
            # Ya es un premio reclamado: el "+" normal del widget no debe
            # sumarle más unidades (el descuento aplica a una sola).
            return {"ok": False, "error": "Este producto ya está en tu carrito como premio."}

        cantidad_actual = item_existente["cantidad"] if item_existente else 0

        # No dejamos que la cantidad en el carrito supere el stock real,
        # sin importar cuántas veces le den al botón "+".
        if cantidad_actual + 1 > producto.stock_actual:
            return {
                "ok": False,
                "error": f'Solo hay {producto.stock_actual} unidades disponibles de "{producto.nombre}".',
            }

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
        return {"ok": True}
    
    def guardar_carro(self):
        self.session["carro"]=self.carro
        self.session.modified=True
    
    # eliminar/restar trabajan con el id y no con el objeto Producto: si el
    # producto se borró del catálogo mientras estaba en el carrito de
    # alguien, esa persona tiene que poder sacarlo igual. Buscándolo en la
    # base primero, la fila quedaba pegada y sin forma de quitarla.
    def eliminar_por_id(self, producto_id):
        producto_id = str(producto_id)
        if producto_id in self.carro:
            del self.carro[producto_id]
            self.guardar_carro()

    def restar_por_id(self, producto_id):
        producto_id = str(producto_id)
        item = self.carro.get(producto_id)
        if not item:
            return

        item["cantidad"] -= 1
        if item["cantidad"] < 1:
            self.eliminar_por_id(producto_id)
            return
        self.guardar_carro()

    def eliminar(self, producto):
        self.eliminar_por_id(producto.id)

    def restar(self, producto):
        self.restar_por_id(producto.id)

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