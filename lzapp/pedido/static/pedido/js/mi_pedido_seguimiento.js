document.addEventListener('DOMContentLoaded', function () {
    const CENTRO_DEFECTO = [6.2442, -75.5812]; // Medellín

    // Orden real del ciclo: la producción arranca con el pago, y
    // "pendiente" es la espera POSTERIOR (ya preparado, sin repartidor
    // libre todavía), no el primer paso.
    const ORDEN_ESTADOS = ['preparando', 'pendiente', 'en_camino', 'entregado'];

    const cajaMapa = document.getElementById('mapaSeguimiento');
    if (!cajaMapa) return;

    // El botón "salir" vive arriba a la izquierda (mismo lugar que el
    // botón de cerrar del mapa de "elegir ubicación de entrega"), la
    // tarjeta de estado abajo al centro y la fila abajo a la izquierda,
    // así que el zoom se queda arriba a la derecha -- la esquina libre.
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

    const TEXTO_ESTADO = {
        preparando: 'Preparando tu pedido',
        pendiente: 'Listo — esperando repartidor',
        en_camino: 'En camino hacia ti',
        entregado: 'Entregado',
        cancelado: 'Pedido cancelado',
    };

    function actualizarEstadoTexto(estado, pedidosAntes) {
        const texto = document.getElementById('mpsEstadoTexto');
        if (!texto) return;

        let etiqueta = TEXTO_ESTADO[estado] || estado;
        if (estado === 'en_camino' && pedidosAntes > 0) {
            etiqueta += ` · ${pedidosAntes} antes de ti`;
        }
        texto.textContent = etiqueta;
    }

    // ---- Chips de arriba: tiempo, distancia, repartidor, incidencia ----
    function mostrarChip(id, visible, texto) {
        const chip = document.getElementById(id);
        if (!chip) return;
        chip.hidden = !visible;
        if (visible && texto !== undefined) {
            chip.querySelector('span').textContent = texto;
        }
    }

    // ---- Fila de entrega (abajo a la izquierda) ----
    // El cliente no ve datos de los pedidos ajenos (ni debe): solo cuántas
    // paradas van antes de la suya y en qué puesto queda.
    function actualizarCola(pedido) {
        const cola = document.getElementById('mpsCola');
        const lista = document.getElementById('mpsColaLista');
        if (!cola || !lista) return;

        const puesto = pedido.orden_en_ruta;
        if (pedido.estado !== 'en_camino' || !puesto) {
            cola.hidden = true;
            return;
        }

        const items = [];
        for (let i = 1; i < puesto; i++) {
            items.push(`
                <li class="mps-cola-item">
                    <span class="mps-cola-punto">${i}</span>
                    <span>Otra entrega</span>
                </li>`);
        }
        items.push(`
            <li class="mps-cola-item tuyo">
                <span class="mps-cola-punto">${puesto}</span>
                <span>Tu pedido</span>
            </li>`);

        lista.innerHTML = items.join('');
        cola.hidden = false;
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

            // Si el pedido ya no viene, se conserva en pantalla lo último
            // que sí se supo: nada de recargar la página encima del cliente.
            if (!pedido) return;
            huboDatosAlgunaVez = true;

            actualizarTimeline(pedido.estado);
            actualizarEstadoTexto(pedido.estado, pedido.pedidos_antes);
            actualizarCola(pedido);

            if (pedido.estado === 'preparando') {
                mostrarModalPreparacion(datos.minutos_preparacion);
            }

            // ---- PIN de entrega (dentro de la tarjeta de estado) ----
            const bloqueCodigo = document.getElementById('mpsCodigo');
            if (bloqueCodigo) {
                const mostrar = Boolean(pedido.codigo_entrega) && pedido.estado === 'en_camino';
                if (mostrar) {
                    document.getElementById('mpsCodigoValor').textContent =
                        pedido.codigo_entrega.split('').join(' ');
                }
                bloqueCodigo.hidden = !mostrar;
            }

            // ---- Chips de arriba: tiempo y distancia ya vienen calculados ----
            mostrarChip('mpsChipTiempo', Boolean(pedido.tiempo_estimado_min),
                        `${pedido.tiempo_estimado_min} min`);
            mostrarChip('mpsChipDistancia', Boolean(pedido.distancia_km),
                        `${pedido.distancia_km} km`);
            mostrarChip('mpsInfoRepartidor', Boolean(pedido.repartidor), pedido.repartidor);
            mostrarChip('mpsIncidencia', Boolean(pedido.incidencia), pedido.incidencia);

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
