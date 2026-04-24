import streamlit as st
import pandas as pd
from datetime import datetime
from read_customer_frequency_data import read_customer_frequency_data, read_total_customers_count, read_all_customer_data
from read_advanced_analytics_data import read_advanced_analytics_data
from read_customer_summary import read_customer_summary
from read_customer_transactions_by_id import read_customer_transactions_by_id
from read_process_last_run import read_process_last_run
from read_cohort_data import read_cohort_data
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
else:
    st.info("Não foi possível carregar os dados do resumo de clientes.")

# ------------------------
# Abas de Visualização
# ------------------------
tab1, tab2, tab3 = st.tabs(["📋 Frequência de Compras", "📊 Análise de Retenção (Coorte)", "💡 Insights Avançados"])

with tab1:
    st.subheader("Frequência de Compras")
    total_customers = read_total_customers_count(
        sales_channel=f_sales_channel or None,
        name=f_name or None,
        phone_number=f_phone or None,
        document_number=f_doc or None
    )

    rows_per_page_options = [25, 50, 100, 200]
    bottom_menu = st.columns((2, 1, 1, 1))

    with bottom_menu[3]:
        rows_per_page = st.selectbox("Linhas por Página", options=rows_per_page_options, key="rows_per_page")

    with bottom_menu[2]:
        total_pages = (total_customers // rows_per_page) + (1 if total_customers % rows_per_page > 0 else 0)
        current_page = st.number_input("Página", min_value=1, max_value=max(total_pages, 1), step=1, key="current_page")

    with bottom_menu[1]:
        if st.checkbox("📥 Preparar Download", key="prep_download"):
            df_all = read_all_customer_data(
                sales_channel=f_sales_channel or None,
                name=f_name or None,
                phone_number=f_phone or None,
                document_number=f_doc or None
            )
            if not df_all.empty:
                csv = df_all.to_csv(index=False).encode('utf-8')
                st.download_button(
                    label="Clique para Baixar (CSV)",
                    data=csv,
                    file_name=f"clientes_thebest_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                    mime="text/csv",
                )

    with bottom_menu[0]:
        st.markdown(f"Página **{current_page}** de **{total_pages}** (Total: {total_customers})")

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
            on_select="rerun",
            selection_mode="single-row",
            hide_index=True
        )

        if selection["selection"]["rows"]:
            selected_index = selection["selection"]["rows"][0]
            selected_row = df_customers.iloc[[selected_index]]
            selected_customer_id = selected_row["Id"].iloc[0]
            selected_customer_name = selected_row["Cliente"].iloc[0]

            st.subheader(f"Transações de {selected_customer_name}")
            transactions_df = read_customer_transactions_by_id(selected_customer_id)
            if not transactions_df.empty:
                st.dataframe(transactions_df, use_container_width=True, hide_index=True)
            else:
                st.info("Não há transações para este cliente.")
    else:
        st.info("Não foi possível carregar os dados detalhados.")

with tab2:
    st.subheader("Retenção Mensal de Clientes (%)")
    st.markdown(f"Análise de retenção para o canal: **{f_sales_channel or 'Todos os Canais'}**")
    
    retention, cohort_matrix = read_cohort_data(sales_channel=f_sales_channel)
    if not retention.empty:
        df_styled = (retention
                     .style
                     .format("{:.1%}", na_rep="")
                     .background_gradient(cmap='YlGnBu', axis=None, low=0, high=1)
                     .set_properties(**{'text-align': 'center'}))
        st.dataframe(df_styled, use_container_width=True)
        with st.expander("Ver números absolutos"):
            st.dataframe(cohort_matrix, use_container_width=True)
    else:
        st.info("Aguardando dados de coorte...")

with tab3:
    st.subheader(f"Insights Estratégicos - {f_sales_channel or 'Todos os Canais'}")
    df_adv = read_advanced_analytics_data(sales_channel=f_sales_channel)
    
    if not df_adv.empty:
        c1, c2 = st.columns(2)
        with c1:
            st.markdown("### 📊 Curva ABC (Concentração)")
            df_abc = df_adv.sort_values("MONETARY", ascending=False).reset_index()
            df_abc['cum_perc'] = 100 * df_abc['MONETARY'].cumsum() / df_abc['MONETARY'].sum()
            st.area_chart(df_abc['cum_perc'], use_container_width=True)
            vip_count = len(df_abc[df_abc['cum_perc'] <= 80])
            st.info(f"**Insight:** {vip_count} clientes representam 80% do seu faturamento.")

        with c2:
            st.markdown("### 🕒 Ciclo de Recompra (Dias)")
            df_cycle = df_adv[df_adv['AVG_CYCLE'] > 0].copy()
            if not df_cycle.empty:
                # Agrupar em faixas de 7 dias para limpar o gráfico
                df_cycle['Faixa (Dias)'] = (df_cycle['AVG_CYCLE'] // 7 * 7).astype(int)
                df_cycle['Faixa_Label'] = df_cycle['Faixa (Dias)'].apply(lambda x: f"{x}-{x+7} dias")
                
                cycle_counts = df_cycle['Faixa_Label'].value_counts().reset_index()
                cycle_counts.columns = ['Faixa', 'Clientes']
                
                # Gráfico Altair para Ciclo
                cycle_chart = alt.Chart(cycle_counts).mark_bar().encode(
                    x=alt.X('Faixa:N', sort=None, title="Intervalo de Recompra"),
                    y=alt.Y('Clientes:Q', title="Número de Clientes"),
                    color=alt.value("#3182bd")
                ).properties(height=300)
                st.altair_chart(cycle_chart, use_container_width=True)
                
                st.info(f"**Média Geral:** Seus clientes fiéis voltam a cada **{df_cycle['AVG_CYCLE'].mean():.0f} dias**.")
            else:
                st.info("Dados insuficientes para ciclo de recompra.")

        st.markdown("---")
        st.markdown("### 🧬 Matriz RFM (Segmentação de Clientes)")
        
        def segment_rfm(df):
            if len(df) < 10: return ["Iniciante"] * len(df)
            df['R_Score'] = pd.qcut(df['RECENCY'], 4, labels=[4, 3, 2, 1])
            df['F_Score'] = pd.qcut(df['FREQUENCY'].rank(method='first'), 4, labels=[1, 2, 3, 4])
            df['M_Score'] = pd.qcut(df['MONETARY'], 4, labels=[1, 2, 3, 4])
            df['RFM'] = df['R_Score'].astype(int) + df['F_Score'].astype(int) + df['M_Score'].astype(int)
            def label(s):
                if s >= 10: return "🏆 Campeões (VIP)"
                if s >= 8: return "📈 Clientes Fiéis"
                if s >= 6: return "⚡ Potenciais"
                return "💤 Em Risco/Perdidos"
            return df['RFM'].apply(label)

        df_adv['Segmento'] = segment_rfm(df_adv)
        segment_counts = df_adv['Segmento'].value_counts().reset_index()
        segment_counts.columns = ['Segmento', 'Quantidade']
        
        m1, m2, m3, m4 = st.columns(4)
        def get_count(name):
            val = segment_counts[segment_counts['Segmento'] == name]['Quantidade']
            return val.iloc[0] if not val.empty else 0

        m1.metric("🏆 Campeões", get_count("🏆 Campeões (VIP)"))
        m2.metric("📈 Fiéis", get_count("📈 Clientes Fiéis"))
        m3.metric("⚡ Potenciais", get_count("⚡ Potenciais"))
        m4.metric("💤 Em Risco", get_count("💤 Em Risco/Perdidos"))

        rfm_chart = alt.Chart(segment_counts).mark_bar().encode(
            x=alt.X('Quantidade:Q', title="Número de Clientes"),
            y=alt.Y('Segmento:N', sort='-x', title=""),
            color=alt.Color('Segmento:N', legend=None, scale=alt.Scale(scheme='viridis')),
            tooltip=['Segmento', 'Quantidade']
        ).properties(height=300)
        st.altair_chart(rfm_chart, use_container_width=True)
        
        with st.expander("❓ O que define cada tipo de cliente?"):
            st.markdown("""
            O sistema utiliza a metodologia **RFM** e atribui pontos de **1 a 4** para cada critério, comparando os clientes entre si (divisão por quartis):
            
            **Como a pontuação é dada:**
            1.  **Recência (R):** Ordenamos os clientes dos que compraram mais recentemente para os mais antigos.
                - Os **25% mais recentes** ganham **nota 4**.
                - Os 25% seguintes ganham nota 3, e assim por diante.
            2.  **Frequência (F):** Ordenamos os clientes pelo número total de pedidos.
                - Os **25% que mais compram** ganham **nota 4**.
                - Os 25% seguintes ganham nota 3, e assim por diante.
            3.  **Valor (M):** Ordenamos os clientes pelo total gasto em dinheiro.
                - Os **25% que mais gastam** ganham **nota 4**.
                - Os 25% seguintes ganham nota 3, e assim por diante.

            **A Soma Final (3 a 12 pontos):**
            - **🏆 Campeões (10 a 12 pontos):** São a elite. Estão no topo (Top 25%) em quase todos os quesitos.
            - **📈 Clientes Fiéis (8 a 9 pontos):** Clientes muito bons que mantêm uma constância alta, mas podem ter falhado em um dos critérios (ex: gastam muito mas não compram toda semana).
            - **⚡ Potenciais (6 a 7 pontos):** Clientes medianos que têm potencial de virar fiéis se receberem o estímulo certo.
            - **💤 Em Risco/Perdidos (baixo de 6 pontos):** Estão na metade inferior da sua base em quase todos os critérios.
            """)
            
        with st.expander("💡 Dicas de Ação para cada Segmento"):
            st.write("""
            - **🏆 Campeões:** Ofereça tratamento VIP, brindes exclusivos ou acesso antecipado a novos sabores/produtos. Não foque em descontos aqui.
            - **📈 Fiéis:** Use programas de fidelidade (ex: 10º açaí grátis) ou cupons de indicação para eles trazerem novos clientes.
            - **⚡ Potenciais:** Envie ofertas personalizadas de produtos que eles ainda não provaram para aumentar o ticket médio.
            - **💤 Em Risco:** Envie uma mensagem automática 'Sentimos sua falta' com um cupom de desconto agressivo válido por 48h.
            """)
    else:
        st.info("Sem dados suficientes para os insights.")
