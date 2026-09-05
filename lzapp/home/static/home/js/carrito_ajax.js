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
   clients.html/users.html y en el navbar propio de carrito_compras.html),
   su badge numérico, y el contador dentro del encabezado del panel. */
function actualizarIndicadorCarrito(cantidadItems) {
    document.querySelectorAll('.nav-link-carrito').forEach((el) => {
        el.classList.toggle('tiene-items', cantidadItems > 0);
    });
    // Ojo: .carrito-badge también la usa la campana de notificaciones,
    // por eso el selector va acotado a la que está dentro del ícono del
    // carrito -- no queremos tocar la de notificaciones acá.
    document.querySelectorAll('.nav-link-carrito .carrito-badge').forEach((el) => {
        el.textContent = cantidadItems > 99 ? '99+' : cantidadItems;
        el.classList.toggle('visible', cantidadItems > 0);
    });
    document.querySelectorAll('.carrito-widget__count').forEach((el) => {
        el.textContent = cantidadItems;
    });
}

/* Badge redondo tipo "notificación" pegado a la tarjeta de cada producto
   en la grilla (esquina de la imagen), con la cantidad que ese producto
   puntual tiene en el carrito ahora mismo. */
function actualizarBadgeProducto(productoId, cantidad) {
    document.querySelectorAll('.producto-card-badge[data-producto-id="' + productoId + '"]').forEach((badge) => {
        badge.textContent = cantidad > 99 ? '99+' : cantidad;
        const yaVisible = badge.classList.contains('visible');
        badge.classList.toggle('visible', cantidad > 0);
        if (cantidad > 0 && yaVisible) {
            badge.classList.remove('producto-card-badge--rebote');
            void badge.offsetWidth; // reinicia la animación aunque ya estuviera visible
            badge.classList.add('producto-card-badge--rebote');
        }
    });
}

/* Aplica el resultado de CUALQUIER acción del carrito (agregar desde la
   grilla, +/- o vaciar desde el widget) a toda la UI que pueda estar
   presente en la página actual: badge de la navbar, la lista + total +
   footer del widget (si está incluido en esta página) y
   el badge de cantidad sobre la tarjeta del producto en la grilla. Se
   centraliza acá para que ambos flujos queden siempre sincronizados sin
   duplicar la lógica de actualización en dos sitios distintos -- antes
   cada uno actualizaba solo una parte, por eso un producto agregado
   desde la grilla nunca aparecía en el carrito sin recargar la página.
   `datos` es la respuesta JSON de cualquiera de los endpoints de
   carrito (agregar/restar/eliminar/limpiar), que siempre trae
   cantidad_items, total y lista_html; `productoId` es opcional (no
   aplica para "vaciar carrito"). */
function aplicarRespuestaCarrito(datos, productoId) {
    actualizarIndicadorCarrito(datos.cantidad_items);

    if (typeof datos.lista_html === 'string') {
        const lista = document.getElementById('carritoLista');
        if (lista) {
            lista.innerHTML = datos.lista_html;
            if (productoId) {
                const fila = lista.querySelector('.carrito-item[data-producto-id="' + productoId + '"]');
                if (fila) {
                    fila.classList.add('carrito-item--resaltado');
                    setTimeout(() => fila.classList.remove('carrito-item--resaltado'), 900);
                }
            }
        }
    }

    const footer = document.querySelector('.carrito-widget__footer');
    if (footer) footer.style.display = datos.cantidad_items > 0 ? '' : 'none';

    if (typeof datos.total !== 'undefined') {
        const totalEl = document.querySelector('.carrito-widget__total strong');
        if (totalEl) {
            totalEl.textContent = '$ ' + Number(datos.total).toLocaleString('es-CO', {
                minimumFractionDigits: 2, maximumFractionDigits: 2,
            }) + ' COP';
        }
    }

    if (productoId) {
        actualizarBadgeProducto(productoId, datos.item ? datos.item.cantidad : 0);
    }
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
                aplicarRespuestaCarrito(datos, boton.dataset.productoId);
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
