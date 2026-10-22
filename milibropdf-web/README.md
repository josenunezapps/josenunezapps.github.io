# MiLibroPDF Web

Primera versión web de MiLibroPDF: biblioteca personal para **PDF y EPUB** en un diseño adaptable a escritorio y celular.

## Funciones implementadas

- Importación de archivos PDF y EPUB mediante selector o arrastrar y soltar.
- Biblioteca con búsqueda, filtros, favoritos, orden y vistas de cuadrícula/lista.
- Lectura PDF con PDF.js, páginas, zoom, rotación y capa de selección de texto cuando el archivo la permite.
- Lectura EPUB con epub.js, navegación, diseño adaptable y restauración de la posición.
- Guardado de progreso y tiempo de lectura; Continuar leyendo; estadísticas simples.
- Notas privadas, notas vinculadas, fragmentos y resaltados (la selección se almacena; no se vuelve a pintar automáticamente sobre el documento al reabrir).
- Texto a voz con Web Speech API y temporizador de sueño (dependiente del navegador, idioma y voces instaladas).
- Temas claro/sepia/oscuro, tipografía y ajustes; Wake Lock si está disponible.
- PWA instalable y uso sin conexión para el shell y recursos previamente almacenados.
- Una lectura de bienvenida funcional de muestra.

## Ejecución

No requiere servidor ni claves de API. Serví esta carpeta con un servidor estático (Service Worker e IndexedDB requieren un origen seguro; localhost es válido):

```bash
python3 -m http.server 8080
```

Abrí `http://localhost:8080` en el navegador. También se puede publicar como subcarpeta en GitHub Pages, Cloudflare Pages o hosting estático.

Dependencias del lector mediante CDN: `pdfjs-dist@4.10.38`, `epubjs@0.3.93`. La primera vez requieren conexión; la PWA cachea los recursos que se hayan cargado.

## Datos y privacidad

**En esta versión no hay cuentas ni sincronización entre dispositivos.** Los PDF, EPUB, notas, posiciones y estadísticas se guardan en **IndexedDB local**. Borrar los datos del sitio puede borrarlos. La exportación JSON de Configuración contiene *solo metadatos y apuntes* (no los archivos de los libros), y todavía no tiene función de importación de respaldo.

No existe backend Supabase ni servicio de subida. Para habilitar la sincronización es necesario añadir autenticación, reglas RLS, almacenamiento de archivos y migración local/nube con pruebas.

## Limitaciones conocidas

- PDF escaneado: se visualiza, pero no realiza OCR; TTS, búsqueda y selección requieren texto extraíble.
- El resaltado se guarda como apunte, no como superposición visual persistente sobre cada PDF/EPUB.
- El seguimiento visual de cada frase de TTS y la continuación automática entre capítulos EPUB aún no están implementados.
- Las estadísticas son por dispositivo, no globales; tiempo aproximado con el lector abierto.
- La experiencia TTS/voz y Wake Lock depende del navegador y restricciones móviles.
- No se incluyen archivos de libros en el repositorio ni se envían al servidor.

## Organización

`index.html` interfaz y recursos SVG · `styles.css` estilos responsive · `app.js` lógica de biblioteca, lectores, estudio, IndexedDB y TTS · `sw.js` service worker · `manifest.webmanifest` PWA · `icon.svg` ícono.

Código de web independiente del proyecto Android. No toca archivos Android.