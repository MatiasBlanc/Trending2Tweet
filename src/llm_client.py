"""Cliente para generar tweets con un LLM compatible con OpenAI."""

from pathlib import Path
from openai import OpenAI

from src import config


def _leer_prompt(nombre_archivo: str, limite_texto: str) -> str:
    """Lee un archivo de prompt y reemplaza las variables."""
    plantilla = Path(nombre_archivo).read_text(encoding="utf-8")
    return plantilla.replace("{limite}", limite_texto)


def _obtener_limite_texto() -> str:
    """Genera el texto descriptivo según la configuración de límite."""
    if config.FORCE_280_CHAR_TWEET:
        return "El texto debe ser hiper-conciso y no superar los 280 caracteres. Optimiza cada palabra."
    return (
        "LONGITUD ESTRICTA: Máximo 8-10 líneas en total. "
        "Cada uno de los 3 puntos del cuerpo = máximo 2 líneas. "
        "Si escribes más de 2 líneas por punto, el tweet es demasiado largo. "
        "Sé directo y elimina todo lo que no sea esencial."
    )


def generate_tweet(prompt_file: str, user_message: str, variables: dict = None, max_reintentos: int = 3, max_tokens_override: int = None) -> str:
    """Genera un tweet usando el LLM configurado.

    Args:
        prompt_file: Ruta al archivo de prompt del sistema.
        user_message: Mensaje del usuario con los datos del item.
        variables: Diccionario con variables adicionales para el prompt.
        max_reintentos: Número máximo de reintentos si el LLM devuelve vacío.
        max_tokens_override: Sobreescribe el límite de tokens (útil para hilos).

    Returns:
        Texto del tweet generado.

    Raises:
        Exception: Error de la API del LLM o si no se puede generar contenido después de reintentos.
    """
    client = OpenAI(
        api_key=config.LLM_API_KEY,
        base_url=config.LLM_BASE_URL,
        timeout=60.0,
    )

    system_prompt = _leer_prompt(prompt_file, _obtener_limite_texto())
    
    if variables:
        for clave, valor in variables.items():
            system_prompt = system_prompt.replace(f"{{{clave}}}", valor)

    max_tokens = max_tokens_override or config.LLM_MAX_TOKENS

    for intento in range(max_reintentos):
        completion = client.chat.completions.create(
            model=config.LLM_MODEL,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_message},
            ],
            max_tokens=max_tokens,
            temperature=config.LLM_TEMPERATURE,
        )

        resultado = completion.choices[0].message.content
        
        if resultado and resultado.strip():
            return resultado.strip()
        
        print(f"  ⚠️ LLM devolvió vacío (intento {intento + 1}/{max_reintentos})")

    raise Exception(f"El LLM no generó contenido después de {max_reintentos} intentos")
