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

    menus.forEach((menu) => {
        const urlMarcarLeidaPlantilla = menu.dataset.urlMarcarLeida; // .../0/marcar-leida/
        const urlMarcarTodas = menu.dataset.urlMarcarTodas;

        // Al hacer clic en una notificación puntual, se marca como leída.
        // Si no tiene enlace propio (url vacía => href="#"), no navega.
        menu.querySelectorAll('.notif-item').forEach((item) => {
            item.addEventListener('click', (e) => {
                const id = item.dataset.id;
                if (item.getAttribute('href') === '#') e.preventDefault();
                if (id && urlMarcarLeidaPlantilla) {
                    peticionPost(urlMarcarLeidaPlantilla.replace('/0/', '/' + id + '/'));
                }
            });
        });

        const btnTodas = menu.querySelector('.notif-marcar-todas');
        if (btnTodas) {
            btnTodas.addEventListener('click', (e) => {
                e.stopPropagation();
                peticionPost(urlMarcarTodas).then(() => {
                    // Refresca la página para reflejar el estado "leídas" en el menú.
                    window.location.reload();
                });
            });
        }
    });
});
