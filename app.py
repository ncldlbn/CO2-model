import streamlit as st
import pandas as pd
import altair as alt
from functions import calcola_svuotamenti, Contadino, Trasporto

st.set_page_config(page_title="Stima CO₂eq")
st.title("Stima CO₂ equivalente")

# -----------------------------------------------------------------
# INPUT
# -----------------------------------------------------------------

# === Sidebar: Sezione Parametri ===
st.sidebar.header("📥 Dati di input")

# Dati zootecnici
with st.sidebar.expander("🐄 Dati Zootecnici", expanded=True):
    nome = st.text_input("Nome contadino")
    col1, col2 = st.columns(2)
    with col1:
        uba = st.number_input("UBA", min_value=1, step=1, value=None)
        deposito_max = st.number_input("Capacità max deposito (kg)", min_value=1, step=100, value=100)
    with col2:
        biomassa = st.number_input("Biomassa (kg/UBA/giorno)", min_value=0.0, step=0.1, value=None)
        deposito_0 = st.slider("Deposito iniziale (kg)", 0, round(deposito_max), 0)
    perc_letame = st.slider("Percentuale Letame/Liquame (%)", 0, 100, 72)

# Parametri del trasporto
with st.sidebar.expander("🚛 Trasporto", expanded=True):
    svuotamenti = st.number_input("Frequenza svuotamenti (giorni)", min_value=0, step=1, value=None)
    distanza = st.number_input("Distanza contadino - impianto (km)", min_value=0, step=1, value=None)
    capacita_camion = st.number_input("Capacità camion (t)", min_value=1, step=1, value=25)

# Fattori di emissione
with st.sidebar.expander("🌍 Emissioni", expanded=False):
    ef_camion = st.number_input("Trasporto (g/km)", min_value=0, step=1, value=620)
    col1, col2 = st.columns(2)
    with col1:
        # EF_NO2 = st.number_input("NO₂ (kg NO₂ / kg biomassa)", min_value=0.00, step=0.01, value=0.01)
        GWP_NO2 = st.number_input("GWP NO₂", min_value=0, step=1, value=265)
    with col2:
        # EF_CH4 = st.number_input("CH₄ (kg CH₄ / kg biomassa)", min_value=0.00, step=0.01, value=0.02)
        GWP_CH4 = st.number_input("GWP CH₄", min_value=0, step=1, value=28)

if st.button("Esegui simulazione", use_container_width=True):

    # -----------------------------------------------------------------
    # CONTROLLO INPUT
    # -----------------------------------------------------------------
    if not uba or not deposito_max or not biomassa or not svuotamenti or not distanza or not capacita_camion or not ef_camion or not GWP_NO2 or not GWP_CH4:
        st.error("⚠️ Dati di INPUT mancanti.")
        st.stop()

    # -----------------------------------------------------------------
    # CALCOLI
    # -----------------------------------------------------------------
    id = 1
    C = Contadino(id, distanza, uba, biomassa, perc_letame, deposito_0, deposito_max, GWP_CH4, GWP_NO2)
    T = Trasporto(capacita_camion, ef_camion)
    calendario = calcola_svuotamenti(svuotamenti)
    giorno_rel = 1

    for day, svuotamento in calendario.items():

        # --- CONTADINO --- #
        # Aggiorna il livello del deposito di biomassa con l'accumulo del giorno corrente
        C.aggiorna_deposito(day)
        # Se il valore nel deposito supera il livello massimo, esci
        if C.deposito[day] > C.deposito_max:
            st.error("⚠️ ATTENZIONE, il deposito è pieno! Aumenta la frequenza di svuotamento.")
            st.stop()

        # Calcola la CO2eq prodotta dal deposito nel giorno corrente
        C.calcola_co2eq(day, giorno_rel)

        # --- TRASPORTO --- #
        # Se nel giorno 'day' è previsto uno svuotamento, chiama il camion ed effettua lo svuotamento completo della vasca
        if svuotamento:
            T.svuota(C, day)
            giorno_rel = 1
        else:
            giorno_rel = giorno_rel + 1

    # -----------------------------------------------------------------
    # VISUALIZZAZIONE RISULTATI
    # ----------------------------------------------------------------- 
    st.write("")
    st.write("")

    # === BOX EMISSIONI === #
    st.write("🌍 **Report Emissioni**")
    st.markdown(
            f"""
            <div style='background-color: #d9edf7; padding: 10px; border-radius: 5px; border: 1px solid #bce8f1; text-align: center; color: #31708f; margin-bottom: 20px;'>
                <strong>CO₂eq totale</strong><br> {round(C.tot_co2eq/1000+T.tot_co2)} kg
            </div>
            """,
            unsafe_allow_html=True
        )

    col1, col2 = st.columns(2)
    with col1:
        st.markdown(
            f"""
            <div style='background-color: #d9edf7; padding: 10px; border-radius: 5px; border: 1px solid #bce8f1; text-align: center; color: #31708f; margin-bottom: 20px;'>
                <strong>CO₂eq da deposito biomassa</strong><br> {round(C.tot_co2eq/1000)} kg
            </div>
            """,
            unsafe_allow_html=True
        )
    with col2:
        st.markdown(
            f"""
            <div style='background-color: #d9edf7; padding: 10px; border-radius: 5px; border: 1px solid #bce8f1; text-align: center; color: #31708f; margin-bottom: 20px;'>
                 <strong>CO₂eq da trasporti</strong><br> {round(T.tot_co2)} kg
            </div>
            """,
            unsafe_allow_html=True
        )

    # === GRAFICO CO2 EQUIVALENTE === #
    df = pd.DataFrame({
        'fonte': ['Trasporti', 'Deposito biomassa'],
        'CO₂eq': [round(T.tot_co2), round(C.tot_co2eq/1000)]
    })
    df['tooltip'] = df.apply(lambda row: f"{row['fonte']}: {row['CO₂eq']} kg", axis=1)
    chart = alt.Chart(df).mark_bar(opacity=0.7).encode(
        x=alt.X('CO₂eq:Q',
                title='CO₂ equivalente (kg)',
                scale=alt.Scale(domain=[0, round(T.tot_co2)+round(C.tot_co2eq/1000)], padding=0),
                stack='zero'),
        y=alt.Y('barra:N', axis=None),
        color=alt.Color('fonte:N', title='Fonte CO₂', legend=None),
        tooltip=alt.Tooltip('tooltip:N', title='CO₂')
    ).properties(
        height=120
    ).configure_view(
        strokeWidth=0
    )
    st.altair_chart(chart, use_container_width=True)




    #st.write(f"💩 Biomassa giornaliera prodotta: {round(C.produzione_giornaliera)} kg/giorno")
    #st.write(f"💩 Biomassa totale prodotta: {round(C.produzione_giornaliera*365/1000)} t")

    #st.dataframe(C.co2_data, use_container_width=True)
    #st.dataframe(T.registro, use_container_width=True)

    # Unisci i DataFrame
    df_merged = pd.merge(
        pd.DataFrame(T.registro),
        pd.DataFrame(C.co2_data),
        on="giorno",
        how="outer"
    )

    # Gestisci i valori NaN sostituendoli con 0
    df_merged = df_merged.fillna(0)

    # Ordina i dati per giorno
    df_merged = df_merged.sort_values(by="giorno").reset_index(drop=True)

    # Calcola i valori cumulati per CO2 emessa e CO2eq biomassa
    df_merged["co2_emessa_cum"] = df_merged["co2_emessa"].cumsum()
    df_merged["co2eq_cum"] = df_merged["co2eq_biomassa"].cumsum()

    # Prepara il DataFrame in formato long per Altair
    df_long = df_merged[["giorno", "co2_emessa_cum", "co2eq_cum"]].melt(
        id_vars="giorno",
        var_name="Fonte",
        value_name="CO2eq_cumulata"
    )

    # Rinomina le fonti per maggiore leggibilità
    df_long["Fonte"] = df_long["Fonte"].map({
        "co2_emessa_cum": "Trasporti",
        "co2eq_cum": "Biomassa"
    })

    # Crea il grafico dell'area
    chart = alt.Chart(df_long).mark_area(opacity=0.7).encode(
        x=alt.X("giorno", title="Giorno", scale=alt.Scale(domain=(1, 365))),
        y=alt.Y("CO2eq_cumulata", title="CO₂ equivalente cumulata [kg]", stack="zero"),
        color=alt.Color("Fonte", title="Fonte", legend=None),
        tooltip=["giorno", "Fonte", alt.Tooltip("CO2eq_cumulata", format=".2f")]
    )
    # Imposta le proprietà del grafico
    chart = chart.properties(
        width=700,
        height=400
    ).interactive()

    # Mostra il grafico con Streamlit
    st.altair_chart(chart, use_container_width=True)


    # === LIVELLO DEPOSITO === #
    st.write("🐄 **Livello deposito nel tempo**")
    df = pd.DataFrame({
            "Giorno": list(C.deposito.keys()),
            "Livello": list(C.deposito.values())
        })
    chart = alt.Chart(df).mark_line().encode(
        x=alt.X("Giorno", title="Giorno", scale=alt.Scale(domain=(1, 365))),
        y=alt.Y("Livello", title="Livello deposito [kg]"),
        tooltip=["Giorno", "Livello"]
    ).properties(
        width=700,
        height=400
    ).interactive()
    st.altair_chart(chart, use_container_width=True)

    # === SVUOTAMENTI === #
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


