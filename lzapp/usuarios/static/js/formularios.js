/* ============================================================
   auth.js — LzApp
   Compartido entre login.html y registro.html.

   - mostrarPassword(): usado por el botón del ojo en ambas
     páginas (login tiene 1 campo, registro tiene 2).
   - Validación de usuario en tiempo real: SOLO existe en la
     página de registro. Se protege con "if (usernameInput)"
     para que este mismo archivo pueda cargarse en login.html
     sin lanzar errores en consola.
   ============================================================ */

/* =========================================================
   VIDEO DE FONDO (panel izquierdo de login/registro)
   ========================================================= */
document.addEventListener('DOMContentLoaded', function () {

    const video = document.querySelector('.auth-video');
    if (!video) return;

    const prefiereMenosMovimiento =
        window.matchMedia && window.matchMedia('(prefers-reduced-motion: reduce)').matches;

    if (prefiereMenosMovimiento) {
        video.pause();
        video.removeAttribute('autoplay');
        return;
    }

    // Algunos navegadores de Android bloquean el autoplay aunque el
    // video esté silenciado. Si el intento automático falla,
    // reintentamos apenas el usuario toque/interactúe con la página.
    const intentarReproducir = () => {
        const promesa = video.play();
        if (promesa !== undefined) {
            promesa.catch(function () {
                const reintentar = () => {
                    video.play().catch(function () {});
                    document.removeEventListener('touchstart', reintentar);
                    document.removeEventListener('click', reintentar);
                };
                document.addEventListener('touchstart', reintentar, { once: true });
                document.addEventListener('click', reintentar, { once: true });
            });
        }
    };
    intentarReproducir();

    // Pausa el video si la pestaña queda en segundo plano, para no
    // gastar batería/datos en móvil sin necesidad.
    document.addEventListener('visibilitychange', function () {
        if (document.hidden) {
            video.pause();
        } else {
            video.play().catch(function () {});
        }
    });
});

/* =========================================================
   MOSTRAR / OCULTAR CONTRASEÑA
   ========================================================= */
function mostrarPassword(id, boton) {
    const campo = document.getElementById(id);
    const icono = boton.querySelector('i');

    if (campo.type === 'password') {
        campo.type = 'text';
        icono.classList.remove('bi-eye-slash');
        icono.classList.add('bi-eye');
    } else {
        campo.type = 'password';
        icono.classList.remove('bi-eye');
        icono.classList.add('bi-eye-slash');
    }
}

/* =========================================================
   INDICADOR DE CARGA (3 puntitos) — compartido entre login y registro
   ========================================================= */
function mostrarCargandoBoton(boton, textoCargando) {
    if (!boton) return;
    if (!boton.dataset.textoOriginal) boton.dataset.textoOriginal = boton.textContent.trim();
    boton.disabled = true;
    boton.innerHTML = (textoCargando || boton.dataset.textoOriginal) +
        ' <span class="puntos-cargando"><span></span><span></span><span></span></span>';
}

function restaurarBoton(boton, texto) {
    if (!boton) return;
    boton.disabled = false;
    boton.textContent = texto || boton.dataset.textoOriginal || boton.textContent;
}

/* =========================================================
   LOGIN: mostrar los puntitos de carga al enviar
   ========================================================= */
document.addEventListener('DOMContentLoaded', function () {
    const loginForm = document.getElementById('loginForm');
    if (!loginForm) return; // no estamos en login.html

    const btnLogin = loginForm.querySelector('.btn-auth');
    loginForm.addEventListener('submit', function () {
        mostrarCargandoBoton(btnLogin, 'Iniciando sesión');
    });
});

/* =========================================================
   CORREO: validación de formato en tiempo real (solo Registro)
   ========================================================= */
document.addEventListener('DOMContentLoaded', function () {
    const emailInput = document.getElementById('id_email');
    const emailFeedback = document.getElementById('email-feedback');
    if (!emailInput || !emailFeedback) return; // no estamos en registro.html

    const EMAIL_VALIDO_RE = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;

    function validarEmail() {
        const valor = emailInput.value.trim();
        emailInput.classList.remove('username-valido', 'username-invalido');

        if (valor === '') {
            emailFeedback.textContent = '';
            emailFeedback.className = 'username-feedback';
            return;
        }

        if (!valor.includes('@')) {
            emailInput.classList.add('username-invalido');
            emailFeedback.textContent = 'Falta el @ en el correo.';
            emailFeedback.className = 'username-feedback error';
            return;
        }

        if (!EMAIL_VALIDO_RE.test(valor)) {
            emailInput.classList.add('username-invalido');
            emailFeedback.textContent = 'Ese correo no tiene un formato válido (ej: nombre@gmail.com).';
            emailFeedback.className = 'username-feedback error';
            return;
        }

        emailInput.classList.add('username-valido');
        emailFeedback.textContent = '✓ Correo válido.';
        emailFeedback.className = 'username-feedback success';
    }

    emailInput.addEventListener('input', validarEmail);
    emailInput.addEventListener('blur', validarEmail);
});

/* =========================================================
   CONTRASEÑA: fortaleza en tiempo real + coincidencia (solo Registro)
   ========================================================= */
document.addEventListener('DOMContentLoaded', function () {
    const password1 = document.getElementById('id_password1');
    const password2 = document.getElementById('id_password2');
    const fortalezaCaja = document.getElementById('password-fortaleza');
    if (!password1 || !fortalezaCaja) return; // no estamos en registro.html

    const barra = fortalezaCaja.querySelector('.fortaleza-barra span');
    const texto = fortalezaCaja.querySelector('.fortaleza-texto');
    const coincideCaja = document.getElementById('password-coincide');

    function evaluarFortaleza() {
        const valor = password1.value;
        fortalezaCaja.classList.remove('fortaleza-debil', 'fortaleza-media', 'fortaleza-fuerte');

        if (valor.length === 0) {
            texto.textContent = '';
            barra.style.width = '0';
            return;
        }

        const esSoloNumeros = /^[0-9]+$/.test(valor);
        let puntos = 0;
        if (valor.length >= 8) puntos++;
        if (/[a-z]/.test(valor) && /[A-Z]/.test(valor)) puntos++;
        if (/[0-9]/.test(valor)) puntos++;
        if (/[^A-Za-z0-9]/.test(valor)) puntos++;

        if (valor.length < 8 || esSoloNumeros || puntos <= 1) {
            fortalezaCaja.classList.add('fortaleza-debil');
            texto.textContent = valor.length < 8
                ? 'Muy corta: usa al menos 8 caracteres.'
                : esSoloNumeros
                    ? 'No puede ser solo números.'
                    : 'Débil: agrega mayúsculas, números o símbolos.';
        } else if (puntos <= 2) {
            fortalezaCaja.classList.add('fortaleza-media');
            texto.textContent = 'Media: agrega algún símbolo o mayúscula para reforzarla.';
        } else {
            fortalezaCaja.classList.add('fortaleza-fuerte');
            texto.textContent = '✓ Contraseña segura.';
        }
    }

    function evaluarCoincidencia() {
        if (!coincideCaja || !password2) return;

        if (password2.value === '') {
            coincideCaja.textContent = '';
            coincideCaja.className = 'username-feedback';
            return;
        }

        if (password1.value === password2.value) {
            coincideCaja.textContent = '✓ Las contraseñas coinciden.';
            coincideCaja.className = 'username-feedback success';
        } else {
            coincideCaja.textContent = 'Las contraseñas no coinciden.';
            coincideCaja.className = 'username-feedback error';
        }
    }

    password1.addEventListener('input', function () {
        evaluarFortaleza();
        evaluarCoincidencia();
    });
    if (password2) password2.addEventListener('input', evaluarCoincidencia);
});

/* =========================================================
   VALIDACIÓN DEL USUARIO EN TIEMPO REAL (solo página Registro)
   ========================================================= */
document.addEventListener('DOMContentLoaded', function () {

    const usernameInput = document.getElementById('id_username');
    const registroForm = document.getElementById('registroForm');

    // login.html también tiene un campo "id_username" (se loguea por
    // usuario, no por correo), así que ese chequeo solo no alcanza para
    // saber si estamos en registro.html -- sin el chequeo de registroForm,
    // este bloque intentaba correr en login.html también y explotaba en
    // registroForm.addEventListener() más abajo (registroForm es null ahí),
    // lo que dejaba SIN REGISTRAR todo el resto del script en esa página.
    if (!usernameInput || !registroForm) return;

    const usernameFeedback = document.getElementById('username-feedback');
    const btnRegistro = document.getElementById('btnRegistro');

    let usernameExiste = false;
    let usernameValidado = false;
    let ultimaConsulta = '';
    let timeoutUsername = null;
    let enviandoDespuesDeValidar = false;

    function mostrarFeedback(mensaje, tipo) {
        usernameFeedback.textContent = mensaje;
        usernameFeedback.className = 'username-feedback ' + tipo;
    }

    function limpiarEstado() {
        usernameInput.classList.remove('username-valido', 'username-invalido', 'username-validando');
    }

    function validarFormato(username) {

        if (username.length === 0) {
            limpiarEstado();
            usernameExiste = false;
            usernameValidado = false;
            ultimaConsulta = '';
            usernameFeedback.textContent = '';
            usernameFeedback.className = 'username-feedback';
            return false;
        }

        if (username.length < 6) {
            limpiarEstado();
            usernameExiste = false;
            usernameValidado = false;
            usernameInput.classList.add('username-invalido');
            mostrarFeedback('El nombre de usuario debe tener al menos 6 caracteres.', 'error');
            return false;
        }

        if (username.length > 20) {
            limpiarEstado();
            usernameExiste = false;
            usernameValidado = false;
            usernameInput.classList.add('username-invalido');
            mostrarFeedback('El nombre de usuario no puede tener más de 20 caracteres.', 'error');
            return false;
        }

        const formatoValido = /^[A-Za-z][A-Za-z0-9_]*$/;
        if (!formatoValido.test(username)) {
            limpiarEstado();
            usernameExiste = false;
            usernameValidado = false;
            usernameInput.classList.add('username-invalido');
            mostrarFeedback('Debe comenzar con una letra y solo puede contener letras, números y guiones bajos (_).', 'error');
            return false;
        }

        if (!/[0-9]/.test(username)) {
            limpiarEstado();
            usernameExiste = false;
            usernameValidado = false;
            usernameInput.classList.add('username-invalido');
            mostrarFeedback('El nombre de usuario debe contener al menos un número.', 'error');
            return false;
        }

        return true;
    }

    function comprobarUsuario(username, enviarDespues = false) {

        ultimaConsulta = username;
        usernameValidado = false;
        usernameExiste = false;

        usernameInput.classList.remove('username-invalido');
        usernameInput.classList.add('username-validando');
        mostrarFeedback('Comprobando disponibilidad...', 'warning');

        const url = window.location.pathname + '?validar_username=' + encodeURIComponent(username);

        fetch(url, { method: 'GET', headers: { 'X-Requested-With': 'XMLHttpRequest' } })
            .then(function (response) {
                if (!response.ok) throw new Error('Error al consultar el usuario.');
                return response.json();
            })
            .then(function (data) {

                const usernameActual = usernameInput.value.trim();
                if (username !== usernameActual) return;

                usernameInput.classList.remove('username-validando');
                usernameExiste = data.existe;
                usernameValidado = true;

                if (data.existe) {
                    usernameInput.classList.add('username-invalido');
                    mostrarFeedback('Este nombre de usuario ya está registrado.', 'error');
                    restaurarBoton(btnRegistro, 'Crear Cuenta');
                    enviandoDespuesDeValidar = false;
                    return;
                }

                usernameInput.classList.add('username-valido');
                mostrarFeedback('✓ Nombre de usuario disponible.', 'success');

                if (enviarDespues || enviandoDespuesDeValidar) {
                    mostrarCargandoBoton(btnRegistro, 'Creando cuenta');
                    HTMLFormElement.prototype.submit.call(registroForm);
                }
            })
            .catch(function (error) {
                console.error('Error:', error);
                usernameValidado = false;
                usernameExiste = false;
                usernameInput.classList.remove('username-validando');
                restaurarBoton(btnRegistro, 'Crear Cuenta');
                enviandoDespuesDeValidar = false;
                mostrarFeedback('No se pudo comprobar el usuario. Intenta nuevamente.', 'error');
            });
    }

    usernameInput.addEventListener('input', function () {

        const username = usernameInput.value.trim();
        clearTimeout(timeoutUsername);

        usernameExiste = false;
        usernameValidado = false;
        ultimaConsulta = '';
        enviandoDespuesDeValidar = false;
        restaurarBoton(btnRegistro, 'Crear Cuenta');

        const formatoCorrecto = validarFormato(username);
        if (!formatoCorrecto) return;

        timeoutUsername = setTimeout(function () {
            comprobarUsuario(username, false);
        }, 400);
    });

    registroForm.addEventListener('submit', function (event) {

        const username = usernameInput.value.trim();
        const formatoCorrecto = validarFormato(username);

        if (!formatoCorrecto) {
            event.preventDefault();
            usernameInput.focus();
            return;
        }

        if (usernameExiste) {
            event.preventDefault();
            usernameInput.focus();
            mostrarFeedback('Este nombre de usuario ya está registrado.', 'error');
            return;
        }

        if (usernameValidado && ultimaConsulta === username) {
            mostrarCargandoBoton(btnRegistro, 'Creando cuenta');
            return;
        }

        event.preventDefault();
        enviandoDespuesDeValidar = true;
        mostrarCargandoBoton(btnRegistro, 'Comprobando usuario');
        mostrarFeedback('Comprobando disponibilidad...', 'warning');

        clearTimeout(timeoutUsername);
        comprobarUsuario(username, true);
    });

});