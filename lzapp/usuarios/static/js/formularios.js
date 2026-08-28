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
   VALIDACIÓN DEL USUARIO EN TIEMPO REAL (solo página Registro)
   ========================================================= */
document.addEventListener('DOMContentLoaded', function () {

    const usernameInput = document.getElementById('id_username');

    // Si no existe (por ejemplo, en login.html), no hacemos nada más.
    if (!usernameInput) return;

    const usernameFeedback = document.getElementById('username-feedback');
    const registroForm = document.getElementById('registroForm');
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
                    btnRegistro.disabled = false;
                    btnRegistro.innerText = 'Crear Cuenta';
                    enviandoDespuesDeValidar = false;
                    return;
                }

                usernameInput.classList.add('username-valido');
                mostrarFeedback('✓ Nombre de usuario disponible.', 'success');

                if (enviarDespues || enviandoDespuesDeValidar) {
                    btnRegistro.disabled = true;
                    btnRegistro.innerText = 'Creando cuenta...';
                    HTMLFormElement.prototype.submit.call(registroForm);
                }
            })
            .catch(function (error) {
                console.error('Error:', error);
                usernameValidado = false;
                usernameExiste = false;
                usernameInput.classList.remove('username-validando');
                btnRegistro.disabled = false;
                btnRegistro.innerText = 'Crear Cuenta';
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
        btnRegistro.disabled = false;
        btnRegistro.innerText = 'Crear Cuenta';

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
            btnRegistro.disabled = true;
            btnRegistro.innerText = 'Creando cuenta...';
            return;
        }

        event.preventDefault();
        enviandoDespuesDeValidar = true;
        btnRegistro.disabled = true;
        btnRegistro.innerText = 'Comprobando usuario...';
        mostrarFeedback('Comprobando disponibilidad...', 'warning');

        clearTimeout(timeoutUsername);
        comprobarUsuario(username, true);
    });

});