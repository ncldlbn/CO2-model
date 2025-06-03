import streamlit as st
import pandas as pd
import altair as alt

def display_results(nome_allevamento, C, T):
    st.write("### Risultati")
    
    # === BOX EMISSIONI === #
    st.write("🌍 **Report Emissioni**")
    st.markdown(
        f"""
        <div style='background-color: #d9edf7; padding: 10px; border-radius: 5px; border: 1px solid #bce8f1; text-align: center; color: #31708f; margin-bottom: 20px;'>
            <strong>CO₂eq totale</strong><br> {round(C.tot_co2eq/1000 + T.tot_co2)} kg
        </div>
        """, unsafe_allow_html=True)

    col1, col2 = st.columns(2)
    with col1:
        st.markdown(
            f"""
            <div style='background-color: #d9edf7; padding: 10px; border-radius: 5px; border: 1px solid #bce8f1; text-align: center; color: #31708f; margin-bottom: 20px;'>
                <strong>CO₂eq da deposito biomassa</strong><br> {round(C.tot_co2eq/1000)} kg
            </div>
            """, unsafe_allow_html=True)
    with col2:
        st.markdown(
            f"""
            <div style='background-color: #d9edf7; padding: 10px; border-radius: 5px; border: 1px solid #bce8f1; text-align: center; color: #31708f; margin-bottom: 20px;'>
                <strong>CO₂eq da trasporti</strong><br> {round(T.tot_co2)} kg
            </div>
            """, unsafe_allow_html=True)

    # === GRAFICO CO2 === #
    df = pd.DataFrame({
        'fonte': ['Trasporti', 'Deposito biomassa'],
        'CO₂eq': [round(T.tot_co2), round(C.tot_co2eq/1000)]
    })
    df['tooltip'] = df.apply(lambda row: f"{row['fonte']}: {row['CO₂eq']} kg", axis=1)
    df['barra'] = "CO₂"
    chart = alt.Chart(df).mark_bar(opacity=0.7).encode(
        x=alt.X('CO₂eq:Q', title='CO₂ equivalente (kg)',
                scale=alt.Scale(domain=[0, max(df["CO₂eq"]) * 1.1]), stack='zero'),
        y=alt.Y('barra:N', axis=None),
        color=alt.Color('fonte:N', title='Fonte CO₂', legend=alt.Legend(orient="bottom")),
        tooltip=alt.Tooltip('tooltip:N', title='CO₂')
    ).properties(height=120).configure_view(strokeWidth=0)
    st.altair_chart(chart, use_container_width=True)

    # === GRAFICO CO2 CUMULATA === #
    df_merged = pd.merge(
        pd.DataFrame(T.registro),
        pd.DataFrame(C.co2_data),
        on="giorno",
        how="outer"
    ).fillna(0).sort_values(by="giorno").reset_index(drop=True)

    df_merged["co2_emessa_cum"] = df_merged["co2_emessa"].cumsum()
    df_merged["co2eq_cum"] = df_merged["co2eq_biomassa"].cumsum()
    df_long = df_merged[["giorno", "co2_emessa_cum", "co2eq_cum"]].melt(
        id_vars="giorno", var_name="Fonte", value_name="CO2eq_cumulata"
    )
    df_long["Fonte"] = df_long["Fonte"].map({
        "co2_emessa_cum": "Trasporti",
        "co2eq_cum": "Biomassa"
    })
    chart = alt.Chart(df_long).mark_area(opacity=0.7).encode(
        x=alt.X("giorno", title="Giorno", scale=alt.Scale(domain=(1, 365))),
        y=alt.Y("CO2eq_cumulata", title="CO₂ equivalente cumulata [kg]", stack="zero"),
        color=alt.Color("Fonte", title="Fonte", legend=alt.Legend(orient="bottom")),
        tooltip=["giorno", "Fonte", alt.Tooltip("CO2eq_cumulata", format=".2f")]
    ).properties(width=700, height=400).interactive()
    st.altair_chart(chart, use_container_width=True)

    # === GRAFICO DEPOSITO === #
    st.write("🐄 **Livello deposito nel tempo**")
    df = pd.DataFrame({
        "Giorno": list(C.deposito.keys()),
        "Livello": list(C.deposito.values())
    })
    chart = alt.Chart(df).mark_line().encode(
        x=alt.X("Giorno", title="Giorno", scale=alt.Scale(domain=(1, 365))),
        y=alt.Y("Livello", title="Livello deposito [kg]"),
        tooltip=["Giorno", "Livello"]
    ).properties(width=700, height=400).interactive()
    st.altair_chart(chart, use_container_width=True)

    # === REGISTRO SVUOTAMENTI === #
    st.write("🚛 **Registro svuotamenti**")
    st.dataframe(
        T.registro,
        column_config={
            "giorno": "Giorno",
            "n_viaggi": st.column_config.NumberColumn("Numero viaggi", format="%.0f"),
            "km_percorsi": st.column_config.NumberColumn("Km percorsi", format="%.0f km"),
            "quantita": st.column_config.NumberColumn("Quantità biomassa", format="%.1f t"),
            "riempimento_medio": st.column_config.NumberColumn("Riempimento medio", format="%.0f%%"),
            "co2_emessa": st.column_config.NumberColumn("CO₂ totale emessa", format="%.1f kg")
        },
        use_container_width=True
    )