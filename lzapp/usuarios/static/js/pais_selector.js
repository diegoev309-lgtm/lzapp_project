/* ============================================================
   pais_selector.js — LzApp
   Reemplaza VISUALMENTE el <select id="id_codigo_pais"> (que Django ya
   arma con las opciones de CODIGOS_PAIS) por un selector propio con
   banderas de verdad -- SVG de la librería flag-icons (cargada por CDN
   en el <head> de cada página), en vez del emoji de bandera dentro de
   un <option>, que en varios sistemas (Windows entre ellos) no se ve
   como bandera sino como texto plano ("CO").

   El <select> original NO se elimina: sigue existiendo oculto y es el
   que de verdad viaja con el formulario -- este script solo lo
   sincroniza con la UI nueva (clic en una opción -> cambia el value
   del select real y dispara 'change', para que
   telefono_validacion.js/los demás listeners de "cambio de país"
   sigan funcionando igual que antes).

   Compartido entre registro.html, registro_empleado.html y
   configuracion.html -- basta con que la página tenga un
   <select id="id_codigo_pais"> ya armado por Django.
   ============================================================ */
document.addEventListener('DOMContentLoaded', function () {
    const selectOriginal = document.getElementById('id_codigo_pais');
    if (!selectOriginal) return;

    // Código de país -> código ISO de 2 letras, para la clase de
    // flag-icons (ej. "co" -> .fi-co). Tiene que cubrir las mismas
    // opciones que CODIGOS_PAIS en usuarios/forms.py.
    const ISO_POR_CODIGO = {
        '+57': 'co',
        '+1': 'us',
        '+52': 'mx',
        '+58': 've',
        '+593': 'ec',
        '+51': 'pe',
        '+56': 'cl',
        '+54': 'ar',
        '+507': 'pa',
        '+506': 'cr',
        '+55': 'br',
        '+34': 'es',
    };

    function crearBandera(codigo) {
        const span = document.createElement('span');
        span.className = 'fi fi-' + (ISO_POR_CODIGO[codigo] || 'xx') + ' pais-selector__bandera';
        return span;
    }

    // El texto del <option> puede venir como "🇨🇴 +57" (emoji + código);
    // nos quedamos solo con la parte "+57" -- la bandera la dibuja este
    // script aparte con flag-icons, no hace falta el emoji del texto.
    function soloCodigo(textoOpcion, valorOpcion) {
        const limpio = (textoOpcion || '').replace(/[^+0-9]/g, '').trim();
        return limpio || valorOpcion;
    }

    function opcionesDesdeSelect() {
        return Array.from(selectOriginal.options).map(function (opt) {
            return { valor: opt.value, texto: soloCodigo(opt.textContent, opt.value) };
        });
    }

    const opciones = opcionesDesdeSelect();

    const contenedor = document.createElement('div');
    contenedor.className = 'pais-selector';

    const boton = document.createElement('button');
    boton.type = 'button';
    boton.className = 'pais-selector__boton';
    boton.setAttribute('aria-haspopup', 'listbox');
    boton.setAttribute('aria-expanded', 'false');

    const lista = document.createElement('ul');
    lista.className = 'pais-selector__lista';
    lista.setAttribute('role', 'listbox');
    lista.hidden = true;

    function pintarBoton() {
        const actual = opciones.find(function (o) { return o.valor === selectOriginal.value; }) || opciones[0];
        boton.innerHTML = '';
        boton.appendChild(crearBandera(actual.valor));
        const codigoSpan = document.createElement('span');
        codigoSpan.className = 'pais-selector__codigo';
        codigoSpan.textContent = actual.texto;
        boton.appendChild(codigoSpan);
        const chevron = document.createElement('i');
        chevron.className = 'bi bi-chevron-down pais-selector__chevron';
        boton.appendChild(chevron);
    }

    function construirLista() {
        opciones.forEach(function (opcion) {
            const li = document.createElement('li');
            li.setAttribute('role', 'option');
            li.className = 'pais-selector__opcion';
            li.dataset.valor = opcion.valor;
            li.appendChild(crearBandera(opcion.valor));
            const span = document.createElement('span');
            span.textContent = opcion.texto;
            li.appendChild(span);
            li.addEventListener('click', function () {
                if (selectOriginal.value !== opcion.valor) {
                    selectOriginal.value = opcion.valor;
                    selectOriginal.dispatchEvent(new Event('change', { bubbles: true }));
                }
                pintarBoton();
                cerrarLista();
            });
            lista.appendChild(li);
        });
    }

    function abrirLista() {
        lista.hidden = false;
        boton.setAttribute('aria-expanded', 'true');
    }
    function cerrarLista() {
        lista.hidden = true;
        boton.setAttribute('aria-expanded', 'false');
    }

    boton.addEventListener('click', function (e) {
        e.stopPropagation();
        if (lista.hidden) abrirLista(); else cerrarLista();
    });
    document.addEventListener('click', function (e) {
        if (!lista.hidden && !contenedor.contains(e.target)) cerrarLista();
    });

    construirLista();
    pintarBoton();

    contenedor.appendChild(boton);
    contenedor.appendChild(lista);
    selectOriginal.insertAdjacentElement('afterend', contenedor);
    selectOriginal.classList.add('pais-selector-input-real');
});
