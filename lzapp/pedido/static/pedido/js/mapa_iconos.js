/* Íconos animados compartidos entre los tres mapas de pedidos (admin,
 * cliente, repartidor) — dibujados en SVG propio, no con emoji ni con un
 * ícono de fuente metido en una burbuja. Requiere Leaflet ya cargado y
 * mapa_iconos.css (que trae las animaciones de cada pieza del SVG). */

/* opciones (todas opcionales):
 *   numero    -> dibuja el puesto de la parada dentro del pin
 *   atenuado  -> pin en gris, para las paradas que todavía no tocan.
 *                El repartidor tiene que ver TODOS sus destinos, pero
 *                distinguiendo de un vistazo cuál es el siguiente. */
function crearIconoDestino(opciones = {}) {
    const { numero = null, atenuado = false } = opciones;

    const centro = numero !== null
        ? `<text class="mi-pin-numero" x="20" y="20.4" text-anchor="middle">${numero}</text>`
        : `<path class="mi-pin-casa" d="M17 18.3v-3.1l3-2.3 3 2.3v3.1h-2v-1.8h-2v1.8h-2z"/>`;

    const svg = `
        <svg class="mi-svg mi-svg-destino${atenuado ? ' mi-destino-atenuado' : ''}"
             viewBox="0 0 40 48" width="40" height="48" xmlns="http://www.w3.org/2000/svg">
            <ellipse class="mi-radar" cx="20" cy="41" rx="5" ry="2"/>
            <ellipse class="mi-radar mi-radar-2" cx="20" cy="41" rx="5" ry="2"/>
            <g class="mi-pin-grupo">
                <path class="mi-pin-cuerpo" d="M20 2C11.72 2 5 8.6 5 16.7c0 11 15 24.5 15 24.5s15-13.5 15-24.5C35 8.6 28.28 2 20 2z"/>
                <circle class="mi-pin-nucleo" cx="20" cy="16.5" r="6.2"/>
                ${centro}
            </g>
        </svg>`;
    return L.divIcon({
        html: svg,
        className: '',
        iconSize: [40, 48],
        iconAnchor: [20, 42],
        popupAnchor: [0, -38],
    });
}

function crearIconoRepartidor() {
    const svg = `
        <svg class="mi-svg mi-svg-repartidor" viewBox="0 0 44 44" width="44" height="44" xmlns="http://www.w3.org/2000/svg">
            <circle class="mi-rep-halo" cx="22" cy="22" r="18"/>
            <circle class="mi-rep-fondo" cx="22" cy="22" r="14"/>
            <g class="mi-rep-lineas" stroke="#f0d98a" stroke-width="2" stroke-linecap="round">
                <line x1="0" y1="16" x2="6" y2="16"/>
                <line x1="-2" y1="22" x2="5" y2="22"/>
                <line x1="0" y1="28" x2="6" y2="28"/>
            </g>
            <g class="mi-rep-scooter" fill="none" stroke="#fff" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                <circle cx="16.5" cy="27.5" r="2.6" fill="#fff" stroke="none"/>
                <circle cx="28.5" cy="27.5" r="2.6" fill="#fff" stroke="none"/>
                <path d="M16.5 27.5h5.5l3-8h3.5"/>
                <path d="M24 15.5h3.2"/>
                <path d="M19 27.5h8.5"/>
                <path d="M25.5 15.5l2.7 3.6"/>
            </g>
        </svg>`;
    return L.divIcon({
        html: svg,
        className: '',
        iconSize: [44, 44],
        iconAnchor: [22, 22],
        popupAnchor: [0, -20],
    });
}

function crearIconoYo() {
    const svg = `
        <svg class="mi-svg mi-svg-yo" viewBox="0 0 24 24" width="24" height="24" xmlns="http://www.w3.org/2000/svg">
            <circle class="mi-yo-halo" cx="12" cy="12" r="10"/>
            <circle class="mi-yo-nucleo" cx="12" cy="12" r="6"/>
        </svg>`;
    return L.divIcon({
        html: svg,
        className: '',
        iconSize: [24, 24],
        iconAnchor: [12, 12],
    });
}
