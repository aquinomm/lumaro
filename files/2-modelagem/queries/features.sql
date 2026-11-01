select 
    '{date}' as dt_ref,
    vendas.CLI_CPF, 
    t3.idade_base,
    1 + cast(t3.idade_base/30 as integer) as idade_base_mes,
    sum(vendas.FATUR_VENDA) as faturamento,
    count(distinct vendas.COD_ATEND) as qtde_visitas,
    sum(vendas.FATUR_VENDA)/count(distinct vendas.COD_ATEND) as ticket_medio,
    count(distinct vendas.COD_ATEND)/min(1+ cast(t3.idade_base/30 as integer),6) as avg_compras_mes,

    count(distinct strftime('%Y-%m', vendas.DATA_ATEND)) as qtd_mes_ativacao,
    cast(count(distinct strftime('%Y-%m',vendas.DATA_ATEND)) as float) / min(1+ cast(t3.idade_base/30 as integer), 6) as prop_ativacao,

    count(vendas.SKU) as qtde_produto,
    count(distinct vendas.SKU) as qtde_produto_dst,

    min(vendas.DATA_ATEND) as prim_compra,
    cast(julianday('{date}')- julianday(max(vendas.DATA_ATEND)) as integer) as qtd_dias_ultima_compra,

    -- Filial: Frequência de Visitas (Rua vs Shopping)
    count(distinct case when vendas.FILIAL = 'RUA' then vendas.COD_ATEND end) as qtde_visitas_rua,
    count(distinct case when vendas.FILIAL = 'SHOPPING' then vendas.COD_ATEND end) as qtde_visitas_shopping,
    1.0 * count(distinct case when vendas.FILIAL = 'RUA' then vendas.COD_ATEND end) / count(distinct vendas.COD_ATEND) as prop_visitas_rua,
    1.0 * count(distinct case when vendas.FILIAL = 'SHOPPING' then vendas.COD_ATEND end) / count(distinct vendas.COD_ATEND) as prop_visitas_shopping,
    -- Filial: Faturamento e Proporção de Gasto
    sum(case when vendas.FILIAL = 'RUA' then vendas.FATUR_VENDA else 0 end) as fatur_rua,
    sum(case when vendas.FILIAL = 'SHOPPING' then vendas.FATUR_VENDA else 0 end) as fatur_shopping,
    1.0 * sum(case when vendas.FILIAL = 'RUA' then vendas.FATUR_VENDA else 0 end) / sum(vendas.FATUR_VENDA) as prop_fatur_rua,
    1.0 * sum(case when vendas.FILIAL = 'SHOPPING' then vendas.FATUR_VENDA else 0 end) / sum(vendas.FATUR_VENDA) as prop_fatur_shopping,
    -- Categorias: Diversidade
    count(distinct produto.CATEGORIA) as qtde_categorias_dst,
    -- Categorias: Faturamento das Top Categorias (>80% da receita da rede)
    sum(case when produto.CATEGORIA = 'Castanhas & Oleaginosas' then vendas.FATUR_VENDA else 0 end) as fatur_castanhas,
    sum(case when produto.CATEGORIA = 'Bacalhau & Pescados' then vendas.FATUR_VENDA else 0 end) as fatur_bacalhau,
    sum(case when produto.CATEGORIA = 'Temperos & Condimentos' then vendas.FATUR_VENDA else 0 end) as fatur_temperos,
    sum(case when produto.CATEGORIA = 'Frutas' then vendas.FATUR_VENDA else 0 end) as fatur_frutas,
    sum(case when produto.CATEGORIA = 'Mixes da Casa' then vendas.FATUR_VENDA else 0 end) as fatur_mixes,
    sum(case when produto.CATEGORIA = 'Grãos' then vendas.FATUR_VENDA else 0 end) as fatur_graos,
    -- Categorias: Share de Gasto (% do faturamento do cliente)
    1.0 * sum(case when produto.CATEGORIA = 'Castanhas & Oleaginosas' then vendas.FATUR_VENDA else 0 end) / sum(vendas.FATUR_VENDA) as prop_fatur_castanhas,
    1.0 * sum(case when produto.CATEGORIA = 'Bacalhau & Pescados' then vendas.FATUR_VENDA else 0 end) / sum(vendas.FATUR_VENDA) as prop_fatur_bacalhau,
    1.0 * sum(case when produto.CATEGORIA = 'Temperos & Condimentos' then vendas.FATUR_VENDA else 0 end) / sum(vendas.FATUR_VENDA) as prop_fatur_temperos,
    1.0 * sum(case when produto.CATEGORIA = 'Frutas' then vendas.FATUR_VENDA else 0 end) / sum(vendas.FATUR_VENDA) as prop_fatur_frutas,
    1.0 * sum(case when produto.CATEGORIA = 'Mixes da Casa' then vendas.FATUR_VENDA else 0 end) / sum(vendas.FATUR_VENDA) as prop_fatur_mixes,
    1.0 * sum(case when produto.CATEGORIA = 'Grãos' then vendas.FATUR_VENDA else 0 end) / sum(vendas.FATUR_VENDA) as prop_fatur_graos


    from vendas
    left join produto on produto.SKU = vendas.SKU

    left join(
    select vendas.CLI_CPF, max(julianday('{date}') - julianday(vendas.DATA_ATEND)) as idade_base 
    from vendas
    left join produto on produto.SKU = vendas.SKU
    where vendas.DATA_ATEND < '{date}' -- pegar todo o histório
    group by vendas.CLI_CPF
    ) as t3 on vendas.CLI_CPF = t3.CLI_CPF

where vendas.DATA_ATEND >= date('{date}', '-6 months') and vendas.DATA_ATEND < '{date}'
group by vendas.CLI_CPF;