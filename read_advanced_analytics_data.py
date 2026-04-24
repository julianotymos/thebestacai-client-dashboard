import streamlit as st
import pandas as pd
from get_bigquery_client import get_bigquery_client

def calculate_segments(df):
    """Aplica a lógica de segmentação RFM no DataFrame."""
    if len(df) < 10: 
        df['SEGMENTO'] = "Iniciante"
        return df
        
    df['R_Score'] = pd.qcut(df['RECENCY'], 4, labels=[4, 3, 2, 1])
    df['F_Score'] = pd.qcut(df['FREQUENCY'].rank(method='first'), 4, labels=[1, 2, 3, 4])
    df['M_Score'] = pd.qcut(df['MONETARY'], 4, labels=[1, 2, 3, 4])
    df['RFM_SCORE'] = df['R_Score'].astype(int) + df['F_Score'].astype(int) + df['M_Score'].astype(int)
    
    def label_segment(s):
        if s >= 10: return "🏆 Campeões (VIP)"
        if s >= 8: return "📈 Clientes Fiéis"
        if s >= 6: return "⚡ Potenciais"
        return "💤 Em Risco/Perdidos"
    
    df['SEGMENTO'] = df['RFM_SCORE'].apply(label_segment)
    return df

@st.cache_data(ttl=3600, show_spinner="Calculando métricas avançadas...")
def read_advanced_analytics_data(sales_channel=None):
    client = get_bigquery_client()

    if sales_channel == "iFood":
        channel_filter = "SELECT CU.ID, CU.NAME, CU.PHONE_NUMBER, CAST(OT.CREATED_AT AS DATE) AS DATA_TRANSACAO, OT.TOTAL_BAG_DETAIL AS TOTAL, 'iFood' as CHANNEL FROM CUSTOMER_UNION CU INNER JOIN `DELIVERY.ORDERS_TABLE` OT ON CU.CUSTOMER_ID_ORIGINAL = OT.CUSTOMER_ID"
    elif sales_channel == "99food":
        channel_filter = "SELECT CU.ID, CU.NAME, CU.PHONE_NUMBER, CAST(OT.CREATED_AT AS DATE) AS DATA_TRANSACAO, OT.TOTAL_BAG_DETAIL AS TOTAL, '99food' as CHANNEL FROM CUSTOMER_UNION CU INNER JOIN `DELIVERY.ORDERS_TABLE` OT ON CU.C_UID_ORIGINAL = OT.C_UID"
    elif sales_channel == "Loja":
        channel_filter = "SELECT CU.ID, CU.NAME, CU.PHONE_NUMBER, CAST(SC.CREATED_AT AS DATE) AS DATA_TRANSACAO, SC.TOTAL AS TOTAL, 'Loja' as CHANNEL FROM CUSTOMER_UNION CU INNER JOIN `DELIVERY.SALES_CLUB` SC ON CU.DOCUMENT_NUMBER_CTB = SC.CLIENT_CPF"
    else:
        channel_filter = """
        SELECT CU.ID, CU.NAME, CU.PHONE_NUMBER, CAST(OT.CREATED_AT AS DATE) AS DATA_TRANSACAO, OT.TOTAL_BAG_DETAIL AS TOTAL, 'iFood' as CHANNEL FROM CUSTOMER_UNION CU INNER JOIN `DELIVERY.ORDERS_TABLE` OT ON CU.CUSTOMER_ID_ORIGINAL = OT.CUSTOMER_ID
        UNION ALL
        SELECT CU.ID, CU.NAME, CU.PHONE_NUMBER, CAST(OT.CREATED_AT AS DATE) AS DATA_TRANSACAO, OT.TOTAL_BAG_DETAIL AS TOTAL, '99food' as CHANNEL FROM CUSTOMER_UNION CU INNER JOIN `DELIVERY.ORDERS_TABLE` OT ON CU.C_UID_ORIGINAL = OT.C_UID
        UNION ALL
        SELECT CU.ID, CU.NAME, CU.PHONE_NUMBER, CAST(SC.CREATED_AT AS DATE) AS DATA_TRANSACAO, SC.TOTAL AS TOTAL, 'Loja' as CHANNEL FROM CUSTOMER_UNION CU INNER JOIN `DELIVERY.SALES_CLUB` SC ON CU.DOCUMENT_NUMBER_CTB = SC.CLIENT_CPF
        """

    query = f"""
    WITH CUSTOMER_UNION AS (
        SELECT
          CONCAT(COALESCE(C.ID, ''), COALESCE(C9.C_UID, ''), COALESCE(CTB.DOCUMENT_NUMBER, '')) AS ID,
          COALESCE(C9.FIRST_NAME, C.FIRST_NAME, CTB.FIRST_NAME, '') || ' ' || COALESCE(C9.LAST_NAME, C.LAST_NAME, CTB.LAST_NAME, '') AS NAME,
          COALESCE(CTB.PHONE_NUMBER, C9.PHONE_NUMBER, '') AS PHONE_NUMBER,
          C.ID AS CUSTOMER_ID_ORIGINAL,
          C9.C_UID AS C_UID_ORIGINAL,
          CTB.DOCUMENT_NUMBER AS DOCUMENT_NUMBER_CTB
        FROM `DELIVERY.CUSTOMER` C
        FULL OUTER JOIN `DELIVERY.CUSTOMER_THE_BEST` CTB ON C.DOCUMENT_NUMBER = CTB.DOCUMENT_NUMBER
        FULL OUTER JOIN `DELIVERY.CUSTOMER_99_FOOD` C9 ON CTB.PHONE_NUMBER = C9.PHONE_NUMBER
    ),
    TRANSACTIONS AS ({channel_filter}),
    CALCULATE_DIFFS AS (
        SELECT 
            ID, NAME, PHONE_NUMBER, TOTAL, DATA_TRANSACAO, CHANNEL,
            DATE_DIFF(DATA_TRANSACAO, LAG(DATA_TRANSACAO) OVER (PARTITION BY ID ORDER BY DATA_TRANSACAO), DAY) as diff
        FROM TRANSACTIONS
    ),
    AGGREGATED AS (
        SELECT 
            ID, NAME, MAX(PHONE_NUMBER) as PHONE_NUMBER,
            SUM(TOTAL) as MONETARY,
            COUNT(1) as FREQUENCY,
            MIN(DATA_TRANSACAO) as FIRST_PURCHASE,
            MAX(DATA_TRANSACAO) as LAST_PURCHASE,
            DATE_DIFF(CURRENT_DATE(), MAX(DATA_TRANSACAO), DAY) as RECENCY,
            AVG(diff) as AVG_CYCLE,
            STRING_AGG(DISTINCT CHANNEL, '/' ORDER BY CHANNEL) AS SALES_CHANNEL
        FROM CALCULATE_DIFFS
        GROUP BY ID, NAME
    )
    SELECT * FROM AGGREGATED
    """
    
    try:
        df = client.query(query).to_dataframe()
        if not df.empty:
            df = calculate_segments(df)
        return df
    except Exception as e:
        st.error(f"Erro ao carregar dados analíticos: {e}")
        return pd.DataFrame()
