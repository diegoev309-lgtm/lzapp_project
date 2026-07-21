/* ---- Navbar scroll effect ---- */
    const nav = document.getElementById('mainNav');
    window.addEventListener('scroll', () => {
        nav.classList.toggle('scrolled', window.scrollY > 60);
    });
    /* ---- Parallax 3D con el mouse en el hero ---- */
    (function () {
        const hero = document.querySelector('#inicio .hero');
        if (!hero || window.matchMedia('(prefers-reduced-motion: reduce)').matches) return;
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
        const track = document.getElementById('carruselTrack');
        const prevBtn = document.getElementById('carruselPrev');
        const nextBtn = document.getElementById('carruselNext');
        const puntos = document.querySelectorAll('.carrusel-punto');
        const progreso = document.getElementById('carruselProgreso');
        if (!track) return;
        const slides = track.querySelectorAll('.carrusel-slide');
        const total = slides.length;
        let actual = 0;
        const DURACION_AUTOPLAY = 6000;
        let autoplayTimer = null;
        let progresoTimeout = null;
        function irA(indice) {
            actual = (indice + total) % total;
            track.style.transform = `translateX(-${actual * 100}%)`;
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
                clearInterval(autoplayTimer);
                progreso && progreso.classList.remove('animando');
            });
            heroCarrusel.addEventListener('mouseleave', () => {
                reiniciarAutoplay();
            });
        }
        if (window.matchMedia('(prefers-reduced-motion: reduce)').matches) {
            irA(0);
        } else {
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

/* ---- Buscador en vivo (tabla con imagen, nombre y precio) ---- */
    (function () {
        const wrapper = document.querySelector('.buscador-wrapper');
        const input = document.getElementById('inputBuscador');
        const resultadosBox = document.getElementById('buscadorResultados');
        if (!wrapper || !input || !resultadosBox) return;
    
        const URL_BUSCAR = wrapper.dataset.urlAjax;
        let timer = null;
    
        function escapeHtml(str) {
            const div = document.createElement('div');
            div.textContent = str;
            return div.innerHTML;
        }
    
        function renderResultados(data) {
            const productos = data.productos || [];
        
            if (productos.length === 0) {
                resultadosBox.innerHTML = `<div class="sin-resultados">No se encontraron productos.</div>`;
                resultadosBox.classList.add('activo');
                return;
            }
        
            const filas = productos.map(p => `
                <tr data-nombre="${escapeHtml(p.nombre)}">
                    <td class="col-img"><img src="${p.imagen}" alt="${escapeHtml(p.nombre)}"></td>
                    <td class="col-nombre">${escapeHtml(p.nombre)}</td>
                    <td class="col-precio">$ ${Number(p.precio).toLocaleString('es-CO')}</td>
                </tr>
            `).join('');
            
            resultadosBox.innerHTML = `<table><tbody>${filas}</tbody></table>`;
            resultadosBox.classList.add('activo');
            
            resultadosBox.querySelectorAll('tr').forEach(tr => {
                tr.addEventListener('click', () => {
                    input.value = tr.dataset.nombre;
                    document.getElementById('formBuscador').submit();
                });
            });
        }
    
        input.addEventListener('input', () => {
            clearTimeout(timer);
            const q = input.value.trim();
        
            if (!q) {
                resultadosBox.classList.remove('activo');
                resultadosBox.innerHTML = '';
                return;
            }
        
            resultadosBox.innerHTML = `<div class="cargando">Buscando...</div>`;
            resultadosBox.classList.add('activo');
        
            timer = setTimeout(() => {
                fetch(`${URL_BUSCAR}?q=${encodeURIComponent(q)}`)
                    .then(res => res.json())
                    .then(renderResultados)
                    .catch(() => {
                        resultadosBox.innerHTML = `<div class="sin-resultados">Ocurrió un error al buscar.</div>`;
                    });
            }, 300);
        });
    
        input.addEventListener('focus', () => {
            if (input.value.trim() && resultadosBox.innerHTML.trim()) {
                resultadosBox.classList.add('activo');
            }
        });
    
        document.addEventListener('click', (e) => {
            if (!wrapper.contains(e.target)) {
                resultadosBox.classList.remove('activo');
            }
        });
    })();