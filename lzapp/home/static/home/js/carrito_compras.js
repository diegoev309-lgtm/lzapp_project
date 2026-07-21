        document.querySelectorAll('.favorito').forEach(btn => {
            btn.addEventListener('click', () => {
                btn.classList.toggle('activo');
                const icono = btn.querySelector('i');
                icono.classList.toggle('bi-heart');
                icono.classList.toggle('bi-heart-fill');
            });
        });
        document.querySelectorAll('.producto-desc-toggle').forEach(btn => {
            btn.addEventListener('click', () => {
                btn.closest('.producto-card').classList.toggle('abierta');
            });
        });

        /* ---- Buscador en vivo: filtra directamente el grid de productos ---- */
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
            const URL_AGREGAR_BASE = wrapper.dataset.urlAgregarBase; // ej: /carro/agregar/1/
            let timer = null;
        
            function escapeHtml(str) {
                const div = document.createElement('div');
                div.textContent = str;
                return div.innerHTML;
            }
        
            function urlAgregar(id) {
                // Reemplaza el ID de ejemplo (el último segmento numérico) por el ID real
                return URL_AGREGAR_BASE.replace(/\/1\/?$/, `/${id}/`);
            }
        
            function tarjetaHtml(p) {
                const stockBajo = p.stock_actual <= p.stock_minimo;
                const badge = stockBajo
                    ? `<span class="badge-stock bajo">Stock bajo</span>`
                    : `<span class="badge-stock disponible">Disponible</span>`;
            
                const descripcion = p.descripcion && p.descripcion.trim()
                    ? escapeHtml(p.descripcion)
                    : 'Producto elaborado con los más altos estándares de calidad, fresco y natural.';
            
                return `
                    <div class="col-12">
                        <div class="card producto-card">
                            <div class="producto-img-wrapper">
                                ${badge}
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
                                    <p class="producto-descripcion">${descripcion}</p>
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