"""Cliente para generar tweets con un LLM compatible con OpenAI."""

from pathlib import Path
from openai import OpenAI

import config


def _leer_prompt(nombre_archivo: str, limite_texto: str, variables: dict = None) -> str:
    """Lee un archivo de prompt y reemplaza las variables.

    Args:
        nombre_archivo: Ruta al archivo de prompt.
        limite_texto: Texto descriptivo del límite de caracteres.
        variables: Diccionario con variables adicionales a reemplazar.

    Returns:
        Prompt del sistema con las variables reemplazadas.
    """
    plantilla = Path(nombre_archivo).read_text(encoding="utf-8")
    resultado = plantilla.replace("{limite}", limite_texto)
    
    if variables:
        for clave, valor in variables.items():
            resultado = resultado.replace(f"{{{clave}}}", valor)
    
    return resultado


def _obtener_limite_texto() -> str:
    """Genera el texto descriptivo según la configuración de límite.

    Returns:
        Texto con las instrucciones de límite.
    """
    if config.FORCE_280_CHAR_TWEET:
        return "El texto debe ser hiper-conciso y no superar los 280 caracteres. Optimiza cada palabra."
    return "Prioriza la escaneabilidad visual. Usa saltos de línea claros, pero mantén la información comprimida y al grano."


def generate_tweet(prompt_file: str, user_message: str, variables: dict = None) -> str:
    """Genera un tweet usando el LLM configurado.

    Args:
        prompt_file: Ruta al archivo de prompt del sistema.
        user_message: Mensaje del usuario con los datos del item.
        variables: Diccionario con variables adicionales para el prompt.

    Returns:
        Texto del tweet generado.

    Raises:
        Exception: Error de la API del LLM.
    """
    client = OpenAI(
        api_key=config.LLM_API_KEY,
        base_url=config.LLM_BASE_URL,
    )

    system_prompt = _leer_prompt(prompt_file, _obtener_limite_texto(), variables)

    completion = client.chat.completions.create(
        model=config.LLM_MODEL,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_message},
        ],
        max_tokens=config.LLM_MAX_TOKENS,
        temperature=config.LLM_TEMPERATURE,
    )

    return completion.choices[0].message.content.strip()
