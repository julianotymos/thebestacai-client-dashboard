import streamlit as st
import psycopg2
import pandas as pd
from psycopg2.extras import RealDictCursor
import datetime
from typing import List

from get_connection import get_connection

def read_process_last_run(process_keys: List[str]):
    """
    Consulta os dados da tabela `process_last_run` para um `process_key` específico.

    :param process_keys: Lista de chaves de processo para o filtro.
    :return: DataFrame contendo os dados da consulta.
    """
    if not process_keys:
        return pd.DataFrame()

    # Cria uma string com placeholders dinâmicos para a cláusula IN, 
    # por exemplo: "%s, %s, %s"
    placeholders = ', '.join(['%s'] * len(process_keys))
    
    query = f"""
    SELECT 
        last_run_date,
        process_key ,
        name
    FROM process_last_run
    WHERE process_key IN ({placeholders});
    """

    with get_connection() as conn:
        with conn.cursor() as cursor:
            # Executa a consulta passando a lista de chaves como tupla
            cursor.execute(query, tuple(process_keys))
            data = cursor.fetchall()
            df = pd.DataFrame(data)
            
    return df

#processos = ["SALES_THE_BEST", "IFOOD_ORDERS_PROCESS"]
#df_ultimas_execucoes = read_process_last_run(processos)
#print(df_ultimas_execucoes)