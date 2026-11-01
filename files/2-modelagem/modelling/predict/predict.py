import os
import joblib
import numpy as np
import pandas as pd
import sqlalchemy

PREDICT_DIR = os.path.dirname(os.path.abspath(__file__))
MODELLING_DIR = os.path.dirname(PREDICT_DIR)
TRAIN_DIR = os.path.join(MODELLING_DIR, 'train')
BASE_DIR = os.path.dirname(MODELLING_DIR)
FILES_DIR = os.path.dirname(BASE_DIR)
DATA_DIR = os.path.join(FILES_DIR, 'data')

engine = sqlalchemy.create_engine("sqlite:///" + os.path.join(DATA_DIR, 'banco_de_dados.db'))


def run_predict(dt_safra: str = '2025-01-01'):
    print("\n" + "=" * 105)
    print(f"PREDIÇÃO EM PRODUÇÃO (SCORING) - SAFRA: {dt_safra}")
    print("=" * 105)

    model_path = os.path.join(TRAIN_DIR, 'best_model.pkl')
    if not os.path.exists(model_path):
        raise FileNotFoundError(
            f"Modelo não encontrado em {model_path}. Execute model.py primeiro."
        )

    bundle = joblib.load(model_path)
    model = bundle['model']
    model_name = bundle['model_name']
    features = bundle['features']

    # Carrega a snapshot de produção (2025-01-01) da Feature Store (tb_book)
    query = f"SELECT * FROM tb_book WHERE dt_ref = '{dt_safra}'"
    df_safra = pd.read_sql_query(query, engine)

    if df_safra.empty:
        print(f"Safra {dt_safra} não encontrada em tb_book. Gerando safra automaticamente...")
        import sys
        queries_dir = os.path.join(BASE_DIR, 'queries')
        sys.path.insert(0, queries_dir)
        from exec_safra import exec_safra
        exec_safra(dt_safra, engine)
        df_safra = pd.read_sql_query(query, engine)

    # Executa o predict e predict_proba
    X_prod = df_safra[features]
    prob_churn = model.predict_proba(X_prod)[:, 1]
    flag_churn_pred = model.predict(X_prod)

    # Classifica em faixas de risco de negócio
    condicoes = [
        prob_churn < 0.40,
        (prob_churn >= 0.40) & (prob_churn < 0.70),
        prob_churn >= 0.70,
    ]
    faixas = ['1. Baixo Risco (< 40%)', '2. Médio Risco (40% - 70%)', '3. Alto Risco (>= 70%)']
    faixa_risco = np.select(condicoes, faixas, default='2. Médio Risco (40% - 70%)')

    # Monta tabela consolidada de predição para uso pelo time de negócios / CRM
    df_pred = pd.DataFrame({
        'dt_ref': df_safra['dt_ref'],
        'CLI_CPF': df_safra['CLI_CPF'],
        'modelo_utilizado': model_name,
        'prob_churn': np.round(prob_churn, 4),
        'flag_churn_pred': flag_churn_pred,
        'faixa_risco': faixa_risco,
        'faturamento_ult_6m': np.round(df_safra['faturamento'], 2),
        'qtde_visitas_ult_6m': df_safra['qtde_visitas'],
        'ticket_medio': np.round(df_safra['ticket_medio'], 2),
        'qtd_dias_ultima_compra': df_safra['qtd_dias_ultima_compra'],
    }).sort_values(by='prob_churn', ascending=False).reset_index(drop=True)

    # Salva no banco de dados e em CSV
    table_name = f"tb_pred_churn_{dt_safra.replace('-', '_')}"
    df_pred.to_sql(table_name, engine, if_exists='replace', index=False)

    csv_path = os.path.join(PREDICT_DIR, f"predicoes_{dt_safra.replace('-', '_')}.csv")
    df_pred.to_csv(csv_path, index=False)

    # Resumo executivo
    total_clientes = len(df_pred)
    qtd_churn_previsto = int(df_pred['flag_churn_pred'].sum())
    taxa_churn_prevista = df_pred['flag_churn_pred'].mean()
    prob_media = df_pred['prob_churn'].mean()

    print(f"Modelo aplicado:                {model_name}")
    print(f"Data de referência (Snapshot):  {dt_safra} (clientes ativos entre 01/07/2024 e 31/12/2024)")
    print(f"Total de clientes avaliados:    {total_clientes:,}")
    print(f"Clientes previstos como Churn:  {qtd_churn_previsto:,} ({taxa_churn_prevista:.2%})")
    print(f"Probabilidade média de Churn:   {prob_media:.2%}\n")

    # Resumo por faixa de risco
    resumo_faixas = (
        df_pred.groupby('faixa_risco')
        .agg(
            qtd_clientes=('CLI_CPF', 'count'),
            prob_churn_media=('prob_churn', 'mean'),
            faturamento_em_risco=('faturamento_ult_6m', 'sum'),
            ticket_medio_grupo=('ticket_medio', 'mean'),
            dias_ult_compra_medio=('qtd_dias_ultima_compra', 'mean'),
        )
        .reset_index()
    )
    resumo_faixas['perc_clientes'] = resumo_faixas['qtd_clientes'] / total_clientes

    print("--- DISTRIBUIÇÃO POR FAIXA DE RISCO DE CHURN ---")
    print(
        resumo_faixas[[
            'faixa_risco',
            'qtd_clientes',
            'perc_clientes',
            'prob_churn_media',
            'faturamento_em_risco',
            'dias_ult_compra_medio',
        ]].to_string(
            index=False,
            formatters={
                'qtd_clientes': '{:,}'.format,
                'perc_clientes': '{:.2%}'.format,
                'prob_churn_media': '{:.2%}'.format,
                'faturamento_em_risco': 'R$ {:,.2f}'.format,
                'dias_ult_compra_medio': '{:.1f} dias'.format,
            },
        )
    )

    print("\n--- TOP 10 CLIENTES DE ALTO VALOR COM MAIOR RISCO DE CHURN (AÇÃO PRIORITÁRIA CRM) ---")
    top_vip_risco = (
        df_pred[df_pred['faixa_risco'] == '3. Alto Risco (>= 70%)']
        .sort_values(by=['faturamento_ult_6m', 'prob_churn'], ascending=[False, False])
        .head(10)
    )
    print(
        top_vip_risco[[
            'CLI_CPF',
            'prob_churn',
            'faturamento_ult_6m',
            'qtde_visitas_ult_6m',
            'ticket_medio',
            'qtd_dias_ultima_compra',
        ]].to_string(index=False)
    )

    print("\n" + "=" * 105)
    print(f"Predições salvas na tabela SQLite '{table_name}' e no arquivo:\n{csv_path}")
    print("=" * 105)

    return df_pred


if __name__ == '__main__':
    run_predict('2025-01-01')
