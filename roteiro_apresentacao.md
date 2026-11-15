# Roteiro de Apresentação Final — PTC3567 (Previsão de Churn no Varejo)

**Duração total:** 15 minutos  
**Apresentadores:** 3 pessoas (Pessoa 1, Pessoa 2, Pessoa 3)  
**Destaques principais:** Arquitetura do Projeto e Resultados  

---

## Visão Geral e Divisão de Tempo

| Seção | Slides | Responsável | Tempo | Acumulado | Foco Principal |
| :--- | :---: | :--- | :---: | :---: | :--- |
| **1. Introdução e Problema** | 1–2 | Pessoa 1 | 1m30s | 01:30 | Contexto do *churn* silencioso no varejo |
| **2. Dados e Insights da EDA** | 3–5 | Pessoa 1 | 2m30s | 04:00 | Definição dos 90 dias e hipóteses de negócio |
| **3. Arquitetura e Modelagem** | 6–9 | Pessoa 2 | 5m00s | 09:00 | Banco em camadas, safras anti-vazamento e *pipeline* |
| **4. Resultados e Predição 2025** | 10–13 | Pessoa 3 | 5m00s | 14:00 | Comparativo OOT, *feature importance* e faixas de risco |
| **5. Conclusão e Próximos Passos** | 14 | Pessoa 3 | 1m00s | 15:00 | Síntese de valor e recomendações |

---

## Seção 1: Introdução e Problema de Negócio — **Pessoa 1 (1m30s)**

### Slide 1: Capa
* **Conteúdo do slide:**
  * Título: *Previsão de Churn de Clientes no Varejo (VAI Store)*
  * Disciplina: PTC3567 – Ciência de Dados em Automação e Engenharia (Poli-USP)
  * Autores: Mariana Aquino Rocha, Lucas Parisotto Fabre, Roberto Machado e Silva Gomide
* **Fala:** Apresentação rápida do tema e dos integrantes.

### Slide 2: O Problema do *Churn* Silencioso
* **Conteúdo do slide:**
  * **Desafio:** Varejo físico não tem cancelamento formal — o cliente apenas deixa de voltar (*churn* silencioso).
  * **Objetivo:** Prever, a partir de 6 meses de histórico transacional, se o cliente entrará em evasão nos próximos 3 meses.
  * **Base de dados (VAI Store / Visagio, 2024):**
    * `vendas.csv`: **556.198 registros** | **102.943 clientes únicos** | **59 SKUs ativos**
    * `produto.csv`: **6.500 itens** | **13 categorias ativas**
    * **2 formatos de loja:** Rua (`101032`) e Shopping (`101042`)
* **Visual sugerido:** Canvas do projeto (`latex/imagens/canva2.png`).
* **Fala:** Explicar a diferença entre *churn* contratual e *churn* silencioso e apresentar a pergunta central do projeto.

---

## Seção 2: Dados, Qualidade e Insights da EDA — **Pessoa 1 (2m30s)**

### Slide 3: Qualidade, LGPD e Granularidade
* **Conteúdo do slide:**
  * **Integridade:** 100% de preenchimento nos 556.198 registros de vendas e nos 59 SKUs ativos em 2024.
  * **Privacidade (LGPD):** `CLI_CPF` pseudonimizado por *hash* irreversível na origem e removido antes do treino.
  * **Mudança de granularidade:** De item faturado para **visita diária por cliente** (`CLI_CPF` + `DATA_ATEND`) → **297.257 visitas únicas**.
* **Fala:** Destacar que consolidar por visita diária evita distorcer a frequência quando um cliente compra vários itens no mesmo cupom.

### Slide 4: Definição Empírica do *Churn* (Janela de 90 Dias)
* **Conteúdo do slide:**
  * **Perfil da base:** 50,20% *one-timers* (51.678 clientes) vs. 49,80% recorrentes (51.265 clientes).
  * **Ciclo de recompra** ($N = 194.314$ intervalos):
    * Q1 (25%): **14 dias** | Mediana (50%): **29 dias** | Q3 (75%): **63 dias**
    * **83,88% das recompras ocorrem em até 90 dias**
  * **Critério oficial (`flag_churn`):** 90 dias (3 meses) sem compra caracterizam evasão.
* **Fala:** Mostrar que a janela de 3 meses não foi arbitrária — foi fundamentada estatisticamente pela distribuição dos intervalos de recompra.

### Slide 5: Síntese das Hipóteses Exploratórias
* **Conteúdo do slide:**
  * **H1 (Confirmada):** **66,93%** de todo o *churn* vem de *one-timers* (falha na conversão para a 2ª compra).
  * **H2.1 (Refutada):** O intervalo entre compras **não** aumenta progressivamente antes do *churn* (medianas idênticas: $33\rightarrow34\rightarrow36$d vs. $31\rightarrow32\rightarrow36$d).
  * **H2.2 (Confirmada):** Itens de rotina (*Conservas* 76%, *Matinais* 74,4%) retêm mais que consumo imediato (*Lanchonete* 49% de *churn*).
  * **H3 (Confirmada):** Clientes **híbridos** (Rua + Shopping) têm apenas **33,41% de *churn*** (vs. 55,40% Shopping e 52,07% Rua).
* **Transição para Pessoa 2:** *"Com essas hipóteses validadas, a [Pessoa 2] vai mostrar como traduzimos esses insights na arquitetura de dados e modelagem."*

---

## Seção 3: Arquitetura do Projeto e Modelagem ⭐ — **Pessoa 2 (5m00s)**

### Slide 6: Arquitetura de Dados em Camadas (SQLite)
* **Conteúdo do slide:**
  * **Banco relacional (`banco_de_dados.db`)** estruturado em 3 camadas:
    1. **Camada Bruta:** `vendas` e `produto` (imutáveis, fonte única da verdade).
    2. **Camada de Atributos (`tb_book`):** 32 variáveis comportamentais agregadas por cliente em cada data de referência (`dt_ref`).
    3. **Camada Analítica (`tb_abt_churn`):** Cruzamento de `tb_book` com o comportamento futuro (`flag_churn`).
* **Visual sugerido:** Diagrama do banco de dados final (`latex/imagens/diagrama_db_2.png`).
* **Fala:** Explicar a separação entre dados brutos, *feature store* (`tb_book`) e tabela final de treino (`tb_abt_churn`).

### Slide 7: Pipeline Modular e Reprodutível
* **Conteúdo do slide:**
  * **Arquitetura inspirada na série DTona**, dividida em 4 scripts sequenciais:
    1. `queries/exec_safra.py` (`features.sql`) → popula `tb_book` com **idempotência** (`DELETE` + `INSERT` por `dt_ref`).
    2. `data_prep/train/exec_abt.py` (`abt.sql`) → gera `tb_abt_churn`.
    3. `modelling/train/model.py` (`random_state=2026`) → treina 7 modelos, exporta métricas e salva `best_model.pkl`.
    4. `modelling/predict/predict.py` → escora a safra de produção (`2025-01-01`).
* **Fala:** Destacar reprodutibilidade, automação e idempotência (reprocessar uma safra não gera duplicatas).

### Slide 8: Engenharia de Atributos e Prevenção de *Data Leakage*
* **Conteúdo do slide:**
  * **Isolamento temporal estrito:**
    * **Janela de Observação (6 meses):** $[\texttt{dt\_ref} - 6\text{m}, \; \texttt{dt\_ref})$ → cálculo das **32 variáveis**.
    * **Janela de Maturação / Target (3 meses):** $[\texttt{dt\_ref}, \; \texttt{dt\_ref} + 3\text{m})$ → marcação de `flag_churn`.
  * **5 Dimensões Comportamentais (32 features):**
    1. Relacionamento e Recência (`idade_base`, `qtd_dias_ultima_compra`)
    2. Frequência e Regularidade (`qtde_visitas`, `qtd_mes_ativacao`, `prop_ativacao`)
    3. Monetário e Volume (`faturamento`, `ticket_medio`, `qtde_produto_dst`)
    4. Canal Rua vs. Shopping (`qtde_visitas_rua/shopping`, proporções)
    5. Mix de Categorias (6 principais categorias = >80% da receita)
  * **Segurança:** `CLI_CPF`, `dt_ref` e `prim_compra` removidos do treino.
* **Fala:** Enfatizar que a separação rigorosa das janelas garante que nenhuma informação futura contamine o modelo.

### Slide 9: Safras, Validação Temporal (*Out-Of-Time*) e Modelos
* **Conteúdo do slide:**
  * **4 safras maturadas (271.783 registros):**
    * **Desenvolvimento (202.082 reg.):** Jul, Ago, Set/2024 → **80% Treino / 20% Teste *In-Time***.
    * **Validação OOT (69.701 reg.):** Out/2024 inteira reservada para simular produção futura.
    * **Predição (73.101 clientes):** `2025-01-01` (base jul–dez/2024 para prever 1º tri/2025).
  * **7 Algoritmos testados:** Árvore sem poda (referência de *overfitting*), Árvore com poda, Regressão Logística, SVM Linear, Random Forest, Gradient Boosting (HistGB) e Rede Neural (MLP).
* **Transição para Pessoa 3:** *"Com essa arquitetura validada temporalmente, a [Pessoa 3] apresenta os resultados comparativos e o impacto de negócio para 2025."*

---

## Seção 4: Resultados e Predição para 2025 ⭐ — **Pessoa 3 (5m00s)**

### Slide 10: Comparativo de Desempenho dos Modelos (OOT)
* **Conteúdo do slide:**
  * **Critério principal:** **ROC AUC na base OOT** (capacidade de ordenar clientes por risco).
  * **Tabela resumo:**
    * **Random Forest:** Acc OOT `72,05%` | **AUC OOT `0,7620`** | **F1 OOT `0,7828`** *(Escolhido)*
    * **Gradient Boosting (HistGB):** Acc OOT `72,09%` | AUC OOT `0,7620` | F1 OOT `0,7823`
    * **MLP / Logística / SVM:** AUC OOT entre `0,7571` e `0,7594` (estáveis).
    * **Árvore sem Poda:** Treino `0,9999` → OOT `0,6208` (*overfitting* severo).
* **Fala:** Explicar por que o Random Forest foi escolhido (empate no AUC OOT com HistGB, mas F1-Score superior no Teste e no OOT) e contrastar com o *overfitting* da árvore sem poda.

### Slide 11: O que Explica o *Churn*? (*Feature Importance* e Correlação)
* **Conteúdo do slide:**
  * **12 variáveis concentram 90,68%** da capacidade preditiva do Random Forest.
  * **Top Preditores:**
    1. `qtde_visitas` (**22,02%**)
    2. `qtd_mes_ativacao` (**19,33%**) → *juntas somam **41,35%***
    3. `qtde_produto` (**11,33%**) e `qtde_produto_dst` (**5,78%**)
  * **Insight:** Hábito de visitação e variedade da cesta pesam muito mais que categorias isoladas (as 12 variáveis de categoria somam apenas **4,06%**).
  * **Multicolinearidade:** 14 pares com $|r| \ge 0,80$ (ex.: proporções Rua/Shopping complementares) mapeados para simplificação futura.
* **Fala:** Conectar o resultado técnico ao comportamento do consumidor: manter o cliente visitando com regularidade mensal é o principal fator de retenção.

### Slide 12: Predição de Produção — Safra `2025-01-01`
* **Conteúdo do slide:**
  * **Base avaliada:** **73.101 clientes ativos** (R\$ 4,67 milhões de faturamento no 2º sem/2024).
  * **Corte padrão ($p \ge 0,50$):** **66,90%** da base (48.908 clientes) em risco de evasão (probabilidade média: **56,76%**).
  * **Segmentação em 3 Faixas de Risco:**
    * **Baixo Risco ($<40\%$):** 21,94% da base (16.041 clientes) | Recência média: 32,0d | **R\$ 2,29 milhões** (quase metade da receita) → *Manter sem descontos agressivos.*
    * **Médio Risco ($40\%$–$70\%$):** 41,25% da base (30.153 clientes) | Recência média: 75,8d | **R\$ 1,45 milhão** → *Foco principal de campanhas preventivas.*
    * **Alto Risco ($\ge 70\%$):** 36,81% da base (26.907 clientes) | Recência média: 92,7d | **R\$ 925,77 mil em risco** → *Ações de reativação.*
* **Fala:** Mostrar que o modelo não dá apenas um "sim/não", mas permite priorizar orçamento de marketing onde há maior retorno.

### Slide 13: Priorização — Top VIPs em Alto Risco
* **Conteúdo do slide:**
  * **Cruzamento Risco ($\ge 70\%$) × Faturamento 6m:**
    * Os 10 clientes de maior gasto no grupo de alto risco faturaram entre **R\$ 717,84 e R\$ 1.201,60** no semestre.
    * **Padrão comum:** Todos realizaram **apenas 1 visita** no semestre (*one-timers* de alto ticket).
  * **Ação imediata:** Abordagem personalizada para conversão da 2ª compra antes que completem 90 dias.
* **Fala:** Exemplo concreto e acionável de como a lista gerada pelo `predict.py` vira ação comercial imediata.

---

## Seção 5: Conclusão e Próximos Passos — **Pessoa 3 (1m00s)**

### Slide 14: Conclusão e Próximos Passos
* **Conteúdo do slide:**
  * **Entrega:** *Pipeline* ponta a ponta reprodutível, sem vazamento temporal, validado em OOT (ROC AUC `0,7620`) e pronto para operação.
  * **Próximos passos:**
    1. Acompanhamento real da safra `2025-01-01` e testes A/B das campanhas de retenção por faixa de risco.
    2. Redução de dimensionalidade removendo variáveis redundantes ($|r| \ge 0,80$).
    3. Explorar **Análise de Sobrevivência** para prever *quando* o cliente evade, complementando a classificação.
* **Fala:** Encerramento objetivo reforçando o valor prático da solução e abrindo para perguntas.
