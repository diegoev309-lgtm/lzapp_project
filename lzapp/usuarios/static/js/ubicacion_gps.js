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
    const btnExpandirMapa = document.getElementById('btn-expandir-mapa');
    const mapaBox = document.getElementById('mapa-ubicacion');

    if (!btnGps) return;

    let mapa, marcador, mapaInicializado = false;
    const CENTRO_DEFECTO = [6.2442, -75.5812]; // Medellín

    const latGuardada = document.getElementById('cliente_latitud').value;
    const lngGuardada = document.getElementById('cliente_longitud').value;
    const tieneUbicacionGuardada = Boolean(latGuardada && lngGuardada);

    // Si el cliente ya registró su ubicación (en el registro o en su
    // perfil), el botón ofrece editarla en vez de pedirla de cero.
    if (tieneUbicacionGuardada) {
        marcarTriggerComoListo();
        if (btnConfirmar) btnConfirmar.disabled = false;
    }

    function marcarTriggerComoListo() {
        if (!btnTrigger || !textoTrigger) return;
        textoTrigger.textContent = 'Editar ubicación de entrega';
        btnTrigger.classList.add('ubicacion-lista');
        btnTrigger.querySelector('i').className = 'bi bi-pencil-square';
    }

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
        // Si ya hay ubicación guardada, el mapa abre ahí en vez de en el
        // centro de Medellín, para que se vea qué está por editar.
        const centro = tieneUbicacionGuardada
            ? [parseFloat(latGuardada), parseFloat(lngGuardada)]
            : CENTRO_DEFECTO;

        // El botón de expandir vive arriba a la derecha (o arriba a la
        // izquierda al maximizar); el control de zoom se pasa abajo a la
        // izquierda para no chocar con él.
        mapa = L.map('mapa-ubicacion', { zoomControl: false }).setView(centro, tieneUbicacionGuardada ? 16 : 13);
        L.control.zoom({ position: 'bottomleft' }).addTo(mapa);

        L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
            attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>',
            maxZoom: 19,
        }).addTo(mapa);

        marcador = L.marker(centro, { draggable: true }).addTo(mapa);

        marcador.on('dragend', function () {
            const pos = marcador.getLatLng();
            fijarUbicacion(pos.lat, pos.lng);
        });

        mapa.on('click', function (e) {
            marcador.setLatLng(e.latlng);
            fijarUbicacion(e.latlng.lat, e.latlng.lng);
        });
    }

    let temporizadorReversa = null;

    function fijarUbicacion(lat, lng, mensajeInicial) {
        document.getElementById('cliente_latitud').value = lat;
        document.getElementById('cliente_longitud').value = lng;
        mostrarEstado(mensajeInicial || 'Ubicación seleccionada, buscando dirección...', 'text-success');
        btnConfirmar.disabled = false;

        // Al arrastrar el marcador se dispara muchas veces seguidas; esperamos
        // a que el usuario suelte y deje de mover el mapa antes de consultar
        // Nominatim, para no saturar el servidor gratuito (máx. 1 petición/seg).
        clearTimeout(temporizadorReversa);
        temporizadorReversa = setTimeout(() => geocodificarInversa(lat, lng, mensajeInicial), 600);
    }

    async function geocodificarInversa(lat, lng, prefijo) {
        try {
            // Pasa por nuestro propio servidor en vez de llamar directo a
            // Nominatim: así el proveedor externo nunca ve la IP real del
            // cliente, solo la del servidor.
            const url = `/usuarios/api/geocodificar-inversa/?lat=${lat}&lng=${lng}`;
            const respuesta = await fetch(url);
            const resultado = await respuesta.json();

            const direccion = resultado.direccion;
            if (direccion) {
                const texto = prefijo ? `${prefijo} — ${direccion}` : direccion;
                mostrarEstado(texto, 'text-success');

                // Antes solo se mostraba, no se guardaba en ningún lado -- se
                // usa para que el pedido final tenga una dirección legible,
                // no solo coordenadas.
                const inputDireccion = document.getElementById('direccion_entrega_texto');
                if (inputDireccion) inputDireccion.value = direccion;
            }
        } catch (error) {
            // Si Nominatim falla, no es crítico: las coordenadas ya quedaron
            // guardadas en los inputs ocultos, solo no mostramos la dirección legible.
            console.error('Error en geocodificación inversa:', error);
        }
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

                const precision = `Ubicación capturada (precisión: ${Math.round(posicion.coords.accuracy)}m)`;
                fijarUbicacion(lat, lng, precision);
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

    // ---------- Expandir/minimizar mapa ----------
    let mapaExpandido = false;

    if (btnExpandirMapa) {
        btnExpandirMapa.addEventListener('click', function () {
            mapaExpandido = !mapaExpandido;
            mapaBox.classList.toggle('mapa-grande', mapaExpandido);
            modalUbicacion.classList.toggle('mapa-expandido', mapaExpandido);
            btnExpandirMapa.querySelector('i').className = mapaExpandido
                ? 'bi bi-fullscreen-exit'
                : 'bi bi-arrows-fullscreen';
            btnExpandirMapa.title = mapaExpandido ? 'Ver mapa normal' : 'Ver mapa completo';

            // Esperamos a que termine la transición de altura antes de que
            // Leaflet recalcule el tamaño de sus tiles, si no quedan a medio cargar.
            setTimeout(() => { if (mapa) mapa.invalidateSize(); }, 380);
        });
    }

    modalUbicacion.addEventListener('hidden.bs.modal', function () {
        if (mapaExpandido) {
            mapaExpandido = false;
            mapaBox.classList.remove('mapa-grande');
            modalUbicacion.classList.remove('mapa-expandido');
            btnExpandirMapa.querySelector('i').className = 'bi bi-arrows-fullscreen';
            btnExpandirMapa.title = 'Ver mapa completo';
        }
    });

    if (btnConfirmar) {
        btnConfirmar.addEventListener('click', function () {
            if (btnTrigger && textoTrigger) {
                // Ya hay ubicación: el botón pasa a ser "editar", no "agregar".
                textoTrigger.textContent = 'Editar ubicación de entrega';
                btnTrigger.classList.add('ubicacion-lista');
                btnTrigger.querySelector('i').className = 'bi bi-pencil-square';
            }
        });
    }
});