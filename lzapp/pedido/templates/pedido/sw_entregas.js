/* Service worker del panel del repartidor.

   Guarda en caché los tiles del mapa que el repartidor ya vio, para que
   la ruta se siga viendo cuando se queda sin señal (que es justo cuando
   más falta hace: en la calle, a mitad de la entrega).

   Alcance honesto: solo se ven offline las zonas por las que ya pasó con
   señal. Un tile que nunca se descargó no está en ninguna parte.
*/
const CACHE_TILES = 'lz-tiles-v1';
const MAX_TILES = 600;   // ~15-20 MB; suficiente para una jornada de reparto

self.addEventListener('install', () => self.skipWaiting());
self.addEventListener('activate', (evento) => evento.waitUntil(self.clients.claim()));

async function recortarCache(cache) {
    // Sin tope, el caché de tiles crece sin fin en el celular del
    // repartidor. Se descartan los más viejos (orden de inserción).
    const claves = await cache.keys();
    if (claves.length <= MAX_TILES) return;
    for (const clave of claves.slice(0, claves.length - MAX_TILES)) {
        await cache.delete(clave);
    }
}

self.addEventListener('fetch', (evento) => {
    const url = evento.request.url;

    // Solo tiles del mapa: el resto (APIs, POSTs) tiene que seguir de
    // largo, si no el repartidor vería datos viejos como si fueran de ahora.
    if (evento.request.method !== 'GET' || !url.includes('tile.openstreetmap.org')) return;

    evento.respondWith((async () => {
        const cache = await caches.open(CACHE_TILES);
        const enCache = await cache.match(evento.request);

        const desdeRed = fetch(evento.request).then(async (respuesta) => {
            if (respuesta && respuesta.status === 200) {
                await cache.put(evento.request, respuesta.clone());
                recortarCache(cache);
            }
            return respuesta;
        }).catch(() => enCache);

        // Primero el caché (instantáneo y sirve sin señal); la red
        // refresca por detrás para la próxima vez.
        return enCache || desdeRed;
    })());
});
