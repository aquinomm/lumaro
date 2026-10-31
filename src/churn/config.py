"""Configurações centrais do estudo: caminhos, período da base e parâmetros."""

from pathlib import Path

import pandas as pd

# --- Caminhos ---------------------------------------------------------------
ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = ROOT / "data"
RAW_DIR = DATA_DIR / "raw"
INTERIM_DIR = DATA_DIR / "interim"
PROCESSED_DIR = DATA_DIR / "processed"
FIG_DIR = ROOT / "reports" / "figures"
TAB_DIR = ROOT / "reports" / "tables"
MODELS_DIR = ROOT / "models"

ARQ_VENDAS = RAW_DIR / "vendas.csv"
ARQ_PRODUTOS = RAW_DIR / "produto.csv"

# --- Período coberto pela base (primeiro e último dia com vendas) -----------
INICIO = pd.Timestamp("2024-01-02")
FIM = pd.Timestamp("2024-12-31")

# --- Parâmetros do estudo ---------------------------------------------------
# Critério de churn: cliente ativo na data de corte (comprou nos últimos TAU
# dias) que não volta a comprar nos TAU dias seguintes.
TAU = 90
# Janela de observação usada para construir os atributos de cada snapshot.
# Fixa para que os atributos tenham o mesmo significado em todas as datas.
LOOKBACK = 120
# Limiares avaliados na análise de sensibilidade do critério.
TAUS_SENSIBILIDADE = (60, 90, 120)
# Datas de corte (snapshots mensais). A primeira é a mais cedo possível com
# LOOKBACK dias de histórico; a última, a mais tarde com o rótulo observável.
CORTES = pd.date_range("2024-05-01", "2024-10-01", freq="MS")

SEED = 42

CATEGORIA_SAZONAL = "Bacalhau & Pescados"
