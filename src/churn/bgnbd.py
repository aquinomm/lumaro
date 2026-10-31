"""Modelo BG/NBD (Fader, Hardie & Lee, 2005) para clientes não contratuais.

Hipóteses do modelo: enquanto ativo, o cliente compra segundo um processo de
Poisson com taxa lambda ~ Gama(r, alpha); após cada compra, abandona a loja com
probabilidade p ~ Beta(a, b). Com (x, t_x, T) de cada cliente — compras
repetidas, instante da última compra e idade, medidos desde a primeira compra —
obtêm-se P(ativo) e P(nenhuma compra nos próximos t dias) em forma fechada.
"""

import numpy as np
import pandas as pd
from scipy.optimize import minimize
from scipy.special import betaln, gammaln, hyp2f1


def resumo_rfm(visitas: pd.DataFrame, corte, inicio=None) -> pd.DataFrame:
    """(x, t_x, T) em dias para todos os clientes com visitas antes do corte."""
    corte = pd.Timestamp(corte)
    vis = visitas[visitas["DATA_ATEND"] < corte]
    if inicio is not None:
        vis = vis[vis["DATA_ATEND"] >= pd.Timestamp(inicio)]
    g = vis.groupby("CLI_CPF")["DATA_ATEND"]
    primeira, ultima = g.min(), g.max()
    return pd.DataFrame(
        {
            "x": g.size() - 1,
            "t_x": (ultima - primeira).dt.days,
            "T": (corte - primeira).dt.days,
        }
    )


class BGNBD:
    """Estimação por máxima verossimilhança e previsões do BG/NBD."""

    def __init__(self):
        self.params_ = None

    @staticmethod
    def _loglik(params, x, t_x, T):
        r, alpha, a, b = params
        ln_a1 = gammaln(r + x) - gammaln(r) + r * np.log(alpha)
        ln_a2 = betaln(a, b + x) - betaln(a, b)
        ln_a3 = -(r + x) * np.log(alpha + T)
        with np.errstate(divide="ignore", invalid="ignore"):
            ln_a4 = np.where(
                x > 0,
                np.log(a) - np.log(np.maximum(b + x - 1, 1e-12)) - (r + x) * np.log(alpha + t_x),
                -np.inf,
            )
        return ln_a1 + ln_a2 + np.logaddexp(ln_a3, ln_a4)

    def fit(self, x, t_x, T, chute=(0.5, 30.0, 0.5, 2.0)):
        x, t_x, T = (np.asarray(v, dtype=float) for v in (x, t_x, T))

        def nll(log_params):
            return -self._loglik(np.exp(log_params), x, t_x, T).sum()

        res = minimize(nll, np.log(chute), method="L-BFGS-B")
        if not res.success:
            raise RuntimeError(f"BG/NBD não convergiu: {res.message}")
        self.params_ = dict(zip(["r", "alpha", "a", "b"], np.exp(res.x)))
        self.loglik_ = -res.fun
        return self

    def p_ativo(self, x, t_x, T):
        r, alpha, a, b = self.params_.values()
        x, t_x, T = (np.asarray(v, dtype=float) for v in (x, t_x, T))
        with np.errstate(divide="ignore", invalid="ignore"):
            razao = (a / (b + x - 1)) * ((alpha + T) / (alpha + t_x)) ** (r + x)
        return np.where(x > 0, 1.0 / (1.0 + razao), 1.0)

    def p_sem_compra(self, t, x, t_x, T):
        """P(nenhuma compra em (T, T + t]) = 1 - P(ativo) * (1 - E[exp(-lambda t)])."""
        r, alpha, _, _ = self.params_.values()
        x, T = np.asarray(x, dtype=float), np.asarray(T, dtype=float)
        pa = self.p_ativo(x, t_x, T)
        sem_compra_se_ativo = ((alpha + T) / (alpha + T + t)) ** (r + x)
        return 1.0 - pa + pa * sem_compra_se_ativo

    def compras_esperadas(self, t, x, t_x, T):
        """E[número de compras em (T, T + t]] (exige a > 1)."""
        r, alpha, a, b = self.params_.values()
        x, t_x, T = (np.asarray(v, dtype=float) for v in (x, t_x, T))
        z = t / (alpha + T + t)
        termo = 1 - ((alpha + T) / (alpha + T + t)) ** (r + x) * hyp2f1(r + x, b + x, a + b + x - 1, z)
        num = (a + b + x - 1) / (a - 1) * termo
        with np.errstate(divide="ignore", invalid="ignore"):
            den = 1 + np.where(
                x > 0, (a / (b + x - 1)) * ((alpha + T) / (alpha + t_x)) ** (r + x), 0.0
            )
        return num / den
