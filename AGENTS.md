## Core Commands
- `python manage.py runserver` – start development server
- `python manage.py makemigrations` – create migrations
- `python manage.py migrate` – apply migrations
- `python manage.py test` – run test suite
- `python manage.py createsuperuser` – create admin user
- `python manage.py collectstatic` – collect static files

## Settings
- Settings module: `lzapp.settings`
- Activate virtual environment before installing packages

## Gotchas
- SQLite is used; always run migrations after model changes.
- Run `makemigrations` before `migrate`.
- Tests are executed with `python manage.py test`.

# Proyecto LzApp – Arquitectura, Apps y Endpoints

## 1. Aplicaciones principales

### **home**
- **Objetivo**: Pantalla principal, catálogo de productos, carrito de compras y búsqueda en vivo.  
- **Vistas** (`home/views.py`):  
  - `buscar_productos` – filtra por `?q=` usando sólo `nombre__icontains`.  
  - `buscar_productos_ajax` – devuelve JSON para la búsqueda en tiempo real.  
  - `main` – renderiza `home/home.html` con ofertas destacadas.  
  - `user`, `client`, `carro` – renderizan páginas de usuarios, clientes y carrito.  
- **Plantillas** (`home/templates/`):  
  - `home.html` – layout base.  
  - `carrito_compras.html` – contiene el buscador y el grid de productos.  
- **URLs** (`home/urls.py`):  
  - `path('main', main)`  
  - `path('buscar-ajax/', buscar_productos_ajax, name='buscar_ajax')`  
  - `path('user', user)`, `path('client', client)`, `path('carro', carro)`.  
- **Problemas detectados**:  
  - **Superposición de la barra de navegación** sobre el buscador (CSS `margin-right: 340px` + `right: 340px`).  
  - **Endpoint no incluido** en versiones previas → 404 al acceder a `/buscar-ajax/` (se soluciona con `path('', include('home.urls'))` en el `urls.py` del proyecto).  

### **carrito**
- **Objetivo**: Mini‑widget de carrito y página `carrito_compras.html`.  
- **Files**: `carrito/widgets.html`, `carrito/urls.py`, `carrito/views.py` (si los tiene).  
- **No se hallaron errores críticos** más allá del layout del buscador.

### **dashboard**
- Funcionalidad de paneles de administración / reporting (no inspeccionada).  

### **descuentos**, **producto**, **usuarios**, **produccion**, **descuentos**, etc.
- Cada una sigue la convención típica `urls.py → views.py → templates/`.  
- No se detectaron fallos de configuración relevantes.

## 2. Configuración de URLs del proyecto

`lzapp/urls.py` (raíz del proyecto)

```python
urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('home.urls')),          # <-- Punto de entrada principal
    path('usuarios/', include('usuarios.urls')),
    path('carro/', include('carrito.urls')),
    path('', include('dashboard.urls')),
    path('productos/', include('producto.urls')),
    path('descuentos/', include('descuentos.urls')),
    path('producciones/', include('produccion.urls')),
]

urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
Requisito crítico: la línea path('', include('home.urls')) debe estar presente; de lo contrario, rutas como /buscar-ajax/ devolvieren 404.
3. Endpoints externos usados en carrito_compras.html
dato	URL generada	Vista destinataria
data-url-ajax	{% url 'buscar_ajax' %}	home.views.buscar_productos_ajax
data-url-agregar-base	{% url 'carro:agregar' 1 %}	base para generar URLs de “agregar” por producto
4. Errores principales y solución propuesta
1. Superposición del navbar sobre el buscador  
- Causa: reglas CSS body { margin-right: 340px; } y #mainNav.navbar.fixed-top { right: 340px; } se aplican sin límite de breakpoint.  
- Solución: envolver esas reglas en @media (min-width: 992px) y, si se necesita forzar, usar !important sólo en ese rango; o bien eliminar margin-right y usar un contenedor flexible (p. ej. col-md-8 offset-md-4) para el contenido principal.
2. Endpoint buscar_ajax no accesible (solo si home.urls no estaba incluido).  
- Solución: asegurarse de que lzapp/urls.py contenga path('', include('home.urls')).
3. Posible inconsistencia de contexto entre la vista buscar_productos_ajax y la plantilla:  
- La vista devuelve {"productos": resultados, "query": query}; el JavaScript de la página espera exactamente esa clave (productos). Mantener el nombre garantiza que la búsqueda siga funcionando.
5. Requisitos de prueba rápida
1. Comprobar la API de búsqueda  
curl http://localhost:8000/buscar-ajax/?q=leche
- Debe devolver JSON con productos y query.  
- Si retorna 404, revisar la inclusión de home.urls.
2. Verificar el layout en diferentes resoluciones  
- Redimensionar a < 992 px → el buscador ya no queda tapado.  
- ≥ 992 px → aplicar la regla @media (min-width: 992px) para que body y navbar no se solapen.