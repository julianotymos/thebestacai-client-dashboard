import streamlit as st
import pandas as pd
from datetime import datetime
import urllib.parse
from read_customer_frequency_data import read_customer_frequency_data, read_total_customers_count, read_all_customer_data
from read_advanced_analytics_data import read_advanced_analytics_data
from read_customer_summary import read_customer_summary
from read_customer_transactions_by_id import read_customer_transactions_by_id
from read_process_last_run import read_process_last_run
from read_cohort_data import read_cohort_data
from log_event import log_whatsapp_event, read_whatsapp_events, read_full_event_history, read_customer_contact_history
import altair as alt

st.set_page_config(layout="wide", page_title="The Best Clientes - Dashboard")

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
st.title("The Best Clientes - Dashboard")

st.subheader("Clientes por Canal")
df_summary = read_customer_summary()
if not df_summary.empty:
    summary_data = df_summary.iloc[0]
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

# ------------------------
# Abas de Visualização
# ------------------------
tab1, tab2, tab3, tab4 = st.tabs(["📋 Frequência", "📊 Coorte", "💡 Insights", "📱 WhatsApp CRM"])

with tab1:
    st.subheader("Frequência de Compras")
    total_customers = read_total_customers_count(sales_channel=f_sales_channel or None, name=f_name or None, phone_number=f_phone or None, document_number=f_doc or None)
    rows_per_page_options = [25, 50, 100, 200]
    bottom_menu = st.columns((2, 1, 1, 1))
    with bottom_menu[3]: rows_per_page = st.selectbox("Linhas por Página", options=rows_per_page_options, key="rows_per_page")
    with bottom_menu[2]:
        total_pages = (total_customers // rows_per_page) + (1 if total_customers % rows_per_page > 0 else 0)
        current_page = st.number_input("Página", min_value=1, max_value=max(total_pages, 1), step=1, key="current_page")
    with bottom_menu[1]:
        if st.checkbox("📥 Preparar Download", key="prep_download"):
            df_all = read_all_customer_data(sales_channel=f_sales_channel or None, name=f_name or None, phone_number=f_phone or None, document_number=f_doc or None)
            if not df_all.empty:
                csv = df_all.to_csv(index=False).encode('utf-8')
                st.download_button(label="Clique para Baixar (CSV)", data=csv, file_name=f"clientes_thebest_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv", mime="text/csv")
    with bottom_menu[0]: st.markdown(f"Página **{current_page}** de **{total_pages}** (Total: {total_customers})")

    df_customers = read_customer_frequency_data(page_number=current_page, rows_per_page=rows_per_page, sales_channel=f_sales_channel or None, name=f_name or None, phone_number=f_phone or None, document_number=f_doc or None)
    if not df_customers.empty:
        selection = st.dataframe(df_customers, use_container_width=True, on_select="rerun", selection_mode="single-row", hide_index=True)
        if selection["selection"]["rows"]:
            selected_index = selection["selection"]["rows"][0]
            selected_row = df_customers.iloc[[selected_index]]
            selected_customer_id = selected_row["Id"].iloc[0]
            selected_customer_name = selected_row["Cliente"].iloc[0]
            st.subheader(f"Transações de {selected_customer_name}")
            transactions_df = read_customer_transactions_by_id(selected_customer_id)
            if not transactions_df.empty: st.dataframe(transactions_df, use_container_width=True, hide_index=True)

with tab2:
    st.subheader("Retenção Mensal de Clientes (%)")
    retention, cohort_matrix = read_cohort_data(sales_channel=f_sales_channel)
    if not retention.empty:
        df_styled = (retention.style.format("{:.1%}", na_rep="").background_gradient(cmap='YlGnBu', axis=None, low=0, high=1).set_properties(**{'text-align': 'center'}))
        st.dataframe(df_styled, use_container_width=True)
        with st.expander("Ver números absolutos"): st.dataframe(cohort_matrix, use_container_width=True)

with tab3:
    st.subheader(f"Insights Estratégicos")
    df_adv = read_advanced_analytics_data(sales_channel=f_sales_channel)
    if not df_adv.empty:
        c1, c2 = st.columns(2)
        with c1:
            st.markdown("### 📊 Curva ABC")
            df_abc = df_adv.sort_values("MONETARY", ascending=False).reset_index()
            df_abc['cum_perc'] = 100 * df_abc['MONETARY'].cumsum() / df_abc['MONETARY'].sum()
            st.area_chart(df_abc['cum_perc'], use_container_width=True)
            
            # Restaurando a descrição 80/20
            vip_count = len(df_abc[df_abc['cum_perc'] <= 80])
            total_count = len(df_abc)
            st.info(f"**Insight:** {vip_count} clientes ({100*vip_count/total_count:.1f}%) representam 80% do seu faturamento.")

        with c2:
            st.markdown("### 🕒 Ciclo de Recompra")
            df_cycle = df_adv[df_adv['AVG_CYCLE'] > 0].copy()
            if not df_cycle.empty:
                df_cycle['Faixa_Label'] = (df_cycle['AVG_CYCLE'] // 7 * 7).astype(int).apply(lambda x: f"{x}-{x+7} dias")
                st.bar_chart(df_cycle['Faixa_Label'].value_counts().sort_index().head(10))
                
                # Restaurando a média de dias
                st.info(f"**Média Geral:** Seus clientes fiéis voltam a cada **{df_cycle['AVG_CYCLE'].mean():.0f} dias**.")
            else:
                st.info("Dados insuficientes para ciclo de recompra.")
        
        st.markdown("---")
        st.markdown("### 🧬 Matriz RFM")
        segment_counts = df_adv['SEGMENTO'].value_counts().reset_index()
        segment_counts.columns = ['Segmento', 'Quantidade']
        m1, m2, m3, m4 = st.columns(4)
        def get_count(name):
            val = segment_counts[segment_counts['Segmento'] == name]['Quantidade']
            return val.iloc[0] if not val.empty else 0
        m1.metric("🏆 Campeões", get_count("🏆 Campeões (VIP)"))
        m2.metric("📈 Fiéis", get_count("📈 Clientes Fiéis"))
        m3.metric("⚡ Potenciais", get_count("⚡ Potenciais"))
        m4.metric("💤 Em Risco", get_count("💤 Em Risco/Perdidos"))
        
        rfm_chart = alt.Chart(segment_counts).mark_bar().encode(x='Quantidade:Q', y=alt.Y('Segmento:N', sort='-x'), color=alt.Color('Segmento:N', scale=alt.Scale(scheme='viridis'))).properties(height=300)
        st.altair_chart(rfm_chart, use_container_width=True)

        st.markdown("---")
        st.subheader("👥 Listagem Detalhada por Segmento")
        selected_seg = st.selectbox("Filtrar por Segmento:", ["Todos"] + sorted(df_adv['SEGMENTO'].unique().tolist()), key="list_seg")
        df_list = df_adv if selected_seg == "Todos" else df_adv[df_adv['SEGMENTO'] == selected_seg]
        st.dataframe(df_list[['NAME', 'PHONE_NUMBER', 'MONETARY', 'FREQUENCY', 'RECENCY', 'SEGMENTO', 'SALES_CHANNEL']].rename(columns={'SALES_CHANNEL': 'Canais'}).sort_values("MONETARY", ascending=False), use_container_width=True, hide_index=True)

with tab4:
    st.subheader("📱 Central de Comunicação WhatsApp (CRM)")
    
    df_wa = read_advanced_analytics_data(sales_channel=f_sales_channel)
    df_events = read_whatsapp_events()
    
    if not df_wa.empty:
        df_wa['ID_STR'] = df_wa['ID'].astype(str)
        df_events['customer_id'] = df_events['customer_id'].astype(str)
        df_wa = df_wa.merge(df_events, left_on='ID_STR', right_on='customer_id', how='left').drop(columns=['customer_id'])
        
        # --- FILTROS ---
        f_col1, f_col2, f_col3 = st.columns([1, 1, 1])
        with f_col1: wa_seg_filter = st.selectbox("Filtrar Segmento:", ["Todos"] + sorted(df_wa['SEGMENTO'].unique().tolist()), key="wa_seg")
        with f_col2: wa_name_filter = st.text_input("Buscar Nome:", placeholder="Ex: Julia...", key="wa_name")
        with f_col3: wa_phone_only = st.toggle("Apenas com Telefone", value=True, key="wa_phone")
        
        if wa_seg_filter != "Todos": df_wa = df_wa[df_wa['SEGMENTO'] == wa_seg_filter]
        if wa_name_filter: df_wa = df_wa[df_wa['NAME'].str.contains(wa_name_filter, case=False, na=False)]
        if wa_phone_only: df_wa = df_wa[df_wa['PHONE_NUMBER'].astype(str).str.len() > 5]

        st.markdown("#### Resumo da Seleção Atual")
        counts_wa = df_wa['SEGMENTO'].value_counts()
        cwa1, c_wa2, c_wa3, c_wa4 = st.columns(4)
        cwa1.metric("🏆 Campeões", counts_wa.get("🏆 Campeões (VIP)", 0))
        c_wa2.metric("📈 Fiéis", counts_wa.get("📈 Clientes Fiéis", 0))
        c_wa3.metric("⚡ Potenciais", counts_wa.get("⚡ Potenciais", 0))
        c_wa4.metric("💤 Em Risco", counts_wa.get("💤 Em Risco/Perdidos", 0))

        # --- GRID DE SELEÇÃO ---
        st.markdown("### 1. Selecione o Cliente na Grade")
        df_wa['Último Contato'] = pd.to_datetime(df_wa['last_contact']).dt.strftime('%d/%m/%Y %H:%M').fillna("Nunca")
        df_wa['Data 1ª Compra'] = pd.to_datetime(df_wa['FIRST_PURCHASE']).dt.strftime('%d/%m/%Y')
        df_wa['Data Ult. Compra'] = pd.to_datetime(df_wa['LAST_PURCHASE']).dt.strftime('%d/%m/%Y')
        
        wa_display = df_wa[['NAME', 'PHONE_NUMBER', 'SALES_CHANNEL', 'SEGMENTO', 'FREQUENCY', 'Data 1ª Compra', 'Data Ult. Compra', 'Último Contato']].rename(columns={
            'NAME': 'Cliente', 'PHONE_NUMBER': 'Telefone', 'SALES_CHANNEL': 'Canais', 'SEGMENTO': 'Tipo', 'FREQUENCY': 'Qtd Compras'
        })
        
        selection_wa = st.dataframe(wa_display, use_container_width=True, on_select="rerun", selection_mode="single-row", hide_index=True, key="wa_grid_v6")
        
        if selection_wa["selection"]["rows"]:
            customer_row = df_wa.iloc[selection_wa["selection"]["rows"][0]]
            st.markdown("---")
            
            c_msg1, c_msg2 = st.columns([1, 2])
            with c_msg1:
                st.info(f"**Cliente:** {customer_row['NAME']}\n\n**Segmento:** {customer_row['SEGMENTO']}\n\n**Canais:** {customer_row['SALES_CHANNEL']}")
                st.subheader("📜 Histórico")
                hist_df = read_customer_contact_history(customer_row['ID'])
                if not hist_df.empty: st.dataframe(hist_df, use_container_width=True, hide_index=True)
                else: st.write("Sem registros.")

            with c_msg2:
                st.markdown("### 2. Configurar e Enviar")
                intuito = st.selectbox("Intuito:", ["Agradecimento", "Saudades", "Promoção", "Feedback"], key="intuito_wa")
                nome = customer_row['NAME'].split()[0]
                templates = {
                    "Agradecimento": f"Olá {nome}! 💜 Passando para agradecer por ser um dos nossos clientes {customer_row['SEGMENTO']}. Sua preferência no The Best Açaí é muito especial para nós!",
                    "Saudades": f"Oi {nome}! 🍦 Sentimos sua falta. Já faz {customer_row['RECENCY']} dias que você não vem nos visitar. Que tal um açaí hoje para matar a saudade?",
                    "Promoção": f"Fala {nome}! 🎁 Como você é um cliente {customer_row['SEGMENTO']}, liberamos um benefício exclusivo para você hoje na loja. Venha conferir!",
                    "Feedback": f"Olá {nome}! 🌟 Como foi sua última experiência? Sendo um cliente {customer_row['SEGMENTO']}, sua opinião nos ajuda a ser cada vez melhores."
                }
                msg_body = st.text_area("Mensagem:", value=templates[intuito], height=120, key="msg_area")
                
                # Link WhatsApp com URLLIB QUOTE robusto para Emojis
                phone_clean = "".join(filter(str.isdigit, str(customer_row['PHONE_NUMBER']).replace(".0","")))
                if not phone_clean.startswith("55") and len(phone_clean) >= 10: phone_clean = "55" + phone_clean
                encoded_msg = urllib.parse.quote(msg_body.encode('utf-8'))
                wa_link = f"https://wa.me/{phone_clean}?text={encoded_msg}"
                
                # INVERSÃO SOLICITADA: Abre WhatsApp primeiro, depois botão de registrar
                st.markdown(f'<a href="{wa_link}" target="_blank" style="text-decoration:none;"><button style="background-color:#25D366; color:white; border:none; padding:15px 30px; border-radius:8px; font-weight:bold; cursor:pointer; width:100%; font-size:16px;">1. ABRIR CONVERSA NO WHATSAPP</button></a>', unsafe_allow_html=True)
                
                st.write("") # Espaçador
                
                if st.button("2. CONFIRMAR REGISTRO NO HISTÓRICO", key="btn_confirm_log", use_container_width=True):
                    if log_whatsapp_event(customer_row['ID'], customer_row['NAME'], phone_clean, customer_row['SEGMENTO'], intuito, msg_body):
                        st.success(f"Contato com {customer_row['NAME']} registrado no BigQuery!")
                        st.balloons()
                    else:
                        st.error("Erro ao registrar.")
    else:
        st.info("Nenhum dado disponível.")

    st.markdown("---")
    st.subheader("📋 Últimos 10 Envios Globais")
    st.dataframe(read_full_event_history().head(10), use_container_width=True, hide_index=True)
