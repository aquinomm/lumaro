"""Leitura, preparação e agregação dos dados transacionais da VAI Store."""

import hashlib
from pathlib import Path

import pandas as pd

from . import config

# Abaixo deste preço relativo (preço pago / mediana do SKU no mês) o item é
# considerado comprado com desconto.
LIMIAR_DESCONTO = 0.95


def sha256(path: Path, chunk: int = 1 << 20) -> str:
    """Hash SHA-256 de um arquivo, para registrar a versão exata dos dados."""
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for bloco in iter(lambda: f.read(chunk), b""):
            h.update(bloco)
    return h.hexdigest()


def ler_vendas(path: Path = config.ARQ_VENDAS) -> pd.DataFrame:
    """Lê a base de vendas bruta (uma linha por item vendido)."""
    return pd.read_csv(
        path,
        dtype={
            "COD_ATEND": str,
            "COD_VENDA": str,
            "COD_FILIAL": str,
            "FILIAL": "category",
            "SKU": "Int64",
            "UNID": "category",
            "CLI_CPF": str,
        },
        parse_dates=["DATA_ATEND"],
    )


def ler_produtos(path: Path = config.ARQ_PRODUTOS) -> pd.DataFrame:
    """Lê o cadastro de produtos, removendo os espaços de preenchimento.

    O SKU vem como texto com zeros à esquerda e espaços ("000003   "); é
    convertido para inteiro para casar com a base de vendas.
    """
    df = pd.read_csv(path, dtype=str)
    df = df.apply(lambda s: s.str.strip())
    df["SKU"] = pd.to_numeric(df["SKU"], errors="coerce").astype("Int64")
    return df


def preparar_itens(vendas: pd.DataFrame, produtos: pd.DataFrame) -> pd.DataFrame:
    """Junta vendas ao cadastro e cria variáveis derivadas no nível do item."""
    prod = produtos.dropna(subset=["SKU"]).drop_duplicates("SKU")
    itens = vendas.merge(
        prod[["SKU", "NOME_PRODUTO", "CATEGORIA", "SUBCATEGORIA"]],
        on="SKU",
        how="left",
        validate="many_to_one",
    )
    itens["CATEGORIA"] = itens["CATEGORIA"].astype("category")
    itens["PRECO_UNIT"] = itens["FATUR_VENDA"] / itens["QTD_VENDA"]
    # Preço de referência: mediana do SKU no mês (absorve reajustes de tabela).
    # Como as datas de corte caem sempre no dia 1º, a referência de um mês da
    # janela de atributos só usa vendas anteriores ao corte.
    mes = itens["DATA_ATEND"].dt.month
    referencia = itens.groupby(["SKU", mes])["PRECO_UNIT"].transform("median")
    itens["PRECO_REL"] = itens["PRECO_UNIT"] / referencia
    itens["DESCONTO"] = itens["PRECO_REL"] < LIMIAR_DESCONTO
    itens["SHOPPING"] = itens["FILIAL"].eq("SHOPPING")
    itens["SAZONAL"] = itens["CATEGORIA"].eq(config.CATEGORIA_SAZONAL)
    return itens


def agregar_visitas(itens: pd.DataFrame) -> pd.DataFrame:
    """Agrega os itens em visitas (cliente-dia), a unidade de análise do churn.

    Um cliente pode ter mais de um atendimento no mesmo dia; para medir
    recorrência, o dia é tratado como uma única ida à loja.
    """
    visitas = (
        itens.groupby(["CLI_CPF", "DATA_ATEND"], observed=True)
        .agg(
            FATUR=("FATUR_VENDA", "sum"),
            N_ITENS=("COD_VENDA", "size"),
            N_SKUS=("SKU", "nunique"),
            N_ATEND=("COD_ATEND", "nunique"),
            SHOPPING=("SHOPPING", "mean"),
            DESCONTO=("DESCONTO", "mean"),
            SAZONAL=("SAZONAL", "max"),
        )
        .reset_index()
        .sort_values(["CLI_CPF", "DATA_ATEND"], ignore_index=True)
    )
    visitas["FDS"] = visitas["DATA_ATEND"].dt.day_of_week >= 5
    visitas["ORDEM"] = visitas.groupby("CLI_CPF").cumcount() + 1
    visitas["GAP_ANTERIOR"] = visitas.groupby("CLI_CPF")["DATA_ATEND"].diff().dt.days
    return visitas


def carregar_base(usar_cache: bool = True) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Retorna (itens, visitas), com cache em parquet em ``data/interim``.

    O cache é refeito se algum arquivo bruto for mais recente que ele.
    """
    arq_itens = config.INTERIM_DIR / "itens.parquet"
    arq_visitas = config.INTERIM_DIR / "visitas.parquet"
    brutos = [config.ARQ_VENDAS, config.ARQ_PRODUTOS]
    cache_valido = (
        usar_cache
        and arq_itens.exists()
        and arq_visitas.exists()
        and min(arq_itens.stat().st_mtime, arq_visitas.stat().st_mtime)
        > max(p.stat().st_mtime for p in brutos)
    )
    if cache_valido:
        return pd.read_parquet(arq_itens), pd.read_parquet(arq_visitas)

    itens = preparar_itens(ler_vendas(), ler_produtos())
    visitas = agregar_visitas(itens)
    config.INTERIM_DIR.mkdir(parents=True, exist_ok=True)
    itens.to_parquet(arq_itens, index=False)
    visitas.to_parquet(arq_visitas, index=False)
    return itens, visitas
