/* ============================================================
   carrito_ajax.js — LzApp
   Compartido entre las páginas de productos (masterpage.html) y el
   carrito (carrito_compras.html): agregar al carrito con un solo clic,
   sin recargar la página. Reutiliza el mismo sistema de toasts
   (.lz-toast) que ya usa masterpage.html para los mensajes de Django,
   por si la página donde se hace clic no tiene ninguno todavía.
   ============================================================ */

function mostrarToastCarrito(mensaje, tipo) {
    tipo = tipo || 'success';

    let contenedor = document.getElementById('lzToasts');
    if (!contenedor) {
        contenedor = document.createElement('div');
        contenedor.className = 'lz-toasts';
        contenedor.id = 'lzToasts';
        document.body.appendChild(contenedor);
    }

    const iconos = {
        success: 'bi-check-circle-fill',
        error: 'bi-x-circle-fill',
        danger: 'bi-x-circle-fill',
        warning: 'bi-exclamation-triangle-fill',
        info: 'bi-info-circle-fill',
    };

    const toast = document.createElement('div');
    toast.className = 'lz-toast lz-toast--' + tipo;
    toast.innerHTML =
        '<i class="bi ' + (iconos[tipo] || iconos.info) + '"></i>' +
        '<span></span>' +
        '<button type="button" class="lz-toast__cerrar" aria-label="Cerrar"><i class="bi bi-x"></i></button>';
    toast.querySelector('span').textContent = mensaje;
    contenedor.appendChild(toast);

    function cerrarToast() {
        toast.classList.add('lz-toast--saliendo');
        setTimeout(() => toast.remove(), 300);
    }
    toast.querySelector('.lz-toast__cerrar').addEventListener('click', cerrarToast);
    setTimeout(cerrarToast, 4000);
}

/* Actualiza cualquier indicador de "hay productos en el carrito" presente
   en la página actual -- el ícono de la navbar (.nav-link-carrito, en
   clients.html y en el navbar propio de carrito_compras.html) y, si está
   el widget del carrito cargado, sus contadores. */
function actualizarIndicadorCarrito(cantidadItems) {
    document.querySelectorAll('.nav-link-carrito').forEach((el) => {
        el.classList.toggle('tiene-items', cantidadItems > 0);
    });
    document.querySelectorAll('.carrito-widget__count').forEach((el) => {
        el.textContent = cantidadItems;
    });
    document.querySelectorAll('.carrito-toggle__count').forEach((el) => {
        el.textContent = cantidadItems;
        el.style.display = cantidadItems > 0 ? '' : 'none';
    });
}

document.addEventListener('DOMContentLoaded', function () {
    // Un solo listener delegado: funciona tanto para los botones que ya
    // vienen en el HTML del servidor como para los que arma el JS de
    // búsqueda en vivo (masterpage.html/carrito_compras.html), sin tener
    // que engancharlo de nuevo cada vez que se re-arma la grilla.
    document.addEventListener('click', function (evento) {
        // Si otro listener (ej. el bloqueo de "inicia sesión para comprar"
        // de usuarios anónimos en masterpage.html) ya llamó
        // preventDefault() sobre este mismo clic, no seguimos -- ese
        // listener corre antes que este porque está pegado directo al
        // botón, no delegado en document.
        if (evento.defaultPrevented) return;

        const boton = evento.target.closest('.btn-carrito[data-producto-id]');
        if (!boton || boton.disabled) return;

        evento.preventDefault();

        const base = document.querySelector('[data-url-agregar-base]');
        if (!base) return; // si no hay URL base en esta página, no hay nada que hacer

        const url = base.dataset.urlAgregarBase.replace(/\/1\/?$/, '/' + boton.dataset.productoId + '/');
        const codigoPremio = boton.dataset.premio;
        const urlFinal = codigoPremio ? url + '?premio=' + encodeURIComponent(codigoPremio) : url;

        boton.disabled = true;
        const contenidoOriginal = boton.innerHTML;
        boton.innerHTML = '<i class="bi bi-hourglass-split"></i> Agregando...';

        fetch(urlFinal, { headers: { 'X-Requested-With': 'XMLHttpRequest' } })
            .then((respuesta) => respuesta.json())
            .then((datos) => {
                if (!datos.ok) {
                    mostrarToastCarrito(datos.error || 'No se pudo agregar el producto.', 'error');
                    return;
                }
                mostrarToastCarrito('Se agregó al carrito.', 'success');
                actualizarIndicadorCarrito(datos.cantidad_items);
            })
            .catch(function () {
                mostrarToastCarrito('No se pudo agregar el producto. Intenta de nuevo.', 'error');
            })
            .finally(function () {
                boton.disabled = false;
                boton.innerHTML = contenidoOriginal;
            });
    });
});
