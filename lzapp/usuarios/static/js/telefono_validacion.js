/* ============================================================
   telefono_validacion.js — LzApp
   Compartido entre registro.html, registro_empleado.html y
   configuracion.html: la REGLA de teléfono vive acá una sola vez
   (sanear el input a solo dígitos, y la cantidad de dígitos esperada
   según el país elegido); cada página decide cómo mostrar el mensaje
   con su propio estilo, así que esto solo expone funciones puras, no
   toca el DOM directamente.

   OJO: LONGITUD_POR_PAIS tiene que reflejar exactamente
   LONGITUD_TELEFONO_POR_PAIS en usuarios/forms.py -- son la misma
   regla duplicada a propósito (servidor autoritativo + feedback en
   vivo en el navegador), no hay una sola fuente de verdad compartida
   entre Python y JS en este proyecto.
   ============================================================ */
window.LZ_TELEFONO = (function () {
    const LONGITUD_POR_PAIS = {
        '+57': [10, 10],   // Colombia
        '+1': [10, 10],    // EE. UU. / Canadá
        '+52': [10, 10],   // México
        '+58': [10, 10],   // Venezuela
        '+593': [9, 9],    // Ecuador
        '+51': [9, 9],     // Perú
        '+56': [9, 9],     // Chile
        '+54': [10, 11],   // Argentina
        '+507': [7, 8],    // Panamá
        '+506': [8, 8],    // Costa Rica
        '+55': [10, 11],   // Brasil
        '+34': [9, 9],     // España
    };
    const RANGO_DEFECTO = [7, 15];

    function rango(codigoPais) {
        return LONGITUD_POR_PAIS[codigoPais] || RANGO_DEFECTO;
    }

    // Quita todo lo que no sea dígito -- el código de país ya lo elige
    // el select aparte, así que acá no hace falta (ni se permite) +,
    // espacios, guiones ni paréntesis.
    function sanear(valor) {
        return (valor || '').replace(/[^0-9]/g, '');
    }

    function textoLongitud(codigoPais) {
        const [minimo, maximo] = rango(codigoPais);
        return minimo === maximo ? `${minimo} dígitos` : `entre ${minimo} y ${maximo} dígitos`;
    }

    // Devuelve { ok: true|false|null, mensaje }. ok=null significa "vacío,
    // no hay nada que mostrar todavía" (para no gritarle al usuario en
    // cuanto entra al campo).
    function validar(codigoPais, valor) {
        const limpio = sanear(valor);
        if (!limpio) return { ok: null, mensaje: '' };

        const [minimo, maximo] = rango(codigoPais);
        if (limpio.length < minimo || limpio.length > maximo) {
            return { ok: false, mensaje: `Para este país, el número debe tener ${textoLongitud(codigoPais)}.` };
        }
        return { ok: true, mensaje: '✓ Teléfono válido.' };
    }

    return { rango, sanear, textoLongitud, validar };
})();
