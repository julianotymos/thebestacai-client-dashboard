import streamlit as st
import pandas as pd
from datetime import datetime
from get_bigquery_client import get_bigquery_client

TABLE_ID = "deliverysales-469113-469510.DELIVERY.WHATSAPP_EVENTS"

def log_whatsapp_event(customer_id, customer_name, phone, segment, message_type, message_body):
    """Registra um evento de mensagem no BigQuery."""
    client = get_bigquery_client()
    rows_to_insert = [{
        "timestamp": datetime.now().isoformat(),
        "customer_id": str(customer_id),
        "customer_name": customer_name,
        "phone": str(phone),
        "segment": segment,
        "message_type": message_type,
        "message_body": message_body
    }]
    try:
        errors = client.insert_rows_json(TABLE_ID, rows_to_insert)
        return errors == []
    except Exception as e:
        st.error(f"Erro BigQuery: {e}")
        return False

def read_whatsapp_events():
    """Lê o resumo de contatos (última data por cliente)."""
    client = get_bigquery_client()
    query = f"SELECT customer_id, MAX(timestamp) as last_contact FROM `{TABLE_ID}` GROUP BY customer_id"
    try:
        return client.query(query).to_dataframe()
    except Exception:
        return pd.DataFrame(columns=['customer_id', 'last_contact'])

def read_customer_contact_history(customer_id):
    """Lê o histórico completo de um cliente específico."""
    client = get_bigquery_client()
    query = f"""
        SELECT timestamp, message_type, message_body 
        FROM `{TABLE_ID}` 
        WHERE customer_id = '{customer_id}' 
        ORDER BY timestamp DESC
    """
    try:
        df = client.query(query).to_dataframe()
        if not df.empty:
            df['timestamp'] = pd.to_datetime(df['timestamp']).dt.strftime('%d/%m/%Y %H:%M')
            df.rename(columns={'timestamp': 'Data/Hora', 'message_type': 'Tipo', 'message_body': 'Mensagem'}, inplace=True)
        return df
    except Exception:
        return pd.DataFrame()

def read_full_event_history():
    """Lê os últimos 50 eventos globais."""
    client = get_bigquery_client()
    query = f"SELECT timestamp, customer_name, segment, message_type FROM `{TABLE_ID}` ORDER BY timestamp DESC LIMIT 50"
    try:
        df = client.query(query).to_dataframe()
        if not df.empty:
            df['timestamp'] = pd.to_datetime(df['timestamp']).dt.strftime('%d/%m/%Y %H:%M')
        return df
    except Exception:
        return pd.DataFrame()
