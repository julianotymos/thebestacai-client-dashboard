import streamlit as st
import pandas as pd
from get_bigquery_client import get_bigquery_client

@st.cache_data(ttl=600, show_spinner=False)
def read_customer_frequency_data(
    page_number=1, 
    rows_per_page=20, 
    sales_channel=None, 
    name=None, 
    phone_number=None, 
    document_number=None
):
    """
    Busca dados de frequência de compra de clientes, com paginação e filtros opcionais.
    """

    client = get_bigquery_client()
    offset = (page_number - 1) * rows_per_page

    # Montando cláusulas de filtro
    filters = []
    if sales_channel:
        filters.append(f"R.SALES_CHANNEL = '{sales_channel}'")
    if name:
        filters.append(f"(CU.FIRST_NAME || ' ' || CU.LAST_NAME) LIKE '%{name}%'")
    if phone_number:
        filters.append(f"CU.PHONE_NUMBER = '{phone_number}'")
    if document_number:
        filters.append(f"CU.DOCUMENT_NUMBER = '{document_number}'")

    where_clause = f"WHERE {' AND '.join(filters)}" if filters else ""

    query = f"""
    WITH CUSTOMER_UNION AS (
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
        C9.C_UID AS C_UID_ORIGINAL,
        COALESCE(C9.FIRST_NAME, C.FIRST_NAME, CTB.FIRST_NAME, '') AS FIRST_NAME,
        COALESCE(C9.LAST_NAME, C.LAST_NAME, CTB.LAST_NAME, '') AS LAST_NAME
      FROM CUSTOMER C
      FULL OUTER JOIN CUSTOMER_THE_BEST CTB 
        ON C.DOCUMENT_NUMBER = CTB.DOCUMENT_NUMBER
      FULL OUTER JOIN CUSTOMER_99_FOOD C9 
        ON CTB.PHONE_NUMBER = C9.PHONE_NUMBER
    ),

    TRANSACOES AS (
      -- iFood
      SELECT 
        CU.ID, DATE(OT.CREATED_AT) AS SALES_DATE, OT.TOTAL_BAG_DETAIL AS TOTAL, 'iFood' AS SALE_CHANNEL
      FROM ORDERS_TABLE OT
      INNER JOIN CUSTOMER_UNION CU ON CU.CUSTOMER_ID_ORIGINAL = OT.CUSTOMER_ID

      UNION ALL

      -- 99Food
      SELECT 
        CU.ID, DATE(OT.CREATED_AT) AS SALES_DATE, OT.TOTAL_BAG_DETAIL AS TOTAL, '99food' AS SALE_CHANNEL
      FROM ORDERS_TABLE OT
      INNER JOIN CUSTOMER_UNION CU ON CU.C_UID_ORIGINAL = OT.C_UID

      UNION ALL

      -- Loja
      SELECT 
        CU.ID, DATE(SC.CREATED_AT) AS SALES_DATE, SC.TOTAL AS TOTAL, 'Loja' AS SALE_CHANNEL
      FROM SALES_CLUB SC
      INNER JOIN CUSTOMER_UNION CU ON CU.DOCUMENT_NUMBER_CTB = SC.CLIENT_CPF
    ),

    COMPRAS AS (
      SELECT
        ID,
        SALES_DATE,
        TOTAL,
        SALE_CHANNEL,
        EXTRACT(DAY FROM (DATE(SALES_DATE) - LAG(DATE(SALES_DATE)) OVER (PARTITION BY ID ORDER BY SALES_DATE))) AS dias_entre_compras
      FROM TRANSACOES
    ),

    RESUMO AS (
      SELECT
        ID,
        COUNT(1) AS QTD_COMPRAS,
        SUM(TOTAL) AS TOTAL_GASTO,
        MIN(SALES_DATE) AS PRIMEIRA,
        MAX(SALES_DATE) AS ULTIMA,
        ROUND(SUM(TOTAL) / COUNT(1), 2) AS TICKET_MEDIO,
        ROUND(AVG(dias_entre_compras), 2) AS MEDIA_FREQUENCIA_COMPRA,
        MAX(dias_entre_compras) AS MAX_DIAS_SEM_RECOMPRA,
        STRING_AGG(DISTINCT SALE_CHANNEL, '/'ORDER BY SALE_CHANNEL ) AS SALES_CHANNEL
      FROM COMPRAS
      GROUP BY ID
    )

    SELECT
      CU.FIRST_NAME || ' ' || CU.LAST_NAME AS NAME,
     FORMAT_TIMESTAMP('%d/%m/%Y', DATE(R.PRIMEIRA))   AS PRIMEIRA_COMPRA,
     FORMAT_TIMESTAMP('%d/%m/%Y', DATE(R.ULTIMA) )  AS ULTIMA_COMPRA,
      R.QTD_COMPRAS AS NUM_COMPRAS,
      R.TOTAL_GASTO,
      R.TICKET_MEDIO,
      CASE WHEN R.QTD_COMPRAS > 1 THEN R.MEDIA_FREQUENCIA_COMPRA ELSE 0 END AS MEDIA_FREQUENCIA_COMPRA,
      CASE WHEN R.QTD_COMPRAS > 1 THEN R.MAX_DIAS_SEM_RECOMPRA ELSE 0 END AS MAX_DIAS_SEM_RECOMPRA,
      R.SALES_CHANNEL,
      CU.DOCUMENT_NUMBER,
      CU.PHONE_NUMBER,
      CU.ID AS ID ,

    FROM CUSTOMER_UNION CU
    INNER JOIN RESUMO R ON R.ID = CU.ID
    {where_clause}
    ORDER BY R.TOTAL_GASTO DESC
    LIMIT {rows_per_page}
    OFFSET {offset}
    """

    try:
        query_job = client.query(query)
        df = query_job.to_dataframe()
        df.rename(columns={
            "NAME": "Cliente",
            "PRIMEIRA_COMPRA": "1ª Compra",
            "ULTIMA_COMPRA": "Última Compra",
            "NUM_COMPRAS": "Nº Compras",
            "TOTAL_GASTO": "Total Gasto",
            "TICKET_MEDIO": "Ticket Médio",
            "MEDIA_FREQUENCIA_COMPRA": "Freq Média (dias)",
            "MAX_DIAS_SEM_RECOMPRA": "Máx Dias s/ Compra",
            "DOCUMENT_NUMBER": "CPF",
            "PHONE_NUMBER": "Telefone",
            "SALES_CHANNEL": "Canal de Venda",
            "ID" : "Id"
        }, inplace=True)
        return df
    except Exception as e:
        st.error(f"Erro ao buscar dados de clientes: {e}")
        return pd.DataFrame()


@st.cache_data(ttl=3600, show_spinner=False)
def read_total_customers_count(sales_channel=None, name=None, phone_number=None, document_number=None):
    """
    Conta total de clientes (com filtros aplicados).
    """
    client = get_bigquery_client()

    filters = []
    if sales_channel:
        filters.append(f"R.SALES_CHANNEL = '{sales_channel}'")
    if name:
        filters.append(f"(CU.FIRST_NAME || ' ' || CU.LAST_NAME) LIKE '%{name}%'")
    if phone_number:
        filters.append(f"CU.PHONE_NUMBER = '{phone_number}'")
    if document_number:
        filters.append(f"CU.DOCUMENT_NUMBER = '{document_number}'")

    where_clause = f"WHERE {' AND '.join(filters)}" if filters else ""

    query = f"""
    WITH CUSTOMER_UNION AS (
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
        C9.C_UID AS C_UID_ORIGINAL,
        COALESCE(C9.FIRST_NAME, C.FIRST_NAME, CTB.FIRST_NAME, '') AS FIRST_NAME,
        COALESCE(C9.LAST_NAME, C.LAST_NAME, CTB.LAST_NAME, '') AS LAST_NAME
      FROM CUSTOMER C
      FULL OUTER JOIN CUSTOMER_THE_BEST CTB ON C.DOCUMENT_NUMBER = CTB.DOCUMENT_NUMBER
      FULL OUTER JOIN CUSTOMER_99_FOOD C9 ON CTB.PHONE_NUMBER = C9.PHONE_NUMBER
    ),

    TRANSACOES AS (
      SELECT CU.ID, 'iFood' AS SALE_CHANNEL
      FROM ORDERS_TABLE OT
      INNER JOIN CUSTOMER_UNION CU ON CU.CUSTOMER_ID_ORIGINAL = OT.CUSTOMER_ID

      UNION ALL
      SELECT CU.ID, '99food'
      FROM ORDERS_TABLE OT
      INNER JOIN CUSTOMER_UNION CU ON CU.C_UID_ORIGINAL = OT.C_UID

      UNION ALL
      SELECT CU.ID, 'Loja'
      FROM SALES_CLUB SC
      INNER JOIN CUSTOMER_UNION CU ON CU.DOCUMENT_NUMBER_CTB = SC.CLIENT_CPF
    ),

    RESUMO AS (
      SELECT ID, STRING_AGG(DISTINCT SALE_CHANNEL, ', ') AS SALES_CHANNEL
      FROM TRANSACOES
      GROUP BY ID
    )

    SELECT COUNT(DISTINCT CU.ID)
    FROM CUSTOMER_UNION CU
    INNER JOIN RESUMO R ON R.ID = CU.ID
    {where_clause}
    """

    return client.query(query).to_dataframe().iloc[0, 0]


#df = read_customer_frequency_data(page_number=1, rows_per_page=20, sales_channel="Loja/iFood")
