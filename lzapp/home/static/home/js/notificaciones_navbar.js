document.addEventListener('DOMContentLoaded', function () {
    // navbarActionsMobile clona el HTML del bloque desktop (ver script de
    // clonado más abajo en masterpage.html), así que puede haber dos copias
    // de ".notif-dropdown-menu" en el DOM (desktop + mobile) con los mismos
    // ids/data-* repetidos. Enlazamos ambas por separado en vez de asumir una sola.
    const menus = document.querySelectorAll('.notif-dropdown-menu');
    if (!menus.length) return;

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

    function peticionPost(url) {
        return fetch(url, {
            method: 'POST',
            headers: {
                'X-CSRFToken': getCookie('csrftoken'),
                'X-Requested-With': 'XMLHttpRequest',
            },
        });
    }

    // La campana se refresca sola: si el pedido cambia de estado mientras
    // el cliente está en la página, el aviso aparece sin recargar.
    const URL_API = menus[0].dataset.urlApi;

    function repintarMenu(menu, datos) {
        const lista = menu.querySelector('.notif-lista');
        if (!lista) return;

        if (datos.notificaciones.length === 0) {
            lista.innerHTML = `
                <div class="notif-vacio">
                    <i class="bi bi-bell-slash"></i>
                    <p>No tienes notificaciones por ahora.</p>
                </div>`;
        } else {
            lista.innerHTML = datos.notificaciones.map(n => `
                <a href="${n.url || '#'}"
                   class="notif-item tipo-${n.tipo}${n.leida ? '' : ' no-leida'}"
                   data-id="${n.id}">
                    <i class="bi ${n.icono}"></i>
                    <div class="notif-item-texto">
                        ${n.titulo ? `<strong>${n.titulo}</strong>` : ''}
                        <p>${n.mensaje}</p>
                        <span class="notif-item-fecha">${n.hace} atrás</span>
                    </div>
                </a>`).join('');
        }

        enlazarItems(menu);
    }

    function repintarBadge(menu, noLeidas) {
        const disparador = menu.previousElementSibling;
        if (!disparador) return;

        let badge = disparador.querySelector('.carrito-badge');
        if (noLeidas > 0) {
            if (!badge) {
                badge = document.createElement('span');
                badge.className = 'carrito-badge';
                disparador.appendChild(badge);
            }
            badge.textContent = noLeidas;
        } else if (badge) {
            badge.remove();
        }
    }

    async function refrescarNotificaciones() {
        if (!URL_API) return;
        try {
            const respuesta = await fetch(URL_API);
            const datos = await respuesta.json();
            menus.forEach((menu) => {
                repintarBadge(menu, datos.no_leidas);
                repintarMenu(menu, datos);
            });
        } catch (error) {
            console.error('Error refrescando notificaciones:', error);
        }
    }

    function enlazarItems(menu) {
        const urlMarcarLeidaPlantilla = menu.dataset.urlMarcarLeida;

        menu.querySelectorAll('.notif-item').forEach((item) => {
            item.addEventListener('click', (e) => {
                const id = item.dataset.id;
                if (item.getAttribute('href') === '#') e.preventDefault();
                if (id && urlMarcarLeidaPlantilla) {
                    peticionPost(urlMarcarLeidaPlantilla.replace('/0/', '/' + id + '/'));
                }
            });
        });
    }

    setInterval(refrescarNotificaciones, 15000);

    menus.forEach((menu) => {
        // Al hacer clic en una notificación puntual, se marca como leída.
        enlazarItems(menu);

        const btnTodas = menu.querySelector('.notif-marcar-todas');
        if (btnTodas) {
            btnTodas.addEventListener('click', (e) => {
                e.stopPropagation();
                peticionPost(menu.dataset.urlMarcarTodas).then(refrescarNotificaciones);
            });
        }
    });
});
