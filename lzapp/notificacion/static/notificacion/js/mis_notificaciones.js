document.addEventListener('DOMContentLoaded', function () {
    const lista = document.querySelector('.mn-lista');
    if (!lista) return;

    const urlMarcarLeidaPlantilla = lista.dataset.urlMarcarLeida; // .../0/marcar-leida/

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

    // Al hacer clic en una notificación puntual, se marca como leída.
    // Si no tiene enlace propio (url vacía => href="#"), no navega.
    lista.querySelectorAll('.mn-item').forEach((item) => {
        item.addEventListener('click', (e) => {
            const id = item.dataset.id;
            if (item.getAttribute('href') === '#') e.preventDefault();
            if (id && urlMarcarLeidaPlantilla) {
                peticionPost(urlMarcarLeidaPlantilla.replace('/0/', '/' + id + '/'));
            }
        });
    });

    const btnTodas = document.getElementById('mnMarcarTodasLeidas');
    if (btnTodas) {
        btnTodas.addEventListener('click', () => {
            peticionPost(btnTodas.dataset.url).then(() => {
                window.location.reload();
            });
        });
    }
});
