document.addEventListener('DOMContentLoaded', function () {
    const CENTRO_DEFECTO = [6.2442, -75.5812]; // Medellín
    const ORDEN_ESTADOS = ['pendiente', 'preparando', 'en_camino', 'entregado'];

    const cajaMapa = document.getElementById('mapaSeguimiento');
    if (!cajaMapa) return;

    // El botón "salir" vive arriba a la izquierda y el badge de estado
    // arriba centrado — el control de zoom se pasa a la derecha para no
    // chocar con ninguno de los dos.
    const mapa = L.map('mapaSeguimiento', { zoomControl: false }).setView(CENTRO_DEFECTO, 13);
    L.control.zoom({ position: 'topright' }).addTo(mapa);
    L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
        attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>',
        maxZoom: 19,
    }).addTo(mapa);
    const capaMarcadores = L.layerGroup().addTo(mapa);

    function decodificarPolyline(codificada) {
        let index = 0, lat = 0, lng = 0;
        const coordenadas = [];
        while (index < codificada.length) {
            let shift = 0, resultado = 0, byte;
            do {
                byte = codificada.charCodeAt(index++) - 63;
                resultado |= (byte & 0x1f) << shift;
                shift += 5;
            } while (byte >= 0x20);
            lat += (resultado & 1) ? ~(resultado >> 1) : (resultado >> 1);

            shift = 0;
            resultado = 0;
            do {
                byte = codificada.charCodeAt(index++) - 63;
                resultado |= (byte & 0x1f) << shift;
                shift += 5;
            } while (byte >= 0x20);
            lng += (resultado & 1) ? ~(resultado >> 1) : (resultado >> 1);

            coordenadas.push([lat / 1e5, lng / 1e5]);
        }
        return coordenadas;
    }

    function actualizarTimeline(estado) {
        const pasos = document.querySelectorAll('#mpsTimeline .mps-paso');
        const lineas = document.querySelectorAll('#mpsTimeline .mps-linea');

        if (estado === 'cancelado') {
            pasos.forEach(p => p.classList.remove('completo', 'actual'));
            pasos[0].classList.add('cancelado');
            return;
        }

        const indiceActual = ORDEN_ESTADOS.indexOf(estado);
        pasos.forEach((paso, i) => {
            paso.classList.remove('completo', 'actual', 'cancelado');
            if (i < indiceActual) paso.classList.add('completo');
            else if (i === indiceActual) paso.classList.add('actual');
        });
        lineas.forEach((linea, i) => {
            linea.classList.toggle('completa', i < indiceActual);
        });
    }

    const TEXTO_BADGE = {
        pendiente: 'Confirmado',
        preparando: 'Preparando tu pedido',
        en_camino: 'En camino hacia ti',
        entregado: 'Entregado',
        cancelado: 'Cancelado',
    };
    const ICONO_BADGE = {
        pendiente: 'bi-check-lg',
        preparando: 'bi-egg-fried',
        en_camino: 'bi-scooter',
        entregado: 'bi-house-check-fill',
        cancelado: 'bi-x-circle-fill',
    };

    function actualizarBadge(estado) {
        const badge = document.getElementById('mpsBadgeEstado');
        if (!badge) return;
        badge.className = 'mps-badge-estado ' + estado;
        document.getElementById('mpsBadgeTexto').textContent = TEXTO_BADGE[estado] || estado;
        document.getElementById('mpsBadgeIcono').className = 'bi ' + (ICONO_BADGE[estado] || 'bi-info-circle-fill');
    }

    let huboDatosAlgunaVez = false;
    let modalPreparacionMostrado = false;

    const modalFondo = document.getElementById('mpsModalFondo');
    const btnCerrarModal = document.getElementById('mpsModalCerrar');
    if (btnCerrarModal) {
        btnCerrarModal.addEventListener('click', () => modalFondo.classList.remove('abierto'));
    }
    if (modalFondo) {
        modalFondo.addEventListener('click', (e) => {
            if (e.target === modalFondo) modalFondo.classList.remove('abierto');
        });
    }

    function mostrarModalPreparacion(minutos) {
        // Se muestra una sola vez por visita, apenas el pedido entra en
        // preparación: no tiene sentido interrumpir en cada refresco.
        if (modalPreparacionMostrado || !modalFondo) return;
        document.getElementById('mpsModalMinutos').textContent = minutos ?? '—';
        modalFondo.classList.add('abierto');
        modalPreparacionMostrado = true;
    }

    async function cargarSeguimiento() {
        try {
            const respuesta = await fetch(MPS_URL_TIEMPO_REAL);
            const datos = await respuesta.json();
            const pedido = (datos.pedidos || []).find(p => p.pedido_id === MPS_PEDIDO_ID);

            if (!pedido) {
                if (huboDatosAlgunaVez) {
                    // El pedido salió de la lista de "activos" (lo entregaron o
                    // lo cancelaron) — recargamos para mostrar el estado final.
                    window.location.reload();
                }
                return;
            }
            huboDatosAlgunaVez = true;

            actualizarTimeline(pedido.estado);
            actualizarBadge(pedido.estado);

            if (pedido.estado === 'preparando') {
                mostrarModalPreparacion(datos.minutos_preparacion);
            }

            const bloqueCodigo = document.getElementById('mpsCodigo');
            if (bloqueCodigo) {
                if (pedido.codigo_entrega && pedido.estado === 'en_camino') {
                    document.getElementById('mpsCodigoValor').textContent =
                        pedido.codigo_entrega.split('').join(' ');
                    bloqueCodigo.style.display = 'block';
                } else {
                    bloqueCodigo.style.display = 'none';
                }
            }

            const infoRepartidor = document.getElementById('mpsInfoRepartidor');
            const repartidorNombre = document.getElementById('mpsRepartidorNombre');
            if (pedido.repartidor) {
                repartidorNombre.textContent = pedido.repartidor;
                infoRepartidor.style.display = 'flex';
            } else {
                infoRepartidor.style.display = 'none';
            }

            const infoDistancia = document.getElementById('mpsInfoDistancia');
            const distanciaTexto = document.getElementById('mpsDistanciaTexto');
            if (pedido.distancia_km) {
                distanciaTexto.textContent = pedido.tiempo_estimado_min
                    ? `${pedido.distancia_km} km · ${pedido.tiempo_estimado_min} min`
                    : `${pedido.distancia_km} km`;
                infoDistancia.style.display = 'flex';
            } else {
                infoDistancia.style.display = 'none';
            }

            const avisoIncidencia = document.getElementById('mpsIncidencia');
            if (pedido.incidencia) {
                document.getElementById('mpsIncidenciaTexto').textContent = pedido.incidencia;
                avisoIncidencia.style.display = 'flex';
            } else {
                avisoIncidencia.style.display = 'none';
            }

            const vacio = document.getElementById('mapaSeguimientoVacio');
            capaMarcadores.clearLayers();

            // El mapa nunca se esconde (display:none le rompe la medida a
            // Leaflet); el aviso de "sin ubicación" flota encima con su
            // propia clase, tapándolo sin desmontarlo.
            if (!pedido.cliente_latitud || !pedido.cliente_longitud) {
                vacio.classList.add('visible');
                mapa.invalidateSize();
                return;
            }
            vacio.classList.remove('visible');

            const puntos = [];

            const marcadorCliente = L.marker([pedido.cliente_latitud, pedido.cliente_longitud], {
                icon: crearIconoDestino(),
            }).bindPopup('Tu dirección de entrega');
            capaMarcadores.addLayer(marcadorCliente);
            puntos.push([pedido.cliente_latitud, pedido.cliente_longitud]);

            if (pedido.repartidor_latitud && pedido.repartidor_longitud) {
                const detalle = pedido.distancia_km
                    ? `${pedido.distancia_km} km · ${pedido.tiempo_estimado_min ?? '—'} min restantes`
                    : 'En camino hacia ti';
                const marcadorRepartidor = L.marker([pedido.repartidor_latitud, pedido.repartidor_longitud], {
                    icon: crearIconoRepartidor(),
                }).bindPopup(`<b>${pedido.repartidor || 'Repartidor'}</b><br>${detalle}`);
                capaMarcadores.addLayer(marcadorRepartidor);
                puntos.push([pedido.repartidor_latitud, pedido.repartidor_longitud]);
            }

            if (pedido.ruta_polyline) {
                const trazado = decodificarPolyline(pedido.ruta_polyline);
                L.polyline(trazado, { color: '#8b5cf6', weight: 4, opacity: 0.7 }).addTo(capaMarcadores);
            }

            mapa.invalidateSize();
            if (puntos.length > 0) {
                mapa.fitBounds(puntos, { padding: [40, 40], maxZoom: 15 });
            }
        } catch (error) {
            console.error('Error cargando seguimiento del pedido:', error);
        }
    }

    cargarSeguimiento();
    setInterval(cargarSeguimiento, 10000);
});
