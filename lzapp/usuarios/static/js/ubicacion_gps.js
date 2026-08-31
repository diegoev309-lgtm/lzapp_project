document.addEventListener('DOMContentLoaded', function () {
    // Saca el modal de cualquier contenedor con transform/overflow que lo
    // atrape (ej. .perfil-wrapper en Configuración) y lo pone directo en <body>.
    const modalUbicacion = document.getElementById('modalUbicacionEntrega');
    if (modalUbicacion && modalUbicacion.parentElement !== document.body) {
        document.body.appendChild(modalUbicacion);
    }

    const btnGps = document.getElementById('btn-usar-gps');
    const btnConfirmar = document.getElementById('btnConfirmarUbicacion');
    const btnTrigger = document.getElementById('btnAbrirUbicacion');
    const textoTrigger = document.getElementById('textoUbicacionTrigger');
    const estado = document.getElementById('estado-ubicacion');
    const inputBuscar = document.getElementById('buscador-direccion');
    const sugerenciasBox = document.getElementById('sugerenciasDireccion');

    if (!btnGps) return;

    let mapa, marcador, mapaInicializado = false;
    const CENTRO_DEFECTO = [6.2442, -75.5812]; // Medellín

    // El mapa de Leaflet necesita que su contenedor sea visible para medir
    // bien el tamaño — como está dentro de un modal oculto, lo inicializamos
    // justo cuando el modal se abre por primera vez.
    modalUbicacion.addEventListener('shown.bs.modal', function () {
        if (!mapaInicializado) {
            inicializarMapa();
            mapaInicializado = true;
        }
        mapa.invalidateSize();
    });

    function inicializarMapa() {
        mapa = L.map('mapa-ubicacion').setView(CENTRO_DEFECTO, 13);

        L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
            attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>',
            maxZoom: 19,
        }).addTo(mapa);

        marcador = L.marker(CENTRO_DEFECTO, { draggable: true }).addTo(mapa);

        marcador.on('dragend', function () {
            const pos = marcador.getLatLng();
            fijarUbicacion(pos.lat, pos.lng);
        });

        mapa.on('click', function (e) {
            marcador.setLatLng(e.latlng);
            fijarUbicacion(e.latlng.lat, e.latlng.lng);
        });
    }

    function fijarUbicacion(lat, lng) {
        document.getElementById('cliente_latitud').value = lat;
        document.getElementById('cliente_longitud').value = lng;
        mostrarEstado('Ubicación seleccionada en el mapa', 'text-success');
        btnConfirmar.disabled = false;
    }

    // ---------- GPS ----------
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

                if (mapa) {
                    mapa.setView([lat, lng], 16);
                    marcador.setLatLng([lat, lng]);
                }

                fijarUbicacion(lat, lng);
                mostrarEstado(`Ubicación capturada (precisión: ${Math.round(posicion.coords.accuracy)}m)`, 'text-success');
            },
            function (error) {
                let mensaje = 'No se pudo obtener tu ubicación.';
                if (error.code === error.PERMISSION_DENIED) mensaje = 'Permiso de ubicación denegado.';
                else if (error.code === error.POSITION_UNAVAILABLE) mensaje = 'Ubicación no disponible en este momento.';
                else if (error.code === error.TIMEOUT) mensaje = 'Se agotó el tiempo. Intenta de nuevo.';
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

    // ---------- Buscador de direcciones (Nominatim) ----------
    let temporizadorBusqueda = null;

    if (inputBuscar) {
        inputBuscar.addEventListener('input', function () {
            clearTimeout(temporizadorBusqueda);
            const texto = this.value.trim();

            if (texto.length < 4) {
                sugerenciasBox.innerHTML = '';
                sugerenciasBox.classList.remove('activo');
                return;
            }

            // Esperamos 500ms sin que el usuario escriba más, para no saturar
            // el servidor gratuito de Nominatim (pide máx. 1 petición/seg).
            temporizadorBusqueda = setTimeout(() => buscarDireccion(texto), 500);
        });
    }

    async function buscarDireccion(texto) {
        try {
            const url = `https://nominatim.openstreetmap.org/search?format=json&q=${encodeURIComponent(texto)}&countrycodes=co&limit=5`;
            const respuesta = await fetch(url, { headers: { 'Accept-Language': 'es' } });
            const resultados = await respuesta.json();

            if (resultados.length === 0) {
                sugerenciasBox.innerHTML = '<div class="ubicacion-sugerencia-vacia">Sin resultados</div>';
                sugerenciasBox.classList.add('activo');
                return;
            }

            sugerenciasBox.innerHTML = resultados.map(r => `
                <div class="ubicacion-sugerencia-item" data-lat="${r.lat}" data-lon="${r.lon}">
                    <i class="bi bi-geo-alt"></i> ${r.display_name}
                </div>
            `).join('');
            sugerenciasBox.classList.add('activo');

            sugerenciasBox.querySelectorAll('.ubicacion-sugerencia-item').forEach((item) => {
                item.addEventListener('click', function () {
                    const lat = parseFloat(this.dataset.lat);
                    const lon = parseFloat(this.dataset.lon);

                    if (mapa) {
                        mapa.setView([lat, lon], 16);
                        marcador.setLatLng([lat, lon]);
                    }
                    fijarUbicacion(lat, lon);

                    inputBuscar.value = this.textContent.trim();
                    sugerenciasBox.innerHTML = '';
                    sugerenciasBox.classList.remove('activo');
                });
            });

        } catch (error) {
            console.error('Error buscando dirección:', error);
        }
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