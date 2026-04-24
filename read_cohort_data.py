import streamlit as st
import pandas as pd
from get_bigquery_client import get_bigquery_client

@st.cache_data(ttl=3600, show_spinner="Calculando análise de coorte...")
def read_cohort_data(sales_channel=None):
    """
    Busca dados de transações filtrados por canal e calcula a matriz de coorte.
    """
    client = get_bigquery_client()

    # Base da query com os canais
    if sales_channel == "iFood":
        channel_filter = "SELECT CU.ID, CAST(OT.CREATED_AT AS DATE) AS DATA_TRANSACAO FROM `DELIVERY.ORDERS_TABLE` OT INNER JOIN CUSTOMER_UNION CU ON CU.CUSTOMER_ID_ORIGINAL = OT.CUSTOMER_ID"
    elif sales_channel == "99food":
        channel_filter = "SELECT CU.ID, CAST(OT.CREATED_AT AS DATE) AS DATA_TRANSACAO FROM `DELIVERY.ORDERS_TABLE` OT INNER JOIN CUSTOMER_UNION CU ON CU.C_UID_ORIGINAL = OT.C_UID"
    elif sales_channel == "Loja":
        channel_filter = "SELECT CU.ID, CAST(SC.CREATED_AT AS DATE) AS DATA_TRANSACAO FROM `DELIVERY.SALES_CLUB` SC INNER JOIN CUSTOMER_UNION CU ON CU.DOCUMENT_NUMBER_CTB = SC.CLIENT_CPF"
    else:
        # Unificado (Todos os canais)
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
        SELECT ID, MIN(DATA_TRANSACAO) as FIRST_TRANSACTION_DATE
        FROM ALL_TRANSACTIONS
        GROUP BY 1
    )
    SELECT 
        T.ID,
        DATE_TRUNC(FP.FIRST_TRANSACTION_DATE, MONTH) as COHORT_MONTH,
        DATE_TRUNC(T.DATA_TRANSACAO, MONTH) as TRANSACTION_MONTH
    FROM ALL_TRANSACTIONS T
    JOIN FIRST_PURCHASE FP ON T.ID = FP.ID
    WHERE FP.FIRST_TRANSACTION_DATE >= DATE_SUB(CURRENT_DATE(), INTERVAL 12 MONTH)
    """

    try:
        query_job = client.query(query)
        df = query_job.to_dataframe()
        
        if df.empty:
            return pd.DataFrame(), pd.DataFrame()

        df['COHORT_MONTH'] = pd.to_datetime(df['COHORT_MONTH'])
        df['TRANSACTION_MONTH'] = pd.to_datetime(df['TRANSACTION_MONTH'])
        
        def get_date_int(df, column):
            year = df[column].dt.year
            month = df[column].dt.month
            return year, month

        cohort_year, cohort_month = get_date_int(df, 'COHORT_MONTH')
        trans_year, trans_month = get_date_int(df, 'TRANSACTION_MONTH')

        year_diff = trans_year - cohort_year
        month_diff = trans_month - cohort_month

        df['cohort_index'] = year_diff * 12 + month_diff + 1
        
        cohort_data = df.groupby(['COHORT_MONTH', 'cohort_index'])['ID'].nunique().reset_index()
        cohort_matrix = cohort_data.pivot(index='COHORT_MONTH', columns='cohort_index', values='ID')
        
        cohort_size = cohort_matrix.iloc[:, 0]
        retention = cohort_matrix.divide(cohort_size, axis=0)
        retention.index = retention.index.strftime('%Y-%m')
        
        return retention, cohort_matrix
    except Exception as e:
        st.error(f"Erro ao calcular coorte: {e}")
        return pd.DataFrame(), pd.DataFrame()
