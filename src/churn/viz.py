"""Identidade visual dos gráficos: paleta validada, tipografia e marcas discretas.

Paleta categórica em ordem fixa (segura para daltonismo nos pares adjacentes);
gráficos com mais de três séries usam ênfase (uma série em cor, contexto em
cinza) ou pequenos múltiplos. Sequencial = um único matiz (azul); divergente =
azul <-> vermelho com ponto médio cinza.
"""

import locale
import logging

import matplotlib as mpl
import pandas as pd
from cycler import cycler
from matplotlib.colors import LinearSegmentedColormap
from matplotlib.ticker import FuncFormatter

from . import config

SUPERFICIE = "#fcfcfb"
TINTA = "#0b0b0b"
TINTA_2 = "#52514e"
TINTA_SUAVE = "#898781"
GRADE = "#e1e0d9"
EIXO = "#c3c2b7"
CONTEXTO = "#c3c2b7"  # cinza de desênfase

CATEGORICA = ["#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#e87ba4", "#008300", "#6250d6", "#e34948"]
AZUL, LARANJA, VERDE, AMARELO, MAGENTA, VERDE_ESCURO, VIOLETA, VERMELHO = CATEGORICA

SEQ_AZUL = [
    "#cde2fb", "#b7d3f6", "#9ec5f4", "#86b6ef", "#6da7ec", "#5598e7", "#3987e5",
    "#2a78d6", "#256abf", "#1c5cab", "#184f95", "#104281", "#0d366b",
]
CMAP_SEQ = LinearSegmentedColormap.from_list("lumaro_seq", [SUPERFICIE] + SEQ_AZUL)
CMAP_DIV = LinearSegmentedColormap.from_list(
    "lumaro_div", ["#184f95", "#5598e7", "#f0efec", "#ec8a87", "#c23b3a"]
)


def _num(x: float, casas: int = 0) -> str:
    """Número no padrão brasileiro (milhar com ponto, decimal com vírgula)."""
    s = f"{x:,.{casas}f}"
    return s.replace(",", "§").replace(".", ",").replace("§", ".")


def fmt_num(x, casas=0):
    return _num(x, casas)


def fmt_pct(x, casas=0):
    return f"{_num(100 * x, casas)}%"


def fmt_brl(x, casas=0):
    if abs(x) >= 1e6:
        return f"R$ {_num(x / 1e6, 1)} mi"
    if abs(x) >= 1e3:
        return f"R$ {_num(x / 1e3, 0)} mil"
    return f"R$ {_num(x, casas)}"


PCT = FuncFormatter(lambda x, _: fmt_pct(x))
BRL = FuncFormatter(lambda x, _: fmt_brl(x))
MILHAR = FuncFormatter(lambda x, _: fmt_num(x / 1e3, 0) + " mil" if abs(x) >= 1e3 else fmt_num(x))
NUM = FuncFormatter(lambda x, _: fmt_num(x, 0) if float(x).is_integer() else fmt_num(x, 1))


def aplicar_estilo() -> None:
    """Configura o matplotlib com a identidade visual do projeto."""
    logging.getLogger("matplotlib.font_manager").setLevel(logging.ERROR)
    usar_locale = False
    for nome in ("pt_BR.UTF-8", "pt_BR.utf8", "Portuguese_Brazil.1252", "pt_BR"):
        try:
            locale.setlocale(locale.LC_NUMERIC, nome)
            usar_locale = True
            break
        except locale.Error:
            continue
    if "lumaro_seq" not in mpl.colormaps:
        mpl.colormaps.register(CMAP_SEQ)
        mpl.colormaps.register(CMAP_DIV)
    mpl.rcParams.update(
        {
            "figure.facecolor": SUPERFICIE,
            "axes.facecolor": SUPERFICIE,
            "savefig.facecolor": SUPERFICIE,
            "figure.dpi": 110,
            "savefig.dpi": 200,
            "savefig.bbox": "tight",
            "figure.figsize": (8, 4.2),
            "figure.constrained_layout.use": True,
            "font.family": "sans-serif",
            "font.sans-serif": ["Segoe UI", "Helvetica Neue", "Helvetica", "Arial", "DejaVu Sans"],
            "font.size": 10,
            "text.color": TINTA,
            "axes.titlesize": 12,
            "axes.titleweight": "semibold",
            "axes.titlelocation": "left",
            "axes.titlecolor": TINTA,
            "axes.titlepad": 10,
            "axes.labelsize": 10,
            "axes.labelcolor": TINTA_2,
            "axes.edgecolor": EIXO,
            "axes.linewidth": 0.8,
            "axes.spines.top": False,
            "axes.spines.right": False,
            "axes.grid": True,
            "axes.grid.axis": "y",
            "axes.axisbelow": True,
            "axes.prop_cycle": cycler(color=CATEGORICA),
            "axes.formatter.use_locale": usar_locale,
            "grid.color": GRADE,
            "grid.linewidth": 0.8,
            "grid.linestyle": "-",
            "xtick.color": EIXO,
            "ytick.color": EIXO,
            "xtick.labelcolor": TINTA_2,
            "ytick.labelcolor": TINTA_2,
            "xtick.labelsize": 9,
            "ytick.labelsize": 9,
            "ytick.major.size": 0,
            "lines.linewidth": 2,
            "lines.solid_capstyle": "round",
            "lines.solid_joinstyle": "round",
            "lines.markersize": 6,
            "patch.force_edgecolor": True,
            "patch.edgecolor": SUPERFICIE,
            "patch.linewidth": 1.0,
            "legend.frameon": False,
            "legend.fontsize": 9,
            "legend.labelcolor": TINTA_2,
            "legend.title_fontsize": 9,
            "image.cmap": "lumaro_seq",
            "pdf.fonttype": 42,
            "svg.fonttype": "none",
        }
    )


def titulo(ax, texto: str, sub: str | None = None) -> None:
    """Título à esquerda e, opcionalmente, um subtítulo discreto logo abaixo."""
    ax.set_title(texto, loc="left", pad=22 if sub else 10)
    if sub:
        ax.text(0, 1.02, sub, transform=ax.transAxes, fontsize=9, color=TINTA_SUAVE,
                va="bottom", ha="left", gid="subtitulo")


def salvar(fig, nome: str, sem_titulo: bool = True) -> None:
    """Exporta a figura em PDF para o relatório.

    Por padrão remove títulos e subtítulos (no LaTeX eles viram a legenda da
    figura); a figura exibida no notebook não é alterada.
    """
    config.FIG_DIR.mkdir(parents=True, exist_ok=True)
    escondidos = []
    if sem_titulo:
        textos = [fig._suptitle] if fig._suptitle is not None else []
        for ax in fig.axes:
            textos += [ax.title, ax._left_title, ax._right_title]
            textos += [t for t in ax.texts if t.get_gid() == "subtitulo"]
        escondidos = [t for t in textos if t.get_text() and t.get_visible()]
        for t in escondidos:
            t.set_visible(False)
    fig.savefig(config.FIG_DIR / f"{nome}.pdf")
    for t in escondidos:
        t.set_visible(True)


def linha_ic(ax, x, tab, cor=AZUL, rotulo=None, marcador=True):
    """Taxa por grupo ordenado: linha com marcadores e faixa do IC 95%."""
    ax.plot(x, tab["taxa"], color=cor, label=rotulo, marker="o" if marcador else None,
            markeredgecolor=SUPERFICIE, markeredgewidth=1.5)
    ax.fill_between(x, tab["ic95_inf"], tab["ic95_sup"], color=cor, alpha=0.12, linewidth=0)


def fmt_tabela(x):
    """Formato pt-BR para números exibidos em tabelas do pandas."""
    if pd.isna(x):
        return ""
    return _num(x, 0) if abs(x) >= 1000 else _num(x, 3)


def rotular_fim(ax, x, y, texto, cor=TINTA_2, dx=4, **kw):
    """Rótulo direto no fim de uma linha (texto em tinta neutra, nunca na cor da série)."""
    ax.annotate(texto, (x, y), xytext=(dx, 0), textcoords="offset points",
                va="center", ha="left", color=cor, fontsize=9, **kw)
