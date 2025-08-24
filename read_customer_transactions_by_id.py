import streamlit as st
import pandas as pd
from get_bigquery_client import get_bigquery_client

@st.cache_data(ttl=600, show_spinner=False)
def read_customer_transactions_by_id(
    customer_id_concat: str
):
    """
    Retorna todas as transações de um cliente dado o ID concatenado,
    separadas por canal de venda.
    """

    client = get_bigquery_client()

    query = f"""
    WITH
  CUSTOMER_UNION AS (
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
    SELECT
      CU.ID,
      'iFood' AS CANAL,
      OT.TOTAL_BAG_DETAIL AS TOTAL,
      OT.CREATED_AT AS DATA_TRANSACAO
    FROM
      `DELIVERY.ORDERS_TABLE` OT
      INNER JOIN CUSTOMER_UNION CU ON CU.CUSTOMER_ID_ORIGINAL = OT.CUSTOMER_ID
    WHERE
      CU.ID = '{customer_id_concat}'

    UNION ALL

    SELECT
      CU.ID,
      '99food' AS CANAL,
      OT.TOTAL_BAG_DETAIL AS TOTAL,
      OT.CREATED_AT AS DATA_TRANSACAO
    FROM
      `DELIVERY.ORDERS_TABLE` OT
      INNER JOIN CUSTOMER_UNION CU ON CU.C_UID_ORIGINAL = OT.C_UID
    WHERE
      CU.ID = '{customer_id_concat}'

    UNION ALL

    SELECT
      CU.ID,
      'Loja' AS CANAL,
      SC.TOTAL AS TOTAL,
      SC.CREATED_AT AS DATA_TRANSACAO
    FROM
      `DELIVERY.SALES_CLUB` SC
      INNER JOIN CUSTOMER_UNION CU ON CU.DOCUMENT_NUMBER_CTB = SC.CLIENT_CPF
    WHERE
      CU.ID = '{customer_id_concat}'
  )

SELECT
  ID,
  CANAL,
    FORMAT_TIMESTAMP('%d/%m/%Y %H:%M', 'America/Sao_Paulo') AS DATA_VENDA ,

  TOTAL
FROM ALL_TRANSACTIONS
ORDER BY
  DATA_TRANSACAO DESC
    """

    try:
        query_job = client.query(query)
        df = query_job.to_dataframe()
        df.rename(columns={
            "ID": "Id",
            "CANAL": "Canal",
            "DATA_VENDA": "Data Venda",
            "TOTAL": "Total"
        }, inplace=True)
        df_display = df.drop(columns=['Id'])

        return df_display
    except Exception as e:
        st.error(f"Erro ao buscar transações do cliente: {e}")
        return pd.DataFrame()

#df = read_customer_transactions_by_id(customer_id_concat= '10040126838')
#print(df)