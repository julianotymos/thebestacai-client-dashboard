from google.cloud import bigquery
from get_bigquery_client import get_bigquery_client

def create_whatsapp_events_table():
    client = get_bigquery_client()
    table_id = "deliverysales-469113-469510.DELIVERY.WHATSAPP_EVENTS"

    schema = [
        bigquery.SchemaField("timestamp", "TIMESTAMP", mode="REQUIRED"),
        bigquery.SchemaField("customer_id", "STRING", mode="NULLABLE"),
        bigquery.SchemaField("customer_name", "STRING", mode="NULLABLE"),
        bigquery.SchemaField("phone", "STRING", mode="NULLABLE"),
        bigquery.SchemaField("segment", "STRING", mode="NULLABLE"),
        bigquery.SchemaField("message_type", "STRING", mode="NULLABLE"),
        bigquery.SchemaField("message_body", "STRING", mode="NULLABLE"),
    ]

    table = bigquery.Table(table_id, schema=schema)
    
    try:
        table = client.create_table(table)  # API request
        print(f"Tabela {table.project}.{table.dataset_id}.{table.table_id} criada com sucesso.")
    except Exception as e:
        print(f"Erro ao criar tabela: {e}")

if __name__ == "__main__":
    create_whatsapp_events_table()
