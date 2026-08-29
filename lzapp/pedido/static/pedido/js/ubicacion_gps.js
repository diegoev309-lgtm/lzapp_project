document.getElementById('btn-usar-gps').addEventListener('click', usarUbicacionGPS);

function usarUbicacionGPS() {
    const estado = document.getElementById('estado-ubicacion');

    if (!navigator.geolocation) {
        estado.textContent = 'Tu navegador no soporta geolocalización. Escribe la dirección manualmente.';
        estado.classList.add('text-danger');
        return;
    }

    estado.textContent = 'Obteniendo ubicación...';
    estado.classList.remove('text-danger', 'text-success');

    navigator.geolocation.getCurrentPosition(
        function (posicion) {
            const lat = posicion.coords.latitude;
            const lng = posicion.coords.longitude;

            document.getElementById('cliente_latitud').value = lat;
            document.getElementById('cliente_longitud').value = lng;

            estado.textContent = `Ubicación capturada (precisión: ${Math.round(posicion.coords.accuracy)}m)`;
            estado.classList.add('text-success');

            // Cuando ya tengamos el mapa de Google, aquí centramos el marcador en lat/lng
        },
        function (error) {
            let mensaje = 'No se pudo obtener tu ubicación.';
            if (error.code === error.PERMISSION_DENIED) {
                mensaje = 'Permiso de ubicación denegado. Puedes escribir tu dirección manualmente.';
            } else if (error.code === error.POSITION_UNAVAILABLE) {
                mensaje = 'Ubicación no disponible en este momento.';
            } else if (error.code === error.TIMEOUT) {
                mensaje = 'Se agotó el tiempo esperando la ubicación. Intenta de nuevo.';
            }
            estado.textContent = mensaje;
            estado.classList.add('text-danger');
        },
        { enableHighAccuracy: true, timeout: 10000 }
    );
}