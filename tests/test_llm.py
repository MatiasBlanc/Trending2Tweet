"""Prueba rápida de conexión con el LLM."""

from openai import OpenAI
import config

print(f"Base URL: {config.LLM_BASE_URL}")
print(f"Modelo: {config.LLM_MODEL}")
print(f"API Key: {config.LLM_API_KEY[:15]}...")

client = OpenAI(
    api_key=config.LLM_API_KEY,
    base_url=config.LLM_BASE_URL,
)

print("\nConectando con el LLM...")

try:
    completion = client.chat.completions.create(
        model=config.LLM_MODEL,
        messages=[
            {"role": "user", "content": "Di hola en una palabra"},
        ],
        max_tokens=10,
        temperature=0.2,
    )
    print(f"Respuesta: {completion.choices[0].message.content}")
    print("\n✅ Conexión exitosa!")
except Exception as e:
    print(f"\n❌ Error: {type(e).__name__}: {e}")
