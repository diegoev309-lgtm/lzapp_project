
class Carro:
    def __init__(self,request):
        self.request=request
        self.session=request.session
        carro=self.session.get("carro")

        if not carro:
            carro=self.session["carro"]={}

        self.carro=carro

    def agregar(self,producto):
        producto_id=str(producto.id)
        if producto_id not in self.carro:
            self.carro[producto_id]={
                "producto_id":producto_id,
                "nombre":producto.nombre,
                "precio":str(producto.precio),
                "cantidad":1,
                "imagen":producto.imagen.url
            }
        else:
            self.carro[producto_id]["cantidad"]+=1
        self.guardar_carro()
    
    def guardar_carro(self):
        self.session["carro"]=self.carro
        self.session.modified=True
    
    def eliminar(self,producto):
        producto.id=str(producto.id)
        if producto.id in self.carro:
            del self.carro[producto.id]
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
