"""Métricas de desempenho, curvas de ganho, bootstrap e medidas de efeito."""

import numpy as np
import pandas as pd
from scipy.stats import chi2_contingency, rankdata
from sklearn.metrics import (
    average_precision_score,
    brier_score_loss,
    log_loss,
    roc_auc_score,
)


def auc_rapida(y, s) -> float:
    """ROC-AUC pela estatística de Mann-Whitney (equivale a ``roc_auc_score``)."""
    y = np.asarray(y).astype(bool)
    r = rankdata(s)
    n1 = y.sum()
    n0 = len(y) - n1
    return (r[y].sum() - n1 * (n1 + 1) / 2) / (n1 * n0)


def _ordem(s):
    return np.argsort(-np.asarray(s), kind="stable")


def lift(y, s, frac: float = 0.1) -> float:
    """Taxa de churn entre os `frac` de maior score ÷ taxa de churn geral."""
    y = np.asarray(y)
    k = max(1, int(round(frac * len(y))))
    return y[_ordem(s)[:k]].mean() / y.mean()


def captura(y, s, frac: float = 0.2) -> float:
    """Fração de todos os churners que está entre os `frac` de maior score."""
    y = np.asarray(y)
    k = max(1, int(round(frac * len(y))))
    return y[_ordem(s)[:k]].sum() / y.sum()


def metricas(y, s, probabilidade: bool = True) -> dict:
    """Métricas de ordenação (AUC, PR-AUC, lift) e, se aplicável, de calibração."""
    out = {
        "auc": roc_auc_score(y, s),
        "pr_auc": average_precision_score(y, s),
        "lift_10": lift(y, s, 0.1),
        "captura_20": captura(y, s, 0.2),
    }
    if probabilidade:
        out["brier"] = brier_score_loss(y, s)
        out["log_loss"] = log_loss(y, np.clip(s, 1e-6, 1 - 1e-6))
    return out


def curva_ganhos(y, s, pontos: int = 201):
    """(fração contatada, fração dos churners capturada), ordenando pelo score."""
    y = np.asarray(y)[_ordem(s)]
    capt = np.concatenate([[0], np.cumsum(y) / y.sum()])
    frac = np.arange(len(y) + 1) / len(y)
    idx = np.linspace(0, len(y), pontos).astype(int)
    return frac[idx], capt[idx]


def bootstrap_auc(y, scores: dict, referencia: str | None = None, n_boot: int = 1000, seed: int = 42):
    """IC 95% (percentil) do AUC de cada modelo, com reamostragem pareada.

    Se `referencia` for dada, também estima a diferença de AUC de cada modelo
    para ela e a fração de réplicas em que a diferença tem sinal oposto
    (p-valor bilateral aproximado).
    """
    rng = np.random.default_rng(seed)
    y = np.asarray(y)
    nomes = list(scores)
    S = {k: np.asarray(v) for k, v in scores.items()}
    boot = np.empty((n_boot, len(nomes)))
    for i in range(n_boot):
        idx = rng.integers(0, len(y), len(y))
        for j, k in enumerate(nomes):
            boot[i, j] = auc_rapida(y[idx], S[k][idx])
    pontual = np.array([auc_rapida(y, S[k]) for k in nomes])
    tab = pd.DataFrame(
        {
            "auc": pontual,
            "ic95_inf": np.percentile(boot, 2.5, axis=0),
            "ic95_sup": np.percentile(boot, 97.5, axis=0),
        },
        index=pd.Index(nomes, name="modelo"),
    )
    if referencia is not None:
        j_ref = nomes.index(referencia)
        dif = boot - boot[:, [j_ref]]
        tab["dif_ref"] = pontual - pontual[j_ref]
        tab["dif_ic95_inf"] = np.percentile(dif, 2.5, axis=0)
        tab["dif_ic95_sup"] = np.percentile(dif, 97.5, axis=0)
        sinal = np.sign(tab["dif_ref"].to_numpy())
        tab["p_valor"] = np.minimum(1, 2 * np.mean(dif * sinal <= 0, axis=0))
        tab.loc[referencia, ["dif_ref", "dif_ic95_inf", "dif_ic95_sup", "p_valor"]] = np.nan
    return tab


def tabela_decis(y, s, valor=None) -> pd.DataFrame:
    """Resumo por decil de risco (1 = maior risco): churn, lift e valor."""
    df = pd.DataFrame({"y": np.asarray(y), "s": np.asarray(s)})
    df["valor"] = np.asarray(valor) if valor is not None else 0.0
    df["decil"] = pd.qcut(rankdata(-df["s"], method="ordinal"), 10, labels=range(1, 11))
    tab = df.groupby("decil", observed=True).agg(
        clientes=("y", "size"),
        score_medio=("s", "mean"),
        taxa_churn=("y", "mean"),
        churners=("y", "sum"),
        valor=("valor", "sum"),
    )
    tab["lift"] = tab["taxa_churn"] / df["y"].mean()
    tab["captura_acum"] = tab["churners"].cumsum() / df["y"].sum()
    tab["valor_share"] = tab["valor"] / df["valor"].sum() if valor is not None else np.nan
    return tab


def taxa_por_grupo(y, grupos) -> pd.DataFrame:
    """Taxa de churn por grupo, com intervalo de confiança de Wilson (95%)."""
    from statsmodels.stats.proportion import proportion_confint

    df = pd.DataFrame({"y": np.asarray(y), "g": pd.Series(grupos).reset_index(drop=True)})
    tab = df.groupby("g", observed=True)["y"].agg(n="size", churners="sum")
    tab["taxa"] = tab["churners"] / tab["n"]
    inf, sup = proportion_confint(tab["churners"], tab["n"], method="wilson")
    tab["ic95_inf"], tab["ic95_sup"] = inf, sup
    return tab


def auc_univariada(y, x) -> float:
    """AUC de um único atributo como score (0,5 = sem poder discriminante).

    Valores abaixo de 0,5 indicam que o atributo está associado a *menos*
    churn; ``|AUC - 0,5|`` mede o tamanho do efeito.
    """
    y, x = np.asarray(y), np.asarray(x, dtype=float)
    ok = ~np.isnan(x)
    return auc_rapida(y[ok], x[ok])


def cramer_v(tabela: pd.DataFrame) -> tuple[float, float]:
    """(V de Cramér, p-valor do qui-quadrado) para uma tabela de contingência."""
    chi2, p, _, _ = chi2_contingency(tabela)
    n = np.asarray(tabela).sum()
    k = min(tabela.shape) - 1
    return float(np.sqrt(chi2 / (n * k))), float(p)
