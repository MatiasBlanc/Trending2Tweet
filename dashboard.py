"""Dashboard TUI para visualizar métricas de tweets."""

import sys
from datetime import datetime
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.layout import Layout
from rich.text import Text
from rich import box

from metrics_db import (
    init_db,
    obtener_todos_tweets,
    obtener_estadisticas_por_fuente,
    obtener_estadisticas_por_prompt,
    obtener_estadisticas_por_estilo,
    obtener_historial_tweet,
)

console = Console()


def formatear_numero(valor: float, decimales: int = 1) -> str:
    """Formatea un número para mostrar en el dashboard.

    Args:
        valor: Número a formatear.
        decimales: Cantidad de decimales.

    Returns:
        Número formateado como string.
    """
    if valor is None:
        return "0"
    if isinstance(valor, float):
        return f"{valor:,.{decimales}f}"
    return f"{valor:,}"


def crear_header() -> Panel:
    """Crea el encabezado del dashboard.

    Returns:
        Panel con el título y fecha.
    """
    titulo = Text("📊 TRENDING2TWEET - ANALYTICS DASHBOARD", style="bold cyan")
    fecha = Text(f"  {datetime.now().strftime('%Y-%m-%d %H:%M')}", style="dim")

    return Panel(
        Text.assemble(titulo, fecha),
        box=box.DOUBLE,
        style="blue",
    )


def crear_tabla_resumen() -> Panel:
    """Crea la tabla de resumen general.

    Returns:
        Panel con estadísticas generales.
    """
    tweets = obtener_todos_tweets(limit=1000)

    if not tweets:
        return Panel(
            "[yellow]No hay tweets registrados todavía.[/yellow]",
            title="Resumen General",
            box=box.ROUNDED,
        )

    total = len(tweets)
    total_likes = sum(t.get("likes_latest", 0) or 0 for t in tweets)
    total_rts = sum(t.get("retweets_latest", 0) or 0 for t in tweets)
    total_replies = sum(t.get("replies_latest", 0) or 0 for t in tweets)
    total_impressions = sum(t.get("impressions_latest", 0) or 0 for t in tweets)
    avg_engagement = sum(t.get("engagement_score", 0) or 0 for t in tweets) / total if total > 0 else 0

    # Mejor tweet
    mejor = max(tweets, key=lambda t: t.get("engagement_score", 0) or 0)

    texto = Text()
    texto.append(f"  Total tweets:      ", style="bold")
    texto.append(f"{total}\n", style="cyan")
    texto.append(f"  Total likes:       ", style="bold")
    texto.append(f"{formatear_numero(total_likes)}\n", style="red")
    texto.append(f"  Total retweets:    ", style="bold")
    texto.append(f"{formatear_numero(total_rts)}\n", style="green")
    texto.append(f"  Total replies:     ", style="bold")
    texto.append(f"{formatear_numero(total_replies)}\n", style="yellow")
    texto.append(f"  Total impressions: ", style="bold")
    texto.append(f"{formatear_numero(total_impressions)}\n", style="magenta")
    texto.append(f"  Avg engagement:    ", style="bold")
    texto.append(f"{formatear_numero(avg_engagement)}\n\n", style="cyan")
    texto.append(f"  🏆 Mejor tweet:\n", style="bold yellow")
    texto.append(f"     ID: {mejor['tweet_id']}\n", style="dim")
    texto.append(f"     Score: {formatear_numero(mejor.get('engagement_score', 0))}\n", style="green")
    texto.append(f"     {mejor['texto'][:80]}...", style="dim")

    return Panel(texto, title="Resumen General", box=box.ROUNDED)


def crear_tabla_por_fuente() -> Panel:
    """Crea la tabla de estadísticas por fuente.

    Returns:
        Panel con tabla de estadísticas por source.
    """
    stats = obtener_estadisticas_por_fuente()

    if not stats:
        return Panel(
            "[yellow]Sin datos de fuentes.[/yellow]",
            title="Por Fuente",
            box=box.ROUNDED,
        )

    table = Table(box=box.SIMPLE, show_header=True, header_style="bold cyan")
    table.add_column("Fuente", style="bold")
    table.add_column("Tweets", justify="right")
    table.add_column("Avg Eng.", justify="right")
    table.add_column("Avg Likes", justify="right")
    table.add_column("Avg RTs", justify="right")
    table.add_column("Avg Replies", justify="right")
    table.add_column("Max Eng.", justify="right", style="green")

    for stat in stats:
        table.add_row(
            stat["source"],
            str(stat["total_tweets"]),
            formatear_numero(stat["avg_engagement"]),
            formatear_numero(stat["avg_likes"]),
            formatear_numero(stat["avg_retweets"]),
            formatear_numero(stat["avg_replies"]),
            formatear_numero(stat["max_engagement"]),
        )

    return Panel(table, title="Rendimiento por Fuente", box=box.ROUNDED)


def crear_tabla_por_prompt() -> Panel:
    """Crea la tabla de estadísticas por prompt.

    Returns:
        Panel con tabla de estadísticas por prompt_file.
    """
    stats = obtener_estadisticas_por_prompt()

    if not stats:
        return Panel(
            "[yellow]Sin datos de prompts.[/yellow]",
            title="Por Prompt",
            box=box.ROUNDED,
        )

    table = Table(box=box.SIMPLE, show_header=True, header_style="bold cyan")
    table.add_column("Prompt", style="bold", max_width=30)
    table.add_column("Tweets", justify="right")
    table.add_column("Avg Eng.", justify="right")
    table.add_column("Avg Likes", justify="right")
    table.add_column("Avg RTs", justify="right")
    table.add_column("Max Eng.", justify="right", style="green")

    for stat in stats:
        # Extraer solo el nombre del archivo
        nombre = stat["prompt_file"].split("/")[-1] if stat["prompt_file"] else "N/A"
        table.add_row(
            nombre,
            str(stat["total_tweets"]),
            formatear_numero(stat["avg_engagement"]),
            formatear_numero(stat["avg_likes"]),
            formatear_numero(stat["avg_retweets"]),
            formatear_numero(stat["max_engagement"]),
        )

    return Panel(table, title="Rendimiento por Prompt", box=box.ROUNDED)


def crear_tabla_por_estilo() -> Panel:
    """Crea la tabla de estadísticas por estilo de gancho.

    Returns:
        Panel con tabla de estadísticas por template_estilo.
    """
    stats = obtener_estadisticas_por_estilo()

    if not stats:
        return Panel(
            "[yellow]Sin datos de estilos (solo aplica a noticias).[/yellow]",
            title="Por Estilo de Gancho",
            box=box.ROUNDED,
        )

    table = Table(box=box.SIMPLE, show_header=True, header_style="bold cyan")
    table.add_column("Estilo", style="bold", max_width=40)
    table.add_column("Tweets", justify="right")
    table.add_column("Avg Eng.", justify="right")
    table.add_column("Avg Likes", justify="right")
    table.add_column("Max Eng.", justify="right", style="green")

    for stat in stats:
        # Truncar el estilo para que quepa
        estilo = (stat["template_estilo"][:37] + "...") if stat["template_estilo"] and len(stat["template_estilo"]) > 40 else (stat["template_estilo"] or "N/A")
        table.add_row(
            estilo,
            str(stat["total_tweets"]),
            formatear_numero(stat["avg_engagement"]),
            formatear_numero(stat["avg_likes"]),
            formatear_numero(stat["max_engagement"]),
        )

    return Panel(table, title="Rendimiento por Estilo de Gancho", box=box.ROUNDED)


def crear_tabla_top_tweets(cantidad: int = 10) -> Panel:
    """Crea la tabla de top tweets por engagement.

    Args:
        cantidad: Número de tweets a mostrar.

    Returns:
        Panel con tabla de top tweets.
    """
    tweets = obtener_todos_tweets(order_by="engagement_score", limit=cantidad)

    if not tweets:
        return Panel(
            "[yellow]Sin tweets registrados.[/yellow]",
            title="Top Tweets",
            box=box.ROUNDED,
        )

    table = Table(box=box.SIMPLE, show_header=True, header_style="bold cyan")
    table.add_column("#", style="dim", width=3)
    table.add_column("ID", style="dim", width=15)
    table.add_column("Fuente", width=12)
    table.add_column("Tweet", max_width=50)
    table.add_column("❤️", justify="right", width=5)
    table.add_column("🔁", justify="right", width=5)
    table.add_column("💬", justify="right", width=5)
    table.add_column("Score", justify="right", style="green", width=8)

    for i, tweet in enumerate(tweets[:cantidad], 1):
        # Truncar texto del tweet
        texto = tweet["texto"][:47] + "..." if len(tweet["texto"]) > 50 else tweet["texto"]
        texto = texto.replace("\n", " ")

        table.add_row(
            str(i),
            tweet["tweet_id"][:12] + "...",
            tweet.get("source", "N/A"),
            texto,
            str(tweet.get("likes_latest", 0) or 0),
            str(tweet.get("retweets_latest", 0) or 0),
            str(tweet.get("replies_latest", 0) or 0),
            formatear_numero(tweet.get("engagement_score", 0) or 0),
        )

    return Panel(table, title=f"Top {cantidad} Tweets por Engagement", box=box.ROUNDED)


def crear_tabla_historial(tweet_id: str) -> Panel:
    """Crea la tabla de historial de métricas para un tweet específico.

    Args:
        tweet_id: ID del tweet a consultar.

    Returns:
        Panel con el historial de métricas.
    """
    historial = obtener_historial_tweet(tweet_id)

    if not historial:
        return Panel(
            f"[yellow]Sin historial para el tweet {tweet_id}.[/yellow]",
            title="Historial de Métricas",
            box=box.ROUNDED,
        )

    table = Table(box=box.SIMPLE, show_header=True, header_style="bold cyan")
    table.add_column("Fecha", style="dim")
    table.add_column("❤️ Likes", justify="right")
    table.add_column("🔁 RTs", justify="right")
    table.add_column("💬 Replies", justify="right")
    table.add_column("👁 Impr.", justify="right")
    table.add_column("🔖 Saves", justify="right")

    for snap in historial:
        fecha = snap["collected_at"][:16] if snap["collected_at"] else "N/A"
        table.add_row(
            fecha,
            str(snap.get("likes", 0)),
            str(snap.get("retweets", 0)),
            str(snap.get("replies", 0)),
            str(snap.get("impressions", 0)),
            str(snap.get("bookmarks", 0)),
        )

    return Panel(table, title=f"Historial: {tweet_id}", box=box.ROUNDED)


def mostrar_dashboard() -> None:
    """Muestra el dashboard completo en la terminal."""
    init_db()

    console.clear()
    console.print(crear_header())
    console.print()

    # Resumen general
    console.print(crear_tabla_resumen())
    console.print()

    # Estadísticas por fuente
    console.print(crear_tabla_por_fuente())
    console.print()

    # Estadísticas por prompt
    console.print(crear_tabla_por_prompt())
    console.print()

    # Estadísticas por estilo (si hay datos)
    console.print(crear_tabla_por_estilo())
    console.print()

    # Top tweets
    console.print(crear_tabla_top_tweets(10))


def mostrar_historial(tweet_id: str) -> None:
    """Muestra el historial de un tweet específico.

    Args:
        tweet_id: ID del tweet a consultar.
    """
    init_db()

    console.clear()
    console.print(crear_header())
    console.print()
    console.print(crear_tabla_historial(tweet_id))


def main() -> None:
    """Punto de entrada principal."""
    if len(sys.argv) > 1 and sys.argv[1] == "--historial":
        if len(sys.argv) < 3:
            print("Uso: python dashboard.py --historial <tweet_id>")
            sys.exit(1)
        mostrar_historial(sys.argv[2])
    else:
        mostrar_dashboard()


if __name__ == "__main__":
    main()
