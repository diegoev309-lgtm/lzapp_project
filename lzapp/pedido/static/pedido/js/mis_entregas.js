/* Panel del repartidor: mapa + consola (entrega actual, cola, incidencias,
 * turno). Las URLs llegan como constantes desde la plantilla. */

document.addEventListener('DOMContentLoaded', function () {

    const CENTRO_DEFECTO = [6.2442, -75.5812]; // Medellín
    const CLAVE_CACHE = 'lz_entregas_cache';

    function getCookie(nombre) {
        let valor = null;
        if (document.cookie && document.cookie !== '') {
            document.cookie.split(';').forEach((cookie) => {
                cookie = cookie.trim();
                if (cookie.substring(0, nombre.length + 1) === (nombre + '=')) {
                    valor = decodeURIComponent(cookie.substring(nombre.length + 1));
                }
            });
        }
        return valor;
    }

    function postear(url, datos) {
        return fetch(url, {
            method: 'POST',
            headers: {
                'X-CSRFToken': getCookie('csrftoken'),
                'Content-Type': 'application/x-www-form-urlencoded',
            },
            body: new URLSearchParams(datos).toString(),
        });
    }

    const escapar = (t) => String(t ?? '').replace(/[&<>"']/g,
        (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));

    // ---------------------------------------------------------------
    // Mapa
    // ---------------------------------------------------------------
    const mapa = L.map('mapaEntregas', { zoomControl: false }).setView(CENTRO_DEFECTO, 13);
    L.control.zoom({ position: 'topleft' }).addTo(mapa);
    L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
        attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>',
        maxZoom: 19,
    }).addTo(mapa);

    const capaEntregas = L.layerGroup().addTo(mapa);
    let marcadorPropio = null;
    const marcadoresPorPedido = {};

    // El encuadre automático se apaga apenas el repartidor toca el mapa.
    // Antes el polling llamaba fitBounds cada 10 s, así que cualquier
    // arrastre se devolvía solo y el mapa parecía trabado.
    let encuadreAutomatico = true;
    let moviendoPorCodigo = false;

    mapa.on('dragstart', () => { encuadreAutomatico = false; });
    mapa.on('zoomstart', () => { if (!moviendoPorCodigo) encuadreAutomatico = false; });

    function encuadrar(puntos) {
        if (!puntos.length) return;
        moviendoPorCodigo = true;
        mapa.fitBounds(puntos, { padding: [50, 50], maxZoom: 15 });
        setTimeout(() => { moviendoPorCodigo = false; }, 500);
    }

    function irA(lat, lng, zoom = 16) {
        moviendoPorCodigo = true;
        mapa.setView([lat, lng], zoom, { animate: true });
        setTimeout(() => { moviendoPorCodigo = false; }, 500);
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

            shift = 0; resultado = 0;
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

    // Línea recta, solo para ordenar/filtrar por cercanía. La ruta real
    // la calcula el servidor con OSRM.
    function distanciaKm(lat1, lng1, lat2, lng2) {
        const R = 6371, rad = (g) => g * Math.PI / 180;
        const dLat = rad(lat2 - lat1), dLng = rad(lng2 - lng1);
        const a = Math.sin(dLat / 2) ** 2 +
                  Math.cos(rad(lat1)) * Math.cos(rad(lat2)) * Math.sin(dLng / 2) ** 2;
        return R * 2 * Math.asin(Math.sqrt(a));
    }

    // ---------------------------------------------------------------
    // Consola: pestañas y plegado
    // ---------------------------------------------------------------
    const consola = document.getElementById('consola');
    const consolaAbrir = document.getElementById('consolaAbrir');

    document.querySelectorAll('.consola-tab').forEach((tab) => {
        tab.addEventListener('click', () => activarPestana(tab.dataset.tab));
    });

    function activarPestana(nombre) {
        document.querySelectorAll('.consola-tab').forEach((t) =>
            t.classList.toggle('activa', t.dataset.tab === nombre));
        document.querySelectorAll('.consola-panel').forEach((p) =>
            p.classList.toggle('activo', p.dataset.panel === nombre));
        consola.hidden = false;
        consolaAbrir.hidden = true;
    }

    function plegarConsola(plegar) {
        consola.hidden = plegar;
        consolaAbrir.hidden = !plegar;
    }

    consolaAbrir.addEventListener('click', () => plegarConsola(false));

    // ---- La manija se arrastra de verdad ----
    // Arrastrar hacia abajo pliega, hacia arriba abre. Mientras se
    // arrastra el panel sigue el dedo, y si el gesto queda a medias vuelve
    // a su sitio en vez de quedarse trabado.
    const agarre = document.getElementById('consolaAgarre');
    const UMBRAL_PLEGAR = 60;   // px que hay que bajar para que se pliegue
    let arrastreY = null;
    let desplazado = 0;

    agarre.addEventListener('pointerdown', (e) => {
        arrastreY = e.clientY;
        desplazado = 0;
        consola.style.transition = 'none';
        agarre.setPointerCapture(e.pointerId);
    });

    agarre.addEventListener('pointermove', (e) => {
        if (arrastreY === null) return;
        // Solo hacia abajo: hacia arriba el panel ya está en su tope.
        desplazado = Math.max(0, e.clientY - arrastreY);
        consola.style.transform = `translateY(${desplazado}px)`;
    });

    function terminarArrastre(e) {
        if (arrastreY === null) return;
        if (e && e.pointerId !== undefined && agarre.hasPointerCapture(e.pointerId)) {
            agarre.releasePointerCapture(e.pointerId);
        }
        arrastreY = null;

        consola.style.transition = 'transform .2s ease';
        consola.style.transform = '';

        // Un arrastre corto cuenta como toque: también pliega.
        plegarConsola(desplazado > UMBRAL_PLEGAR || desplazado < 4);
        desplazado = 0;
    }

    agarre.addEventListener('pointerup', terminarArrastre);
    agarre.addEventListener('pointercancel', terminarArrastre);

    // Accesible desde el teclado, ya que visualmente es un control.
    agarre.addEventListener('keydown', (e) => {
        if (e.key === 'Enter' || e.key === ' ') {
            e.preventDefault();
            plegarConsola(true);
        }
    });

    // ---------------------------------------------------------------
    // Botones del mapa
    // ---------------------------------------------------------------
    const wrap = document.getElementById('mapaEntregasWrap');
    const btnExpandir = document.getElementById('btnExpandirMapaEntregas');
    let expandido = false;

    btnExpandir.addEventListener('click', () => {
        expandido = !expandido;
        wrap.classList.toggle('expandido', expandido);
        btnExpandir.querySelector('i').className = expandido
            ? 'bi bi-fullscreen-exit' : 'bi bi-arrows-fullscreen';
        btnExpandir.title = expandido ? 'Ver mapa normal' : 'Ver mapa completo';
        setTimeout(() => mapa.invalidateSize(), 320);
    });

    document.addEventListener('keydown', (e) => {
        if (e.key === 'Escape' && expandido) btnExpandir.click();
    });

    document.getElementById('btnRecentrar').addEventListener('click', () => {
        encuadreAutomatico = true;
        encuadrar(puntosDeLaRuta());
    });

    // Buscar el pedido más cercano a donde estoy ahora.
    document.getElementById('btnCercano').addEventListener('click', () => {
        const cercano = pedidoMasCercano();
        if (!cercano) {
            alert(marcadorPropio
                ? 'No hay entregas con ubicación para comparar.'
                : 'Primero empieza a repartir para que sepamos dónde estás.');
            return;
        }
        encuadreAutomatico = false;
        irA(cercano.cliente_latitud, cercano.cliente_longitud);
        const marcador = marcadoresPorPedido[cercano.pedido_id];
        if (marcador) marcador.openPopup();
        activarPestana('cola');
    });

    function pedidoMasCercano() {
        if (!marcadorPropio) return null;
        const yo = marcadorPropio.getLatLng();
        return ultimosPedidos
            .filter((p) => p.cliente_latitud && p.cliente_longitud)
            .map((p) => ({ p, d: distanciaKm(yo.lat, yo.lng, p.cliente_latitud, p.cliente_longitud) }))
            .sort((a, b) => a.d - b.d)
            .map((x) => x.p)[0] || null;
    }

    function puntosDeLaRuta() {
        const puntos = ultimosPedidos
            .filter((p) => p.cliente_latitud && p.cliente_longitud)
            .map((p) => [p.cliente_latitud, p.cliente_longitud]);
        if (marcadorPropio) puntos.push(marcadorPropio.getLatLng());
        return puntos;
    }

    // ---------------------------------------------------------------
    // Turno y ubicación
    // ---------------------------------------------------------------
    const btnTurno = document.getElementById('btnCompartirUbicacion');
    const punto = document.getElementById('puntoEstado');
    const textoEstado = document.getElementById('textoEstadoUbicacion');
    let watchId = null;

    btnTurno.addEventListener('click', () => {
        if (watchId === null) iniciarTurno(); else terminarTurno();
    });

    async function iniciarTurno() {
        if (!navigator.geolocation) {
            textoEstado.textContent = 'Tu navegador no soporta geolocalización.';
            return;
        }

        btnTurno.disabled = true;
        try {
            const respuesta = await postear(URL_TURNO, { activo: 1 });
            const datos = await respuesta.json();
            if (datos.entregas_asignadas) {
                textoEstado.textContent = `Te asignaron ${datos.entregas_asignadas} entrega(s)`;
            }
        } catch (e) {
            textoEstado.textContent = 'No se pudo iniciar el turno. Revisa tu conexión.';
            btnTurno.disabled = false;
            return;
        }
        btnTurno.disabled = false;

        watchId = navigator.geolocation.watchPosition(
            (posicion) => {
                enviarUbicacion(posicion.coords.latitude, posicion.coords.longitude);
                punto.classList.add('activo');
                textoEstado.textContent = 'Repartiendo — el cliente ve dónde vas';
            },
            () => { textoEstado.textContent = 'No se pudo obtener tu ubicación.'; },
            { enableHighAccuracy: true, maximumAge: 10000 }
        );

        btnTurno.classList.add('compartiendo');
        btnTurno.innerHTML = '<i class="bi bi-stop-circle"></i> Terminar turno';
        cargarEntregas();
    }

    async function terminarTurno() {
        if (watchId !== null) {
            navigator.geolocation.clearWatch(watchId);
            watchId = null;
        }
        try { await postear(URL_TURNO, { activo: 0 }); } catch (e) { /* sin señal */ }

        btnTurno.classList.remove('compartiendo');
        btnTurno.innerHTML = '<i class="bi bi-scooter"></i> Empezar a repartir las entregas';
        punto.classList.remove('activo');
        textoEstado.textContent = 'Fuera de turno — no te llegarán entregas nuevas';
    }

    function enviarUbicacion(lat, lng) {
        postear(URL_UBICACION, { latitud: lat, longitud: lng }).catch(() => {});
        if (!marcadorPropio) {
            marcadorPropio = L.marker([lat, lng], { icon: crearIconoYo() })
                .bindPopup('Mi ubicación').addTo(mapa);
        } else {
            marcadorPropio.setLatLng([lat, lng]);
        }
    }

    // ---------------------------------------------------------------
    // Vehículo
    // ---------------------------------------------------------------
    const ICONO_VEHICULO = {
        moto: 'bi-scooter', bicicleta: 'bi-bicycle', carro: 'bi-car-front-fill', a_pie: 'bi-person-walking',
    };

    // El vehículo se registra en su propio módulo del dashboard
    // (pedido/mi-vehiculo). Acá solo se muestra el que está guardado.

    function actualizarTurno(info) {
        if (!info) return;

        document.getElementById('cargaBarra').hidden = false;
        document.getElementById('cargaTexto').textContent =
            `${info.carga_actual} / ${info.capacidad_productos} unidades`;

        const porcentaje = info.capacidad_productos
            ? Math.min((info.carga_actual / info.capacidad_productos) * 100, 100) : 0;
        const relleno = document.getElementById('cargaRelleno');
        relleno.style.width = `${porcentaje}%`;
        relleno.classList.toggle('lleno', porcentaje >= 100);

        document.getElementById('vehiculoActual').textContent = info.vehiculo_display;
        document.getElementById('capacidadActual').textContent = info.capacidad_productos;
        document.getElementById('iconoVehiculo').className =
            'bi ' + (ICONO_VEHICULO[info.vehiculo] || 'bi-truck');

        // Si el turno quedó abierto y la página se recargó, el botón tiene
        // que reflejar el estado real del servidor, no el de la pantalla.
        if (info.disponible && watchId === null) {
            btnTurno.classList.add('compartiendo');
            btnTurno.innerHTML = '<i class="bi bi-stop-circle"></i> Terminar turno';
            punto.classList.add('activo');
            textoEstado.textContent = 'En turno — activa el GPS para que te vean';
        }
    }

    // ---------------------------------------------------------------
    // Entrega actual
    // ---------------------------------------------------------------
    function filaProducto(pr) {
        const foto = pr.imagen
            ? `<img class="ea-foto" src="${escapar(pr.imagen)}" alt="${escapar(pr.nombre)}">`
            : `<div class="ea-foto ea-foto-vacia"><i class="bi bi-box"></i></div>`;
        return `
            <div class="ea-producto">
                ${foto}
                <span class="ea-producto-nombre">${escapar(pr.nombre)}</span>
                <span class="ea-producto-cant">×${pr.cantidad}</span>
            </div>`;
    }

    function pintarEntregaActual(pedidos) {
        const caja = document.getElementById('entregaActual');
        const actual = pedidos.find((p) => p.estado === 'en_camino' && p.orden_en_ruta === 1)
                    || pedidos.find((p) => p.estado === 'en_camino');

        if (!actual) {
            caja.innerHTML = '<p class="consola-vacio">No tienes ninguna entrega en curso.</p>';
            return;
        }

        const datos = [];
        if (actual.distancia_km) datos.push(`<span class="ea-dato">${actual.distancia_km} km</span>`);
        if (actual.tiempo_estimado_min) datos.push(`<span class="ea-dato">${actual.tiempo_estimado_min} min</span>`);
        if (actual.incidencia) datos.push(`<span class="ea-dato alerta">⚠ ${escapar(actual.incidencia)}</span>`);

        caja.innerHTML = `
            <div class="ea-cabecera">
                <span class="ea-puesto">${actual.orden_en_ruta || 1}</span>
                <div class="ea-titulo">
                    <strong>#${actual.pedido_id} — ${escapar(actual.cliente)}</strong>
                    <small>${escapar(actual.direccion_entrega || 'Sin dirección registrada')}</small>
                </div>
            </div>
            <div class="ea-productos">
                ${(actual.productos || []).map(filaProducto).join('')
                  || '<p class="consola-vacio">Sin detalle de productos.</p>'}
            </div>
            ${datos.length ? `<div class="ea-datos">${datos.join('')}</div>` : ''}
            <div class="ea-pin-nota">
                <i class="bi bi-shield-lock"></i>
                La entrega no se cierra hasta que el cliente te dé su PIN.
            </div>
            <div class="ea-acciones">
                <input type="text" inputmode="numeric" maxlength="4" placeholder="PIN"
                       class="ea-pin" id="pinActual">
                <button type="button" class="ea-btn entregar" id="btnEntregar">
                    <i class="bi bi-check-circle-fill"></i> Entregar
                </button>
                <button type="button" class="ea-btn ir" id="btnIrAlPunto" title="Ver en el mapa">
                    <i class="bi bi-geo-alt-fill"></i>
                </button>
            </div>
            <div class="ea-aviso" id="avisoEntrega"></div>`;

        document.getElementById('btnEntregar')
            .addEventListener('click', () => confirmarEntrega(actual.pedido_id));
        document.getElementById('btnIrAlPunto').addEventListener('click', () => {
            if (!actual.cliente_latitud) return;
            encuadreAutomatico = false;
            irA(actual.cliente_latitud, actual.cliente_longitud);
        });
    }

    async function confirmarEntrega(pedidoId) {
        const pin = document.getElementById('pinActual');
        const aviso = document.getElementById('avisoEntrega');
        const boton = document.getElementById('btnEntregar');

        aviso.className = 'ea-aviso';
        if ((pin.value || '').trim().length !== 4) {
            aviso.textContent = 'Pídele al cliente su PIN de 4 dígitos.';
            aviso.className = 'ea-aviso error visible';
            return;
        }

        boton.disabled = true;
        try {
            const url = URL_CONFIRMAR_BASE.replace('/0/', '/' + pedidoId + '/');
            const respuesta = await postear(url, { codigo: pin.value.trim() });
            const datos = await respuesta.json();

            if (!respuesta.ok) {
                aviso.textContent = datos.error || 'No se pudo confirmar.';
                aviso.className = 'ea-aviso error visible';
                return;
            }
            aviso.textContent = 'Entrega confirmada.';
            aviso.className = 'ea-aviso ok visible';
            cargarEntregas();
        } catch (e) {
            aviso.textContent = navigator.onLine
                ? 'No se pudo confirmar.' : 'Sin conexión: intenta cuando tengas señal.';
            aviso.className = 'ea-aviso error visible';
        } finally {
            boton.disabled = false;
        }
    }

    // ---------------------------------------------------------------
    // Cola de clientes
    // ---------------------------------------------------------------
    const inputBuscar = document.getElementById('buscarEntrega');
    const chkCercanos = document.getElementById('chkCercanos');
    const radioCercanos = document.getElementById('radioCercanos');

    inputBuscar.addEventListener('input', () => pintar(ultimosPedidos));
    chkCercanos.addEventListener('change', () => pintar(ultimosPedidos));
    radioCercanos.addEventListener('input', () => {
        document.getElementById('radioTexto').textContent = `${radioCercanos.value} km`;
        if (chkCercanos.checked) pintar(ultimosPedidos);
    });

    function aplicarFiltros(pedidos) {
        const texto = inputBuscar.value.trim().toLowerCase();
        let lista = pedidos.filter((p) =>
            !texto || p.cliente.toLowerCase().includes(texto) || String(p.pedido_id).includes(texto));

        if (chkCercanos.checked && marcadorPropio) {
            const yo = marcadorPropio.getLatLng();
            const limite = parseFloat(radioCercanos.value);
            lista = lista.filter((p) => p.cliente_latitud && p.cliente_longitud &&
                distanciaKm(yo.lat, yo.lng, p.cliente_latitud, p.cliente_longitud) <= limite);
        }
        return lista;
    }

    function pintarCola(pedidos) {
        const lista = document.getElementById('entregasLista');
        const vacio = document.getElementById('entregasSinResultados');

        document.getElementById('contadorCola').textContent = pedidos.length;
        document.getElementById('contadorCola').dataset.cero = pedidos.length ? '0' : '1';

        if (!pedidos.length) {
            lista.innerHTML = '';
            vacio.hidden = false;
            return;
        }
        vacio.hidden = true;

        lista.innerHTML = pedidos.map((p) => {
            const proxima = p.orden_en_ruta === 1;
            const chips = (p.productos || [])
                .map((pr) => `<span class="cola-chip${proxima ? '' : ' gris'}">${pr.cantidad} × ${escapar(pr.nombre)}</span>`)
                .join('') || '<span class="cola-chip gris">Sin detalle</span>';
            const detalle = [
                p.distancia_km ? `${p.distancia_km} km` : null,
                p.tiempo_estimado_min ? `${p.tiempo_estimado_min} min` : null,
            ].filter(Boolean).join(' · ');

            return `
                <div class="cola-item${proxima ? ' proxima' : ''}" data-pedido-id="${p.pedido_id}">
                    <div class="cola-item-cabecera">
                        <span class="cola-puesto">${p.orden_en_ruta || '·'}</span>
                        <span class="cola-cliente">#${p.pedido_id} — ${escapar(p.cliente)}</span>
                    </div>
                    <div class="cola-dir">${escapar(p.direccion_entrega || 'Sin dirección')}${detalle ? ' · ' + detalle : ''}</div>
                    <div class="cola-chips">${chips}</div>
                </div>`;
        }).join('');

        // Tocar una entrega de la lista la centra en el mapa.
        lista.querySelectorAll('.cola-item').forEach((item) => {
            item.addEventListener('click', () => {
                const pedido = pedidos.find((p) => String(p.pedido_id) === item.dataset.pedidoId);
                if (!pedido || !pedido.cliente_latitud) return;
                encuadreAutomatico = false;
                irA(pedido.cliente_latitud, pedido.cliente_longitud);
                const marcador = marcadoresPorPedido[pedido.pedido_id];
                if (marcador) marcador.openPopup();
            });
        });
    }

    // ---------------------------------------------------------------
    // Incidencias
    // ---------------------------------------------------------------
    function pintarIncidencias(pedidos) {
        const lista = document.getElementById('incidenciasLista');

        if (!pedidos.length) {
            lista.innerHTML = '<p class="consola-vacio">No tienes entregas activas para reportar.</p>';
            return;
        }

        const enCurso = {};
        lista.querySelectorAll('.incidencia-texto').forEach((i) => { enCurso[i.dataset.pedidoId] = i.value; });

        lista.innerHTML = pedidos.map((p) => `
            <div class="incidencia-card">
                <div class="incidencia-card-titulo">#${p.pedido_id} — ${escapar(p.cliente)}</div>
                <div class="incidencia-card-dir">${escapar(p.direccion_entrega || 'Sin dirección registrada')}</div>
                ${p.incidencia ? `
                    <div class="incidencia-actual">
                        <i class="bi bi-exclamation-triangle-fill"></i>
                        <span>Reportado: ${escapar(p.incidencia)}${p.minutos_extra_incidencia ? ` (+${p.minutos_extra_incidencia} min)` : ''}</span>
                    </div>` : ''}
                <div class="incidencia-campos">
                    <input type="text" class="incidencia-texto" maxlength="255" data-pedido-id="${p.pedido_id}"
                           placeholder="¿Qué pasó? Ej: trancón en la 80"
                           value="${escapar(enCurso[p.pedido_id] ?? (p.incidencia || ''))}">
                    <div class="incidencia-fila">
                        <input type="number" class="incidencia-minutos" min="0" max="600" step="1"
                               data-pedido-id="${p.pedido_id}" placeholder="Demora (min)"
                               value="${p.minutos_extra_incidencia || 0}">
                        <button type="button" data-pedido-id="${p.pedido_id}">
                            <i class="bi bi-send-fill"></i> Reportar
                        </button>
                    </div>
                </div>
                <div class="incidencia-aviso" id="avisoIncidencia${p.pedido_id}"></div>
            </div>`).join('');

        lista.querySelectorAll('.incidencia-fila button').forEach((boton) => {
            boton.addEventListener('click', () => reportarIncidencia(boton.dataset.pedidoId, boton));
        });
    }

    async function reportarIncidencia(pedidoId, boton) {
        const texto = document.querySelector(`.incidencia-texto[data-pedido-id="${pedidoId}"]`);
        const minutos = document.querySelector(`.incidencia-minutos[data-pedido-id="${pedidoId}"]`);
        const aviso = document.getElementById(`avisoIncidencia${pedidoId}`);

        aviso.className = 'incidencia-aviso';
        boton.disabled = true;

        try {
            const url = URL_INCIDENCIA_BASE.replace('/0/', '/' + pedidoId + '/');
            const respuesta = await postear(url, {
                incidencia: texto.value,
                minutos_extra: minutos.value || 0,
            });
            const datos = await respuesta.json();

            if (!respuesta.ok) {
                aviso.textContent = datos.error || 'No se pudo reportar.';
                aviso.className = 'incidencia-aviso error visible';
                return;
            }
            aviso.textContent = 'Reportado. Al cliente ya le llegó el aviso.';
            aviso.className = 'incidencia-aviso ok visible';
            cargarEntregas();
        } catch (e) {
            aviso.textContent = navigator.onLine
                ? 'No se pudo reportar.' : 'Sin conexión: intenta cuando tengas señal.';
            aviso.className = 'incidencia-aviso error visible';
        } finally {
            boton.disabled = false;
        }
    }

    // ---------------------------------------------------------------
    // Pintado general
    // ---------------------------------------------------------------
    let ultimosPedidos = [];

    function pintar(todos) {
        ultimosPedidos = todos;
        const visibles = aplicarFiltros(todos);

        pintarEntregaActual(todos);
        pintarCola(visibles);
        pintarIncidencias(todos);

        const conUbicacion = visibles.filter((p) => p.cliente_latitud && p.cliente_longitud);
        const vacio = document.getElementById('mapaEntregasVacio');

        capaEntregas.clearLayers();
        Object.keys(marcadoresPorPedido).forEach((k) => delete marcadoresPorPedido[k]);

        if (!conUbicacion.length) {
            vacio.classList.add('visible');
            mapa.invalidateSize();
            return;
        }
        vacio.classList.remove('visible');

        conUbicacion.forEach((p) => {
            // Todas las paradas, no solo la primera: la que sigue a color
            // y el resto en gris, para ver la jornada completa.
            const proxima = p.orden_en_ruta === 1;
            const productos = (p.productos || [])
                .map((pr) => `${pr.cantidad} × ${escapar(pr.nombre)}`).join('<br>') || 'Sin detalle';

            const marcador = L.marker([p.cliente_latitud, p.cliente_longitud], {
                icon: crearIconoDestino({ numero: p.orden_en_ruta, atenuado: !proxima }),
                zIndexOffset: proxima ? 500 : 0,
            }).bindPopup(
                `<b>#${p.pedido_id} — ${escapar(p.cliente)}</b><br>` +
                `${escapar(p.direccion_entrega || 'Destino de entrega')}<br><br>` +
                `<b>Lleva:</b><br>${productos}<br><br>` +
                (proxima ? '<i>Tu próxima parada</i>' : `<i>Parada #${p.orden_en_ruta} — aún no toca</i>`)
            );
            capaEntregas.addLayer(marcador);
            marcadoresPorPedido[p.pedido_id] = marcador;

            if (p.ruta_polyline && proxima) {
                L.polyline(decodificarPolyline(p.ruta_polyline),
                    { color: '#8b5cf6', weight: 4, opacity: 0.7 }).addTo(capaEntregas);
            }
        });

        mapa.invalidateSize();
        if (encuadreAutomatico) encuadrar(puntosDeLaRuta());
    }

    async function cargarEntregas() {
        try {
            const respuesta = await fetch(URL_ENTREGAS);
            const datos = await respuesta.json();
            const todos = datos.pedidos || [];

            try {
                localStorage.setItem(CLAVE_CACHE, JSON.stringify(todos));
            } catch (e) { /* storage lleno o bloqueado */ }

            actualizarTurno(datos.repartidor);
            pintar(todos);
        } catch (error) {
            // Sin señal se deja lo que ya estaba en pantalla, que es justo
            // lo que el repartidor necesita en la calle.
            marcarConexion();
            console.error('Error cargando entregas:', error);
        }
    }

    // ---------------------------------------------------------------
    // Sin conexión
    // ---------------------------------------------------------------
    function marcarConexion() {
        document.getElementById('avisoOffline').hidden = navigator.onLine;
    }
    window.addEventListener('online', () => { marcarConexion(); cargarEntregas(); });
    window.addEventListener('offline', marcarConexion);
    marcarConexion();

    if ('serviceWorker' in navigator) {
        navigator.serviceWorker.register(URL_SW).catch(() => {
            // Sin service worker el panel funciona igual, solo que el mapa
            // no se ve offline.
        });
    }

    // Arranca con lo último guardado: si abre la app sin señal, ve sus
    // entregas en vez de una pantalla vacía.
    try {
        const guardado = localStorage.getItem(CLAVE_CACHE);
        if (guardado) pintar(JSON.parse(guardado));
    } catch (e) { /* caché corrupto */ }

    cargarEntregas();
    setInterval(cargarEntregas, 10000);
});
