/* ---- Navbar scroll effect ---- */
        const nav = document.getElementById('mainNav');
        window.addEventListener('scroll', () => {
            nav.classList.toggle('scrolled', window.scrollY > 60);
        });

        /* ---- Parallax 3D con el mouse en el hero ---- */
(function () {
    const hero = document.querySelector('#inicio .hero');
    if (!hero || window.matchMedia('(prefers-reduced-motion: reduce)').matches) return;

    // FIX: no activar el parallax de mouse en móvil/pantallas táctiles.
    const esTactilOMovil = window.matchMedia('(max-width: 991px)').matches ||
                            window.matchMedia('(pointer: coarse)').matches;
    if (esTactilOMovil) return;

    const capas = hero.querySelectorAll('[data-depth]');
    let raf = null;
    let targetX = 0, targetY = 0, curX = 0, curY = 0;

    hero.addEventListener('mousemove', (e) => {
        const r = hero.getBoundingClientRect();
        targetX = ((e.clientX - r.left) / r.width - 0.5) * 2;
        targetY = ((e.clientY - r.top) / r.height - 0.5) * 2;
        if (!raf) raf = requestAnimationFrame(animar);
    });

    hero.addEventListener('mouseleave', () => {
        targetX = 0; targetY = 0;
        if (!raf) raf = requestAnimationFrame(animar);
    });

    function animar() {
        curX += (targetX - curX) * 0.08;
        curY += (targetY - curY) * 0.08;

        capas.forEach((el) => {
            const d = parseFloat(el.dataset.depth) || 0.3;
            const x = -curX * d * 32;
            const y = -curY * d * 32;
            el.style.transform = `translate3d(${x}px, ${y}px, 0)`;
        });

        if (Math.abs(targetX - curX) > 0.001 || Math.abs(targetY - curY) > 0.001) {
            raf = requestAnimationFrame(animar);
        } else {
            raf = null;
        }
    }
})();
        /* ---- Carrusel del hero ---- */
        (function () {
            const DURACION_AUTOPLAY = 6000; // ms entre cada slide automático
            const ESPERA_INACTIVIDAD = 6000; // ms sin interactuar antes de reanudar
            const track = document.getElementById('carruselTrack');
            const prevBtn = document.getElementById('carruselPrev');
            const nextBtn = document.getElementById('carruselNext');
            const puntos = document.querySelectorAll('.carrusel-punto');
            const progreso = document.getElementById('carruselProgreso');
            if (!track) return;

            const slides = track.querySelectorAll('.carrusel-slide');
            const total = slides.length;
            let actual = 0;
            let autoplayTimer = null;
            let progresoTimeout = null;
            let bloqueoInteraccion = false;
            let inactividadTimer = null;

            function irA(indice) {
                bloqueoInteraccion = false;
                clearTimeout(inactividadTimer);

                actual = (indice + total) % total;
                slides.forEach((s, i) => s.classList.toggle('activo', i === actual));
                puntos.forEach((p, i) => p.classList.toggle('activo', i === actual));
                reiniciarAutoplay();
            }

            function siguiente() { irA(actual + 1); }
            function anterior() { irA(actual - 1); }

            function reiniciarProgreso() {
                if (!progreso) return;
                progreso.classList.remove('animando');
                progreso.style.width = '0%';
                clearTimeout(progresoTimeout);
                progresoTimeout = setTimeout(() => {
                    progreso.classList.add('animando');
                }, 30);
            }

            function reiniciarAutoplay() {
                clearInterval(autoplayTimer);
                reiniciarProgreso();
                autoplayTimer = setInterval(siguiente, DURACION_AUTOPLAY);
            }

            // Alguien está interactuando con el slide (globo, quesos, botón
            // de sorteo): pausa el autoplay indefinidamente y solo lo
            // reanuda tras un rato sin más interacciones.
            function notificarInteraccion() {
                bloqueoInteraccion = true;
                clearInterval(autoplayTimer);
                progreso && progreso.classList.remove('animando');
                clearTimeout(inactividadTimer);
                inactividadTimer = setTimeout(() => {
                    bloqueoInteraccion = false;
                    reiniciarAutoplay();
                }, ESPERA_INACTIVIDAD);
            }
            window.LZ_notificarInteraccion = notificarInteraccion;

            nextBtn && nextBtn.addEventListener('click', siguiente);
            prevBtn && prevBtn.addEventListener('click', anterior);

            puntos.forEach((p) => {
                p.addEventListener('click', () => irA(parseInt(p.dataset.slide, 10)));
            });

            let touchStartX = 0;
            track.addEventListener('touchstart', (e) => {
                touchStartX = e.changedTouches[0].screenX;
            }, { passive: true });

            track.addEventListener('touchend', (e) => {
                const touchEndX = e.changedTouches[0].screenX;
                const diff = touchEndX - touchStartX;
                if (Math.abs(diff) > 50) {
                    diff < 0 ? siguiente() : anterior();
                }
            }, { passive: true });

            const heroCarrusel = document.querySelector('.hero-carrusel');
            if (heroCarrusel) {
                heroCarrusel.addEventListener('mouseenter', () => {
                    if (bloqueoInteraccion) return;
                    clearInterval(autoplayTimer);
                    progreso && progreso.classList.remove('animando');
                });
                heroCarrusel.addEventListener('mouseleave', () => {
                    if (bloqueoInteraccion) return;
                    reiniciarAutoplay();
                });
            }

            if (window.matchMedia('(prefers-reduced-motion: reduce)').matches) {
                irA(0);
            } else {
                slides.forEach((s, i) => s.classList.toggle('activo', i === 0));
                puntos.forEach((p, i) => p.classList.toggle('activo', i === 0));
                reiniciarAutoplay();
            }
        })();

        /* ---- Scroll reveal con Intersection Observer ---- */
        const revealEls = document.querySelectorAll('.reveal, .reveal-left, .reveal-right');
        const observer = new IntersectionObserver((entries) => {
            entries.forEach(entry => {
                if (entry.isIntersecting) {
                    entry.target.classList.add('visible');
                    observer.unobserve(entry.target);
                }
            });
        }, { threshold: 0.15 });

        revealEls.forEach(el => observer.observe(el));


        (function () {
            const wrap = document.querySelector('.quesos-interactivos');
            if (!wrap) return;

            const slide = wrap.closest('.slide-imagen');
            const img = slide.querySelector('.slide-imagen-fondo');
            const bgUrl = wrap.dataset.bg;
            const ofertaFondoUrl = wrap.dataset.ofertaFondo;
            const puntosEls = wrap.querySelectorAll('.queso-punto');
            // Precargamos la imagen de oferta para conocer su tamaño real
            // (necesario para calcular cuánto hay que escalarla dentro de
            // la caja conjunta de los 3 quesos)
            const imgOferta = new Image();
            let ofertaLista = false;
            if (ofertaFondoUrl) {
                imgOferta.onload = () => { ofertaLista = true; actualizar(); };
                imgOferta.src = ofertaFondoUrl;
            }
            function parsearPuntos(str) {
                return str.trim().split(',').map((par) => {
                    const partes = par.trim().split(/\s+/);
                    return [parseFloat(partes[0]), parseFloat(partes[1])];
                });
            }

            const quesos = Array.from(puntosEls).map((p) => {
                const left = parseFloat(p.dataset.left);
                const top = parseFloat(p.dataset.top);
                const width = parseFloat(p.dataset.width);
                const height = parseFloat(p.dataset.height);
                const clipLocal = parsearPuntos(p.dataset.clip);

                const puntosGlobal = clipLocal.map(([cx, cy]) => [
                    left + (cx / 100) * width,
                    top + (cy / 100) * height
                ]);

                const glow = p.querySelector('.queso-punto-glow');
                const ventana = p.querySelector('.queso-punto-ventana');
                const borde = p.querySelector('.queso-punto-borde');
                const flip = p.querySelector('.queso-punto-flip');
                const reverso = p.querySelector('.queso-punto-reverso');

ventana.style.backgroundImage = `url(${bgUrl})`;

const video = reverso ? reverso.querySelector('.queso-oferta-video') : null;
if (video && p.dataset.ofertaVideo) {
    video.src = p.dataset.ofertaVideo;
    if (p.dataset.ofertaPos) {
        video.style.objectPosition = p.dataset.ofertaPos;
    }
}
const tieneDescuento = p.dataset.descuento && !isNaN(parseInt(p.dataset.descuento, 10));
if (reverso) {
    reverso.classList.toggle('con-descuento', tieneDescuento);
    reverso.classList.toggle('sin-descuento', !tieneDescuento);
}
return { el: p, ventana, borde, glow, flip, video, reverso, puntosGlobal };
            });

            function geometriaCover() {
                const W = img.naturalWidth, H = img.naturalHeight;
                const rect = slide.getBoundingClientRect();
                const Cw = rect.width, Ch = rect.height;
                if (!W || !H || Cw < 50 || Ch < 50) return null;

                const scale = Math.max(Cw / W, Ch / H);
                const offsetX = (Cw - W * scale) / 2;
                const offsetY = (Ch - H * scale) / 2;

                return { W, H, Cw, Ch, scale, offsetX, offsetY };
            }

            function puntoAContenedor(xPct, yPct, geo) {
                const xImgPx = (xPct / 100) * geo.W;
                const yImgPx = (yPct / 100) * geo.H;
                const xScreenPx = geo.offsetX + xImgPx * geo.scale;
                const yScreenPx = geo.offsetY + yImgPx * geo.scale;
                return [(xScreenPx / geo.Cw) * 100, (yScreenPx / geo.Ch) * 100];
            }

            let intentos = 0;
            function actualizar() {
                const geo = geometriaCover();
                if (!geo) {
                    if (intentos < 20) {
                        intentos++;
                        requestAnimationFrame(actualizar);
                    }
                    return;
                }
                intentos = 0;
                window.LZ_CONTENEDOR_SIZE = { w: geo.Cw, h: geo.Ch };
                window.LZ_PERIMETROS = window.LZ_PERIMETROS || [];
                let uMinX = Infinity, uMaxX = -Infinity, uMinY = Infinity, uMaxY = -Infinity;
                quesos.forEach(({ el, ventana, borde, glow, flip, video, reverso, puntosGlobal }, idx) => {
                    try {
                    const puntosPantalla = puntosGlobal.map(([x, y]) => puntoAContenedor(x, y, geo));
                    window.LZ_PERIMETROS[idx] = puntosPantalla;

                    const clipStr = 'polygon(' +
                    puntosPantalla.map(([x, y]) => `${x.toFixed(3)}% ${y.toFixed(3)}%`).join(', ') +
                    ')';

                    if (el) el.style.clipPath = clipStr;
                    if (ventana) ventana.style.clipPath = clipStr;
                    if (borde) borde.style.clipPath = clipStr;
                    if (glow) glow.style.clipPath = clipStr;
                    if (flip) flip.style.clipPath = clipStr;

                    let minX = Infinity, maxX = -Infinity, minY = Infinity, maxY = -Infinity;
                    puntosPantalla.forEach(([x, y]) => {
                        if (x < minX) minX = x;
                        if (x > maxX) maxX = x;
                        if (y < minY) minY = y;
                        if (y > maxY) maxY = y;
                    });
                    if (minX < uMinX) uMinX = minX;
                    if (maxX > uMaxX) uMaxX = maxX;
                    if (minY < uMinY) uMinY = minY;
                    if (maxY > uMaxY) uMaxY = maxY;
                

                    const centroX = (minX + maxX) / 2;
                    const centroY = (minY + maxY) / 2;

                    borde.style.transformOrigin = `${centroX}% ${centroY}%`;
                    ventana.style.transformOrigin = `${centroX}% ${centroY}%`;
                    if (glow) glow.style.transformOrigin = `${centroX}% ${centroY}%`;
                    el.dataset.centroX = centroX.toFixed(2);
                    el.dataset.centroY = centroY.toFixed(2);
                    const ofertaCentro = el.querySelector('.queso-oferta-centro');
                    if (ofertaCentro) {
                        const offX = parseFloat(el.dataset.ofertaOffsetX) || 0;
                        const offY = parseFloat(el.dataset.ofertaOffsetY) || 6;
                        ofertaCentro.style.left = `${centroX + offX}%`;
                        ofertaCentro.style.top = `${centroY + offY}%`;
                    }

                } catch (err) {
                    console.error('Error recortando un queso:', err);
                }
            });
            
           const infoUnica = document.getElementById('ofertaInfoUnica');
            if (infoUnica) {
                // ---- CONTROL MANUAL: ajusta estos 3 números a mano ----
                const izquierdaPct = 64;
                const arribaPct = 59;
                const anchoPct = 25;

                infoUnica.style.left = `${izquierdaPct}%`;
                infoUnica.style.top = `${arribaPct}%`;
                infoUnica.style.width = `${anchoPct}%`;
            }

            const ruletaSuelta = document.getElementById('ofertaRuletaSuelta');
            if (ruletaSuelta) {
                // ---- CONTROL MANUAL de la ruleta, totalmente independiente ----
                const ruletaIzquierdaPct = 78;
                const ruletaArribaPct = 45;

                ruletaSuelta.style.left = `${ruletaIzquierdaPct}%`;
                ruletaSuelta.style.top = `${ruletaArribaPct}%`;
            }

            // ---- Posiciona el video "OFERTA DEL DÍA" como UNA sola pieza
            // continua repartida entre los 3 quesos, igual que hacía la
            // imagen: los 3 <video> comparten el mismo left/top/width/height
            // (la caja que envuelve a los 3 quesos juntos) y cada uno se ve
            // recortado solo por su propio clip-path.
            if (isFinite(uMinX)) {
                quesos.forEach(({ video }) => {
                    if (!video) return;
                    video.style.left   = uMinX + '%';
                    video.style.top    = uMinY + '%';
                    video.style.width  = (uMaxX - uMinX) + '%';
                    video.style.height = (uMaxY - uMinY) + '%';
                });
            }

            // ---- Delineado dorado SOLO arriba y abajo (libre en el centro,
            // por donde pasa el texto "OFERTA DEL DÍA") ----
            if (isFinite(uMinY)) {
                const centro = (uMinY + uMaxY) / 2;
                // % de la altura total de los 3 quesos que queda LIBRE en el
                // centro (sin borde). Súbelo si quieres franja libre más
                // ancha, bájalo si quieres que el borde se acerque más al texto.
                const bandaLibre = (uMaxY - uMinY) * 0.34;
                const bandaTop = centro - bandaLibre / 2;
                const bandaBottom = centro + bandaLibre / 2;

                const maskCSS = `linear-gradient(to bottom,
                    black 0%, black ${bandaTop.toFixed(2)}%,
                    transparent ${(bandaTop + 4).toFixed(2)}%,
                    transparent ${(bandaBottom - 4).toFixed(2)}%,
                    black ${bandaBottom.toFixed(2)}%, black 100%)`;

                quesos.forEach(({ borde }) => {
                    if (!borde) return;
                    borde.style.maskImage = maskCSS;
                    borde.style.webkitMaskImage = maskCSS;
                });
            }
            }
            window.addEventListener('resize', actualizar);
            img.addEventListener('load', actualizar);
            actualizar();
            if (window.ResizeObserver) {
                new ResizeObserver(actualizar).observe(slide);
            }
        })();


    (function () {
        const wrap = document.querySelector('.quesos-interactivos');
        const boton = document.getElementById('botonOfertas');
        const banner = document.getElementById('ofertaBanner');
        const confettiWrap = document.getElementById('confettiContenedor');
        const indicador = document.getElementById('globoIndicador');
        const ruedaWrap = document.getElementById('ofertaRuedaWrap');
        const fragmentosWrap = document.getElementById('globoFragmentos');
        if (!wrap || !boton) return;
        const quesosArr = Array.from(wrap.querySelectorAll('.queso-punto'));
        const botonSortearWrap = document.getElementById('botonSortearWrap');
        const botonSortear = document.getElementById('botonSortear');

        let vistos = new Set();
        let sorteoHecho = false;
        let sorteoEnCurso = false;
        let sincronizando = false;

        const CLAVE_OFERTA = 'lz_oferta_del_dia';

        function leerOfertaGuardada() {
            try {
                const raw = localStorage.getItem(CLAVE_OFERTA);
                if (!raw) return null;
                const data = JSON.parse(raw);
                if (!data || !data.timestamp || !data.valor) return null;
                const segundosPasados = (Date.now() - data.timestamp) / 1000;
                if (segundosPasados >= 1) {
                    localStorage.removeItem(CLAVE_OFERTA);
                    return null;
                }
                return data;
            } catch (e) {
                return null;
            }
        }

        function guardarOfertaDelDia(valor) {
            try {
                localStorage.setItem(CLAVE_OFERTA, JSON.stringify({ valor, timestamp: Date.now() }));
            } catch (e) {}
        }
        const ofertaGuardada = leerOfertaGuardada();
        if (ofertaGuardada) {
            sorteoHecho = true;
            quesosArr.forEach((q) => q.classList.add('encendido'));
            if (ruedaWrap) {
                const texto = ruedaWrap.querySelector('.rueda-descuento');
                if (texto) texto.textContent = `${ofertaGuardada.valor}% de descuento hoy`;
                ruedaWrap.classList.add('visible');
            }
        }

        function obtenerVideo(p) {
            const reverso = p.querySelector('.queso-punto-reverso');
            return reverso ? reverso.querySelector('.queso-oferta-video') : null;
        }
        function reproducirVideoQueso(p) {
            const video = obtenerVideo(p);
            if (video) {
                video.currentTime = 0;
                video.classList.add('reproduciendo');
                video.play().catch(() => {});
            }
        }
        function pausarVideoQueso(p) {
            const video = obtenerVideo(p);
            if (video) {
                video.pause();
                video.classList.remove('reproduciendo');
            }
        }
        function reproducirTodosSincronizados() {
            const videos = quesosArr.map(obtenerVideo).filter(Boolean);
            if (!videos.length) return;

            videos.forEach((v) => { v.currentTime = 0; });

            Promise.all(videos.map((v) => v.play().catch(() => {})))
                .then(() => {
                    videos.forEach((v) => v.classList.add('reproduciendo'));
                    iniciarLoopSincronizacion(videos);
                });
        }

        function iniciarLoopSincronizacion(videos) {
            if (sincronizando) return;
            sincronizando = true;
            const maestro = videos[0];

            function paso() {
                if (maestro.paused || maestro.ended) {
                    sincronizando = false;
                    return;
                }
                videos.forEach((v) => {
                    if (v === maestro) return;
                    if (Math.abs(v.currentTime - maestro.currentTime) > 0.08) {
                        v.currentTime = maestro.currentTime;
                    }
                });
                requestAnimationFrame(paso);
            }
            requestAnimationFrame(paso);
        }
       function mostrarBotonSortear() {
            if (botonSortearWrap) botonSortearWrap.classList.add('visible');
        }

        function mostrarNumeroFijo(contenedor, valorFinal) {
            const digitos = String(Math.max(0, Math.min(99, valorFinal))).padStart(2, '0').split('');
            contenedor.innerHTML = digitos.map(d =>
                `<span class="ruleta-digito"><span class="ruleta-cinta"><span>${d}</span></span></span>`
            ).join('');
        }

        // Versión animada tipo tragamonedas: cada columna de dígitos gira
        // por varios números al azar antes de frenar en el valor final.
        function generarCintaAnimada(digitoFinal) {
            const pasos = 12;
            let html = '';
            for (let i = 0; i < pasos; i++) {
                html += `<span>${Math.floor(Math.random() * 10)}</span>`;
            }
            html += `<span>${digitoFinal}</span>`;
            return html;
        }

        function mostrarNumeroConGiro(contenedor, valorFinal, alturaItem = 34) {
            const digitos = String(Math.max(0, Math.min(99, valorFinal))).padStart(2, '0').split('');
            contenedor.innerHTML = digitos.map((d) =>
                `<span class="ruleta-digito"><span class="ruleta-cinta">${generarCintaAnimada(d)}</span></span>`
            ).join('');

            const cintas = contenedor.querySelectorAll('.ruleta-cinta');
            cintas.forEach((cinta, idx) => {
                const totalItems = cinta.children.length;
                cinta.style.transition = 'none';
                cinta.style.transform = 'translateY(0)';
                void cinta.offsetHeight;
                requestAnimationFrame(() => {
                    cinta.style.transition = `transform ${1.1 + idx * 0.4}s cubic-bezier(0.15, 0.75, 0.25, 1)`;
                    cinta.style.transform = `translateY(-${(totalItems - 1) * alturaItem}px)`;
                });
            });
        }

        /* ---------------------------------------------------------------
           SORTEO "TIPO RULETA" — enciende el borde dorado de cada queso
           uno por uno (usa el mismo clip-path real que ya tienen), va
           saltando cada vez más lento hasta frenar en el ganador. Sin
           SVG ni trazado: solo la clase .resaltado-sorteo sobre
           .queso-punto-borde de cada queso.
        --------------------------------------------------------------- */
        function iniciarSorteo() {
            if (sorteoEnCurso || sorteoHecho) return;
            const candidatos = quesosArr.filter(q => q.dataset.descuento);
            if (!candidatos.length) return;
        
            const ganadorEl = elegirGanadorPonderado(candidatos); // <-- cambio aquí
            sorteoEnCurso = true;
            botonSortear.disabled = true;
            botonSortearWrap.classList.remove('visible');
        
            const ruletaUnica = document.getElementById('ofertaInfoRuleta');
            const valor = parseInt(ganadorEl.dataset.descuento, 10);
        
            mostrarNumeroConGiro(ruletaUnica, valor);
            setTimeout(() => mostrarFelicidades(ganadorEl, valor), 2600);
        }

        function elegirGanadorPonderado(candidatos) {
            // Cada queso pesa según su ratio de stock (más stock sobrante = más
            // probabilidad de "ganar" el sorteo). Mínimo 0.1 para que ninguno
            // quede en 0% de probabilidad, aunque tenga stock justo.
            const pesos = candidatos.map(c => Math.max(parseFloat(c.dataset.pesoStock) || 1, 0.1));
            const total = pesos.reduce((a, b) => a + b, 0);
            let r = Math.random() * total;
            for (let i = 0; i < candidatos.length; i++) {
                r -= pesos[i];
                if (r <= 0) return candidatos[i];
            }
            return candidatos[candidatos.length - 1];
        }

        function mostrarFelicidades(ganadorEl, valor) {
            const overlay = document.getElementById('ofertaRevealOverlay');
            const subtitulo = document.getElementById('ofertaRevealSubtitulo');
            if (subtitulo) subtitulo.textContent = `Tienes ${valor}% de descuento`;
            if (overlay) overlay.classList.add('visible');
            lanzarConfetti(90);

            setTimeout(() => cerrarReveal(ganadorEl, valor), 2800);
        }

        function cerrarReveal(ganadorEl, valor) {
            const overlay = document.getElementById('ofertaRevealOverlay');
            if (overlay) overlay.classList.remove('visible');

            sorteoEnCurso = false;
            sorteoHecho = true;
            wrap.classList.add('sorteo-hecho');
            guardarOfertaDelDia(valor);

            quesosArr.forEach((q) => {
                q.classList.remove('volteado');
                pausarVideoQueso(q);
            });
            wrap.classList.remove('todos-encendidos');

            let sumX = 0, sumY = 0, n = 0;
            quesosArr.forEach((q) => {
                sumX += parseFloat(q.dataset.centroX) || 50;
                sumY += parseFloat(q.dataset.centroY) || 50;
                n++;
            });
            const cx = n ? sumX / n : 50;
            const cy = n ? sumY / n : 50;

            setTimeout(() => volarBrilloHaciaBadge(cx, cy, valor), 500);
        }

        function volarBrilloHaciaBadge(cx, cy, valor) {
            if (!ruedaWrap) return;
            const slide = wrap.closest('.slide-imagen');

            const spark = document.createElement('span');
            spark.className = 'brillo-volador';
            spark.style.left = cx + '%';
            spark.style.top = cy + '%';
            slide.appendChild(spark);

            const destino = ruedaWrap.getBoundingClientRect();
            const origenSlide = slide.getBoundingClientRect();
            const dx = (destino.left + destino.width / 2) - (origenSlide.left + (cx / 100) * origenSlide.width);
            const dy = (destino.top + destino.height / 2) - (origenSlide.top + (cy / 100) * origenSlide.height);

            spark.style.setProperty('--dx', dx + 'px');
            spark.style.setProperty('--dy', dy + 'px');

            requestAnimationFrame(() => spark.classList.add('volando'));

            spark.addEventListener('animationend', () => {
                spark.remove();
                const texto = ruedaWrap.querySelector('.rueda-descuento');
                if (texto) texto.textContent = `${valor}% de descuento hoy`;
                ruedaWrap.classList.add('visible', 'aparicion-pop');
            });
        }
        function volarBrilloHaciaBadge(cx, cy, valor) {
            if (!ruedaWrap) return;
            const slide = wrap.closest('.slide-imagen');

            const spark = document.createElement('span');
            spark.className = 'brillo-volador';
            spark.style.left = cx + '%';
            spark.style.top = cy + '%';
            slide.appendChild(spark);

            const destino = ruedaWrap.getBoundingClientRect();
            const origenSlide = slide.getBoundingClientRect();
            const dx = (destino.left + destino.width / 2) - (origenSlide.left + (cx / 100) * origenSlide.width);
            const dy = (destino.top + destino.height / 2) - (origenSlide.top + (cy / 100) * origenSlide.height);

            spark.style.setProperty('--dx', dx + 'px');
            spark.style.setProperty('--dy', dy + 'px');

            requestAnimationFrame(() => spark.classList.add('volando'));

            spark.addEventListener('animationend', () => {
                spark.remove();
                const texto = ruedaWrap.querySelector('.rueda-descuento');
                if (texto) texto.textContent = `${valor}% de descuento hoy`;
                ruedaWrap.classList.add('visible', 'aparicion-pop');
            });
        }
        botonSortear && botonSortear.addEventListener('click', () => {
            window.LZ_notificarInteraccion && window.LZ_notificarInteraccion();
            iniciarSorteo();
        });

        function reventarGlobo() {
            if (!fragmentosWrap) return;
            const formas = ['50% 50% 50% 10%', '50% 10% 50% 50%', '10% 50% 50% 50%', '50%'];
            const cantidad = 14;

            for (let i = 0; i < cantidad; i++) {
                const frag = document.createElement('span');
                frag.className = 'globo-fragmento';

                const angulo = (Math.PI * 2 * i) / cantidad + (Math.random() * 0.4 - 0.2);
                const distancia = 40 + Math.random() * 50;
                const fx = Math.cos(angulo) * distancia;
                const fy = Math.sin(angulo) * distancia - 10; // ligero sesgo hacia arriba

                frag.style.setProperty('--fx', fx + 'px');
                frag.style.setProperty('--fy', fy + 'px');
                frag.style.setProperty('--frot', (Math.random() * 360 - 180) + 'deg');

                const tam = 6 + Math.random() * 9;
                frag.style.width = tam + 'px';
                frag.style.height = tam + 'px';
                frag.style.borderRadius = formas[Math.floor(Math.random() * formas.length)];
                frag.style.animationDelay = (Math.random() * 0.05) + 's';

                fragmentosWrap.appendChild(frag);
                frag.addEventListener('animationend', () => frag.remove());
            }
        }

        setTimeout(() => indicador && indicador.classList.add('visible'), 900);

        const colores = ['#c9a84c', '#f0d98a', '#e2402d', '#ffffff', '#1a5fa8'];

        function lanzarConfetti(cantidad = 70) {
            for (let i = 0; i < cantidad; i++) {
                const pieza = document.createElement('span');
                pieza.className = 'confetti-pieza';
                pieza.style.left = Math.random() * 100 + '%';
                pieza.style.background = colores[Math.floor(Math.random() * colores.length)];
                pieza.style.width = (6 + Math.random() * 6) + 'px';
                pieza.style.height = (10 + Math.random() * 8) + 'px';
                pieza.style.animationDuration = (2.2 + Math.random() * 1.6) + 's';
                pieza.style.animationDelay = (Math.random() * 0.4) + 's';
                confettiWrap.appendChild(pieza);
                pieza.addEventListener('animationend', () => pieza.remove());
            }
        }

        function lanzarConfettiLocal(xPct, yPct, cantidad = 24) {
            if (!confettiWrap) return;
            for (let i = 0; i < cantidad; i++) {
                const pieza = document.createElement('span');
                pieza.className = 'confetti-pieza-local';
                pieza.style.left = xPct + '%';
                pieza.style.top = yPct + '%';
                pieza.style.background = colores[Math.floor(Math.random() * colores.length)];
                pieza.style.width = (10 + Math.random() * 8) + 'px';
                pieza.style.height = (16 + Math.random() * 12) + 'px';

                const angulo = Math.random() * Math.PI * 2;
                const distancia = 50 + Math.random() * 80;
                pieza.style.setProperty('--cx', (Math.cos(angulo) * distancia) + 'px');
                pieza.style.setProperty('--cy', (Math.sin(angulo) * distancia - 30) + 'px');
                pieza.style.setProperty('--crot', (Math.random() * 720 - 360) + 'deg');
                pieza.style.animationDuration = (0.8 + Math.random() * 0.5) + 's';
                pieza.style.animationDelay = (Math.random() * 0.08) + 's';

                confettiWrap.appendChild(pieza);
                pieza.addEventListener('animationend', () => pieza.remove());
            }
        }

        let modoActivo = false;
        let bannerTimeout = null;

        function activar() {
            modoActivo = true;
            wrap.classList.add('modo-ofertas');
            boton.classList.add('activo');
            lanzarConfetti(70);

            if (!sorteoHecho) {
                banner.classList.add('visible');
                clearTimeout(bannerTimeout);
                bannerTimeout = setTimeout(() => banner.classList.remove('visible'), 4000);
            }

            // Precarga los 3 videos de oferta ahora, para que cuando el
            // usuario encienda los 3 quesos ya estén listos y no haya
            // retraso al reproducirlos.
            quesosArr.forEach((q) => {
                const video = obtenerVideo(q);
                if (video && video.readyState < 2) {
                    video.load();
                }
            });
        }

        function desactivar() {
            modoActivo = false;
            wrap.classList.remove('modo-ofertas');
            banner.classList.remove('visible');

            if (sorteoHecho) {
                // La oferta ya se sorteó y sigue vigente (24h): los quesos
                // y el aviso de la esquina se quedan tal cual, sin resetear.
                boton.classList.remove('volando', 'reventado');
                return;
            }

            wrap.classList.remove('sorteo-hecho');
            ruedaWrap && ruedaWrap.classList.remove('visible');
            wrap.querySelectorAll('.queso-punto.volteado')
                .forEach((el) => {
                    el.classList.remove('volteado');
                    pausarVideoQueso(el);
                    const v = obtenerVideo(el);
                    if (v) { v.currentTime = 0; v.classList.remove('reproduciendo'); }
                });
            sincronizando = false;
            wrap.querySelectorAll('.queso-punto-borde.resaltado-sorteo')
                .forEach((el) => el.classList.remove('resaltado-sorteo'));

            wrap.querySelectorAll('.queso-punto.encendido')
                .forEach((el) => el.classList.remove('encendido'));
            wrap.classList.remove('todos-encendidos');
            const ruletaSueltaReset = document.getElementById('ofertaRuletaSuelta');
            if (ruletaSueltaReset) ruletaSueltaReset.classList.remove('revelada');

            vistos.clear();
            sorteoEnCurso = false;
            botonSortearWrap && botonSortearWrap.classList.remove('visible');
            botonSortear && (botonSortear.disabled = false);

            wrap.querySelectorAll('.es-ganador').forEach(el => el.classList.remove('es-ganador'));

            boton.classList.remove('volando', 'reventado');
            setTimeout(() => indicador && indicador.classList.add('visible'), 400);
        }

        boton.addEventListener('click', () => {
            window.LZ_notificarInteraccion && window.LZ_notificarInteraccion();
            if (modoActivo) {
                desactivar();
                return;
            }
            if (boton.classList.contains('volando')) return;

            indicador && indicador.classList.remove('visible');
            boton.classList.add('volando');

            setTimeout(() => {
                boton.classList.add('reventado');
                reventarGlobo();
                activar();
            }, 750);
        });

        wrap.querySelectorAll('.queso-punto').forEach((p) => {
            p.addEventListener('click', (e) => {
                window.LZ_notificarInteraccion && window.LZ_notificarInteraccion();
                if (!modoActivo || sorteoEnCurso || sorteoHecho) return;
                e.preventDefault();

                const encendiendo = !p.classList.contains('encendido');
                p.classList.toggle('encendido');

                const cx = parseFloat(p.dataset.centroX) || 50;
                const cy = parseFloat(p.dataset.centroY) || 50;

                if (encendiendo) {
                    lanzarConfettiLocal(cx, cy);
                    vistos.add(p);
                } else {
                    vistos.delete(p);
                    // Si se apaga uno, se oculta el video/reverso en los 3 a la vez
                    quesosArr.forEach((q) => {
                        q.classList.remove('volteado');
                        pausarVideoQueso(q);
                    });
                    wrap.classList.remove('todos-encendidos');
                    botonSortearWrap && botonSortearWrap.classList.remove('visible');
                }

                // Solo cuando los 3 están encendidos a la vez, se revela el
                // video en los 3 quesos AL MISMO TIEMPO, con transición.
                if (vistos.size === quesosArr.length && !sorteoHecho) {
                    quesosArr.forEach((q) => q.classList.add('volteado'));
                    wrap.classList.add('todos-encendidos');
                    reproducirTodosSincronizados();

                    const tarjetaDescuento = document.getElementById('ofertaDescuentoTarjeta');
                    const ruletaUnica = document.getElementById('ofertaInfoRuleta');
                    if (tarjetaDescuento) tarjetaDescuento.classList.add('visible');
                    if (ruletaUnica) mostrarNumeroFijo(ruletaUnica, 50);

                    mostrarBotonSortear();
                } else {
                    wrap.classList.remove('todos-encendidos');
                }
            });
        });
    })();

    /* ---- Buscador en vivo: filtra el grid de productos (horizontal o vertical) ---- */
    (function () {
        const wrapper = document.querySelector('.buscador-wrapper');
        const input = document.getElementById('inputBuscador');
        const lista = document.getElementById('listaProductos');
        const infoResultados = document.getElementById('infoResultados');
        const infoQuery = document.getElementById('infoQuery');
        const infoCantidad = document.getElementById('infoCantidad');
        const contador = document.getElementById('contadorProductos');
        if (!wrapper || !input || !lista) return;

        const URL_BUSCAR = wrapper.dataset.urlAjax;
        const URL_AGREGAR_BASE = wrapper.dataset.urlAgregarBase;
        const LAYOUT = wrapper.dataset.layout || 'horizontal';
        let timer = null;

        function escapeHtml(str) {
            const div = document.createElement('div');
            div.textContent = str;
            return div.innerHTML;
        }

        function urlAgregar(id) {
            return URL_AGREGAR_BASE.replace(/\/1\/?$/, `/${id}/`);
        }

        function badgeHtml(p) {
            return p.stock_actual <= p.stock_minimo
                ? `<span class="badge-stock bajo">Stock bajo</span>`
                : `<span class="badge-stock disponible">Disponible</span>`;
        }

        function descripcionSegura(p) {
            return p.descripcion && p.descripcion.trim()
                ? escapeHtml(p.descripcion)
                : 'Producto elaborado con los más altos estándares de calidad, fresco y natural.';
        }

        function tarjetaHorizontal(p) {
            return `
                <div class="col-12">
                    <div class="card producto-card">
                        <div class="producto-img-wrapper">
                            ${badgeHtml(p)}
                            <img src="${p.imagen}" class="imagen-producto" alt="${escapeHtml(p.nombre)}">
                        </div>
                        <div class="producto-info">
                            <div class="card-body">
                                <div class="estrellas">
                                    <i class="bi bi-star-fill"></i>
                                    <i class="bi bi-star-fill"></i>
                                    <i class="bi bi-star-fill"></i>
                                    <i class="bi bi-star-fill"></i>
                                    <i class="bi bi-star-half"></i>
                                </div>
                                <div class="precio-fila">
                                    <h5 class="titulo-producto">${escapeHtml(p.nombre)}</h5>
                                    <p class="precio">$ ${Number(p.precio).toLocaleString('es-CO')}</p>
                                </div>
                                <p class="producto-descripcion"><strong>Descripcion:</strong></p>
                                <p class="producto-descripcion">${descripcionSegura(p)}</p>
                            </div>
                            <div class="card-footer bg-white border-0">
                                <div class="footer-botones">
                                    <a href="${urlAgregar(p.id)}" class="btn btn-carrito">
                                        <i class="bi bi-cart-plus"></i> Añadir al carrito
                                    </a>
                                </div>
                            </div>
                        </div>
                    </div>
                </div>
            `;
        }

        function tarjetaVertical(p) {
            return `
                <div class="col-lg-3 col-md-6">
                    <div class="card producto-card producto-card--vertical h-100">
                        <div class="producto-img-wrapper">
                            ${badgeHtml(p)}
                            <img src="${p.imagen}" class="imagen-producto" alt="${escapeHtml(p.nombre)}">
                        </div>
                        <div class="card-body">
                            <div class="estrellas">
                                <i class="bi bi-star-fill"></i>
                                <i class="bi bi-star-fill"></i>
                                <i class="bi bi-star-fill"></i>
                                <i class="bi bi-star-fill"></i>
                                <i class="bi bi-star-half"></i>
                            </div>
                            <h5 class="titulo-producto">${escapeHtml(p.nombre)}</h5>
                            <p class="producto-descripcion">${descripcionSegura(p)}</p>
                            <p class="precio">$ ${Number(p.precio).toLocaleString('es-CO')}</p>
                        </div>
                        <div class="card-footer bg-white border-0">
                            <a href="${urlAgregar(p.id)}" class="btn btn-carrito w-100">
                                <i class="bi bi-cart-plus"></i> Añadir al carrito
                            </a>
                        </div>
                    </div>
                </div>
            `;
        }

        function tarjetaHtml(p) {
            return LAYOUT === 'vertical' ? tarjetaVertical(p) : tarjetaHorizontal(p);
        }

        function renderLista(data) {
            const productos = data.productos || [];
            const query = data.query || '';

            if (query) {
                infoResultados.style.display = '';
                infoQuery.textContent = query;
                infoCantidad.textContent = productos.length;
            } else {
                infoResultados.style.display = 'none';
            }

            if (contador) {
                contador.textContent = `${productos.length} Producto${productos.length === 1 ? '' : 's'}`;
            }

            if (productos.length === 0) {
                lista.innerHTML = `
                    <div class="col-12">
                        <div class="alert alert-info text-center buscador-sin-resultados">
                            <i class="bi bi-search"></i>
                            No encontramos productos para "<strong>${escapeHtml(query)}</strong>".
                            <a href="?">Ver todos los productos</a>
                        </div>
                    </div>
                `;
                return;
            }

            lista.innerHTML = productos.map(tarjetaHtml).join('');
        }

        input.addEventListener('input', () => {
            clearTimeout(timer);
            const q = input.value.trim();

            timer = setTimeout(() => {
                fetch(`${URL_BUSCAR}?q=${encodeURIComponent(q)}`)
                    .then(res => res.json())
                    .then(renderLista)
                    .catch(() => {
                        lista.innerHTML = `
                            <div class="col-12">
                                <div class="alert alert-danger text-center">Ocurrió un error al buscar.</div>
                            </div>
                        `;
                    });
            }, 300);
        });
    })();