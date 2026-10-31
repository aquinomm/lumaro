# Churn por inatividade na VAI Store

Projeto da disciplina **PTC3567 — Ciência dos Dados** (Escola Politécnica da USP), Grupo 4.
Tema: Finanças, Crédito e Comportamento do Consumidor.

| Integrantes | NUSP |
|---|---|
| Lucas Parisotto Fabre | 18005349 |
| Mariana Aquino Rocha | 13680251 |
| Roberto Machado e Silva Gomide | 11321371 |

Professores: Felipe Miguel Pait e Pedro Luiz Pizzigatti Corrêa.

## O problema

A VAI Store é uma rede de varejo alimentar saudável. Seus clientes não têm contrato: não cancelam, simplesmente
param de comprar. O churn precisa ser **definido por inatividade** ("τ dias sem comprar"), e essa escolha é
deliberada. O projeto (i) fundamenta τ na dinâmica de recompra, (ii) caracteriza quem fica inativo, (iii) prevê a
inatividade numa data de corte e (iv) mede a sensibilidade das conclusões a τ.

Questões de pesquisa e hipóteses: [`docs/questoes_e_hipoteses.md`](docs/questoes_e_hipoteses.md).

## Principais resultados

- **Critério:** a chance de o cliente voltar cai de forma contínua com o tempo sem compra — não há corte natural.
  Adotamos **τ = 90 dias** (churn = cliente ativo que não volta nos 90 dias seguintes), com sensibilidade para 60 e
  120 dias. Prevalência: ~53%.
- **Predição** (validação fora do tempo, teste em 01/10/2024): LightGBM e regressão logística têm AUC ≈ 0,770;
  o modelo probabilístico BG/NBD, 0,763; a heurística de recência, 0,610. O ganho sobre o BG/NBD é pequeno, mas
  significativo, e vem dos atributos de histórico, não do algoritmo.
- **Explicação:** frequência e antiguidade concentram quase todo o poder preditivo; amplitude de categorias,
  tendência do gasto e sazonalidade (bacalhau) têm efeito estatístico pequeno; a recência relativa ao ritmo do
  cliente não supera a recência absoluta.
- **Robustez:** a ordenação de risco é praticamente a mesma para τ = 60, 90 ou 120 (Spearman ≥ 0,96).
- **Limitação central:** a base cobre 59 dos 6.500 produtos, então a inatividade é medida nesse recorte.

## Estrutura

```
├── data/                     # NÃO versionado (dados da Visagio)
│   ├── raw/                  # vendas.csv e produto.csv originais, intocados
│   ├── interim/              # cache em parquet (itens e visitas)
│   └── processed/            # previsões e tabelas intermediárias
├── docs/
│   └── questoes_e_hipoteses.md
├── notebooks/
│   ├── 01_eda.ipynb          # caracterização, qualidade, EDA e escolha do critério de churn
│   └── 02_modelagem.ipynb    # atributos, validação fora do tempo, modelos, SHAP, sensibilidade
├── reports/
│   ├── figures/              # figuras em PDF para o relatório (sem título; o LaTeX dá a legenda)
│   └── tables/               # métricas e tabelas de resultados (CSV)
├── src/churn/                # código reutilizado pelos dois notebooks
│   ├── config.py             # caminhos, período da base e parâmetros do estudo (τ, janela, cortes)
│   ├── data.py               # leitura, limpeza e agregação em visitas (cliente-dia)
│   ├── features.py           # snapshots cliente × data de corte e rótulo de churn
│   ├── bgnbd.py              # modelo BG/NBD (máxima verossimilhança)
│   ├── evaluation.py         # métricas, curvas de ganho, bootstrap
│   └── viz.py                # identidade visual dos gráficos
├── models/                   # modelos treinados (não versionados; refeitos pelo notebook 2)
└── requirements.txt
```

## Como reproduzir

1. **Ambiente (Python 3.13).** Com [uv](https://docs.astral.sh/uv/):

   ```bash
   uv venv --python 3.13 .venv
   uv pip install -r requirements.txt
   ```

   ou com o `venv` padrão: `python3.13 -m venv .venv`, ative o ambiente e rode
   `pip install -r requirements.txt`.

2. **Dados.** Copie `vendas.csv` e `produto.csv` (pasta "Dados Projeto" fornecida pela disciplina) para
   `data/raw/` e confira os hashes (seção abaixo).

3. **Notebooks**, nesta ordem: `01_eda.ipynb` e `02_modelagem.ipynb` (Jupyter Lab ou VS Code, com o kernel do
   `.venv`). Para executar tudo pela linha de comando:

   ```bash
   cd notebooks
   python -m nbconvert --to notebook --execute --inplace 01_eda.ipynb 02_modelagem.ipynb
   ```

   O primeiro acesso aos dados cria um cache em `data/interim/` (apague a pasta se alterar `src/churn/data.py`).
   As figuras e tabelas de `reports/` são regeneradas a cada execução. Tempo total: ~10 minutos num notebook comum.

## Gestão dos dados

Notas para a seção "Estratégias de Gestão dos Dados" do relatório, organizadas pelo ciclo de vida DataONE.

- **Fonte e acesso.** Base de vendas da VAI Store cedida pela Visagio (VLabs) para uso na disciplina: todas as
  vendas de 2024 (02/01 a 31/12) de 59 SKUs, em duas lojas (rua e shopping), com o cliente identificado por um
  código anonimizado, mais o cadastro de 6.500 produtos. É um conjunto **proprietário, sem DOI**; por isso não é
  versionado nem redistribuído. O que é público é o código, a documentação e os resultados agregados.
- **Integridade (assegurar).** Cada execução recalcula o SHA-256 dos arquivos brutos (notebook 1, seção 1).
  Versão analisada:

  | arquivo | linhas (sem cabeçalho) | SHA-256 |
  |---|---|---|
  | `vendas.csv` | 556.198 | `4a4560758c71aa265072fad0da05547d004539e3eb44be16a112925a12c52bd6` |
  | `produto.csv` | 6.500 | `5216141e648fc2716994ca3739567a63788946d3c21c4a1244b286cc82f1be09` |

- **Descrição.** Dicionário de dados e classificação dos atributos no notebook 1 (seção 2); dicionário dos
  atributos de modelagem em `reports/tables/dicionario_atributos.csv`.
- **Preservação.** Os arquivos originais ficam intocados em `data/raw/`; tudo o que é derivado (cache, previsões,
  modelos) é regenerável a partir deles pelo código.
- **Reprodutibilidade.** Versões fixadas em `requirements.txt`, semente única (`SEED = 42`), parâmetros
  centralizados em `src/churn/config.py`, código compartilhado entre os notebooks em `src/churn/` e testes
  automáticos de vazamento de informação no notebook 2.
- **Privacidade.** Nenhum dado individual é versionado; as saídas publicadas são agregadas.

## Licença dos dados

Os dados pertencem à Visagio/VAI Store e são usados exclusivamente para fins acadêmicos nesta disciplina.
