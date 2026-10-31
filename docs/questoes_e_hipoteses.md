# Churn por inatividade na VAI Store: questões de pesquisa e hipóteses

## 1. Contexto e problema

A VAI Store é uma rede de varejo alimentar saudável (grãos, castanhas, frutas
secas, temperos, bacalhau etc.). A base cedida pela Visagio cobre **todas as
vendas de 2024** (02/01 a 31/12) de **59 SKUs** em **duas lojas** (rua e
shopping), com 556.198 itens vendidos, 302.228 atendimentos e 102.943 clientes
identificados por um código anonimizado.

A relação com o cliente é **não contratual**: ninguém cancela uma assinatura, o
cliente simplesmente para de comprar. O churn, portanto, **não é observado, é
definido**: considera-se perdido quem fica τ dias sem comprar. A escolha de τ é
deliberada e muda tudo o que vem depois (taxa de churn, rótulos do modelo,
quem recebe ação de retenção). Por isso o projeto trata o próprio critério como
objeto de estudo:

1. fundamentar τ na dinâmica de recompra observada nos dados;
2. caracterizar os comportamentos que antecedem a inatividade;
3. prever, numa data de corte, quais clientes ativos ficarão inativos;
4. medir o quanto as conclusões dependem de τ.

## 2. Definições operacionais

| Termo | Definição |
|---|---|
| Visita | Dia com compra de um cliente (cliente-dia). Atendimentos no mesmo dia contam como uma visita. |
| Data de corte (t₀) | Momento em que o modelo seria usado. Snapshots mensais de 01/05 a 01/10/2024. |
| Base ativa em t₀ | Clientes com ao menos uma visita nos τ dias anteriores a t₀. |
| **Churn por inatividade** | Cliente da base ativa que **não faz nenhuma visita nos τ dias seguintes** a t₀. Valor central: **τ = 90 dias**; sensibilidade: 60 e 120. |
| Janela de observação | Atributos de comportamento: 120 dias antes de t₀ (mesmo significado em todo corte). Atributos de histórico: desde a primeira visita observada (a base começa em 02/01/2024, então a antiguidade é truncada à esquerda). |

Nenhum atributo usa informação posterior a t₀, e a avaliação é **fora do
tempo**: o modelo é treinado em cortes cujo rótulo já estaria disponível na data
em que seria aplicado (Kaufman et al., 2012; Gattermann-Itschert & Thonemann, 2021).

Ressalva: a base é um recorte de 59 dos 6.500 produtos da loja, então a
inatividade é medida nesse recorte — um cliente pode seguir comprando outros
itens e aparecer como inativo. Compras sem identificação do cliente não
aparecem na base.

## 3. Questões de pesquisa

- **QP1 — Critério.** Qual janela de inatividade τ é defensável nesta base, e qual
  o custo de cada escolha? (clientes rotulados como perdidos que voltam × atraso
  para detectar o churn × prevalência)
- **QP2 — Caracterização.** Que padrões de recência, frequência, ritmo, valor,
  mix de produtos, loja e sazonalidade distinguem quem fica inativo de quem
  continua comprando?
- **QP3 — Predição.** Com que qualidade é possível antecipar a inatividade? Modelos
  de aprendizado de máquina superam (a) a heurística de recência usada na prática
  e (b) o modelo probabilístico BG/NBD?
- **QP4 — Robustez.** Taxa de churn, desempenho e fatores explicativos mudam com τ
  e com a época do ano (sazonalidade)?
- **QP5 — Priorização.** Quanto do faturamento da base ativa está nos clientes de
  maior risco, e como ordenar uma ação de retenção?

## 4. Hipóteses

### Bloco A — Critério de inatividade (QP1, QP4)

| # | Hipótese | Fundamentação | Como testar |
|---|---|---|---|
| **H1** | Não há um corte "natural": a probabilidade de o cliente voltar cai de forma contínua com o tempo de inatividade, então τ é um compromisso entre falsos churns e atraso de detecção, não uma propriedade dos dados. | Clemente-Císcar et al. (2014); Wübben & von Wangenheim (2008) | Curva de Kaplan–Meier do intervalo entre visitas (com censura) e probabilidade condicional de retorno P(volta em 90 d \| inativo há d dias); tabela de trade-off para τ ∈ {30, …, 180}. |
| **H2** | A taxa de churn é muito sensível a τ, mas a **ordenação de risco** é robusta: modelos treinados com τ = 60, 90 e 120 apontam praticamente os mesmos clientes como prioritários. | Ascarza et al. (2018) | Prevalência, AUC e correlação de Spearman entre os scores dos modelos por τ; sobreposição do decil de maior risco. |

### Bloco B — Comportamento do cliente (QP2)

| # | Hipótese | Fundamentação | Como testar |
|---|---|---|---|
| **H3** | O risco cresce com a recência, e a **recência relativa ao ritmo do próprio cliente** (recência ÷ intervalo médio entre visitas) discrimina melhor que a recência absoluta. | Wübben & von Wangenheim (2008); Platzer & Reutterer (2016) | AUC univariada de `recencia` × `atraso_relativo` entre clientes com ≥ 2 visitas; SHAP. |
| **H4** | Quanto mais visitas e mais longo o relacionamento, menor o risco; clientes de **visita única** concentram o churn (o problema é a segunda compra). | Fader, Hardie & Lee (2005a); Reinartz & Kumar (2000) | Taxa de churn por nº de visitas e por estágio; razões de chance; SHAP. |
| **H5** | Clientes com **intervalos mais regulares** (menor coeficiente de variação) têm menor risco, dada a mesma frequência. | Platzer & Reutterer (2016) | Taxa de churn por quintil de `ipt_cv` estratificada pela frequência (≥ 3 visitas). |
| **H6** | O churn é precedido por **defecção parcial**: queda recente de frequência ou de gasto aumenta o risco. | Buckinx & Van den Poel (2005) | Taxa de churn por `tend_visitas` e `tend_gasto` entre clientes recorrentes; SHAP. |
| **H7** | Clientes que compram **mais categorias** (relação mais ampla) têm menor risco, mesmo controlando a frequência. | Reinartz & Kumar (2003); Kumar, George & Pancras (2008) | Taxa de churn por `n_categorias` dentro de estratos de frequência; regressão logística explicativa. |
| **H8** | Clientes de **ocasião** — cujo gasto se concentra em bacalhau, produto de Páscoa e Natal — ficam mais inativos: parte do churn medido é **sazonal** e não perda real, um viés do critério global. | Evidência da EDA (58% do faturamento de bacalhau ocorre em março e dezembro) | Taxa de churn por `share_bacalhau`; retorno no Natal de quem comprou na Páscoa. |
| **H9** | O **valor monetário** (ticket médio) é fracamente associado ao churn depois de controladas recência e frequência. | Fader, Hardie & Lee (2005b) | Taxa de churn por quintil de ticket dentro de estratos de frequência; coeficiente na logística. |

Variáveis de controle exploradas sem hipótese formal: loja (rua × shopping),
compras com desconto, visitas no fim de semana e mix das demais categorias.

### Bloco C — Predição (QP3, QP5)

| # | Hipótese | Fundamentação | Como testar |
|---|---|---|---|
| **H10** | Modelos de aprendizado de máquina com atributos comportamentais superam a heurística de recência e o BG/NBD em AUC e lift, mas com ganho moderado sobre o BG/NBD. | Tamaddoni, Stakhovych & Ewing (2016); Neslin et al. (2006) | Validação fora do tempo em três cortes; IC 95% por bootstrap pareado das diferenças de AUC. |

## 5. Experimentos semelhantes (para a Introdução)

Sugestão de duas referências principais:

1. **Buckinx & Van den Poel (2005)** — preveem a defecção parcial de clientes
   leais em um varejo de bens de consumo, também não contratual, com variáveis
   transacionais (recência, frequência, valor, intervalo entre compras) e
   comparam regressão logística, redes neurais e random forests. É o
   experimento mais próximo do nosso.
2. **Gattermann-Itschert & Thonemann (2021)** — mostram que treinar com vários
   snapshots no tempo (*multi-slicing*) melhora a previsão de churn; é o desenho
   experimental adotado aqui.

Complementares: Wübben & von Wangenheim (2008) (heurística de hiato × modelos
probabilísticos), Fader, Hardie & Lee (2005a) (BG/NBD), Tamaddoni et al. (2016)
(modelos probabilísticos × aprendizado de máquina) e Miguéis et al. (2012)
(churn parcial no varejo alimentar).

## 6. Referências

- ASCARZA, E. Retention futility: targeting high-risk customers might be ineffective. *Journal of Marketing Research*, v. 55, n. 1, p. 80–98, 2018. DOI: 10.1509/jmr.16.0163.
- ASCARZA, E. et al. In pursuit of enhanced customer retention management: review, key issues, and future directions. *Customer Needs and Solutions*, v. 5, p. 65–81, 2018. DOI: 10.1007/s40547-017-0080-0.
- BALLINGS, M.; VAN DEN POEL, D. Customer event history for churn prediction: how long is long enough? *Expert Systems with Applications*, v. 39, n. 18, p. 13517–13522, 2012. DOI: 10.1016/j.eswa.2012.07.006.
- BUCKINX, W.; VAN DEN POEL, D. Customer base analysis: partial defection of behaviourally loyal clients in a non-contractual FMCG retail setting. *European Journal of Operational Research*, v. 164, n. 1, p. 252–268, 2005. DOI: 10.1016/j.ejor.2003.12.010.
- CLEMENTE-CÍSCAR, M.; SAN MATÍAS, S.; GINER-BOSCH, V. A methodology based on profitability criteria for defining the partial defection of customers in non-contractual settings. *European Journal of Operational Research*, v. 239, n. 1, p. 276–285, 2014. DOI: 10.1016/j.ejor.2014.04.029.
- FADER, P. S.; HARDIE, B. G. S.; LEE, K. L. "Counting your customers" the easy way: an alternative to the Pareto/NBD model. *Marketing Science*, v. 24, n. 2, p. 275–284, 2005a. DOI: 10.1287/mksc.1040.0098.
- FADER, P. S.; HARDIE, B. G. S.; LEE, K. L. RFM and CLV: using iso-value curves for customer base analysis. *Journal of Marketing Research*, v. 42, n. 4, p. 415–430, 2005b. DOI: 10.1509/jmkr.2005.42.4.415.
- GATTERMANN-ITSCHERT, T.; THONEMANN, U. W. How training on multiple time slices improves performance in churn prediction. *European Journal of Operational Research*, v. 295, n. 2, p. 664–674, 2021. DOI: 10.1016/j.ejor.2021.05.035.
- KAPLAN, E. L.; MEIER, P. Nonparametric estimation from incomplete observations. *Journal of the American Statistical Association*, v. 53, n. 282, p. 457–481, 1958. DOI: 10.1080/01621459.1958.10501452.
- KAUFMAN, S. et al. Leakage in data mining: formulation, detection, and avoidance. *ACM Transactions on Knowledge Discovery from Data*, v. 6, n. 4, p. 1–21, 2012. DOI: 10.1145/2382577.2382579.
- KUMAR, V.; GEORGE, M.; PANCRAS, J. Cross-buying in retailing: drivers and consequences. *Journal of Retailing*, v. 84, n. 1, p. 15–27, 2008. DOI: 10.1016/j.jretai.2008.01.007.
- MIGUÉIS, V. L. et al. Modeling partial customer churn: on the value of first product-category purchase sequences. *Expert Systems with Applications*, v. 39, n. 12, p. 11250–11256, 2012. DOI: 10.1016/j.eswa.2012.03.073.
- NESLIN, S. A. et al. Defection detection: measuring and understanding the predictive accuracy of customer churn models. *Journal of Marketing Research*, v. 43, n. 2, p. 204–211, 2006. DOI: 10.1509/jmkr.43.2.204.
- PLATZER, M.; REUTTERER, T. Ticking away the moments: timing regularity helps to better predict customer activity. *Marketing Science*, v. 35, n. 5, p. 779–799, 2016. DOI: 10.1287/mksc.2015.0963.
- REINARTZ, W. J.; KUMAR, V. On the profitability of long-life customers in a noncontractual setting: an empirical investigation and implications for marketing. *Journal of Marketing*, v. 64, n. 4, p. 17–35, 2000. DOI: 10.1509/jmkg.64.4.17.18077.
- REINARTZ, W. J.; KUMAR, V. The impact of customer relationship characteristics on profitable lifetime duration. *Journal of Marketing*, v. 67, n. 1, p. 77–99, 2003. DOI: 10.1509/jmkg.67.1.77.18589.
- TAMADDONI, A.; STAKHOVYCH, S.; EWING, M. Comparing churn prediction techniques and assessing their performance: a contingent perspective. *Journal of Service Research*, v. 19, n. 2, p. 123–141, 2016. DOI: 10.1177/1094670515616376.
- WÜBBEN, M.; VON WANGENHEIM, F. Instant customer base analysis: managerial heuristics often "get it right". *Journal of Marketing*, v. 72, n. 3, p. 82–93, 2008. DOI: 10.1509/jmkg.72.3.082.

Métodos e ferramentas citados nos notebooks: Schmittlein, Morrison & Colombo
(1987, DOI 10.1287/mnsc.33.1.1), Efron (1979, DOI 10.1214/aos/1176344552),
Shmueli (2010, DOI 10.1214/10-STS330), Verbraken, Verbeke & Baesens (2013, DOI
10.1109/TKDE.2012.50), Akiba et al. (2019, Optuna, DOI
10.1145/3292500.3330701), Davidson-Pilon (2019, lifelines, DOI
10.21105/joss.01317), Ke et al. (2017, LightGBM, NeurIPS) e Lundberg & Lee
(2017, SHAP, NeurIPS).
