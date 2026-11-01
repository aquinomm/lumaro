import os
import pandas as pd
from sqlalchemy import create_engine, text

ep_dir = os.path.dirname(os.path.abspath(__file__))
src_dir = os.path.dirname(ep_dir)
base_dir = os.path.dirname(src_dir)
data_dir = os.path.join(base_dir, 'data')

def import_query(path, **kwargs):
    with open(path, 'r', **kwargs) as file_open:
        return file_open.read()

def connect_db():
    return create_engine("sqlite:///" + os.path.join(data_dir, 'banco_de_dados.db'))

def exec_safra(date: str, engine):
    """Executa o processamento e inserção da safra para a data de referência indicada."""
    print(f"\n--- Processando safra: {date} ---")

    # Carrega a query e remove ponto e vírgula final se houver
    raw_query = import_query(os.path.join(ep_dir, 'features.sql')).strip().rstrip(';')
    query = raw_query.format(date=date)

    with engine.connect() as con:
        # 1. Tenta apagar a safra caso já tenha sido processada anteriormente
        try:
            delete_query = f"DELETE FROM tb_book WHERE dt_ref = '{date}'"
            con.execute(text(delete_query))
            con.commit()
            print(f"Safra {date} anterior removida (se existia).")
        except Exception:
            # Caso a tabela ainda não exista, o DELETE irá falhar e é seguro ignorar
            pass

        # 2. Tenta criar a tabela; se já existir, faz INSERT
        try:
            create_query = f"CREATE TABLE tb_book AS\n{query}"
            con.execute(text(create_query))
            con.commit()
            print(f"Tabela tb_book criada com a safra {date}.")
        except Exception:
            # Tabela já existe, apenas insere a nova safra
            insert_query = f"INSERT INTO tb_book\n{query}"
            con.execute(text(insert_query))
            con.commit()
            print(f"Safra {date} inserida em tb_book.")

def exec_safras_periodo(start_date: str, end_date: str):
    """Gera todas as safras mês a mês no período (início de cada mês)."""
    engine = connect_db()
    # Gera as datas de primeiro dia de cada mês: ex. '2024-01-01', '2024-02-01', ...
    dates = pd.date_range(start=start_date, end=end_date, freq='MS').strftime('%Y-%m-%d')

    for dt in dates:
        exec_safra(dt, engine)

if __name__ == '__main__':
    # 1. Safras com 6 meses de histórico e 3 meses de target maturados (Treino e OOT)
    exec_safras_periodo(start_date='2024-07-01', end_date='2024-10-01')

    # 2. Safra de Produção / Predict (observa 01/07/2024 a 31/12/2024 para prever Q1 2025)
    engine = connect_db()
    exec_safra('2025-01-01', engine)