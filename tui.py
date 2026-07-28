"""Dashboard TUI interactivo para analytics de tweets usando textual."""

from datetime import datetime
from typing import Optional

from rich.text import Text
from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Container, Horizontal, Vertical, VerticalScroll
from textual.css.query import NoMatches
from textual.screen import ModalScreen, Screen
from textual.widgets import (
    DataTable,
    Footer,
    Header,
    Label,
    Rule,
    Sparkline,
    Static,
    TabbedContent,
    TabPane,
)

from metrics_db import (
    init_db,
    obtener_estadisticas_por_estilo,
    obtener_estadisticas_por_fuente,
    obtener_estadisticas_por_prompt,
    obtener_historial_tweet,
    obtener_resumen_global,
    obtener_todos_tweets,
    obtener_tweet,
    obtener_tweets_para_few_shot,
)

# ── Constantes ────────────────────────────────────────────────

FUENTES = [None, "github", "news", "github_manual"]
ORDENES = {
    "published_at": "Fecha",
    "likes_latest": "Likes",
    "engagement_score": "Score",
}
AUTO_REFRESH_SECS = 60
TWEETS_LIMIT = 200


# ── Helpers ───────────────────────────────────────────────────

def formatear_numero(valor: float | int | None, decimales: int = 1) -> str:
    """Formatea un número para mostrar en la UI."""
    if valor is None:
        return "0"
    if isinstance(valor, float):
        if valor == int(valor):
            return f"{int(valor):,}"
        return f"{valor:,.{decimales}f}"
    return f"{valor:,}"


def truncar(texto: str, max_len: int = 50) -> str:
    """Trunca texto a max_len caracteres, colapsando saltos de línea."""
    limpio = (texto or "").replace("\n", " ").strip()
    if len(limpio) <= max_len:
        return limpio
    return limpio[: max_len - 3] + "..."


def delta_str(actual: int, anterior: int | None) -> Text:
    """Devuelve un Text con el delta respecto al snapshot anterior."""
    if anterior is None:
        return Text("—", style="dim")
    diff = actual - anterior
    if diff > 0:
        return Text(f"+{diff}", style="green")
    if diff < 0:
        return Text(str(diff), style="red")
    return Text("0", style="dim")


def fuente_style(source: str | None) -> str:
    """Color por tipo de fuente."""
    return {
        "github": "cyan",
        "news": "yellow",
        "github_manual": "magenta",
    }.get(source or "", "white")


# ── Widgets de paneles ────────────────────────────────────────

class StatusBar(Static):
    """Barra de estado con orden, filtro y última actualización."""

    def actualizar(
        self,
        orden: str,
        filtro: str | None,
        total: int,
        last_refresh: datetime | None = None,
    ) -> None:
        orden_label = ORDENES.get(orden, orden)
        filtro_label = filtro or "todas"
        hora = last_refresh.strftime("%H:%M:%S") if last_refresh else "—"

        texto = Text()
        texto.append("  Orden: ", style="bold dim")
        texto.append(orden_label, style="bold cyan")
        texto.append("  │  Filtro: ", style="dim")
        texto.append(filtro_label, style="bold yellow")
        texto.append("  │  Tweets: ", style="dim")
        texto.append(str(total), style="bold green")
        texto.append("  │  Refresh: ", style="dim")
        texto.append(hora, style="bold")
        texto.append("  │  ? ayuda", style="dim")
        self.update(texto)


class ResumenPanel(Static):
    """Panel de resumen general con breakdown por fuente y top tweets."""

    def compose(self) -> ComposeResult:
        with VerticalScroll():
            yield Static(id="resumen-stats")
            yield Rule()
            yield Label("Por fuente", classes="section-title")
            yield DataTable(id="fuentes-table", cursor_type="row")
            yield Rule()
            yield Label("Top engagement (few-shot)", classes="section-title")
            yield Static(id="resumen-top")

    def on_mount(self) -> None:
        table = self.query_one("#fuentes-table", DataTable)
        table.add_columns("Fuente", "Tweets", "Avg Eng", "Avg ❤️", "Avg 🔁", "Avg 💬", "Max Eng")
        table.zebra_stripes = True
        self.actualizar()

    def actualizar(self) -> None:
        resumen = obtener_resumen_global()
        total = resumen["total_tweets"]

        stats = Text()
        if total == 0:
            stats.append("\n  No hay tweets registrados todavía.\n", style="yellow")
            stats.append("  Publica con main_github.py / main_news.py y recolecta métricas.\n", style="dim")
            self.query_one("#resumen-stats").update(stats)
            self.query_one("#resumen-top").update(Text("  —", style="dim"))
            table = self.query_one("#fuentes-table", DataTable)
            table.clear()
            return

        stats.append("\n")
        filas = [
            ("Total tweets", formatear_numero(total, 0), "bold cyan"),
            ("Likes", formatear_numero(resumen["total_likes"], 0), "red"),
            ("Retweets", formatear_numero(resumen["total_retweets"], 0), "green"),
            ("Replies", formatear_numero(resumen["total_replies"], 0), "yellow"),
            ("Bookmarks", formatear_numero(resumen["total_bookmarks"], 0), "blue"),
            ("Impressions", formatear_numero(resumen["total_impressions"], 0), "magenta"),
            ("Avg engagement", formatear_numero(resumen["avg_engagement"]), "cyan"),
            ("Max engagement", formatear_numero(resumen["max_engagement"]), "bold green"),
        ]
        for label, valor, style in filas:
            stats.append(f"  {label:<16} ", style="bold")
            stats.append(f"{valor}\n", style=style)

        mejor = resumen.get("mejor_tweet")
        if mejor:
            stats.append("\n  🏆 Mejor tweet\n", style="bold yellow")
            stats.append(f"     [{mejor.get('source', '?')}] ", style=fuente_style(mejor.get("source")))
            stats.append(f"score {formatear_numero(mejor.get('engagement_score', 0))}  ", style="green")
            stats.append(f"id {mejor['tweet_id']}\n", style="dim")
            stats.append(f"     {truncar(mejor.get('texto', ''), 90)}\n", style="dim")

        self.query_one("#resumen-stats").update(stats)

        # Tabla por fuente
        table = self.query_one("#fuentes-table", DataTable)
        table.clear()
        for stat in obtener_estadisticas_por_fuente():
            source = stat["source"] or "N/A"
            table.add_row(
                Text(source, style=fuente_style(source)),
                str(stat["total_tweets"]),
                formatear_numero(stat["avg_engagement"]),
                formatear_numero(stat["avg_likes"]),
                formatear_numero(stat["avg_retweets"]),
                formatear_numero(stat["avg_replies"]),
                formatear_numero(stat["max_engagement"]),
                key=source,
            )

        # Top few-shot
        top = obtener_tweets_para_few_shot(5)
        top_text = Text()
        if not top:
            top_text.append("  Sin métricas colectadas todavía.\n", style="dim")
        else:
            for i, t in enumerate(top, 1):
                top_text.append(f"  {i}. ", style="bold")
                top_text.append(f"score {formatear_numero(t.get('engagement_score', 0)):<8} ", style="green")
                top_text.append(f"❤️{t.get('likes_latest', 0)} 🔁{t.get('retweets_latest', 0)}  ", style="dim")
                top_text.append(f"{truncar(t.get('texto', ''), 70)}\n", style="white")
        self.query_one("#resumen-top").update(top_text)


class TweetsPanel(Static):
    """Panel de lista de tweets con métricas."""

    def compose(self) -> ComposeResult:
        yield DataTable(id="tweets-table")

    def on_mount(self) -> None:
        table = self.query_one("#tweets-table", DataTable)
        table.add_columns("#", "Fuente", "Tweet", "❤️", "🔁", "💬", "🔖", "Score", "Fecha", "ID")
        table.cursor_type = "row"
        table.zebra_stripes = True
        self.actualizar()

    def actualizar(self, orden: str = "engagement_score", filtro: str | None = None) -> int:
        """Recarga la tabla. Devuelve la cantidad de filas mostradas."""
        table = self.query_one("#tweets-table", DataTable)
        table.clear()

        tweets = obtener_todos_tweets(order_by=orden, limit=TWEETS_LIMIT)
        if filtro:
            tweets = [t for t in tweets if t.get("source") == filtro]

        for i, tweet in enumerate(tweets, 1):
            source = tweet.get("source", "N/A")
            fecha = (tweet.get("published_at") or "")[:16]
            score = tweet.get("engagement_score", 0) or 0

            table.add_row(
                str(i),
                Text(source, style=fuente_style(source)),
                truncar(tweet.get("texto", ""), 48),
                str(tweet.get("likes_latest", 0) or 0),
                str(tweet.get("retweets_latest", 0) or 0),
                str(tweet.get("replies_latest", 0) or 0),
                str(tweet.get("bookmarks_latest", 0) or 0),
                Text(formatear_numero(score), style="bold green" if score > 0 else "dim"),
                Text(fecha, style="dim"),
                Text(tweet["tweet_id"], style="dim"),
                key=tweet["tweet_id"],
            )

        return len(tweets)


class PromptsPanel(Static):
    """Panel de rendimiento por prompt."""

    def compose(self) -> ComposeResult:
        yield DataTable(id="prompts-table")

    def on_mount(self) -> None:
        table = self.query_one("#prompts-table", DataTable)
        table.add_columns("Prompt", "Tweets", "Avg Eng", "Avg Likes", "Avg RTs", "Avg Replies", "Max Eng")
        table.cursor_type = "row"
        table.zebra_stripes = True
        self.actualizar()

    def actualizar(self) -> None:
        table = self.query_one("#prompts-table", DataTable)
        table.clear()

        stats = obtener_estadisticas_por_prompt()
        if not stats:
            table.add_row("—", "0", "—", "—", "—", "—", "—")
            return

        for stat in stats:
            nombre = (stat["prompt_file"] or "N/A").split("/")[-1]
            table.add_row(
                nombre,
                str(stat["total_tweets"]),
                formatear_numero(stat["avg_engagement"]),
                formatear_numero(stat["avg_likes"]),
                formatear_numero(stat["avg_retweets"]),
                formatear_numero(stat["avg_replies"]),
                formatear_numero(stat["max_engagement"]),
                key=nombre,
            )


class EstilosPanel(Static):
    """Panel de rendimiento por estilo de gancho."""

    def compose(self) -> ComposeResult:
        yield DataTable(id="estilos-table")

    def on_mount(self) -> None:
        table = self.query_one("#estilos-table", DataTable)
        table.add_columns("Estilo", "Tweets", "Avg Eng", "Avg Likes", "Avg RTs", "Max Eng")
        table.cursor_type = "row"
        table.zebra_stripes = True
        self.actualizar()

    def actualizar(self) -> None:
        table = self.query_one("#estilos-table", DataTable)
        table.clear()

        stats = obtener_estadisticas_por_estilo()
        if not stats:
            table.add_row("Sin estilos registrados", "0", "—", "—", "—", "—")
            return

        for stat in stats:
            estilo = truncar(stat["template_estilo"] or "N/A", 55)
            table.add_row(
                estilo,
                str(stat["total_tweets"]),
                formatear_numero(stat["avg_engagement"]),
                formatear_numero(stat["avg_likes"]),
                formatear_numero(stat["avg_retweets"]),
                formatear_numero(stat["max_engagement"]),
                key=estilo,
            )


class HistorialPanel(Static):
    """Panel de historial de un tweet específico con sparkline de tendencia."""

    def __init__(self) -> None:
        super().__init__()
        self._tweet_id: str | None = None
        self._columns_ready = False

    def compose(self) -> ComposeResult:
        yield Label(
            "Selecciona un tweet en la pestaña Tweets y pulsa Enter (o h)",
            id="historial-label",
        )
        yield Static(id="historial-spark-label")
        yield Sparkline(id="historial-spark", min_color="#1a4d2e", max_color="#4ade80")
        yield DataTable(id="historial-table")

    def on_mount(self) -> None:
        table = self.query_one("#historial-table", DataTable)
        if not self._columns_ready:
            table.add_columns(
                "Fecha", "❤️ Likes", "Δ", "🔁 RTs", "Δ", "💬 Replies", "Δ", "👁 Impr.", "🔖 Saves"
            )
            table.zebra_stripes = True
            self._columns_ready = True
        self.query_one("#historial-spark", Sparkline).display = False
        self.query_one("#historial-spark-label").update("")

    def mostrar_historial(self, tweet_id: str) -> None:
        self._tweet_id = tweet_id
        tweet = obtener_tweet(tweet_id)
        titulo = Text()
        titulo.append("Historial · ", style="bold")
        titulo.append(tweet_id, style="cyan")
        if tweet:
            titulo.append(f"  [{tweet.get('source', '?')}]", style=fuente_style(tweet.get("source")))
            titulo.append(f"  score {formatear_numero(tweet.get('engagement_score', 0))}", style="green")
        self.query_one("#historial-label").update(titulo)

        table = self.query_one("#historial-table", DataTable)
        table.clear()

        historial = obtener_historial_tweet(tweet_id)
        if not historial:
            table.add_row("Sin snapshots", "—", "—", "—", "—", "—", "—", "—", "—")
            spark = self.query_one("#historial-spark", Sparkline)
            spark.display = False
            self.query_one("#historial-spark-label").update(
                Text("  Aún no hay colectas de métricas para este tweet.", style="dim yellow")
            )
            return

        prev = None
        likes_series: list[float] = []
        for snap in historial:
            likes = snap.get("likes", 0) or 0
            rts = snap.get("retweets", 0) or 0
            replies = snap.get("replies", 0) or 0
            likes_series.append(float(likes))
            fecha = (snap.get("collected_at") or "")[:16] or "N/A"
            table.add_row(
                fecha,
                str(likes),
                delta_str(likes, prev["likes"] if prev else None),
                str(rts),
                delta_str(rts, prev["retweets"] if prev else None),
                str(replies),
                delta_str(replies, prev["replies"] if prev else None),
                str(snap.get("impressions", 0) or 0),
                str(snap.get("bookmarks", 0) or 0),
            )
            prev = snap

        spark = self.query_one("#historial-spark", Sparkline)
        spark.display = True
        spark.data = likes_series
        self.query_one("#historial-spark-label").update(
            Text(f"  Tendencia de likes ({len(likes_series)} snapshots)", style="dim")
        )


# ── Screens ───────────────────────────────────────────────────

class HelpScreen(ModalScreen[None]):
    """Overlay de ayuda con atajos de teclado."""

    BINDINGS = [
        Binding("escape", "dismiss_help", "Cerrar"),
        Binding("q", "dismiss_help", "Cerrar"),
        Binding("question_mark", "dismiss_help", "Cerrar"),
    ]

    def compose(self) -> ComposeResult:
        help_text = Text()
        help_text.append("\n  Atajos de teclado\n\n", style="bold cyan")
        filas = [
            ("q", "Salir"),
            ("r", "Refrescar datos"),
            ("1 / 2 / 3", "Ordenar por fecha / likes / score"),
            ("f", "Ciclar filtro de fuente"),
            ("Enter", "Detalle del tweet seleccionado"),
            ("h", "Ver historial del tweet seleccionado"),
            ("Tab / ← →", "Cambiar pestaña"),
            ("?", "Mostrar / ocultar esta ayuda"),
            ("Esc", "Cerrar modal o detalle"),
        ]
        for tecla, desc in filas:
            help_text.append(f"  {tecla:<14}", style="bold yellow")
            help_text.append(f"{desc}\n", style="white")
        help_text.append("\n  Auto-refresh cada ", style="dim")
        help_text.append(f"{AUTO_REFRESH_SECS}s\n", style="dim cyan")

        with Vertical(id="help-dialog"):
            yield Static(help_text, id="help-body")
            yield Label("Esc para cerrar", classes="help-hint")

    def action_dismiss_help(self) -> None:
        self.dismiss()


class DetalleTweetScreen(Screen):
    """Pantalla de detalle de un tweet con historial y sparkline."""

    BINDINGS = [
        Binding("escape", "volver", "Volver"),
        Binding("q", "volver", "Volver"),
        Binding("h", "ir_historial", "Historial"),
    ]

    def __init__(self, tweet_id: str) -> None:
        super().__init__()
        self.tweet_id = tweet_id

    def compose(self) -> ComposeResult:
        yield Header()
        with VerticalScroll(id="detalle-container"):
            yield Label(f"Tweet {self.tweet_id}", id="detalle-titulo")
            yield Static(id="detalle-texto")
            yield Rule()
            yield Label("Evolución de likes", classes="section-title")
            yield Sparkline(id="detalle-spark", min_color="#1e3a5f", max_color="#60a5fa")
            yield Label("Historial de métricas", classes="section-title")
            yield DataTable(id="detalle-historial")
            yield Label("Esc / q volver  ·  h historial en pestaña", classes="help-hint")
        yield Footer()

    def on_mount(self) -> None:
        tweet = obtener_tweet(self.tweet_id)

        texto = Text()
        if not tweet:
            texto.append("  Tweet no encontrado en la base de datos.\n", style="red")
            self.query_one("#detalle-texto").update(texto)
            return

        source = tweet.get("source", "N/A")
        texto.append("  Fuente:     ", style="bold")
        texto.append(f"{source}\n", style=fuente_style(source))
        texto.append("  Publicado:  ", style="bold")
        texto.append(f"{(tweet.get('published_at') or 'N/A')[:19]}\n", style="dim")
        texto.append("  Prompt:     ", style="bold")
        texto.append(f"{tweet.get('prompt_file') or 'N/A'}\n", style="dim")
        if tweet.get("template_estilo"):
            texto.append("  Estilo:     ", style="bold")
            texto.append(f"{tweet['template_estilo']}\n", style="dim")
        if tweet.get("item_id"):
            texto.append("  Item:       ", style="bold")
            texto.append(f"{tweet['item_id']}\n", style="dim")
        texto.append("\n  📝 Texto\n", style="bold yellow")
        texto.append(f"  {tweet.get('texto', '')}\n", style="white")
        texto.append("\n  ")
        texto.append(f"❤️ {tweet.get('likes_latest', 0) or 0}  ", style="red")
        texto.append(f"🔁 {tweet.get('retweets_latest', 0) or 0}  ", style="green")
        texto.append(f"💬 {tweet.get('replies_latest', 0) or 0}  ", style="yellow")
        texto.append(f"🔖 {tweet.get('bookmarks_latest', 0) or 0}  ", style="blue")
        texto.append(f"👁 {tweet.get('impressions_latest', 0) or 0}  ", style="magenta")
        texto.append(
            f"📊 {formatear_numero(tweet.get('engagement_score', 0) or 0)}",
            style="bold cyan",
        )
        if tweet.get("last_collected_at"):
            texto.append(f"\n\n  Última colecta: {tweet['last_collected_at'][:19]}", style="dim")

        self.query_one("#detalle-texto").update(texto)

        table = self.query_one("#detalle-historial", DataTable)
        table.add_columns("Fecha", "❤️", "Δ", "🔁", "Δ", "💬", "Δ", "👁", "🔖")
        table.zebra_stripes = True

        historial = obtener_historial_tweet(self.tweet_id)
        spark = self.query_one("#detalle-spark", Sparkline)

        if not historial:
            table.add_row("Sin datos", "—", "—", "—", "—", "—", "—", "—", "—")
            spark.display = False
            return

        prev = None
        likes_series: list[float] = []
        for snap in historial:
            likes = snap.get("likes", 0) or 0
            rts = snap.get("retweets", 0) or 0
            replies = snap.get("replies", 0) or 0
            likes_series.append(float(likes))
            fecha = (snap.get("collected_at") or "")[:16] or "N/A"
            table.add_row(
                fecha,
                str(likes),
                delta_str(likes, prev["likes"] if prev else None),
                str(rts),
                delta_str(rts, prev["retweets"] if prev else None),
                str(replies),
                delta_str(replies, prev["replies"] if prev else None),
                str(snap.get("impressions", 0) or 0),
                str(snap.get("bookmarks", 0) or 0),
            )
            prev = snap

        spark.data = likes_series

    def action_volver(self) -> None:
        self.app.pop_screen()

    def action_ir_historial(self) -> None:
        app = self.app
        if isinstance(app, DashboardApp):
            app.mostrar_historial_tweet(self.tweet_id)
        self.app.pop_screen()


# ── App principal ─────────────────────────────────────────────

class DashboardApp(App):
    """Aplicación principal del dashboard TUI."""

    CSS = """
    Screen {
        background: $surface;
    }

    StatusBar {
        dock: bottom;
        height: 1;
        background: $boost;
        color: $text;
    }

    #status-bar {
        dock: bottom;
        height: 1;
        background: #1e293b;
        color: #e2e8f0;
        padding: 0 1;
    }

    DataTable {
        height: 1fr;
    }

    .section-title {
        text-style: bold;
        color: $accent;
        padding: 1 1 0 1;
        height: 2;
    }

    .help-hint {
        color: $text-muted;
        text-align: center;
        padding: 1;
        height: 3;
    }

    #detalle-container {
        padding: 1 2;
    }

    #detalle-titulo {
        height: 3;
        content-align: center middle;
        background: $accent;
        color: $text;
        text-style: bold;
    }

    #detalle-texto {
        height: auto;
        padding: 1;
        margin-bottom: 1;
    }

    #detalle-spark, #historial-spark {
        height: 5;
        margin: 0 1 1 1;
    }

    #historial-label {
        padding: 1;
        height: auto;
    }

    #historial-spark-label {
        padding: 0 1;
        height: auto;
    }

    #help-dialog {
        width: 60;
        height: auto;
        max-height: 80%;
        border: heavy $accent;
        background: $surface;
        padding: 1 2;
        align: center middle;
    }

    HelpScreen {
        align: center middle;
        background: rgba(0, 0, 0, 0.55);
    }

    #help-body {
        height: auto;
        width: 100%;
    }

    #resumen-stats, #resumen-top {
        height: auto;
        padding: 0 1;
    }

    TabbedContent {
        height: 1fr;
    }
    """

    BINDINGS = [
        Binding("q", "quit", "Salir"),
        Binding("r", "refrescar", "Refrescar"),
        Binding("1", "ordenar_fecha", "Fecha"),
        Binding("2", "ordenar_likes", "Likes"),
        Binding("3", "ordenar_score", "Score"),
        Binding("f", "filtrar", "Filtro"),
        Binding("h", "historial_seleccionado", "Historial"),
        Binding("question_mark", "ayuda", "Ayuda"),
    ]

    TITLE = "Trending2Tweet · Analytics"
    SUB_TITLE = "dashboard de métricas"

    def __init__(self) -> None:
        super().__init__()
        self.filtro_fuente: Optional[str] = None
        self.orden_actual: str = "engagement_score"
        self.last_refresh: datetime | None = None
        self._selected_tweet_id: str | None = None
        self._total_visible: int = 0

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)
        with TabbedContent(initial="tab-tweets"):
            with TabPane("Resumen", id="tab-resumen"):
                yield ResumenPanel()
            with TabPane("Tweets", id="tab-tweets"):
                yield TweetsPanel()
            with TabPane("Prompts", id="tab-prompts"):
                yield PromptsPanel()
            with TabPane("Estilos", id="tab-estilos"):
                yield EstilosPanel()
            with TabPane("Historial", id="tab-historial"):
                yield HistorialPanel()
        yield StatusBar(id="status-bar")
        yield Footer()

    def on_mount(self) -> None:
        init_db()
        self.set_interval(AUTO_REFRESH_SECS, self._auto_refrescar)
        # Sincronizar contadores tras el mount de los paneles hijos
        try:
            self._total_visible = self.query_one(TweetsPanel).actualizar(
                orden=self.orden_actual, filtro=self.filtro_fuente
            )
            self.last_refresh = datetime.now()
        except NoMatches:
            pass
        self._actualizar_status()
        self.notify(
            f"Auto-refresh cada {AUTO_REFRESH_SECS}s · pulsa ? para ayuda",
            severity="information",
            timeout=4,
        )

    def _auto_refrescar(self) -> None:
        """Refresh silencioso del timer (sin toast)."""
        self._refrescar_paneles(notificar=False)

    def on_data_table_row_highlighted(self, event: DataTable.RowHighlighted) -> None:
        """Guarda el tweet resaltado para atajos h / Enter."""
        if event.data_table.id == "tweets-table" and event.row_key is not None:
            self._selected_tweet_id = str(event.row_key.value)

    def on_data_table_row_selected(self, event: DataTable.RowSelected) -> None:
        """Enter sobre un tweet abre el detalle."""
        if event.data_table.id == "tweets-table":
            tweet_id = event.row_key.value if event.row_key else None
            if tweet_id:
                self._selected_tweet_id = str(tweet_id)
                self.push_screen(DetalleTweetScreen(str(tweet_id)))

    def _actualizar_status(self) -> None:
        try:
            bar = self.query_one("#status-bar", StatusBar)
            bar.actualizar(
                orden=self.orden_actual,
                filtro=self.filtro_fuente,
                total=self._total_visible,
                last_refresh=self.last_refresh,
            )
        except NoMatches:
            pass

        filtro_texto = self.filtro_fuente or "todas"
        self.sub_title = (
            f"{ORDENES.get(self.orden_actual, self.orden_actual)} · "
            f"fuente: {filtro_texto} · {self._total_visible} tweets"
        )

    def action_refrescar(self) -> None:
        """Refresca todos los paneles (manual, con toast)."""
        self._refrescar_paneles(notificar=True)

    def _refrescar_paneles(self, notificar: bool = True) -> None:
        """Recarga datos de todos los paneles visibles."""
        try:
            self.query_one(ResumenPanel).actualizar()
            self._total_visible = self.query_one(TweetsPanel).actualizar(
                orden=self.orden_actual, filtro=self.filtro_fuente
            )
            self.query_one(PromptsPanel).actualizar()
            self.query_one(EstilosPanel).actualizar()
            if self._selected_tweet_id:
                self.query_one(HistorialPanel).mostrar_historial(self._selected_tweet_id)
            self.last_refresh = datetime.now()
            self._actualizar_status()
            if notificar:
                self.notify("Datos actualizados", severity="information", timeout=2)
        except NoMatches:
            pass

    def action_ordenar_fecha(self) -> None:
        self._aplicar_orden("published_at")

    def action_ordenar_likes(self) -> None:
        self._aplicar_orden("likes_latest")

    def action_ordenar_score(self) -> None:
        self._aplicar_orden("engagement_score")

    def _aplicar_orden(self, orden: str) -> None:
        self.orden_actual = orden
        try:
            self._total_visible = self.query_one(TweetsPanel).actualizar(
                orden=orden, filtro=self.filtro_fuente
            )
            self._actualizar_status()
            self.notify(f"Orden: {ORDENES.get(orden, orden)}", timeout=2)
        except NoMatches:
            pass

    def action_filtrar(self) -> None:
        """Cicla el filtro de fuente."""
        try:
            idx = FUENTES.index(self.filtro_fuente)
        except ValueError:
            idx = 0
        self.filtro_fuente = FUENTES[(idx + 1) % len(FUENTES)]

        try:
            self._total_visible = self.query_one(TweetsPanel).actualizar(
                orden=self.orden_actual, filtro=self.filtro_fuente
            )
            self._actualizar_status()
            self.notify(f"Filtro: {self.filtro_fuente or 'todas'}", timeout=2)
        except NoMatches:
            pass

    def action_historial_seleccionado(self) -> None:
        """Muestra el historial del tweet resaltado en la pestaña Historial."""
        if not self._selected_tweet_id:
            self.notify("Selecciona un tweet en la pestaña Tweets", severity="warning")
            return
        self.mostrar_historial_tweet(self._selected_tweet_id)

    def mostrar_historial_tweet(self, tweet_id: str) -> None:
        """Carga historial y salta a la pestaña Historial."""
        self._selected_tweet_id = tweet_id
        try:
            self.query_one(HistorialPanel).mostrar_historial(tweet_id)
            tabs = self.query_one(TabbedContent)
            tabs.active = "tab-historial"
        except NoMatches:
            pass

    def action_ayuda(self) -> None:
        self.push_screen(HelpScreen())


def main() -> None:
    """Punto de entrada principal."""
    init_db()
    app = DashboardApp()
    app.run()


if __name__ == "__main__":
    main()
