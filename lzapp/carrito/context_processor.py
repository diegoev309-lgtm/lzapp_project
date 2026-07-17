def totalizar_carro(request):
    total = 0
    carro = request.session.get("carro", {})
    for key, value in carro.items():
        total += float(value["precio"]) * value["cantidad"]
    return {"totalizar_carro": total}