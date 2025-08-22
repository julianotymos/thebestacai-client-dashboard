import streamlit as st
import pandas as pd
from get_bigquery_client import get_bigquery_client

@st.cache_data(ttl=600, show_spinner=False)
def read_customer_summary():
    """
    Retorna a quantidade de clientes por tabela e intersecções entre elas.
    """
    client = get_bigquery_client()

    query = """
    SELECT 
        COUNT(1) AS TOTAL_CLIENTE, 
        SUM(CASE WHEN CUSTOMER_ID_ORIGINAL IS NOT NULL THEN 1 ELSE 0 END) AS CLIENTES_IFOOD,
        SUM(CASE WHEN DOCUMENT_NUMBER_CTB IS NOT NULL THEN 1 ELSE 0 END) AS CLIENTES_LOJA,
        SUM(CASE WHEN C_UID_ORIGINAL IS NOT NULL THEN 1 ELSE 0 END) AS CLIENTES_99FOOD,
        
        SUM(CASE WHEN C_UID_ORIGINAL IS NOT NULL AND DOCUMENT_NUMBER_CTB IS NOT NULL THEN 1 ELSE 0 END) AS CLIENTES_LOJA_99FOOD,
        SUM(CASE WHEN CUSTOMER_ID_ORIGINAL IS NOT NULL AND DOCUMENT_NUMBER_CTB IS NOT NULL THEN 1 ELSE 0 END) AS CLIENTES_LOJA_IFOOD,
        SUM(CASE WHEN C_UID_ORIGINAL IS NOT NULL AND CUSTOMER_ID_ORIGINAL IS NOT NULL THEN 1 ELSE 0 END) AS CLIENTES_IFOOD_99FOOD,
        
        SUM(CASE WHEN DOCUMENT_NUMBER_CTB IS NOT NULL AND C_UID_ORIGINAL IS NOT NULL AND CUSTOMER_ID_ORIGINAL IS NOT NULL THEN 1 ELSE 0 END) AS CLIENTES_LOJA_IFOOD_99FOOD
    FROM (
        SELECT
            CONCAT(
              COALESCE(C.ID, ''), 
              COALESCE(C9.C_UID, ''), 
              COALESCE(CTB.DOCUMENT_NUMBER, '')
            ) AS ID, 
            COALESCE(C.ID, C9.C_UID) AS CUSTOMER_ID,
            COALESCE(C.DOCUMENT_NUMBER, CTB.DOCUMENT_NUMBER) AS DOCUMENT_NUMBER,
            COALESCE(CTB.PHONE_NUMBER, C9.PHONE_NUMBER) AS PHONE_NUMBER,
            C.ID AS CUSTOMER_ID_ORIGINAL,
            C.DOCUMENT_NUMBER AS DOCUMENT_NUMBER_C,
            CTB.DOCUMENT_NUMBER AS DOCUMENT_NUMBER_CTB,
            CTB.PHONE_NUMBER AS PHONE_NUMBER_CTB,
            C9.PHONE_NUMBER AS PHONE_NUMBER_C9,
            C9.C_UID AS C_UID_ORIGINAL
        FROM CUSTOMER C
        FULL OUTER JOIN CUSTOMER_THE_BEST CTB 
            ON C.DOCUMENT_NUMBER = CTB.DOCUMENT_NUMBER
        FULL OUTER JOIN CUSTOMER_99_FOOD C9 
            ON CTB.PHONE_NUMBER = C9.PHONE_NUMBER
    ) AS CU;
    """

    try:
        query_job = client.query(query)
        df = query_job.to_dataframe()
        
        return df
    except Exception as e:
        st.error(f"Erro ao buscar resumo de clientes: {e}")
        return pd.DataFrame()

