        window.LZ_USUARIO_AUTENTICADO = {{ request.user.is_authenticated|yesno:"true,false" }};

        /* ---- Navbar scroll effect ---- */
        const nav = document.getElementById('mainNav');
        window.addEventListener('scroll', () => {
            nav.classList.toggle('scrolled', window.scrollY > 60);
        });

        /* ---- Parallax 3D con el mouse en el hero ---- */
        (function () {
            const hero = document.querySelector('#inicio .hero');
            if (!hero || window.matchMedia('(prefers-reduced-motion: reduce)').matches) return;

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
            const DURACION_AUTOPLAY = 6000;
            const ESPERA_INACTIVIDAD = 6000;
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
                slides.forEach((s, i) => {
                    const esActivo = i === actual;
                    s.classList.toggle('activo', esActivo);

                    // Pausa los videos de los slides que no se están viendo,
                    // y reanuda el del slide activo. Esto evita que el
                    // navegador siga decodificando video en segundo plano
                    // sin necesidad (causa principal del lag).
                    s.querySelectorAll('video').forEach((v) => {
                        if (esActivo) {
                            v.play().catch(() => {});
                        } else {
                            v.pause();
                        }
                    });
                });
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
                slides.forEach((s, i) => {
                    const esActivo = i === 0;
                    s.classList.toggle('activo', esActivo);
                    s.querySelectorAll('video').forEach((v) => {
                        if (esActivo) v.play().catch(() => {});
                        else v.pause();
                    });
                });
                puntos.forEach((p, i) => p.classList.toggle('activo', i === 0));
                reiniciarAutoplay();
            }
            /* ---- Pausar todos los videos cuando la pestaña no está visible ---- */
        document.addEventListener('visibilitychange', () => {
            const videos = document.querySelectorAll('video');
            if (document.hidden) {
                videos.forEach((v) => v.pause());
            } else {
                // Solo reanuda los que pertenecen al slide activo del carrusel
                const slideActivo = document.querySelector('.carrusel-slide.activo');
                if (slideActivo) {
                    slideActivo.querySelectorAll('video').forEach((v) => v.play().catch(() => {}));
                }
            }
        });
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

            const siluetaUnica = document.getElementById('siluetaUnica');
            const siluetaLinea = siluetaUnica ? siluetaUnica.querySelector('.silueta-unica-linea') : null;
            let siluetaPuntosGlobal = null;
            if (siluetaUnica) {
                const sLeft = parseFloat(siluetaUnica.dataset.left);
                const sTop = parseFloat(siluetaUnica.dataset.top);
                const sWidth = parseFloat(siluetaUnica.dataset.width);
                const sHeight = parseFloat(siluetaUnica.dataset.height);
                const clipLocal = parsearPuntos(siluetaUnica.dataset.clip);
                siluetaPuntosGlobal = clipLocal.map(([cx, cy]) => [
                    sLeft + (cx / 100) * sWidth,
                    sTop + (cy / 100) * sHeight
                ]);
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
                const contornoSvg = p.querySelector('.queso-punto-contorno');
                const contornoPoligono = p.querySelector('.queso-punto-contorno-linea');

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
                return { el: p, ventana, borde, glow, flip, video, reverso, contornoSvg, contornoPoligono, puntosGlobal };
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
                quesos.forEach(({ el, ventana, borde, glow, flip, video, reverso, contornoSvg, contornoPoligono, puntosGlobal }, idx) => {
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

                        // Contorno dorado real (stroke), usando los MISMOS
                        // puntos del recorte pero en px del contenedor, para
                        // que el <svg> no se deforme con el viewBox.
                        if (contornoSvg && contornoPoligono) {
                            contornoSvg.setAttribute('viewBox', `0 0 ${geo.Cw} ${geo.Ch}`);
                            const puntosPx = puntosPantalla
                                .map(([xPct, yPct]) => `${(xPct / 100 * geo.Cw).toFixed(2)},${(yPct / 100 * geo.Ch).toFixed(2)}`)
                                .join(' ');
                            contornoPoligono.setAttribute('points', puntosPx);
                        }

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

                if (siluetaUnica && siluetaLinea && siluetaPuntosGlobal) {
                    siluetaUnica.setAttribute('viewBox', `0 0 ${geo.Cw} ${geo.Ch}`);
                    const puntosPx = siluetaPuntosGlobal
                        .map(([gx, gy]) => puntoAContenedor(gx, gy, geo))
                        .map(([xPct, yPct]) => `${(xPct / 100 * geo.Cw).toFixed(2)},${(yPct / 100 * geo.Ch).toFixed(2)}`)
                        .join(' ');
                    siluetaLinea.setAttribute('points', puntosPx);
                }

                const infoUnica = document.getElementById('ofertaInfoUnica');
                if (infoUnica) {
                    const izquierdaPct = 64;
                    const arribaPct = 68;
                    const anchoPct = 20;

                    infoUnica.style.left = `${izquierdaPct}%`;
                    infoUnica.style.top = `${arribaPct}%`;
                    infoUnica.style.width = `${anchoPct}%`;
                }

                const ruletaSuelta = document.getElementById('ofertaRuletaSuelta');
                if (ruletaSuelta) {
                    const ruletaIzquierdaPct = 78;
                    const ruletaArribaPct = 45;

                    ruletaSuelta.style.left = `${ruletaIzquierdaPct}%`;
                    ruletaSuelta.style.top = `${ruletaArribaPct}%`;
                }

                if (isFinite(uMinX)) {
                    quesos.forEach(({ video }) => {
                        if (!video) return;
                        video.style.left   = uMinX + '%';
                        video.style.top    = uMinY + '%';
                        video.style.width  = (uMaxX - uMinX) + '%';
                        video.style.height = (uMaxY - uMinY) + '%';
                    });
                }

                if (isFinite(uMinY)) {
                    const centro = (uMinY + uMaxY) / 2;
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

        // --- Datos reales del premio, inyectados desde el backend ---
        // origenPremio distingue de DÓNDE viene el premio que se está por
        // mostrar/sortear: 'campana' (DescuentoAsignado, comportamiento
        // 100% igual al de siempre) o 'ruleta_diaria' (TiradaDiaria, Parte 2).
        // estadoJuegoDiario solo aplica cuando origenPremio es 'ruleta_diaria'.
        const origenPremio = wrap.dataset.origenPremio || 'ninguno'; // 'campana' | 'ruleta_diaria' | 'ninguno'
        const estadoJuegoDiario = wrap.dataset.estadoJuegoDiario || ''; // 'disponible' | 'ganado' | 'sin_premio' | ''

        const tienePremio = wrap.dataset.tienePremio === 'true';
        // premioTipo: '' (campaña) | 'CUPON_5' | 'ENVIO_GRATIS' | 'BOLETO_DORADO'.
        // Se reasigna en tiempo real cuando el resultado llega por fetch
        // (caso estadoJuegoDiario === 'disponible').
        let premioTipo = wrap.dataset.premioTipo || '';
        let premioProducto = wrap.dataset.premioProducto || '';
        let premioPorcentaje = parseFloat(wrap.dataset.premioPorcentaje) || 0;
        let premioPrecioOriginal = parseFloat(wrap.dataset.premioPrecioOriginal) || 0;
        let premioPrecioDescuento = parseFloat(wrap.dataset.premioPrecioDescuento) || 0;
        let premioCodigo = wrap.dataset.premioCodigo || '';
        let premioImagen = wrap.dataset.premioImagen || '';
        const urlMarcarMostrado = wrap.dataset.urlMarcarMostrado || '';
        const urlJugarRuleta = wrap.dataset.urlJugarRuleta || '';
        const urlReclamarPremioDia = wrap.dataset.urlReclamarPremioDia || '';

        // Textos/ícono para los premios de la ruleta diaria que no tienen
        // producto/foto/precio real (ver explicación al inicio de la respuesta).
        const CONFIG_PREMIO_RULETA = {
            CUPON_5: {
                icono: 'bi-ticket-perforated-fill',
                badge: '-5%',
                titulo: '¡Felicidades!',
                subtitulo: () => `Tienes 5% de descuento en ${premioProducto}`,
                mostrarPrecios: false,
                nota: 'Se aplica automáticamente al pagar tu carrito.',
            },
            ENVIO_GRATIS: {
                icono: 'bi-truck',
                badge: 'GRATIS',
                titulo: '¡Felicidades!',
                subtitulo: () => 'Ganaste envío gratis en tu próximo pedido',
                mostrarPrecios: false,
                nota: 'Se aplica automáticamente al pagar tu carrito.',
            },
            BOLETO_DORADO: {
                icono: 'bi-award-fill',
                badge: '🎫',
                titulo: '¡Boleto dorado!',
                subtitulo: () => 'Quedas participando en el próximo sorteo de premios especiales',
                mostrarPrecios: false,
                nota: 'Te avisaremos si resultas ganador.',
            },
        };

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

        function marcarPremioMostrado() {
            if (!urlMarcarMostrado || !premioCodigo) return;
            fetch(urlMarcarMostrado, {
                method: 'POST',
                headers: {
                    'X-CSRFToken': getCookie('csrftoken'),
                    'Content-Type': 'application/x-www-form-urlencoded',
                },
                body: 'codigo=' + encodeURIComponent(premioCodigo),
            }).catch(() => {
                // silencioso: si falla, en el peor caso el premio sigue "no mostrado"
                // en la base de datos, pero el cliente ya vio la animación.
            });
        }

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

        // "Ya jugaste hoy y no salió premio" (ruleta diaria): a diferencia
        // de 'ganado', esta variante NO deja jugar la ruleta otra vez —
        // se muestra directamente el aviso reutilizando el mismo
        // #ofertaRuedaWrap que ya usa el flujo de campaña para "ya tienes
        // el descuento de hoy".
        if (estadoJuegoDiario === 'sin_premio') {
            sorteoHecho = true;
            wrap.classList.add('sorteo-hecho', 'modo-ofertas');
            quesosArr.forEach((q) => q.classList.add('encendido'));
            if (ruedaWrap) {
                const texto = ruedaWrap.querySelector('.rueda-descuento');
                const aviso = ruedaWrap.querySelector('.rueda-aviso');
                if (texto) texto.textContent = 'Vuelve mañana';
                if (aviso) aviso.textContent = 'Hoy no salió premio, vuelve mañana por otra tirada';
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

        function generarCintaAnimada(digitoFinal) {
            const pasos = 12;
            let html = '';
            for (let i = 0; i < pasos; i++) {
                html += `<span>${Math.floor(Math.random() * 10)}</span>`;
            }
            html += `<span>${digitoFinal}</span>`;
            return html;
        }

        function mostrarNumeroConGiro(contenedor, valorFinal) {
            const digitos = String(Math.max(0, Math.min(99, valorFinal))).padStart(2, '0').split('');
            contenedor.innerHTML = digitos.map((d) =>
                `<span class="ruleta-digito"><span class="ruleta-cinta">${generarCintaAnimada(d)}</span></span>`
            ).join('');

            const cintas = contenedor.querySelectorAll('.ruleta-cinta');
            cintas.forEach((cinta, idx) => {
                const totalItems = cinta.children.length;
                const alturaItem = cinta.children[0].getBoundingClientRect().height || 34;
                cinta.style.transition = 'none';
                cinta.style.transform = 'translateY(0)';
                void cinta.offsetHeight;
                requestAnimationFrame(() => {
                    cinta.style.transition = `transform ${1.1 + idx * 0.4}s cubic-bezier(0.15, 0.75, 0.25, 1)`;
                    cinta.style.transform = `translateY(-${(totalItems - 1) * alturaItem}px)`;
                });
            });
        }
        function formatearPrecio(valor) {
            return '$' + Math.round(valor).toLocaleString('es-CO');
        }

        function iniciarSorteo() {
            if (sorteoEnCurso || sorteoHecho) return;
            if (origenPremio === 'ninguno') return; // salvaguarda, no debería pasar

            sorteoEnCurso = true;
            botonSortear.disabled = true;
            botonSortearWrap.classList.remove('visible');

            if (origenPremio === 'ruleta_diaria' && estadoJuegoDiario === 'disponible') {
                // Único caso donde el resultado NO viene precalculado desde
                // el contexto: hay que pedirlo al backend antes de animar.
                jugarRuletaDiariaYContinuar();
                return;
            }

            // 'campana' (premio_activo) o 'ganado' (ya jugó hoy y ganó):
            // el resultado ya viene precalculado en los data-* del wrap.
            continuarConResultadoConocido();
        }

        function continuarConResultadoConocido() {
            // Solo animamos el número (%) cuando ese % es real:
            // campaña oficial, o CUPON_5 (5% real). ENVIO_GRATIS y
            // BOLETO_DORADO no tienen un % que mostrar, así que se salta
            // ese paso e igual se reutiliza la MISMA tarjeta de revelación.
            const hayPorcentajeReal = origenPremio === 'campana' || premioTipo === 'CUPON_5';
            if (hayPorcentajeReal) {
                const ruletaUnica = document.getElementById('ofertaInfoRuleta');
                mostrarNumeroConGiro(ruletaUnica, premioPorcentaje);
                setTimeout(() => mostrarFelicidades(), 2600);
            } else {
                setTimeout(() => mostrarFelicidades(), 600);
            }
        }

        function jugarRuletaDiariaYContinuar() {
            fetch(urlJugarRuleta, {
                method: 'POST',
                headers: {
                    'X-CSRFToken': getCookie('csrftoken'),
                    'Content-Type': 'application/x-www-form-urlencoded',
                },
            })
                .then((res) => res.json())
                .then((data) => {
                    if (!data.ok) throw new Error(data.error || 'No se pudo jugar la ruleta');

                    premioTipo = data.resultado;

                    if (data.resultado === 'SIGUE_INTENTANDO') {
                        setTimeout(() => mostrarSinPremioHoy(), 300);
                        return;
                    }

                    if (data.resultado === 'CUPON_5') {
                        premioProducto = 'tu próxima compra';
                        premioPorcentaje = 5;
                    } else if (data.resultado === 'ENVIO_GRATIS') {
                        premioProducto = 'tu próximo pedido';
                        premioPorcentaje = 0;
                    } else if (data.resultado === 'BOLETO_DORADO') {
                        premioProducto = '';
                        premioPorcentaje = 0;
                    }

                    continuarConResultadoConocido();
                })
                .catch(() => {
                    // Si falla el fetch, deshacemos el "bloqueo" visual para
                    // que el usuario pueda reintentar sin recargar la página.
                    sorteoEnCurso = false;
                    botonSortear.disabled = false;
                    botonSortearWrap && botonSortearWrap.classList.add('visible');
                });
        }
        
        function mostrarFelicidades() {
            const overlay = document.getElementById('ofertaRevealOverlay');
            const titulo = document.getElementById('ofertaRevealTitulo');
            const subtitulo = document.getElementById('ofertaRevealSubtitulo');
            const badge = document.getElementById('ofertaRevealBadge');
            const precios = document.getElementById('ofertaRevealPrecios');
            const precioAnterior = document.getElementById('ofertaRevealPrecioAnterior');
            const precioNuevo = document.getElementById('ofertaRevealPrecioNuevo');
            const imagenReveal = document.getElementById('ofertaRevealImagen');
            const iconoReveal = document.getElementById('ofertaRevealIcono');
            const nota = document.getElementById('ofertaRevealNota');

            const esPremioRuletaSinDatosReales = origenPremio === 'ruleta_diaria' && CONFIG_PREMIO_RULETA[premioTipo];
            const config = esPremioRuletaSinDatosReales ? CONFIG_PREMIO_RULETA[premioTipo] : null;

            if (config) {
                // CUPON_5 / ENVIO_GRATIS / BOLETO_DORADO: sin producto/foto
                // real -> ícono en vez de <img>, sin fila de precios.
                if (imagenReveal) imagenReveal.style.display = 'none';
                if (iconoReveal) {
                    iconoReveal.className = `oferta-reveal-icono bi ${config.icono}`;
                    iconoReveal.style.cssText = 'display:flex;align-items:center;justify-content:center;width:100%;height:100%;font-size:3.2rem;color:#c9a84c;';
                }
                if (badge) { badge.style.display = ''; badge.textContent = config.badge; }
                if (titulo) titulo.textContent = config.titulo;
                if (subtitulo) subtitulo.textContent = config.subtitulo();
                if (precios) precios.style.display = 'none';
                if (nota) { nota.textContent = config.nota; nota.style.display = ''; }
            } else {
                // Comportamiento original: premio real de campaña (premio_activo).
                if (iconoReveal) iconoReveal.style.display = 'none';
                if (imagenReveal) {
                    imagenReveal.style.display = '';
                    if (premioImagen) imagenReveal.src = premioImagen;
                }
                if (titulo) titulo.textContent = '¡Felicidades!';
                if (subtitulo) subtitulo.textContent = `Tienes ${premioPorcentaje}% de descuento en ${premioProducto}`;
                if (badge) { badge.style.display = ''; badge.textContent = `-${premioPorcentaje}%`; }
                if (precioAnterior) precioAnterior.textContent = formatearPrecio(premioPrecioOriginal);
                if (precioNuevo) precioNuevo.textContent = formatearPrecio(premioPrecioDescuento);
                if (precios) precios.style.display = '';
                if (nota) nota.style.display = 'none';
            }

            if (overlay) overlay.classList.add('visible');
            lanzarConfetti(90);

            setTimeout(() => cerrarReveal(), 2800);
        }

        function mostrarSinPremioHoy() {
            // Variante "vuelve mañana" tras jugar y salir SIGUE_INTENTANDO.
            // Reusa el MISMO overlay, sin badge ni confetti, sin animación nueva.
            const overlay = document.getElementById('ofertaRevealOverlay');
            const titulo = document.getElementById('ofertaRevealTitulo');
            const subtitulo = document.getElementById('ofertaRevealSubtitulo');
            const badge = document.getElementById('ofertaRevealBadge');
            const precios = document.getElementById('ofertaRevealPrecios');
            const imagenReveal = document.getElementById('ofertaRevealImagen');
            const iconoReveal = document.getElementById('ofertaRevealIcono');
            const nota = document.getElementById('ofertaRevealNota');

            if (imagenReveal) imagenReveal.style.display = 'none';
            if (iconoReveal) {
                iconoReveal.className = 'oferta-reveal-icono bi bi-calendar-heart';
                iconoReveal.style.cssText = 'display:flex;align-items:center;justify-content:center;width:100%;height:100%;font-size:3.2rem;color:#c9a84c;';
            }
            if (badge) badge.style.display = 'none';
            if (titulo) titulo.textContent = 'Sigue intentando';
            if (subtitulo) subtitulo.textContent = 'Hoy no salió premio, vuelve mañana por otra tirada';
            if (precios) precios.style.display = 'none';
            if (nota) nota.style.display = 'none';

            if (overlay) overlay.classList.add('visible');
            // Sin confetti: no hay nada que celebrar acá.

            setTimeout(() => cerrarRevealSinPremio(), 2600);
        }

        function cerrarRevealSinPremio() {
            const overlay = document.getElementById('ofertaRevealOverlay');
            if (overlay) overlay.classList.remove('visible');
            const badge = document.getElementById('ofertaRevealBadge');
            if (badge) badge.style.display = '';

            indicador && indicador.classList.remove('visible');

            sorteoEnCurso = false;
            sorteoHecho = true;
            wrap.classList.add('sorteo-hecho');

            // Se cierra la "ventana"/video del queso, pero se queda encendido (brillando).
            quesosArr.forEach((q) => {
                q.classList.remove('volteado');
                pausarVideoQueso(q);
                q.classList.add('encendido');
            });
            wrap.classList.remove('todos-encendidos');
            detenerConfettiSuave();

            if (ruedaWrap) {
                const texto = ruedaWrap.querySelector('.rueda-descuento');
                const aviso = ruedaWrap.querySelector('.rueda-aviso');
                if (texto) texto.textContent = 'Vuelve mañana';
                if (aviso) aviso.textContent = 'Ya jugaste hoy, inténtalo de nuevo mañana';
                ruedaWrap.classList.add('visible');
            }
            // No se llama a reclamar-premio-dia: SIGUE_INTENTANDO no tiene nada que reclamar.
        }
        
        function cerrarReveal() {
            const overlay = document.getElementById('ofertaRevealOverlay');
            if (overlay) overlay.classList.remove('visible');

            sorteoEnCurso = false;
            sorteoHecho = true;
            wrap.classList.add('sorteo-hecho');

            if (origenPremio === 'campana') {
                guardarOfertaDelDia(premioPorcentaje);
                marcarPremioMostrado(); // avisa al backend: este premio real ya se le mostró al cliente
            } else if (origenPremio === 'ruleta_diaria') {
                reclamarPremioDia(); // aplica el efecto real: cupón/envío en sesión, o marca el boleto dorado
            }

            quesosArr.forEach((q) => {
                q.classList.remove('volteado');
                pausarVideoQueso(q);
            });
            wrap.classList.remove('todos-encendidos');
            detenerConfettiSuave();

            let sumX = 0, sumY = 0, n = 0;
            quesosArr.forEach((q) => {
                sumX += parseFloat(q.dataset.centroX) || 50;
                sumY += parseFloat(q.dataset.centroY) || 50;
                n++;
            });
            const cx = n ? sumX / n : 50;
            const cy = n ? sumY / n : 50;

            // Para campaña, el valor numérico real; para ruleta diaria, null
            // (volarBrilloHaciaBadge arma el texto según premioTipo).
            const valorParaGlobo = origenPremio === 'campana' ? premioPorcentaje : null;
            setTimeout(() => volarBrilloHaciaBadge(cx, cy, valorParaGlobo), 500);
        }

        function reclamarPremioDia() {
            if (!urlReclamarPremioDia) return;
            fetch(urlReclamarPremioDia, {
                method: 'POST',
                headers: {
                    'X-CSRFToken': getCookie('csrftoken'),
                    'Content-Type': 'application/x-www-form-urlencoded',
                },
            }).catch(() => {
                // silencioso, igual que marcarPremioMostrado: si falla, el
                // cliente ya vio la animación igual, y puede reintentar
                // reclamar desde la tarjeta del listado de productos.
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
                if (texto) {
                    if (valor !== null) {
                        texto.textContent = `${valor}% de descuento hoy`;
                    } else {
                        const textos = {
                            CUPON_5: '5% de descuento hoy',
                            ENVIO_GRATIS: 'Envío gratis hoy',
                            BOLETO_DORADO: 'Boleto dorado hoy',
                        };
                        texto.textContent = textos[premioTipo] || 'Premio de hoy reclamado';
                    }
                }
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
                const fy = Math.sin(angulo) * distancia - 10;

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

        if (!sorteoHecho) {
            setTimeout(() => indicador && indicador.classList.add('visible'), 900);
        }

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

        // --- Goteo suave de confetti dorado mientras están los 3 quesos encendidos ---
        const coloresSuaves = ['#f0d98a', '#ffe9a8', '#c9a84c', '#ffd966'];
        let confettiSuaveTimer = null;

        function lanzarConfettiSuavePieza() {
            if (!confettiWrap) return;
            const pieza = document.createElement('span');
            pieza.className = 'confetti-pieza-suave';
            pieza.style.left = Math.random() * 100 + '%';
            pieza.style.background = coloresSuaves[Math.floor(Math.random() * coloresSuaves.length)];
            pieza.style.width = (3 + Math.random() * 3) + 'px';
            pieza.style.height = (6 + Math.random() * 5) + 'px';
            pieza.style.animationDuration = (4.5 + Math.random() * 2.5) + 's';
            pieza.style.boxShadow = '0 0 6px rgba(240, 217, 138, 0.9)';
            confettiWrap.appendChild(pieza);
            pieza.addEventListener('animationend', () => pieza.remove());
        }

        function iniciarConfettiSuave() {
            if (confettiSuaveTimer) return;
            lanzarConfettiSuavePieza();
            confettiSuaveTimer = setInterval(lanzarConfettiSuavePieza, 550);
        }

        function detenerConfettiSuave() {
            clearInterval(confettiSuaveTimer);
            confettiSuaveTimer = null;
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
            if (sorteoHecho) return; // ya jugó hoy: nada que reventar/animar de nuevo
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
                    quesosArr.forEach((q) => {
                        q.classList.remove('volteado');
                        pausarVideoQueso(q);
                    });
                    wrap.classList.remove('todos-encendidos');
                    botonSortearWrap && botonSortearWrap.classList.remove('visible');
                }

                if (vistos.size === quesosArr.length && !sorteoHecho) {
                    quesosArr.forEach((q) => q.classList.add('volteado'));
                    wrap.classList.add('todos-encendidos');
                    reproducirTodosSincronizados();
                    iniciarConfettiSuave();
                
                    const tarjetaDescuento = document.getElementById('ofertaDescuentoTarjeta');
                    const ruletaUnica = document.getElementById('ofertaInfoRuleta');
                    if (tarjetaDescuento) tarjetaDescuento.classList.add('visible');
                    if (ruletaUnica) mostrarNumeroFijo(ruletaUnica, premioPorcentaje);

                    mostrarBotonSortear();
                } else {
                    wrap.classList.remove('todos-encendidos');
                    detenerConfettiSuave();
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

        function estrellasHtml(p) {
            const anon = !window.LZ_USUARIO_AUTENTICADO;
            let estrellas = '';
            for (let v = 1; v <= 5; v++) {
                estrellas += `<i class="bi bi-star estrella-pub" data-valor="${v}"></i>`;
            }
            return `
                <div class="calificacion-widget-pub ${anon ? 'anonima' : ''}" data-producto-id="${p.id}"
                     data-mi-calificacion="${p.mi_calificacion || 0}" data-anon="${anon}">
                    ${estrellas}
                    <span class="calificacion-promedio-pub">${p.promedio_calificacion != null ? p.promedio_calificacion : '—'}</span>
                    <span class="calificacion-total-pub">(${p.total_calificaciones || 0})</span>
                </div>`;
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
                                ${estrellasHtml(p)}
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
                            ${estrellasHtml(p)}
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
            window.LZ_activarWidgetsCalificacion && window.LZ_activarWidgetsCalificacion(lista);
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

(function () {
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

    document.querySelectorAll('.boton-reclamar-premio-dia').forEach((btn) => {
        btn.addEventListener('click', () => {
            const url = btn.dataset.urlReclamarPremioDia;
            if (!url) return;
            btn.disabled = true;
            fetch(url, {
                method: 'POST',
                headers: {
                    'X-CSRFToken': getCookie('csrftoken'),
                    'Content-Type': 'application/x-www-form-urlencoded',
                },
            })
                .then((res) => res.json())
                .then((data) => {
                    if (data.ok) {
                        // Recargamos para que la tarjeta pase a mostrar
                        // "Ya reclamado" y el contexto (cupón/envío en
                        // sesión) quede reflejado en el resto de la página.
                        window.location.reload();
                    } else {
                        btn.disabled = false;
                    }
                })
                .catch(() => { btn.disabled = false; });
        });
    });

    (function () {
        const csrfTokenPub = (function(){
            const nombre = 'csrftoken';
            let valor = null;
            document.cookie.split(';').forEach(function(c){
                c = c.trim();
                if (c.indexOf(nombre + '=') === 0) valor = decodeURIComponent(c.substring(nombre.length + 1));
            });
            return valor;
        })();
    
        function activarWidgetsCalificacion(root) {
            (root || document).querySelectorAll('.calificacion-widget-pub').forEach(function(widget){
                if (widget.dataset.activado) return;
                widget.dataset.activado = '1';
            
                const estrellas = widget.querySelectorAll('.estrella-pub');
                let miCalificacion = parseInt(widget.dataset.miCalificacion) || 0;
            
                function pintar(valor){
                    estrellas.forEach(function(e){
                        const activa = parseInt(e.dataset.valor) <= valor;
                        e.classList.toggle('activa', activa);
                        e.classList.toggle('bi-star-fill', activa);
                        e.classList.toggle('bi-star', !activa);
                    });
                }
                pintar(miCalificacion);
            
                estrellas.forEach(function(estrella){
                    estrella.addEventListener('mouseenter', function(){ pintar(parseInt(estrella.dataset.valor)); });
                    estrella.addEventListener('mouseleave', function(){ pintar(miCalificacion); });
                    estrella.addEventListener('click', function(e){
                        e.preventDefault();

                        if (widget.dataset.anon === 'true') {
                            const modalEl = document.getElementById('modalPromoRegistro');
                            if (modalEl && window.bootstrap) {
                                bootstrap.Modal.getOrCreateInstance(modalEl).show();
                            }
                            return;
                        }
                        
                        const valor = parseInt(estrella.dataset.valor);
                        const productoId = widget.dataset.productoId;
                    
                        fetch(`/productos/producto/${productoId}/calificar/`, {
                            method: 'POST',
                            headers: {
                                'X-CSRFToken': csrfTokenPub,
                                'Content-Type': 'application/x-www-form-urlencoded',
                            },
                            body: `puntaje=${valor}`,
                        })
                        .then(function(resp){ return resp.json(); })
                        .then(function(data){
                            if (!data.ok) return;
                            miCalificacion = valor;
                            widget.dataset.miCalificacion = valor;
                            pintar(valor);
                            const promedioEl = widget.querySelector('.calificacion-promedio-pub');
                            const totalEl = widget.querySelector('.calificacion-total-pub');
                            if (promedioEl) promedioEl.textContent = data.promedio;
                            if (totalEl) totalEl.textContent = `(${data.total})`;
                        })
                        .catch(function(){ console.error('No se pudo guardar la calificación.'); });
                    });
                });
            });
        }
    
        document.addEventListener('DOMContentLoaded', function(){ activarWidgetsCalificacion(); });
        window.LZ_activarWidgetsCalificacion = activarWidgetsCalificacion;
    })();
})();