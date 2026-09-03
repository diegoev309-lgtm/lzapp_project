document.addEventListener('DOMContentLoaded', function () {
    const CENTRO_DEFECTO = [6.2442, -75.5812]; // Medellín
    const ORDEN_ESTADOS = ['pendiente', 'preparando', 'en_camino', 'entregado'];

    const cajaMapa = document.getElementById('mapaSeguimiento');
    if (!cajaMapa) return;

    const mapa = L.map('mapaSeguimiento').setView(CENTRO_DEFECTO, 13);
    L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
        attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>',
        maxZoom: 19,
    }).addTo(mapa);
    const capaMarcadores = L.layerGroup().addTo(mapa);

    function iconoEmoji(emoji) {
        return L.divIcon({
            html: `<span style="font-size:24px; line-height:1;">${emoji}</span>`,
            className: '',
            iconSize: [26, 26],
            iconAnchor: [13, 13],
        });
    }

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

    let huboDatosAlgunaVez = false;

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

            const vacio = document.getElementById('mapaSeguimientoVacio');
            capaMarcadores.clearLayers();

            if (!pedido.cliente_latitud || !pedido.cliente_longitud) {
                cajaMapa.style.display = 'none';
                vacio.style.display = 'block';
                return;
            }
            cajaMapa.style.display = 'block';
            vacio.style.display = 'none';

            const puntos = [];

            const marcadorCliente = L.marker([pedido.cliente_latitud, pedido.cliente_longitud], {
                icon: iconoEmoji('📍'),
            }).bindPopup('Tu dirección de entrega');
            capaMarcadores.addLayer(marcadorCliente);
            puntos.push([pedido.cliente_latitud, pedido.cliente_longitud]);

            if (pedido.repartidor_latitud && pedido.repartidor_longitud) {
                const detalle = pedido.distancia_km
                    ? `${pedido.distancia_km} km · ${pedido.tiempo_estimado_min ?? '—'} min restantes`
                    : 'En camino hacia ti';
                const marcadorRepartidor = L.marker([pedido.repartidor_latitud, pedido.repartidor_longitud], {
                    icon: iconoEmoji('🚚'),
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
