def totalizar_carro(request):
    total = 0
    carro = request.session.get("carro", {})
    for key, value in carro.items():
        total += float(value["precio"]) * value["cantidad"]
    return {"totalizar_carro": total}

# carrito/context_processors.py
from django.conf import settings

def mercadopago_public_key(request):
    return {"MP_PUBLIC_KEY": settings.MERCADOPAGO_PUBLIC_KEY}