"""Engenharia de atributos: snapshots (cliente x data de corte) e rótulo de churn.

Para cada data de corte ``t0``:

* **base ativa**: clientes com ao menos uma visita em ``[t0 - tau, t0)``;
* **atributos de janela**: calculados só com visitas em ``[t0 - lookback, t0)``,
  com o mesmo significado em qualquer data de corte;
* **atributos de histórico**: visitas desde o início da base até ``t0``;
* **rótulo** ``churn = 1``: nenhuma visita em ``[t0, t0 + tau)``.

Nenhum atributo usa informação posterior ao corte (sem vazamento).
"""

import numpy as np
import pandas as pd

from . import config

CATEGORIAS = {
    "Bacalhau & Pescados": "share_bacalhau",
    "Castanhas & Oleaginosas": "share_castanhas",
    "Temperos & Condimentos": "share_temperos",
    "Frutas": "share_frutas",
    "Mixes da Casa": "share_mixes",
    "Grãos": "share_graos",
    "Superalimentos & Energéticos": "share_superalimentos",
    "Matinais": "share_matinais",
    "Aperitivos": "share_aperitivos",
    "Conservas": "share_conservas",
    "Lanchonete": "share_lanchonete",
    "Azeites & Vinagres": "share_azeites",
    "Ervas & Chás": "share_ervas",
}

# (bloco, descrição, hipótese associada)
DICIONARIO = {
    "recencia": ("Recência", "Dias desde a última visita até a data de corte", "H3"),
    "atraso_relativo": ("Ritmo", "Recência ÷ intervalo médio entre visitas (≥ 2 visitas)", "H3"),
    "n_visitas": ("Frequência", "Visitas (dias com compra) na janela de observação", "H4"),
    "visitas_0_30": ("Frequência", "Visitas entre 1 e 30 dias antes do corte", "H6"),
    "visitas_30_60": ("Frequência", "Visitas entre 31 e 60 dias antes do corte", "H6"),
    "visitas_60_90": ("Frequência", "Visitas entre 61 e 90 dias antes do corte", "H6"),
    "visitas_90_120": ("Frequência", "Visitas entre 91 e 120 dias antes do corte", "H6"),
    "dias_desde_primeira": ("Frequência", "Dias desde a primeira visita na janela (antiguidade observada)", "H4"),
    "ipt_medio": ("Ritmo", "Intervalo médio entre visitas consecutivas, em dias (≥ 2 visitas)", "H3"),
    "ipt_ultimo": ("Ritmo", "Intervalo entre as duas últimas visitas, em dias (≥ 2 visitas)", "H6"),
    "ipt_cv": ("Regularidade", "Coeficiente de variação dos intervalos (≥ 3 visitas)", "H5"),
    "tend_visitas": ("Tendência", "Visitas nos 60 dias recentes − visitas nos 60 dias anteriores", "H6"),
    "tend_gasto": ("Tendência", "(Gasto recente − gasto anterior) ÷ gasto total, em [−1, 1]", "H6"),
    "gasto_total": ("Valor", "Faturamento do cliente na janela (R$)", "H9"),
    "ticket_medio": ("Valor", "Gasto médio por visita (R$)", "H9"),
    "itens_por_visita": ("Cesta", "SKUs distintos por visita (média)", "H7"),
    "n_skus": ("Cesta", "SKUs distintos comprados na janela", "H7"),
    "n_categorias": ("Amplitude", "Categorias distintas compradas na janela", "H7"),
    "entropia_categorias": ("Amplitude", "Entropia de Shannon da divisão do gasto entre categorias", "H7"),
    "share_desconto": ("Preço", "Fração de itens pagos ≥ 5% abaixo da mediana do SKU no mês", "controle"),
    "share_shopping": ("Loja", "Fração de visitas na loja de shopping", "controle"),
    "multiloja": ("Loja", "Visitou as duas lojas na janela (0/1)", "controle"),
    "share_fds": ("Hábito", "Fração de visitas em sábados e domingos", "controle"),
    "hist_visitas": ("Histórico", "Visitas desde a primeira visita observada na base", "H4"),
    "hist_dias": ("Histórico", "Dias desde a primeira visita observada (limite inferior da antiguidade)", "H4"),
    "hist_taxa": ("Histórico", "Visitas por 30 dias desde a primeira visita observada", "H4"),
}
for _cat, _nome in CATEGORIAS.items():
    DICIONARIO[_nome] = (
        "Mix" if _nome != "share_bacalhau" else "Sazonalidade",
        f"Participação de '{_cat}' no gasto da janela",
        "H8" if _nome == "share_bacalhau" else "controle",
    )

ATRIBUTOS = list(DICIONARIO)
ATRIBUTOS_HISTORICO = ["hist_visitas", "hist_dias", "hist_taxa"]
ATRIBUTOS_JANELA = [a for a in ATRIBUTOS if a not in ATRIBUTOS_HISTORICO]


def construir_snapshot(
    itens: pd.DataFrame,
    visitas: pd.DataFrame,
    corte,
    tau: int = config.TAU,
    lookback: int = config.LOOKBACK,
    rotular: bool = True,
) -> pd.DataFrame:
    """Atributos (e rótulo) de todos os clientes ativos em uma data de corte."""
    corte = pd.Timestamp(corte)
    inicio = corte - pd.Timedelta(days=lookback)
    if inicio < config.INICIO:
        raise ValueError(f"Corte {corte.date()} não tem {lookback} dias de histórico.")
    if lookback % 30 or tau > lookback:
        raise ValueError("lookback deve ser múltiplo de 30 e maior ou igual a tau.")

    vis = visitas[(visitas["DATA_ATEND"] >= inicio) & (visitas["DATA_ATEND"] < corte)]
    ultima = vis.groupby("CLI_CPF")["DATA_ATEND"].max()
    ativos = ultima.index[ultima >= corte - pd.Timedelta(days=tau)].sort_values()
    vis = vis[vis["CLI_CPF"].isin(ativos)].sort_values(["CLI_CPF", "DATA_ATEND"]).copy()
    vis["DIAS_ATRAS"] = (corte - vis["DATA_ATEND"]).dt.days  # 1 .. lookback
    vis["GAP"] = vis.groupby("CLI_CPF")["DATA_ATEND"].diff().dt.days
    g = vis.groupby("CLI_CPF")

    X = pd.DataFrame(index=pd.Index(ativos, name="CLI_CPF"))
    X["recencia"] = g["DIAS_ATRAS"].min()
    X["n_visitas"] = g.size()

    faixas = np.arange(0, lookback + 1, 30)
    rotulos = [f"visitas_{a}_{b}" for a, b in zip(faixas[:-1], faixas[1:])]
    faixa = pd.cut(vis["DIAS_ATRAS"], bins=faixas, labels=rotulos)
    contagem = vis.groupby(["CLI_CPF", faixa], observed=False).size().unstack(fill_value=0)
    X = X.join(contagem[rotulos])
    X["dias_desde_primeira"] = g["DIAS_ATRAS"].max()

    gaps = vis.dropna(subset=["GAP"]).groupby("CLI_CPF")["GAP"]
    X["ipt_medio"] = gaps.mean()
    X["ipt_ultimo"] = gaps.last()
    X["ipt_cv"] = gaps.std() / gaps.mean()  # indefinido com menos de 2 intervalos
    X["atraso_relativo"] = X["recencia"] / X["ipt_medio"]

    recente = vis["DIAS_ATRAS"] <= lookback / 2
    n_rec = vis[recente].groupby("CLI_CPF").size().reindex(X.index, fill_value=0)
    n_ant = vis[~recente].groupby("CLI_CPF").size().reindex(X.index, fill_value=0)
    X["tend_visitas"] = n_rec - n_ant
    X["gasto_total"] = g["FATUR"].sum()
    g_rec = vis[recente].groupby("CLI_CPF")["FATUR"].sum().reindex(X.index, fill_value=0)
    X["tend_gasto"] = (2 * g_rec - X["gasto_total"]) / X["gasto_total"]
    X["ticket_medio"] = g["FATUR"].mean()
    X["itens_por_visita"] = g["N_SKUS"].mean()
    X["share_shopping"] = g["SHOPPING"].mean()
    X["multiloja"] = ((g["SHOPPING"].max() > 0) & (g["SHOPPING"].min() < 1)).astype("int8")
    X["share_fds"] = g["FDS"].mean()

    it = itens[
        (itens["DATA_ATEND"] >= inicio)
        & (itens["DATA_ATEND"] < corte)
        & itens["CLI_CPF"].isin(ativos)
    ]
    gi = it.groupby("CLI_CPF")
    X["n_skus"] = gi["SKU"].nunique()
    X["n_categorias"] = gi["CATEGORIA"].nunique()
    X["share_desconto"] = gi["DESCONTO"].mean()
    gasto_cat = it.pivot_table(
        index="CLI_CPF", columns="CATEGORIA", values="FATUR_VENDA",
        aggfunc="sum", fill_value=0, observed=False,
    ).reindex(columns=list(CATEGORIAS), fill_value=0)
    p = gasto_cat.div(gasto_cat.sum(axis=1), axis=0)
    X["entropia_categorias"] = -(p * np.log(p.where(p > 0, 1))).sum(axis=1)
    X = X.join(p.rename(columns=CATEGORIAS))

    # Histórico acumulado desde o início da base. A base começa em 02/01/2024,
    # então a antiguidade é truncada à esquerda (limite inferior da real).
    hist = visitas[(visitas["DATA_ATEND"] < corte) & visitas["CLI_CPF"].isin(ativos)]
    gh = hist.groupby("CLI_CPF")
    X["hist_visitas"] = gh.size()
    X["hist_dias"] = (corte - gh["DATA_ATEND"].min()).dt.days
    X["hist_taxa"] = X["hist_visitas"] / X["hist_dias"] * 30

    X = X[ATRIBUTOS]
    if rotular:
        fim = corte + pd.Timedelta(days=tau)
        if fim - pd.Timedelta(days=1) > config.FIM:
            raise ValueError(f"Rótulo do corte {corte.date()} exige dados após {config.FIM.date()}.")
        futuros = visitas.loc[
            (visitas["DATA_ATEND"] >= corte) & (visitas["DATA_ATEND"] < fim), "CLI_CPF"
        ].unique()
        X["churn"] = (~X.index.isin(futuros)).astype("int8")
    X.insert(0, "corte", corte)
    return X.reset_index()


def construir_snapshots(itens, visitas, cortes=config.CORTES, **kwargs) -> pd.DataFrame:
    """Empilha os snapshots de várias datas de corte (multi-slicing)."""
    return pd.concat(
        [construir_snapshot(itens, visitas, c, **kwargs) for c in cortes], ignore_index=True
    )


def segmento(n_visitas: pd.Series) -> pd.Series:
    """Estágio do relacionamento na janela: visita única x recorrente."""
    return pd.Series(
        np.where(n_visitas <= 1, "1 visita", np.where(n_visitas == 2, "2 visitas", "3+ visitas")),
        index=n_visitas.index,
    )


def dicionario_atributos() -> pd.DataFrame:
    """Tabela (atributo, bloco, descrição, hipótese) para documentação."""
    return pd.DataFrame(
        [(nome, *info) for nome, info in DICIONARIO.items()],
        columns=["atributo", "bloco", "descricao", "hipotese"],
    )
