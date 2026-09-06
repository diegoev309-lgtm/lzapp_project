/* ============================================================
   ORQUESTA LA CARGA Y LAS ANIMACIONES DEL DASHBOARD

   Tres trabajos:
     1. Quitar el velo de carga apenas la página es usable.
     2. Escalonar la entrada de los bloques de cada módulo.
     3. Dar señal inmediata al navegar entre módulos (barra + desvanecido),
        que es lo que hace que la espera del servidor no se sienta muerta.
   ============================================================ */
(function () {
    'use strict';

    const sinMovimiento = window.matchMedia('(prefers-reduced-motion: reduce)').matches;

    // ------------------------------------------------------------
    // 1. Velo de carga
    //
    // Solo en el arranque en frío. Al navegar entre módulos el velo
    // sobraba: se veía pasar la barra de progreso, DESPUÉS aparecía el
    // spinner y recién ahí el contenido. Dos esperas encadenadas para una
    // sola navegación, que es exactamente lo que hacía sentir lento algo
    // que en realidad ya había cargado. Dentro de la sesión el CSS y las
    // fuentes ya están en caché, así que no hay nada que tapar: basta la
    // barra de arriba y la entrada escalonada.
    // ------------------------------------------------------------
    const velo = document.getElementById('cargaVelo');
    const CLAVE_VISITADO = 'lzapp-dash-visitado';

    let yaVisitado = false;
    try {
        yaVisitado = sessionStorage.getItem(CLAVE_VISITADO) === '1';
        sessionStorage.setItem(CLAVE_VISITADO, '1');
    } catch (e) { /* modo privado o storage bloqueado: se usa el velo */ }

    function quitarVelo(inmediato) {
        if (!velo || velo.classList.contains('oculto')) return;
        if (inmediato) velo.style.transition = 'none';
        velo.classList.add('oculto');
        // Se saca del DOM al terminar la transición: dejarlo puesto,
        // aunque sea invisible, se come los clics de toda la página si
        // algo falla con pointer-events.
        setTimeout(() => velo.remove(), inmediato ? 0 : 400);
        animarEntradas();
    }

    if (yaVisitado) {
        // Navegación dentro de la sesión: nada de spinner.
        quitarVelo(true);
    } else {
        // 'load' espera a imágenes y fuentes, que es cuando la página deja
        // de moverse de verdad. El tope es por si un recurso externo (un
        // CDN caído, una imagen rota) nunca resuelve: el velo no puede
        // quedarse tapando la aplicación para siempre.
        window.addEventListener('load', () => quitarVelo(false));
        setTimeout(() => quitarVelo(false), 3500);
    }

    // Por si el script diferido llega después de 'load' (pasa con el CSS
    // ya en caché): sin esto el velo se quedaría puesto.
    if (document.readyState === 'complete') quitarVelo(yaVisitado);

    // ------------------------------------------------------------
    // 2. Entrada escalonada de los bloques del módulo
    // ------------------------------------------------------------
    // Se apunta a los contenedores de primer nivel de cada página, no a
    // todo: animar cientos de nodos cuesta más de lo que aporta.
    const SELECTOR_BLOQUES = [
        '.dash-header',
        '.pedidos-stats > *',
        '.sugerencias-zona > *',
        '.productos-toolbar',
        '.contenedor-productos',
        '.mv-grid > *',
        '.dash-card',
        '.panel-seccion',
        '.bloque-productos',
        '.aviso-offline',
        '.mapa-entregas-wrap',
    ].join(',');

    function animarEntradas() {
        if (sinMovimiento) return;

        const bloques = document.querySelectorAll(SELECTOR_BLOQUES);
        let i = 0;
        bloques.forEach((bloque) => {
            if (bloque.dataset.animado) return;
            bloque.dataset.animado = '1';
            bloque.style.setProperty('--i', i++);
            bloque.classList.add('anim-entrada');
        });

        animarFilas(document);
    }

    // Las filas de tabla se pintan por JS en varios módulos, así que esto
    // se expone para volver a llamarlo cuando se repinta una tabla.
    function animarFilas(raiz) {
        if (sinMovimiento) return;
        const filas = raiz.querySelectorAll('.tabla-productos tbody tr:not([data-animado])');
        let i = 0;
        filas.forEach((fila) => {
            fila.dataset.animado = '1';
            fila.style.setProperty('--i', i++);
            fila.classList.add('anim-fila');
        });
    }

    // Si el contenido llega después (tablas que se pintan por fetch), un
    // observador se encarga sin que cada módulo tenga que avisar.
    const observador = new MutationObserver(() => animarFilas(document));
    document.addEventListener('DOMContentLoaded', () => {
        const cuerpos = document.querySelectorAll('.tabla-productos tbody');
        cuerpos.forEach((cuerpo) => observador.observe(cuerpo, { childList: true }));
    });

    // ------------------------------------------------------------
    // 3. Navegación entre módulos
    // ------------------------------------------------------------
    const barra = document.getElementById('cargaBarra');
    let avance = 0;
    let temporizador = null;

    function arrancarBarra() {
        if (!barra) return;
        avance = 0;
        barra.classList.add('activa');
        barra.style.width = '0';

        clearInterval(temporizador);
        temporizador = setInterval(() => {
            // Se acerca al 90% cada vez más lento y nunca lo pasa: el
            // 100% lo pone la página nueva al cargar. Una barra que llega
            // al final y se queda ahí es peor que no tener barra.
            avance += (90 - avance) * 0.12;
            barra.style.width = avance + '%';
        }, 180);
    }

    function detenerBarra() {
        if (!barra) return;
        clearInterval(temporizador);
        barra.style.width = '100%';
        setTimeout(() => {
            barra.classList.remove('activa');
            barra.style.width = '0';
        }, 300);
    }

    // Cualquier enlace interno que cambie de página dispara la señal.
    document.addEventListener('click', (e) => {
        const enlace = e.target.closest('a[href]');
        if (!enlace) return;

        const href = enlace.getAttribute('href');
        if (!href || href.startsWith('#') || href.startsWith('javascript:')) return;
        if (enlace.target === '_blank' || enlace.hasAttribute('download')) return;
        if (enlace.origin && enlace.origin !== window.location.origin) return;
        if (e.metaKey || e.ctrlKey || e.shiftKey) return;   // abrir en otra pestaña

        arrancarBarra();
        if (sinMovimiento) return;

        document.body.classList.add('saliendo');

        // Si lo que se tocó es un módulo del menú, ese icono se marca de
        // una: el usuario ve a dónde va antes de que el servidor conteste.
        const item = enlace.closest('.dash-nav-item');
        if (item) {
            document.querySelectorAll('.dash-nav-item.eligiendo')
                .forEach((n) => n.classList.remove('eligiendo'));
            item.classList.add('eligiendo');
        }
    });

    // Al volver con la flecha atrás la página puede restaurarse desde el
    // caché: hay que limpiar la señal de "saliendo" o queda medio borrosa.
    window.addEventListener('pageshow', () => {
        document.body.classList.remove('saliendo');
        detenerBarra();
    });

    // ------------------------------------------------------------
    // Utilidades para los módulos
    // ------------------------------------------------------------
    function animarNumero(elemento, valorFinal, duracion = 600) {
        if (!elemento) return;
        const inicio = parseFloat(elemento.textContent.replace(/[^\d.-]/g, '')) || 0;
        const destino = Number(valorFinal) || 0;

        if (sinMovimiento || inicio === destino) {
            elemento.textContent = destino;
            return;
        }

        const t0 = performance.now();
        function paso(ahora) {
            const avance = Math.min((ahora - t0) / duracion, 1);
            // easeOutCubic: arranca rápido y frena al final, que es como
            // se lee natural un contador.
            const suave = 1 - Math.pow(1 - avance, 3);
            elemento.textContent = Math.round(inicio + (destino - inicio) * suave);
            if (avance < 1) requestAnimationFrame(paso);
        }
        requestAnimationFrame(paso);
    }

    window.LzAnim = {
        animarNumero,
        animarFilas,
        animarEntradas,
        barra: { arrancar: arrancarBarra, detener: detenerBarra },
    };
})();
