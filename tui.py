"""Dashboard TUI interactivo para analytics de tweets usando textual."""

import sys
from datetime import datetime
from typing import Optional

from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Container, Horizontal, Vertical
from textual.css.query import NoMatches
from textual.screen import Screen
from textual.widgets import (
    DataTable,
    Footer,
    Header,
    Label,
    ListItem,
    ListView,
    ProgressBar,
    RichLog,
    Static,
    TabbedContent,
    TabPane,
)
from rich.text import Text
from rich.table import Table
from rich.panel import Panel
from rich import box

from metrics_db import (
    init_db,
    obtener_todos_tweets,
    obtener_estadisticas_por_fuente,
    obtener_estadisticas_por_prompt,
    obtener_estadisticas_por_estilo,
    obtener_historial_tweet,
    obtener_tweets_para_few_shot,
)


def formatear_numero(valor: float, decimales: int = 1) -> str:
    """Formatea un número para mostrar."""
    if valor is None:
        return "0"
    if isinstance(valor, float):
        return f"{valor:,.{decimales}f}"
    return f"{valor:,}"


class ResumenPanel(Static):
    """Panel de resumen general."""

    def compose(self) -> ComposeResult:
        yield Label("Cargando resumen...", id="resumen-label")

    def on_mount(self) -> None:
        self.actualizar()

    def actualizar(self) -> None:
        tweets = obtener_todos_tweets(limit=1000)

        if not tweets:
            self.query_one("#resumen-label").update(
                "[yellow]No hay tweets registrados todavía.[/yellow]"
            )
            return

        total = len(tweets)
        total_likes = sum(t.get("likes_latest", 0) or 0 for t in tweets)
        total_rts = sum(t.get("retweets_latest", 0) or 0 for t in tweets)
        total_replies = sum(t.get("replies_latest", 0) or 0 for t in tweets)
        total_impressions = sum(t.get("impressions_latest", 0) or 0 for t in tweets)
        avg_engagement = sum(t.get("engagement_score", 0) or 0 for t in tweets) / total if total > 0 else 0

        mejor = max(tweets, key=lambda t: t.get("engagement_score", 0) or 0)

        texto = Text()
        texto.append("  Total tweets:      ", style="bold")
        texto.append(f"{total}\n", style="cyan")
        texto.append("  Total likes:       ", style="bold")
        texto.append(f"{formatear_numero(total_likes)}\n", style="red")
        texto.append("  Total retweets:    ", style="bold")
        texto.append(f"{formatear_numero(total_rts)}\n", style="green")
        texto.append("  Total replies:     ", style="bold")
        texto.append(f"{formatear_numero(total_replies)}\n", style="yellow")
        texto.append("  Total impressions: ", style="bold")
        texto.append(f"{formatear_numero(total_impressions)}\n", style="magenta")
        texto.append("  Avg engagement:    ", style="bold")
        texto.append(f"{formatear_numero(avg_engagement)}\n\n", style="cyan")
        texto.append("  🏆 Mejor tweet:\n", style="bold yellow")
        texto.append(f"     ID: {mejor['tweet_id']}\n", style="dim")
        texto.append(f"     Score: {formatear_numero(mejor.get('engagement_score', 0))}\n", style="green")
        texto.append(f"     {mejor['texto'][:80]}...", style="dim")

        self.query_one("#resumen-label").update(texto)


class TweetsPanel(Static):
    """Panel de lista de tweets."""

    def compose(self) -> ComposeResult:
        yield DataTable(id="tweets-table")

    def on_mount(self) -> None:
        table = self.query_one("#tweets-table", DataTable)
        table.add_columns("#", "Fuente", "Tweet", "❤️", "🔁", "💬", "Score", "Tweet ID")
        table.cursor_type = "row"
        self.actualizar()

    def actualizar(self, orden: str = "engagement_score", filtro: str = None) -> None:
        table = self.query_one("#tweets-table", DataTable)
        table.clear()

        tweets = obtener_todos_tweets(order_by=orden, limit=100)

        if filtro:
            tweets = [t for t in tweets if t.get("source") == filtro]

        for i, tweet in enumerate(tweets, 1):
            texto = tweet["texto"][:47] + "..." if len(tweet["texto"]) > 50 else tweet["texto"]
            texto = texto.replace("\n", " ")

            table.add_row(
                str(i),
                tweet.get("source", "N/A"),
                texto,
                str(tweet.get("likes_latest", 0) or 0),
                str(tweet.get("retweets_latest", 0) or 0),
                str(tweet.get("replies_latest", 0) or 0),
                formatear_numero(tweet.get("engagement_score", 0) or 0),
                tweet["tweet_id"],
                key=tweet["tweet_id"],
            )


class PromptsPanel(Static):
    """Panel de rendimiento por prompt."""

    def compose(self) -> ComposeResult:
        yield DataTable(id="prompts-table")

    def on_mount(self) -> None:
        table = self.query_one("#prompts-table", DataTable)
        table.add_columns("Prompt", "Tweets", "Avg Eng", "Avg Likes", "Avg RTs", "Max Eng")
        table.cursor_type = "row"
        self.actualizar()

    def actualizar(self) -> None:
        table = self.query_one("#prompts-table", DataTable)
        table.clear()

        stats = obtener_estadisticas_por_prompt()

        for stat in stats:
            nombre = stat["prompt_file"].split("/")[-1] if stat["prompt_file"] else "N/A"
            table.add_row(
                nombre,
                str(stat["total_tweets"]),
                formatear_numero(stat["avg_engagement"]),
                formatear_numero(stat["avg_likes"]),
                formatear_numero(stat["avg_retweets"]),
                formatear_numero(stat["max_engagement"]),
                key=nombre,
            )


class EstilosPanel(Static):
    """Panel de rendimiento por estilo de gancho."""

    def compose(self) -> ComposeResult:
        yield DataTable(id="estilos-table")

    def on_mount(self) -> None:
        table = self.query_one("#estilos-table", DataTable)
        table.add_columns("Estilo", "Tweets", "Avg Eng", "Avg Likes", "Max Eng")
        table.cursor_type = "row"
        self.actualizar()

    def actualizar(self) -> None:
        table = self.query_one("#estilos-table", DataTable)
        table.clear()

        stats = obtener_estadisticas_por_estilo()

        for stat in stats:
            estilo = stat["template_estilo"]
            if estilo and len(estilo) > 50:
                estilo = estilo[:47] + "..."
            table.add_row(
                estilo or "N/A",
                str(stat["total_tweets"]),
                formatear_numero(stat["avg_engagement"]),
                formatear_numero(stat["avg_likes"]),
                formatear_numero(stat["max_engagement"]),
                key=estilo or "N/A",
            )


class HistorialPanel(Static):
    """Panel de historial de un tweet específico."""

    def compose(self) -> ComposeResult:
        yield Label("Selecciona un tweet en la pestaña 'Tweets' y presiona Enter", id="historial-label")
        yield DataTable(id="historial-table")

    def mostrar_historial(self, tweet_id: str) -> None:
        self.query_one("#historial-label").update(f"Historial del tweet: {tweet_id}")

        table = self.query_one("#historial-table", DataTable)
        table.clear()
        table.add_columns("Fecha", "❤️ Likes", "🔁 RTs", "💬 Replies", "👁 Impr.", "🔖 Saves")

        historial = obtener_historial_tweet(tweet_id)

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


class DetalleTweetScreen(Screen):
    """Pantalla de detalle de un tweet."""

    BINDINGS = [
        Binding("escape", "volver", "Volver"),
        Binding("q", "volver", "Volver"),
    ]

    def __init__(self, tweet_id: str) -> None:
        super().__init__()
        self.tweet_id = tweet_id

    def compose(self) -> ComposeResult:
        yield Header()
        yield Container(
            Label(f"Detalle del tweet: {self.tweet_id}", id="detalle-titulo"),
            Static(id="detalle-texto"),
            Label("Historial de métricas:", style="bold"),
            DataTable(id="detalle-historial"),
            Label("\n[dim]Presiona Escape o q para volver[/dim]"),
            id="detalle-container",
        )
        yield Footer()

    def on_mount(self) -> None:
        tweets = obtener_todos_tweets(limit=1000)
        tweet = next((t for t in tweets if t["tweet_id"] == self.tweet_id), None)

        if tweet:
            texto = Text()
            texto.append("  Fuente: ", style="bold")
            texto.append(f"{tweet.get('source', 'N/A')}\n", style="cyan")
            texto.append("  Publicado: ", style="bold")
            texto.append(f"{tweet.get('published_at', 'N/A')[:16]}\n", style="dim")
            texto.append("  Prompt: ", style="bold")
            texto.append(f"{tweet.get('prompt_file', 'N/A')}\n", style="dim")
            texto.append("\n  📝 Texto del tweet:\n", style="bold yellow")
            texto.append(f"  {tweet['texto']}\n", style="white")
            texto.append(f"\n  ❤️ {tweet.get('likes_latest', 0) or 0}", style="red")
            texto.append(f"  🔁 {tweet.get('retweets_latest', 0) or 0}", style="green")
            texto.append(f"  💬 {tweet.get('replies_latest', 0) or 0}", style="yellow")
            texto.append(f"  👁 {tweet.get('impressions_latest', 0) or 0}", style="magenta")
            texto.append(f"  📊 Score: {formatear_numero(tweet.get('engagement_score', 0) or 0)}", style="cyan")

            self.query_one("#detalle-texto").update(texto)

        # Historial
        table = self.query_one("#detalle-historial", DataTable)
        table.add_columns("Fecha", "❤️ Likes", "🔁 RTs", "💬 Replies", "👁 Impr.", "🔖 Saves")

        historial = obtener_historial_tweet(self.tweet_id)
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

    def action_volver(self) -> None:
        self.app.pop_screen()


class DashboardApp(App):
    """Aplicación principal del dashboard TUI."""

    CSS = """
    Screen {
        background: $surface;
    }

    #resumen-label {
        width: 100%;
        height: auto;
        padding: 1;
    }

    DataTable {
        height: 1fr;
    }

    .panel-title {
        dock: top;
        height: 3;
        content-align: center middle;
        background: $accent;
        color: $text;
    }

    #detalle-container {
        padding: 2;
    }

    #detalle-titulo {
        height: 3;
        text-align: center;
        background: $accent;
        color: $text;
        padding: 1;
    }

    #detalle-texto {
        height: auto;
        padding: 1;
        margin-bottom: 1;
    }
    """

    BINDINGS = [
        Binding("q", "quit", "Salir"),
        Binding("r", "refrescar", "Refrescar"),
        Binding("1", "ordenar_fecha", "Ordenar: Fecha"),
        Binding("2", "ordenar_likes", "Ordenar: Likes"),
        Binding("3", "ordenar_score", "Ordenar: Score"),
        Binding("f", "filtrar", "Filtrar fuente"),
    ]

    TITLE = "📊 Trending2Tweet - Analytics Dashboard"

    def __init__(self) -> None:
        super().__init__()
        self.filtro_fuente: Optional[str] = None

    def compose(self) -> ComposeResult:
        yield Header()
        yield TabbedContent(
            TabPane("Resumen", id="tab-resumen"),
            TabPane("Tweets", id="tab-tweets"),
            TabPane("Prompts", id="tab-prompts"),
            TabPane("Estilos", id="tab-estilos"),
            TabPane("Historial", id="tab-historial"),
            initial="tab-tweets",
        )
        yield Footer()

    def on_mount(self) -> None:
        init_db()

        # Agregar paneles
        try:
            resumen_pane = self.query_one("#tab-resumen")
            resumen_pane.compose_add_child(ResumenPanel())

            tweets_pane = self.query_one("#tab-tweets")
            tweets_pane.compose_add_child(TweetsPanel())

            prompts_pane = self.query_one("#tab-prompts")
            prompts_pane.compose_add_child(PromptsPanel())

            estilos_pane = self.query_one("#tab-estilos")
            estilos_pane.compose_add_child(EstilosPanel())

            historial_pane = self.query_one("#tab-historial")
            historial_pane.compose_add_child(HistorialPanel())
        except NoMatches:
            pass

    def on_data_table_row_selected(self, event: DataTable.RowSelected) -> None:
        """Maneja la selección de una fila en la tabla de tweets."""
        if event.data_table.id == "tweets-table":
            tweet_id = event.row_key.value
            if tweet_id:
                self.push_screen(DetalleTweetScreen(tweet_id))

    def action_refrescar(self) -> None:
        """Refresca todos los paneles."""
        try:
            self.query_one(ResumenPanel).actualizar()
            self.query_one(TweetsPanel).actualizar(filtro=self.filtro_fuente)
            self.query_one(PromptsPanel).actualizar()
            self.query_one(EstilosPanel).actualizar()
        except NoMatches:
            pass

    def action_ordenar_fecha(self) -> None:
        """Ordena tweets por fecha."""
        try:
            self.query_one(TweetsPanel).actualizar(orden="published_at", filtro=self.filtro_fuente)
        except NoMatches:
            pass

    def action_ordenar_likes(self) -> None:
        """Ordena tweets por likes."""
        try:
            self.query_one(TweetsPanel).actualizar(orden="likes_latest", filtro=self.filtro_fuente)
        except NoMatches:
            pass

    def action_ordenar_score(self) -> None:
        """Ordena tweets por engagement score."""
        try:
            self.query_one(TweetsPanel).actualizar(orden="engagement_score", filtro=self.filtro_fuente)
        except NoMatches:
            pass

    def action_filtrar(self) -> None:
        """Filtra por fuente (cicla entre todas, github, news, manual)."""
        fuentes = [None, "github", "news", "github_manual"]
        try:
            idx = fuentes.index(self.filtro_fuente)
            self.filtro_fuente = fuentes[(idx + 1) % len(fuentes)]
        except ValueError:
            self.filtro_fuente = fuentes[0]

        filtro_texto = self.filtro_fuente or "todas"
        self.title = f"📊 Dashboard - Fuente: {filtro_texto}"

        try:
            self.query_one(TweetsPanel).actualizar(filtro=self.filtro_fuente)
        except NoMatches:
            pass


def main() -> None:
    """Punto de entrada principal."""
    app = DashboardApp()
    app.run()


if __name__ == "__main__":
    main()
