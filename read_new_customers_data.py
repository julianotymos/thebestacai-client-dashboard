import streamlit as st
import pandas as pd
from get_bigquery_client import get_bigquery_client

@st.cache_data(ttl=3600, show_spinner="Calculando novos clientes por mês...")
def read_new_customers_data(sales_channel=None):
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
        FROM
          `DELIVERY.CUSTOMER` C
          FULL OUTER JOIN `DELIVERY.CUSTOMER_THE_BEST` CTB ON C.DOCUMENT_NUMBER = CTB.DOCUMENT_NUMBER
          FULL OUTER JOIN `DELIVERY.CUSTOMER_99_FOOD` C9 ON CTB.PHONE_NUMBER = C9.PHONE_NUMBER
    ),
    ALL_TRANSACTIONS AS (
        {channel_filter}
    ),
    FIRST_PURCHASE AS (
        SELECT ID, MIN(DATA_TRANSACAO) AS FIRST_DATE
        FROM ALL_TRANSACTIONS
        GROUP BY ID
    ),
    NEW_PER_MONTH AS (
        SELECT
            DATE_TRUNC(FIRST_DATE, MONTH) AS MES,
            COUNT(DISTINCT ID) AS NOVOS_CLIENTES
        FROM FIRST_PURCHASE
        WHERE FIRST_DATE >= DATE_SUB(CURRENT_DATE(), INTERVAL 13 MONTH)
          AND FIRST_DATE < DATE_TRUNC(CURRENT_DATE(), MONTH)
        GROUP BY 1
    ),
    TOTAL_PER_MONTH AS (
        SELECT
            DATE_TRUNC(DATA_TRANSACAO, MONTH) AS MES,
            COUNT(DISTINCT ID) AS TOTAL_CLIENTES
        FROM ALL_TRANSACTIONS
        WHERE DATA_TRANSACAO >= DATE_SUB(CURRENT_DATE(), INTERVAL 13 MONTH)
          AND DATA_TRANSACAO < DATE_TRUNC(CURRENT_DATE(), MONTH)
        GROUP BY 1
    )
    SELECT
        N.MES,
        N.NOVOS_CLIENTES,
        T.TOTAL_CLIENTES,
        ROUND(100.0 * N.NOVOS_CLIENTES / T.TOTAL_CLIENTES, 1) AS PCT_NOVOS
    FROM NEW_PER_MONTH N
    JOIN TOTAL_PER_MONTH T ON N.MES = T.MES
    ORDER BY N.MES
    """

    try:
        df = client.query(query).to_dataframe()
        if df.empty:
            return pd.DataFrame()

        df['MES'] = pd.to_datetime(df['MES'])
        df = df.sort_values('MES').reset_index(drop=True)
        df['MES_LABEL'] = df['MES'].dt.strftime('%b/%y')
        df['VARIACAO_PCT'] = df['NOVOS_CLIENTES'].pct_change() * 100

        return df
    except Exception as e:
        st.error(f"Erro ao buscar novos clientes: {e}")
        return pd.DataFrame()
