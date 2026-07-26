"""Cliente para generar tweets con un LLM compatible con OpenAI."""

from openai import OpenAI

import config

def _build_system_prompt() -> str:
    """Construye el system prompt según la configuración de longitud."""
    if config.FORCE_280_CHAR_TWEET:
        limite = "El texto debe ser conciso, fluido y no superar los 250 caracteres (excluyendo la URL)."
    else:
        limite = "Puedes extender el tweet con más detalle técnico, sin límite estricto de caracteres. pero con máximo 2 líneas de texto (sin contar la URL). Ve al grano de inmediato. Si te extiendes más, el post se rechaza."

    return f"""Actúa como un Ingeniero de Software Senior y curador de contenido técnico en X.
Tu única tarea es recibir datos de un repositorio de GitHub (nombre, descripción, lenguaje, estrellas, URL) y transformarlos en un tweet de altísimo impacto.

REGLAS ESTRICTAS DE FORMATO Y TONO:
1. Cero "Fluff" de IA y Cero Marketing: Prohibido usar introducciones genéricas ("Descubre...", "En el mundo del desarrollo...", "Atención desarrolladores"). PROHIBIDO usar palabras cliché como "solución", "valioso", "esencial", "recurso" o "facilita".
2. El Gancho (Hook): La primera línea debe atrapar al lector yendo directo a un problema ("dolor" técnico) que el repositorio resuelve, o a su principal caso de uso.
3. Valor Técnico: Explica en una frase asertiva y técnica cómo funciona el código por debajo (arquitectura, lenguaje o implementación), prohibido sonar como un anuncio publicitario.
4. Estética Minimalista: Prohibido el uso de emojis. Prohibido el uso de hashtags. Separa los bloques de texto con un salto de línea para facilitar la lectura.
5. Longitud: {limite}
6. Cierre: El tweet siempre debe terminar con la URL del repositorio.
7. Formato de Salida: Devuelve ÚNICAMENTE el texto final del tweet en español, listo para publicarse. No uses comillas, ni confirmes la orden, ni agregues explicaciones. CERO MARKDOWN (CRÍTICO) Genera texto plano puro. La plataforma de destino no soporta Markdown. Está estrictamente prohibido usar asteriscos (**) para negritas, guiones bajos (_) para cursivas o sintaxis de enlaces como [texto](url).
"""

def generate_tweet(repo: dict) -> str:
    """Genera un tweet descriptivo sobre el repositorio.

    Args:
        repo: Diccionario con name, description, language, stars, html_url.

    Returns:
        Texto del tweet generado.

    Raises:
        Exception: Error de la API del LLM.
    """
    client = OpenAI(
        api_key=config.LLM_API_KEY,
        base_url=config.LLM_BASE_URL,
    )

    user_msg = (
        f"Repo: {repo['name']}\n"
        f"Descripción: {repo['description']}\n"
        f"Lenguaje: {repo['language']}\n"
        f"Stars: {repo['stars']}\n"
        f"URL: {repo['html_url']}"
    )

    # Incluir contenido del README si está disponible
    readme_content = repo.get("readme_content")
    if readme_content:
        user_msg += f"\n\n--- README del repositorio ---\n{readme_content}\n--- Fin del README ---"


    system_prompt = _build_system_prompt()

    completion = client.chat.completions.create(
        model=config.LLM_MODEL,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_msg},
        ],
        max_tokens=config.LLM_MAX_TOKENS,
        temperature=config.LLM_TEMPERATURE,
    )

    respuesta_cruda = completion.choices[0].message.content
    return respuesta_cruda.strip()
