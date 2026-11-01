import os
import joblib
import pandas as pd
import sqlalchemy
from sklearn import (
    calibration,
    ensemble,
    linear_model,
    metrics,
    model_selection,
    neural_network,
    pipeline,
    preprocessing,
    svm,
    tree,
)

TRAIN_DIR = os.path.dirname(os.path.abspath(__file__))
MODELLING_DIR = os.path.dirname(TRAIN_DIR)
BASE_DIR = os.path.dirname(MODELLING_DIR)
FILES_DIR = os.path.dirname(BASE_DIR)
DATA_DIR = os.path.join(FILES_DIR, 'data')

engine = sqlalchemy.create_engine("sqlite:///" + os.path.join(DATA_DIR, 'banco_de_dados.db'))


def train_and_compare_models():
    print("Carregando base tb_abt_churn...")
    abt = pd.read_sql_table('tb_abt_churn', engine)

    # Separando a última snapshot maturada (2024-10-01) para validação Out-Of-Time (OOT)
    max_dt = abt['dt_ref'].max()
    df_oot = abt[abt['dt_ref'] == max_dt].copy()
    df_abt = abt[abt['dt_ref'] < max_dt].copy()

    print(f"Safras de Treino/Teste (< {max_dt}): { sorted(df_abt['dt_ref'].unique()) } -> {len(df_abt):,} linhas")
    print(f"Safra Out-Of-Time (== {max_dt}):     ['{max_dt}'] -> {len(df_oot):,} linhas\n")

    # Definição de target e features
    target = 'flag_churn'
    to_remove = ['dt_ref', 'CLI_CPF', 'prim_compra', target]

    features = [c for c in df_abt.columns if c not in to_remove]

    # Divisão Treino (80%) e Teste (20%) nas safras de modelagem
    X_train, X_test, y_train, y_test = model_selection.train_test_split(
        df_abt[features],
        df_abt[target],
        test_size=0.2,
        random_state=2026,
    )
    X_oot = df_oot[features]
    y_oot = df_oot[target]

    # Dicionário com os modelos a serem comparados
    models = {
        'Decision Tree (Sem Poda)': tree.DecisionTreeClassifier(
            random_state=2026
        ),
        'Decision Tree (max_depth=8)': tree.DecisionTreeClassifier(
            max_depth=16,
            min_samples_leaf=50,
            random_state=2026,
        ),
        'Regressão Logística': pipeline.Pipeline([
            ('scaler', preprocessing.StandardScaler()),
            ('clf', linear_model.LogisticRegression(max_iter=1000, random_state=2026)),
        ]),
        'SVM Linear': pipeline.Pipeline([
            ('scaler', preprocessing.StandardScaler()),
            ('clf', calibration.CalibratedClassifierCV(
                svm.LinearSVC(random_state=2026, max_iter=2000), cv=3
            )),
        ]),
        'Random Forest': ensemble.RandomForestClassifier(
            n_estimators=100,
            max_depth=10,
            min_samples_leaf=30,
            random_state=2026,
            n_jobs=-1,
        ),
        'Gradient Boosting (HistGB)': ensemble.HistGradientBoostingClassifier(
            max_iter=150,
            max_depth=8,
            learning_rate=0.05,
            random_state=2026,
        ),
        'Rede Neural (MLP)': pipeline.Pipeline([
            ('scaler', preprocessing.StandardScaler()),
            ('clf', neural_network.MLPClassifier(
                hidden_layer_sizes=(64, 32),
                max_iter=80,
                early_stopping=True,
                random_state=2026,
            )),
        ]),
    }

    results = []
    trained_models = {}

    for name, clf in models.items():
        print(f"Treinando: {name}...")
        clf.fit(X_train, y_train)
        trained_models[name] = clf

        # Predições de classe (0 ou 1)
        y_train_pred = clf.predict(X_train)
        y_test_pred = clf.predict(X_test)
        y_oot_pred = clf.predict(X_oot)

        # Predições de probabilidade (score contínuo de 0 a 1)
        y_train_proba = clf.predict_proba(X_train)[:, 1]
        y_test_proba = clf.predict_proba(X_test)[:, 1]
        y_oot_proba = clf.predict_proba(X_oot)[:, 1]

        results.append({
            'Modelo': name,
            'Acc Treino': metrics.accuracy_score(y_train, y_train_pred),
            'Acc Teste': metrics.accuracy_score(y_test, y_test_pred),
            'Acc OOT': metrics.accuracy_score(y_oot, y_oot_pred),
            'AUC Treino': metrics.roc_auc_score(y_train, y_train_proba),
            'AUC Teste': metrics.roc_auc_score(y_test, y_test_proba),
            'AUC OOT': metrics.roc_auc_score(y_oot, y_oot_proba),
            'F1 Teste': metrics.f1_score(y_test, y_test_pred),
            'F1 OOT': metrics.f1_score(y_oot, y_oot_pred),
        })

    # Consolida tabela comparativa ordenada pela performance na safra Out-Of-Time (AUC OOT)
    df_comp = pd.DataFrame(results).sort_values(by='AUC OOT', ascending=False).reset_index(drop=True)

    print("\n" + "=" * 105)
    print("COMPARATIVO CONSOLIDADO DE MODELOS (ORDENADO POR ROC AUC NA BASE OUT-OF-TIME)")
    print("=" * 105)
    print(df_comp.to_string(index=False, float_format=lambda x: f"{x:.4f}"))
    print("=" * 105)

    # Salva o comparativo em CSV e no banco de dados
    comp_csv_path = os.path.join(TRAIN_DIR, 'comparativo_modelos.csv')
    df_comp.to_csv(comp_csv_path, index=False)
    df_comp.to_sql('tb_comparativo_modelos', engine, if_exists='replace', index=False)

    # Seleciona e salva o melhor modelo
    best_model_name = df_comp.iloc[0]['Modelo']
    best_model = trained_models[best_model_name]
    best_metrics = df_comp.iloc[0].to_dict()

    model_bundle = {
        'model': best_model,
        'model_name': best_model_name,
        'features': features,
        'metrics': best_metrics,
    }
    model_path = os.path.join(TRAIN_DIR, 'best_model.pkl')
    joblib.dump(model_bundle, model_path)

    print(f"\nMelhor modelo selecionado: {best_model_name} (AUC OOT = {best_metrics['AUC OOT']:.4f})")
    print(f"Modelo salvo em: {model_path}")
    print(f"Tabela comparativa salva em: {comp_csv_path}")

    # Análise de Importância de Features e Multicolinearidade (Correlação)
    analyze_features(best_model, X_train, features)

    return model_bundle


def analyze_features(model, X_train: pd.DataFrame, features: list):
    """Extrai a importância das features do modelo campeão e identifica pares com alta correlação."""
    print("\n" + "=" * 105)
    print("1. IMPORTÂNCIA DAS FEATURES NO MODELO CAMPEÃO (RANDOM FOREST)")
    print("=" * 105)

    importances = model.feature_importances_
    df_imp = pd.DataFrame({
        'Feature': features,
        'Importancia': importances,
        'Importancia_%': importances * 100,
    }).sort_values(by='Importancia', ascending=False).reset_index(drop=True)
    df_imp['Importancia_Acumulada_%'] = df_imp['Importancia_%'].cumsum()

    print(
        df_imp.to_string(
            index=False,
            formatters={
                'Importancia': '{:.4f}'.format,
                'Importancia_%': '{:.2f}%'.format,
                'Importancia_Acumulada_%': '{:.2f}%'.format,
            },
        )
    )

    imp_csv_path = os.path.join(TRAIN_DIR, 'feature_importances.csv')
    df_imp.to_csv(imp_csv_path, index=False)
    df_imp.to_sql('tb_feature_importances', engine, if_exists='replace', index=False)

    # Mapa de importância para decidir qual variável remover em cada par correlacionado
    imp_map = dict(zip(df_imp['Feature'], df_imp['Importancia']))

    print("\n" + "=" * 105)
    print("2. PARES DE FEATURES COM ALTA CORRELAÇÃO (|r| >= 0.80) E SUGESTÃO DE REMOÇÃO")
    print("=" * 105)

    corr_matrix = X_train.corr()
    high_corr_pairs = []

    cols = corr_matrix.columns
    for i in range(len(cols)):
        for j in range(i + 1, len(cols)):
            f1, f2 = cols[i], cols[j]
            r = corr_matrix.iloc[i, j]
            if abs(r) >= 0.80:
                imp1, imp2 = imp_map.get(f1, 0), imp_map.get(f2, 0)
                sugestao_remover = f2 if imp1 >= imp2 else f1
                sugestao_manter = f1 if imp1 >= imp2 else f2
                high_corr_pairs.append({
                    'Feature_A': f1,
                    'Feature_B': f2,
                    'Correlacao_r': r,
                    'Abs_r': abs(r),
                    'Imp_A_%': imp1 * 100,
                    'Imp_B_%': imp2 * 100,
                    'Manter': sugestao_manter,
                    'Candidata_Remover': sugestao_remover,
                })

    df_corr = (
        pd.DataFrame(high_corr_pairs)
        .sort_values(by='Abs_r', ascending=False)
        .drop(columns=['Abs_r'])
        .reset_index(drop=True)
    )

    print(
        df_corr.to_string(
            index=False,
            formatters={
                'Correlacao_r': '{:+.4f}'.format,
                'Imp_A_%': '{:.2f}%'.format,
                'Imp_B_%': '{:.2f}%'.format,
            },
        )
    )

    candidatas_unicas = list(dict.fromkeys(df_corr['Candidata_Remover'].tolist()))
    print("\n--- RESUMO DE CANDIDATAS À REMOÇÃO POR REDUNDÂNCIA (MULTICOLINEARIDADE) ---")
    print(f"Total de variáveis redundantes sugeridas para remoção ({len(candidatas_unicas)}):")
    print(candidatas_unicas)

    corr_csv_path = os.path.join(TRAIN_DIR, 'correlacoes_altas.csv')
    df_corr.to_csv(corr_csv_path, index=False)
    df_corr.to_sql('tb_correlacoes_altas', engine, if_exists='replace', index=False)


if __name__ == '__main__':
    train_and_compare_models()

    # Executa também a predição para a última snapshot (2025-01-01)
    predict_dir = os.path.join(MODELLING_DIR, 'predict')
    predict_script = os.path.join(predict_dir, 'predict.py')
    if os.path.exists(predict_script):
        import sys
        sys.path.insert(0, predict_dir)
        from predict import run_predict
        run_predict()
