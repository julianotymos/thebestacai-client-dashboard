import streamlit as st
import pandas as pd
from read_customer_frequency_data import read_customer_frequency_data, read_total_customers_count
from read_customer_summary import read_customer_summary
from read_customer_transactions_by_id import read_customer_transactions_by_id
from read_process_last_run import read_process_last_run
st.set_page_config(layout="wide")

# ------------------------
# Filtros na barra lateral
# ------------------------
sales_channels = ["", "Loja", "iFood", "99food", "Loja/iFood", "Loja/99food", "iFood/99food", "Loja/iFood/99food"]

with st.sidebar:
    st.subheader("Filtros")
    f_sales_channel = st.selectbox("Selecione o canal de vendas:", sales_channels)
    f_name = st.text_input("Nome do Cliente")
    f_phone = st.text_input("Telefone")
    f_doc = st.text_input("CPF")
    
    st.sidebar.markdown("---")
    st.sidebar.header("🔄 Status de Processamento")
    last_run_df = read_process_last_run(["BIG_QUERY_PROCESS"])
    if not last_run_df.empty:
        for index, row in last_run_df.iterrows():
            st.sidebar.info(f"**{row['name']}**\nÚltima atualização: {row['last_run_date'].strftime('%d/%m/%Y %H:%M:%S')}")
# ------------------------
# Resumo de clientes por canal
# ------------------------
st.title("The Best Clientes - Dashboard ")

st.subheader("Clientes por Canal")
df_summary = read_customer_summary()
if not df_summary.empty:
    summary_data = df_summary.iloc[0]  # pega a primeira linha
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Total Clientes", summary_data["TOTAL_CLIENTE"])
    col2.metric("Clientes Loja", summary_data["CLIENTES_LOJA"])
    col3.metric("Clientes iFood", summary_data["CLIENTES_IFOOD"])
    col4.metric("Clientes 99food", summary_data["CLIENTES_99FOOD"])
    
    col5, col6, col7, col8 = st.columns(4)
    col5.metric("Loja + iFood", summary_data["CLIENTES_LOJA_IFOOD"])
    col6.metric("Loja + 99food", summary_data["CLIENTES_LOJA_99FOOD"])
    col7.metric("iFood + 99food", summary_data["CLIENTES_IFOOD_99FOOD"])
    col8.metric("Loja + iFood + 99food", summary_data["CLIENTES_LOJA_IFOOD_99FOOD"])
else:
    st.info("Não foi possível carregar os dados do resumo de clientes.")

# ------------------------
# Total de clientes e Paginação
# ------------------------
st.subheader("Frequência de Compras")
total_customers = read_total_customers_count(
    sales_channel=f_sales_channel or None,
    name=f_name or None,
    phone_number=f_phone or None,
    document_number=f_doc or None
)

rows_per_page_options = [25, 50, 100, 200]
bottom_menu = st.columns((4, 1, 1))

with bottom_menu[2]:
    rows_per_page = st.selectbox("Linhas por Página", options=rows_per_page_options)

with bottom_menu[1]:
    total_pages = (total_customers // rows_per_page) + (1 if total_customers % rows_per_page > 0 else 0)
    current_page = st.number_input("Página", min_value=1, max_value=max(total_pages, 1), step=1)

with bottom_menu[0]:
    st.markdown(f"Página **{current_page}** de **{total_pages}** ")

# ------------------------
# Dados detalhados na tabela principal
# ------------------------
df_customers = read_customer_frequency_data(
    page_number=current_page,
    rows_per_page=rows_per_page,
    sales_channel=f_sales_channel or None,
    name=f_name or None,
    phone_number=f_phone or None,
    document_number=f_doc or None
)

if not df_customers.empty:
    selection = st.dataframe(
        df_customers,
        use_container_width=True,
        on_select="rerun",  # Roda o script novamente quando uma linha é clicada
        selection_mode="single-row",
        hide_index=True
    )
    
    # Exibe as transações do cliente selecionado
    if selection["selection"]["rows"]:
        selected_index = selection["selection"]["rows"][0]
        selected_row = df_customers.iloc[[selected_index]]
        
        selected_customer_id = selected_row["Id"].iloc[0]
        selected_customer_name = selected_row["Cliente"].iloc[0]

        st.subheader(f"Transações de {selected_customer_name}")
        print(selected_customer_id)
        transactions_df = read_customer_transactions_by_id(selected_customer_id)
        
        if not transactions_df.empty:
            st.dataframe(transactions_df, use_container_width=True , hide_index=True)
        else:
            st.info("Não há transações para este cliente.")
else:
    st.info("Não foi possível carregar os dados. Verifique os filtros ou a conexão com o BigQuery.")