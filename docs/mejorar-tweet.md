# Bot de Mejora de Tweets

Bot interactivo que lee tus borradores de tweets manuales y usa IA para mejorarlos y hacerlos más virales.

## Uso

```bash
python -m bots.mejorar_tweet
```

## Flujo de Trabajo

1. **Ejecuta el bot** - Se mostrará una lista de todos los tweets con status `draft`
2. **Selecciona un tweet** - Escribe el ID o número de la lista
3. **Revisa el tweet actual** - El bot te mostrará el contenido actual
4. **Confirma la mejora** - La IA analizará y mejorará el tweet
5. **Compara los resultados** - Verás el original vs. el mejorado
6. **Guarda si te gusta** - Se agregará una sección "Update" al archivo

## Formato de los Borradores Manuales

Los tweets manuales deben tener este formato en tu bóveda de Obsidian:

### Formato Simple (Recomendado para escritura rápida)

```markdown
---
type: tweet
status: draft
source: manual
item_id: mn_001
titulo: Mi Tweet Increíble
---

Aquí va el texto de tu tweet. Puede ser multilinea.

Cada párrafo se considera parte del tweet.
```

### Formato Completo (Con secciones adicionales)

```markdown
---
type: tweet
status: draft
source: manual
item_id: mn_002
---

# Título del Tweet

## Tweet

Texto principal del tweet aquí.

## Metadata

- **Fuente**: manual
- **Fecha**: 2024-01-15

## Notas

Ideas adicionales o contexto.

## Revisión

- [ ] Revisar ortografía
- [ ] Publicar en Twitter
```

## Ubicación de los Borradores

Los borradores se guardan en:
```
<VAULT>/T2T/borradores/
```

Pero también se buscarán en cualquier subdirectorio del vault que contenga archivos `.md` con `status: draft`.

## ¿Qué hace la IA?

La IA analiza tu tweet y aplica técnicas virales:

- **Hook más provocador** - Captura atención en los primeros 5 segundos
- **Cuerpo más escaneable** - Elimina relleno, usa datos concretos
- **Cierre que genera debate** - Preguntas que provocan respuestas
- **Tono natural** - Como un dev senior hablando con otro dev

## Ejemplo de Mejora

### Original (escrito por ti):
```
DeepSeek V4 Flash acaba de superar a su propia versión Pro y a los modelos premium más pesados del ecosistema, pero costando $0.14 / $0.28 por 1M tokens (in/out)

La optimización real está en el caché de los prompts...
```

### Mejorado (por la IA):
```
¿Quién necesita modelos de $10/M tokens cuando DeepSeek V4 Flash los supera por $0.14?

El truco está en el caché de prompts:
→ Contextos repetidos = $0.0028/1M tokens
→ 284B params totales, solo 13B activos por consulta
→ 1M tokens de contexto

Modo "Thinking" para razonamiento profundo o "Non-Thinking" para latencia ultra baja.

¿Alguien está usando esto en producción o es hype?
#LLM #DeepSeek
```

## Archivos Creados

- `bots/mejorar_tweet.py` - Bot principal
- `prompts/prompt_mejorar_tweet.txt` - Prompt para la IA

## Variables de Entorno

Asegúrate de tener configuradas en `.env`:

```env
OBSIDIAN_VAULT_PATH=/ruta/a/tu/vault
LLM_API_KEY=tu-api-key
LLM_BASE_URL=https://api.openai.com/v1  # O tu proveedor
LLM_MODEL=gpt-4o-mini  # O el modelo que prefieras
```
