drop table if exists tb_abt_churn;
create table tb_abt_churn as 
    SELECT 
        t1.*,
        -- Se encontrou pelo menos 1 venda nos 3 meses seguintes, flag = 0, senão 1
        CASE 
            WHEN COUNT(t2.COD_ATEND) > 0 THEN 0 
            ELSE 1
        END AS flag_churn

    FROM tb_book AS t1

    LEFT JOIN vendas AS t2
        ON t1.CLI_CPF = t2.CLI_CPF
        -- Compras a partir da data de corte até 3 meses depois:
        AND t2.DATA_ATEND >= t1.dt_ref
        AND t2.DATA_ATEND < DATE(t1.dt_ref, '+3 months')

    -- Apenas safras cujo target de 3 meses já maturou na base de 2024
    WHERE t1.dt_ref <= '2024-10-01'

    GROUP BY t1.dt_ref, t1.CLI_CPF
    ORDER BY t1.dt_ref;