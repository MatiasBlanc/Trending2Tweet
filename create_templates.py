"""Script para crear templates iniciales de estilos de gancho."""

from obsidian_vault import guardar_template


ESTILOS_GANCHO = [
    {
        "nombre": "Consecuencia Incómoda",
        "estilo": "Abre con la consecuencia más incómoda o inesperada de esta noticia para los developers. No la noticia en sí, sino lo que implica en la práctica para quien escribe código hoy.",
        "estructura": "1. Consecuencia práctica\n2. Por qué importa ahora\n3. Ejemplo concreto",
        "ejemplo": "Los juniors van a sufrir con esto. No porque sea difícil, sino porque todo lo que aprendieron sobre [X] ya no aplica..."
    },
    {
        "nombre": "Todo Cambió",
        "estilo": "Usa el formato 'Todo lo que sabíamos sobre [X] acaba de cambiar' adaptado al contexto exacto de la noticia. Sé específico con qué es lo que cambió.",
        "estructura": "1. Afirmación de cambio\n2. Qué era antes\n3. Qué es ahora",
        "ejemplo": "Todo lo que sabíamos sobre memory safety acaba de cambiar. El borrow checker ya no es la única opción..."
    },
    {
        "nombre": "Dato Oculto",
        "estilo": "Abre revelando el dato más sorprendente o contraintuitivo de la noticia — el que la mayoría pasaría por alto pero que cambia cómo se lee todo lo demás.",
        "estructura": "1. Dato sorprendente\n2. Por qué es importante\n3. Implicación",
        "ejemplo": "El 73% de los desarrolladores no sabe que [X] ahora hace [Y]. Y eso cambia todo..."
    },
    {
        "nombre": "Tensión Ecosistema",
        "estilo": "Plantea la tensión central que esta noticia crea en el ecosistema: ¿quién gana, quién pierde, qué stack queda en duda? Empieza con esa fricción.",
        "estructura": "1. Tensión/conflicto\n2. Quién gana\n3. Quién pierde",
        "ejemplo": "La guerra entre [X] e [Y] acaba de escalar. Y los que usamos [Z] estamos en medio..."
    },
    {
        "nombre": "Pregunta Senior",
        "estilo": "Abre con la pregunta que los seniors de tu empresa estarían haciendo en Slack ahora mismo si vieran esta noticia. Concreta, técnica, sin respuesta obvia.",
        "estructura": "1. Pregunta técnica\n2. Contexto\n3. Por qué es difícil",
        "ejemplo": "¿Migramos a [X] o esperamos a que [Y] esté listo? Esa es la pregunta que todos están haciendo..."
    },
    {
        "nombre": "Antes vs Ahora",
        "estilo": "Usa el contraste: muestra cómo era antes vs. cómo cambia ahora con esta noticia. Una sola línea, sin relleno.",
        "estructura": "1. Antes (una línea)\n2. Ahora (una línea)\n3. Implicación",
        "ejemplo": "Antes: [X] era imposible. Ahora: [X] es trivial. La diferencia es [Y]..."
    },
    {
        "nombre": "Afirmación Divisiva",
        "estilo": "Abre con una afirmación que divida a la comunidad en dos posiciones claras. El objetivo es que quien lee sienta la necesidad de posicionarse.",
        "estructura": "1. Afirmación polémica\n2. Argumento a favor\n3. Argumento en contra",
        "ejemplo": "[X] es mejor que [Y]. Punto. Y si no estás de acuerdo, es porque no has visto [Z]..."
    },
    {
        "nombre": "Trazabilidad HN",
        "estilo": "Comienza con el dato de tracción de Hacker News (puntos + comentarios) como prueba social de por qué esta noticia merece atención ahora, luego revela el tema.",
        "estructura": "1. Métrica social\n2. Tema\n3. Por qué importa",
        "ejemplo": "500+ puntos en HN en 2 horas. 340+ comentarios. La comunidad está hablando de [X]..."
    },
]


def main():
    """Crea los templates iniciales."""
    print("━" * 50)
    print("  Creando templates de gancho...")
    print("━" * 50)
    
    for estilo in ESTILOS_GANCHO:
        guardar_template(
            nombre=estilo["nombre"],
            estilo_gancho=estilo["estilo"],
            estructura=estilo["estructura"],
            ejemplo_tweet=estilo.get("ejemplo"),
        )
    
    print("\n✅ Templates creados correctamente")


if __name__ == "__main__":
    main()
