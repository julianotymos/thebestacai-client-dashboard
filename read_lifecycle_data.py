import streamlit as st
import pandas as pd
from get_bigquery_client import get_bigquery_client

@st.cache_data(ttl=3600, show_spinner="Calculando ciclo de vida dos clientes...")
def read_lifecycle_data(sales_channel=None):
    client = get_bigquery_client()

    if sales_channel == "iFood":
        channel_filter = "SELECT CU.ID, CAST(OT.CREATED_AT AS DATE) AS DATA_TRANSACAO FROM `DELIVERY.ORDERS_TABLE` OT INNER JOIN CUSTOMER_UNION CU ON CU.CUSTOMER_ID_ORIGINAL = OT.CUSTOMER_ID"
    elif sales_channel == "99food":
        channel_filter = "SELECT CU.ID, CAST(OT.CREATED_AT AS DATE) AS DATA_TRANSACAO FROM `DELIVERY.ORDERS_TABLE` OT INNER JOIN CUSTOMER_UNION CU ON CU.C_UID_ORIGINAL = OT.C_UID"
    elif sales_channel == "Loja":
        channel_filter = "SELECT CU.ID, CAST(SC.CREATED_AT AS DATE) AS DATA_TRANSACAO FROM `DELIVERY.SALES_CLUB` SC INNER JOIN CUSTOMER_UNION CU ON CU.DOCUMENT_NUMBER_CTB = SC.CLIENT_CPF"
    else:
        channel_filter = """
        SELECT CU.ID, CAST(OT.CREATED_AT AS DATE) AS DATA_TRANSACAO FROM `DELIVERY.ORDERS_TABLE` OT INNER JOIN CUSTOMER_UNION CU ON CU.CUSTOMER_ID_ORIGINAL = OT.CUSTOMER_ID
        UNION ALL
        SELECT CU.ID, CAST(OT.CREATED_AT AS DATE) AS DATA_TRANSACAO FROM `DELIVERY.ORDERS_TABLE` OT INNER JOIN CUSTOMER_UNION CU ON CU.C_UID_ORIGINAL = OT.C_UID
        UNION ALL
        SELECT CU.ID, CAST(SC.CREATED_AT AS DATE) AS DATA_TRANSACAO FROM `DELIVERY.SALES_CLUB` SC INNER JOIN CUSTOMER_UNION CU ON CU.DOCUMENT_NUMBER_CTB = SC.CLIENT_CPF
        """

    query = f"""
    WITH CUSTOMER_UNION AS (
        SELECT
          CONCAT(
            COALESCE(C.ID, ''),
            COALESCE(C9.C_UID, ''),
            COALESCE(CTB.DOCUMENT_NUMBER, '')
          ) AS ID,
          C.ID AS CUSTOMER_ID_ORIGINAL,
          C9.C_UID AS C_UID_ORIGINAL,
          CTB.DOCUMENT_NUMBER AS DOCUMENT_NUMBER_CTB
        FROM `DELIVERY.CUSTOMER` C
        FULL OUTER JOIN `DELIVERY.CUSTOMER_THE_BEST` CTB ON C.DOCUMENT_NUMBER = CTB.DOCUMENT_NUMBER
        FULL OUTER JOIN `DELIVERY.CUSTOMER_99_FOOD` C9 ON CTB.PHONE_NUMBER = C9.PHONE_NUMBER
    ),
    ALL_TRANSACTIONS AS (
        {channel_filter}
    ),
    -- Meses de compra únicos por cliente
    CUSTOMER_MONTHLY AS (
        SELECT DISTINCT ID, DATE_TRUNC(DATA_TRANSACAO, MONTH) AS PURCHASE_MONTH
        FROM ALL_TRANSACTIONS
    ),
    -- Primeira compra de cada cliente
    FIRST_PURCHASE AS (
        SELECT ID, MIN(DATE_TRUNC(DATA_TRANSACAO, MONTH)) AS FIRST_MONTH
        FROM ALL_TRANSACTIONS
        GROUP BY ID
    ),
    -- Janela de análise: últimos 12 meses completos
    ANALYSIS_MONTHS AS (
        SELECT month AS ANALYSIS_MONTH
        FROM UNNEST(GENERATE_DATE_ARRAY(
            DATE '2025-01-01',
            DATE_SUB(DATE_TRUNC(CURRENT_DATE(), MONTH), INTERVAL 1 MONTH),
            INTERVAL 1 MONTH
        )) AS month
    ),
    -- Para cada cliente x mês de análise: última compra até aquele mês
    CUSTOMER_STATUS AS (
        SELECT
            AM.ANALYSIS_MONTH,
            FP.ID,
            FP.FIRST_MONTH,
            MAX(CM.PURCHASE_MONTH) AS LAST_PURCHASE_MONTH
        FROM ANALYSIS_MONTHS AM
        CROSS JOIN FIRST_PURCHASE FP
        LEFT JOIN CUSTOMER_MONTHLY CM
            ON CM.ID = FP.ID
            AND CM.PURCHASE_MONTH <= AM.ANALYSIS_MONTH
        -- 3 meses antes de Jan/25 para popular corretamente os grupos do primeiro mês
        WHERE FP.FIRST_MONTH >= DATE '2024-10-01'
          AND FP.FIRST_MONTH <= AM.ANALYSIS_MONTH
        GROUP BY 1, 2, 3
    )
    SELECT
        ANALYSIS_MONTH,
        COUNTIF(FIRST_MONTH = ANALYSIS_MONTH)                                                          AS NOVOS_CLIENTES,
        COUNTIF(LAST_PURCHASE_MONTH = ANALYSIS_MONTH AND FIRST_MONTH < ANALYSIS_MONTH)                 AS RETORNOU_MENOS_1M,
        COUNTIF(LAST_PURCHASE_MONTH = DATE_SUB(ANALYSIS_MONTH, INTERVAL 1 MONTH))                      AS ENTRE_1_2M,
        COUNTIF(LAST_PURCHASE_MONTH = DATE_SUB(ANALYSIS_MONTH, INTERVAL 2 MONTH))                      AS ENTRE_2_3M,
        COUNTIF(LAST_PURCHASE_MONTH = DATE_SUB(ANALYSIS_MONTH, INTERVAL 3 MONTH))                      AS SAIU
    FROM CUSTOMER_STATUS
    GROUP BY 1
    ORDER BY 1 DESC
    """

    try:
        df = client.query(query).to_dataframe()
        if df.empty:
            return pd.DataFrame()

        df['ANALYSIS_MONTH'] = pd.to_datetime(df['ANALYSIS_MONTH'])
        df['MES_LABEL'] = df['ANALYSIS_MONTH'].dt.strftime('%b/%y')
        return df
    except Exception as e:
        st.error(f"Erro ao calcular ciclo de vida: {e}")
        return pd.DataFrame()
