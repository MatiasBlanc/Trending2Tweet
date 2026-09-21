# Hoja de ruta de persistencia

## Versión base

La aplicación mantiene dos piezas locales y deliberadamente pequeñas:

- Los borradores y su revisión viven en Markdown dentro de Obsidian.
- `metrics.db` usa SQLite únicamente para evitar procesar dos veces una fuente.

No se añade una base remota, un servidor MCP ni una migración obligatoria mientras
se valida el flujo de descubrimiento y asistencia a la redacción.

## Extensión posterior

Cuando exista suficiente volumen de publicaciones revisadas, evaluar una tabla de
métricas por post con al menos:

- `draft_id`, fuente, categoría y versión del prompt;
- fecha de generación, fecha de publicación y estado;
- impresiones, respuestas, reposts, likes y clics, si la API utilizada los ofrece;
- variante elegida y si el usuario editó el borrador antes de publicarlo.

La evaluación debe partir de datos exportables y opt-in. No conviene acoplar la
versión base a una API de X ni usar rendimiento pasado para publicar automáticamente:
el usuario conserva el criterio final, la edición y la publicación.
