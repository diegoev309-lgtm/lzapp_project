let mapa, marcador, autocomplete;

function initMapaUbicacion() {
    // Se llama automáticamente cuando carga la API de Google Maps
    // 1. Crear mapa centrado en Medellín por defecto
    // 2. Crear marcador arrastrable
    // 3. Conectar autocompletado al #buscador-direccion
    // 4. Listener de arrastre del marcador -> actualizarCamposOcultos()
}

function usarUbicacionGPS() {
    // navigator.geolocation.getCurrentPosition()
    // -> mover mapa y marcador a esa posición
    // -> actualizarCamposOcultos()
}

function actualizarCamposOcultos(lat, lng, direccion) {
    document.getElementById('cliente_latitud').value = lat;
    document.getElementById('cliente_longitud').value = lng;
    document.getElementById('cliente_direccion').value = direccion || '';
}

document.getElementById('btn-usar-gps').addEventListener('click', usarUbicacionGPS);