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