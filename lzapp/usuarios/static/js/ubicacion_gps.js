document.addEventListener('DOMContentLoaded', function () {
    const btnConfirmar = document.getElementById('btnConfirmarUbicacion');
    const btnTrigger = document.getElementById('btnAbrirUbicacion');
    const textoTrigger = document.getElementById('textoUbicacionTrigger');
    const estado = document.getElementById('estado-ubicacion');
    const modalUbicacion = document.getElementById('modalUbicacionEntrega');
    if (modalUbicacion && modalUbicacion.parentElement !== document.body) {
        document.body.appendChild(modalUbicacion);
    }

    const btnGps = document.getElementById('btn-usar-gps');

    if (!btnGps) return;

    btnGps.addEventListener('click', usarUbicacionGPS);

    function usarUbicacionGPS() {
        if (!navigator.geolocation) {
            mostrarEstado('Tu navegador no soporta geolocalización.', 'text-danger');
            return;
        }

        mostrarEstado('Obteniendo ubicación...', '');

        navigator.geolocation.getCurrentPosition(
            function (posicion) {
                const lat = posicion.coords.latitude;
                const lng = posicion.coords.longitude;

                document.getElementById('cliente_latitud').value = lat;
                document.getElementById('cliente_longitud').value = lng;

                mostrarEstado(`Ubicación capturada (precisión: ${Math.round(posicion.coords.accuracy)}m)`, 'text-success');
                btnConfirmar.disabled = false;
            },
            function (error) {
                let mensaje = 'No se pudo obtener tu ubicación.';
                if (error.code === error.PERMISSION_DENIED) {
                    mensaje = 'Permiso de ubicación denegado.';
                } else if (error.code === error.POSITION_UNAVAILABLE) {
                    mensaje = 'Ubicación no disponible en este momento.';
                } else if (error.code === error.TIMEOUT) {
                    mensaje = 'Se agotó el tiempo. Intenta de nuevo.';
                }
                mostrarEstado(mensaje, 'text-danger');
            },
            { enableHighAccuracy: true, timeout: 10000 }
        );
    }

    function mostrarEstado(mensaje, clase) {
        estado.textContent = mensaje;
        estado.classList.remove('text-success', 'text-danger');
        if (clase) estado.classList.add(clase);
    }

    if (btnConfirmar) {
        btnConfirmar.addEventListener('click', function () {
            if (btnTrigger && textoTrigger) {
                textoTrigger.textContent = 'Ubicación de entrega guardada';
                btnTrigger.classList.add('ubicacion-lista');
                btnTrigger.querySelector('i').className = 'bi bi-check-circle-fill';
            }
        });
    }
});