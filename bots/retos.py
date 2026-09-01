"""Bot de Retos de Código: genera desafíos, quizzes y acertijos técnicos para X en Obsidian.

Uso:
    python -m bots.retos [lenguaje/tema] [cantidad] [dificultad]
    o con flags: python -m bots.retos [lenguaje] --dificultad [facil|medio|dificil] [cantidad]

Ejemplos:
    python -m bots.retos                       # Dificultad fácil (por defecto), 1 reto
    python -m bots.retos python 2              # Python, 2 retos, fácil (por defecto)
    python -m bots.retos python 2 dificil      # Python, 2 retos, difícil
    python -m bots.retos javascript medio      # JS, 1 reto, medio
    python -m bots.retos sql --dificultad dificil
    python -m bots.retos dificil               # Aleatorio, 1 reto, difícil
"""

import random
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional

from src import config
from src.db import mark_as_processed
from src.llm_client import generate_tweet
from src.obsidian_vault import guardar_borrador

PROMPT_FILE = "prompts/prompt_retos.txt"

DIFICULTADES_VALIDAS = {
    "facil": "facil",
    "fácil": "facil",
    "easy": "facil",
    "basico": "facil",
    "básico": "facil",
    "principiante": "facil",
    "junior": "facil",
    "medio": "medio",
    "medium": "medio",
    "intermedio": "medio",
    "inter": "medio",
    "mid": "medio",
    "dificil": "dificil",
    "difícil": "dificil",
    "hard": "dificil",
    "avanzado": "dificil",
    "senior": "dificil",
}

TEMAS_Y_LENGUAJES = [
    {
        "lenguaje": "Python",
        "conceptos": {
            "facil": [
                "is vs == con strings y enteros pequeños",
                "mutabilidad de listas vs inmutabilidad de tuplas",
                "valores por defecto falsy ([], {}, 0, '')",
                "slicing básico y pasos negativos (lista[::-1])",
                "orden de precedencia y evaluación en 'and' / 'or'",
                "scope básico de variables en funciones vs globales",
            ],
            "medio": [
                "mutabilidad de listas/dicts como default args en funciones",
                "closures y late binding en list comprehensions o bucles",
                "desempaquetado avanzado con * y **",
                "generadores y preservación de estado con yield",
                "decoradores con y sin argumentos",
                "comportamiento de copy() shallow vs deepcopy()",
            ],
            "dificil": [
                "metaclases y orden de ejecución de __new__ vs __init__",
                "descriptores (__get__, __set__) y getattr vs getattribute",
                "generadores con send(), throw() y yield from delegados",
                "internals de memoria: sys.intern, id recycling y small int cache",
                "closures con variables no locales y memory reference leaks",
                "subtyping con TypeVar, Generic y runtime protocols en typing",
            ],
        },
    },
    {
        "lenguaje": "JavaScript",
        "conceptos": {
            "facil": [
                "== vs === (loose vs strict equality)",
                "typeof null, typeof undefined y typeof NaN",
                "mutación de propiedades en objetos declarados con const",
                "diferencia entre .map() y .forEach()",
                "Truthy y Falsy values (![] vs !'')",
                "orden de operaciones con operadores de incremento (++x vs x++)",
            ],
            "medio": [
                "coerción de tipos extraña ([] + {}, +!+[], [1,2] + [3,4])",
                "event loop y orden de ejecución de microtasks (Promise) vs macrotasks (setTimeout)",
                "closures y scope léxico con var vs let en bucles for",
                "this en arrow functions vs funciones normales y bind/call/apply",
                "hoisting de variables var vs funciones declaradas",
                "Array.prototype methods mutables vs inmutables (.sort, .splice vs .slice)",
            ],
            "dificil": [
                "prototype pollution y cadena de prototipos con Object.create(null)",
                "async generators con Symbol.asyncIterator y recursión con backpressure",
                "WeakRef y FinalizationRegistry con garbage collection internals",
                "Tagged template literals avanzados y raw strings",
                "Promise.race vs Promise.any con rejection handling no capturado",
                "Proxy traps, Reflect API y manipulación de property descriptors",
            ],
        },
    },
    {
        "lenguaje": "TypeScript",
        "conceptos": {
            "facil": [
                "any vs unknown: cuándo usar cada uno",
                "interfaces vs type aliases básicos",
                "optional chaining (?.) y nullish coalescing (??)",
                "arrays de sólo lectura (readonly number[])",
                "tipado de parámetros opcionales con valores por defecto",
            ],
            "medio": [
                "type narrowing con type guards (typeof, instanceof, in)",
                "discriminated unions con propiedad común de tipo literal",
                "inmutabilidad estricta con 'as const'",
                "satisfies operator vs type annotation",
                "utility types clave: Pick, Omit, Partial, Record",
            ],
            "dificil": [
                "inferencia en tipos condicionales con 'infer' anidado",
                "distribución de tipos unión sobre condicionales genéricos",
                "template literal types recursivos para parsing de strings en compilación",
                "marca nominal (nominal/branded types) para IDs seguros",
                "covarianza y contravarianza en firmas de funciones",
            ],
        },
    },
    {
        "lenguaje": "SQL",
        "conceptos": {
            "facil": [
                "WHERE vs HAVING en consultas agrupadas",
                "comportamiento básico de NULL con IS NULL vs = NULL",
                "INNER JOIN vs LEFT JOIN cuando no hay coincidencias",
                "COUNT(*) vs COUNT(nombre_columna) cuando hay nulos",
                "ORDER BY con NULLS FIRST / NULLS LAST",
            ],
            "medio": [
                "trampa de NOT IN con subqueries que contienen NULL",
                "diferencia de filtrado en ON vs WHERE en un LEFT JOIN",
                "Window Functions: ROW_NUMBER() vs RANK() vs DENSE_RANK()",
                "COALESCE vs IFNULL vs NULLIF",
                "UNION vs UNION ALL: rendimiento y duplicados",
            ],
            "dificil": [
                "CTE recursivas (WITH RECURSIVE) para árboles jerárquicos",
                "niveles de aislamiento de transacciones (Phantom Reads vs Non-repeatable)",
                "LATERAL JOINs y correlated subqueries avanzadas",
                "Window Frames con ROWS BETWEEN vs RANGE BETWEEN",
                "índices compuestos y el problema del orden de columnas en B-Tree",
            ],
        },
    },
    {
        "lenguaje": "Rust",
        "conceptos": {
            "facil": [
                "inmutabilidad por defecto en variables (let vs let mut)",
                "shadowing de variables con el mismo nombre",
                "match básico con cobertura exhaustiva",
                "Option<T> y manejo básico con unwrap vs unwrap_or",
                "ownership básico: mover un String vs copiar un i32",
            ],
            "medio": [
                "borrow checker: referencias mutables (&mut) vs múltiples inmutables (&)",
                "Result<T, E> y propagación de errores con el operador ?",
                "clonación (.clone()) vs referencias prestadas",
                "iteradores con .map(), .filter() y recolección con .collect()",
                "closures y captura de entorno: Fn, FnMut y FnOnce",
            ],
            "dificil": [
                "lifetimes explícitos ('a) en structs y referencias cruzadas",
                "smart pointers: Rc/Arc vs RefCell/Mutex y RefCell borrow panic en runtime",
                "trait objects (dyn Trait) y tamaño dinámico (Sized vs ?Sized)",
                "unsafe Rust: raw pointers (*const / *mut) y desreferenciación",
                "Drop order y drop flags en structs complejos",
            ],
        },
    },
    {
        "lenguaje": "Go",
        "conceptos": {
            "facil": [
                "declaración corta con := vs var",
                "retorno de múltiples valores y manejo básico de error",
                "for como único bucle en Go (equivalente a while)",
                "defer básico y orden de ejecución LIFO",
                "structs y valores por defecto (zero values)",
            ],
            "medio": [
                "slices vs arrays: capacidad vs longitud al hacer append",
                "shadowing accidental de variables con := en bloques if/for",
                "goroutines con channels sin buffer (deadlock simple)",
                "punteros en métodos receptores: (t Tipo) vs (t *Tipo)",
                "defer evaluando argumentos en el momento de la declaración",
            ],
            "dificil": [
                "select con múltiples channels y caso default no bloqueante",
                "data races en closures capturando variables del bucle for (pre Go 1.22)",
                "interfaces vacías (any) y type assertions con coma-ok vs panic",
                "sync.WaitGroup con Add/Done pasados por valor vs por puntero",
                "internals del runtime: memory escape analysis (stack vs heap)",
            ],
        },
    },
    {
        "lenguaje": "Algoritmos",
        "conceptos": {
            "facil": [
                "complejidad temporal O(1) vs O(n)",
                "búsqueda lineal vs búsqueda binaria en array ordenado",
                "fuerza bruta en comparación de strings",
                "reversión de arrays in-place",
                "detección de palíndromos simple",
            ],
            "medio": [
                "complejidad Big-O de bucles anidados con saltos variables",
                "búsqueda binaria y el error off-by-one con low/high",
                "Two Pointers vs Fuerza Bruta O(n^2) a O(n)",
                "recursión y límite de call stack (Stack Overflow)",
                "tablas hash y resolución de colisiones básicas",
            ],
            "dificil": [
                "complejidad amortizada vs peor caso en estructuras dinámicas",
                "programación dinámica: memoization vs tabulación con optimización de espacio",
                "algoritmo de Floyd de detección de ciclos (Tortuga y Liebre) y punto de inicio",
                "Fast Exponentiation (O(log n)) y operaciones modulares",
                "Sliding Window con deque/monotonic queue para máximo en ventana O(n)",
            ],
        },
    },
]


def normalizar_dificultad(dif: Optional[str]) -> str:
    """Normaliza el nombre del nivel de dificultad. Por defecto 'facil'."""
    if not dif:
        return "facil"
    dif_clean = dif.strip().lower().lstrip("-")
    return DIFICULTADES_VALIDAS.get(dif_clean, "facil")


def _seleccionar_tema(
    filtro_lenguaje: Optional[str] = None, dificultad: str = "facil"
) -> tuple[str, str]:
    """Selecciona un lenguaje y un concepto técnico según el nivel de dificultad."""
    dif_norm = normalizar_dificultad(dificultad)

    temas = TEMAS_Y_LENGUAJES
    if filtro_lenguaje:
        filtro_lower = filtro_lenguaje.lower()
        coincidencias = [
            t for t in TEMAS_Y_LENGUAJES if filtro_lower in t["lenguaje"].lower()
        ]
        if coincidencias:
            temas = coincidencias

    tema_obj = random.choice(temas)
    conceptos_obj = tema_obj.get("conceptos", {})

    if isinstance(conceptos_obj, dict):
        conceptos_lista = (
            conceptos_obj.get(dif_norm)
            or conceptos_obj.get("facil")
            or list(conceptos_obj.values())[0]
        )
    else:
        conceptos_lista = conceptos_obj

    concepto = (
        random.choice(conceptos_lista)
        if conceptos_lista
        else "conceptos clave del lenguaje"
    )
    return tema_obj["lenguaje"], concepto


def generar_reto(lenguaje: str, concepto: str, dificultad: str = "facil") -> str:
    """Invoca al LLM para generar un reto técnico calibrado a la dificultad deseada."""
    dif_norm = normalizar_dificultad(dificultad)
    desc_dif = {
        "facil": "FÁCIL / PRINCIPIANTE: concepto fundamental, sintaxis limpia, accesible para juniors y estudiantes.",
        "medio": "MEDIO / INTERMEDIO: trampa común en entrevistas, comportamiento no evidente del lenguaje, nivel mid-level.",
        "dificil": "DIFÍCIL / AVANZADO: caso borde oscuro, internals de compilador o memoria, diseñado para hacer dudar a desarrolladores senior.",
    }.get(dif_norm, "FÁCIL")

    user_msg = (
        f"Genera un reto de código interactivo para X sobre:\n"
        f"- Lenguaje / Tema: {lenguaje}\n"
        f"- Nivel de dificultad: {dif_norm.upper()} ({desc_dif})\n"
        f"- Concepto / Trampa clave: {concepto}\n"
        f"- Formato: Pregunta + Snippet de código de 4 a 8 líneas + 4 opciones (A, B, C, D) o pregunta directa.\n"
        f"- Incluye la solución al final tras '--- RESPUESTA ---'."
    )
    return generate_tweet(PROMPT_FILE, user_msg)


def parse_args(argv: list[str]) -> tuple[Optional[str], int, str]:
    """Parsea los argumentos CLI para lenguaje, cantidad y dificultad.

    Por defecto dificultad es 'facil' y cantidad es 1.
    """
    filtro_lenguaje = None
    limite = 1
    dificultad = "facil"

    args = [a for a in argv if a.strip()]
    i = 0
    while i < len(args):
        arg = args[i]
        arg_lower = arg.lower().lstrip("-")

        # Flags explícitos de dificultad
        if arg.lower() in ("--dificultad", "-d", "--dif", "--level") and i + 1 < len(args):
            dificultad = normalizar_dificultad(args[i + 1])
            i += 2
            continue
        elif arg.lower().startswith("--dificultad="):
            dificultad = normalizar_dificultad(arg.split("=", 1)[1])
            i += 1
            continue

        # Dificultad como argumento posicional
        if arg_lower in DIFICULTADES_VALIDAS:
            dificultad = normalizar_dificultad(arg_lower)
            i += 1
            continue

        # Cantidad numérica
        if arg.isdigit():
            limite = min(max(1, int(arg)), config.MAX_GENERATION_LIMIT)
            i += 1
            continue

        # Lenguaje o tema
        if not filtro_lenguaje and not arg.startswith("-"):
            filtro_lenguaje = arg
            i += 1
            continue

        i += 1

    return filtro_lenguaje, limite, dificultad


def main() -> None:
    filtro_lenguaje, limite, dificultad = parse_args(sys.argv[1:])
    dif_display = dificultad.capitalize()

    print("━" * 55)
    print("  🧩 Bot de Retos de Código (Obsidian / codigo/)")
    print(f"  🎯 Dificultad: {dif_display} | Cantidad: {limite}")
    if filtro_lenguaje:
        print(f"  🔍 Filtro de tema: {filtro_lenguaje}")
    print("━" * 55)

    guardados = 0
    for i in range(limite):
        lenguaje, concepto = _seleccionar_tema(filtro_lenguaje, dificultad=dificultad)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        item_id = f"reto_{lenguaje.lower()}_{dificultad}_{timestamp}_{i+1}"

        print(
            f"\n  🎯 Generando reto [{i+1}/{limite}]: {lenguaje} [{dif_display}] ({concepto})..."
        )

        try:
            contenido_completo = generar_reto(
                lenguaje=lenguaje, concepto=concepto, dificultad=dificultad
            )
        except Exception as e:
            print(f"  ❌ Error generando reto: {e}")
            continue

        # Separar el tweet principal de la respuesta
        partes = contenido_completo.split("--- RESPUESTA ---")
        tweet_text = partes[0].strip()
        solucion = partes[1].strip() if len(partes) > 1 else ""

        if config.FORCE_280_CHAR_TWEET and len(tweet_text) > 280:
            tweet_text = tweet_text[:277] + "..."

        print(f"\n{'━' * 55}")
        print(f"  Reto de Código generado ({dif_display}):")
        print(f"{'━' * 55}")
        print(tweet_text)
        if solucion:
            print(f"\n💡 Solución / Explicación:\n{solucion}")
        print(f"{'━' * 55}")

        titulo = f"Reto {lenguaje} ({dif_display}): {concepto[:30]}"
        filepath = guardar_borrador(
            texto=tweet_text,
            categoria="codigo",
            source="retos_codigo",
            titulo=titulo,
            item_id=item_id,
            prompt_file=PROMPT_FILE,
            dificultad=dificultad,
            notas=f"### Solución y Explicación\n\n{solucion}" if solucion else None,
        )

        if filepath:
            mark_as_processed(item_id, "retos_codigo", texto=tweet_text[:100])
            print(f"  ✅ Reto guardado en Obsidian: {Path(filepath).name}")
            print(f"  📂 Carpeta: codigo/ (Dificultad: {dif_display})")
            guardados += 1

    if guardados > 0:
        print(
            f"\n✨ Completado: {guardados} reto(s) [{dif_display}] guardado(s) en Obsidian [codigo/]."
        )
    else:
        print("\n  ⚠️ No se pudo generar ningún reto.")


if __name__ == "__main__":
    main()
