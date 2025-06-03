import streamlit as st
import pandas as pd
from db import get_connection, create_tables
import sqlite3
from functions import calcola_svuotamenti, Contadino, Trasporto
from results import display_results
import altair as alt

st.markdown("""
<style>
div.stButton > button {
    width: 100%;
}
</style>
""", unsafe_allow_html=True)

conn = get_connection()
cursor = conn.cursor()

#st.set_page_config(page_title="Calcolo CO2", layout="centered")
st.title("📊 Simulazione CO2")

st.write(
    """
    Prima di iniziare una simulazione, assicurati di aver definito le caratteristiche di un impianto, 
    di tutti gli allevamenti associati ad esso e dei mezzi di trasporto necessari utilizzando le schede nella barra laterale.
    """
)

# Seleziona l'impianto
cursor.execute("SELECT nome FROM Impianto")
impianti = ["-"] + [row[0] for row in cursor.fetchall()]
impianto_sel = st.selectbox("Seleziona un impianto per iniziare la simulazione", impianti)

if st.button("Esegui simulazione") and impianto_sel != "-":
    allevamenti = pd.read_sql_query("SELECT * FROM Allevamento WHERE impianto = ?", conn, params=(impianto_sel,))
    
    tab_labels = ["**Totali**"] + [f"{a['nome']}" for _, a in allevamenti.iterrows()]
    tabs = st.tabs(tab_labels)
    risultati = []
    dizionario_risultati = {}

    for i, (_, a) in enumerate(allevamenti.iterrows()):
        with tabs[i+1]:
            # --- DATI ALLEVAMENTO ---
            id_allev = a['id_allevamento']
            nome = a['nome']
            distanza = int(a['distanza_impianto'])
            uba = int(a['uba'])
            biomassa = float(a['biomassa_uba_giorno'])
            perc_letame = 100 if a['tipo_biomassa'].lower() == 'letame' else 0
            deposito_0 = 0
            deposito_max = float(a['deposito_max'])
            nome_trasporto = a['trasporto']
            modalita_svuotamento = a['modalita_svuotamento']
            GWP_CH4 = 100
            GWP_NO2 = 100

            C = Contadino(id_allev, distanza, uba, biomassa, perc_letame, deposito_0, deposito_max, GWP_CH4, GWP_NO2)

            trasporto = pd.read_sql_query("SELECT * FROM Trasporto WHERE nome = ?", conn, params=(nome_trasporto,))
            EF = int(trasporto.at[0, 'EF'])
            capacita_max = int(trasporto.at[0, 'capacita_max'])
            T = Trasporto(capacita_max, EF)

            if modalita_svuotamento == "Imposta frequenza":
                svuotamenti = int(a['svuotamenti'])
                calendario = calcola_svuotamenti(svuotamenti)
                giorno_rel = 1
                for day, svuotamento in calendario.items():
                    C.aggiorna_deposito(day)
                    if C.deposito[day] > C.deposito_max:
                        st.error("⚠️ ATTENZIONE, il deposito è pieno! Aumenta la frequenza di svuotamento.")
                        st.stop()
                    C.calcola_co2eq(day, giorno_rel)
                    if svuotamento:
                        T.svuota(C, day)
                        giorno_rel = 1
                    else:
                        giorno_rel += 1
            else:
                calendario = []
                giorno_rel = 1
                for day in range(1, 366, 1):
                    C.aggiorna_deposito(day)
                    C.calcola_co2eq(day, giorno_rel)
                    if C.deposito[day] + C.produzione_giornaliera >= T.capacita:
                        T.svuota(C, day)
                        giorno_rel = 1
                    else:
                        giorno_rel += 1

            risultati.append({
                "Nome allevamento": nome,
                "Produzione giornaliera": round(C.uba * C.biomassa_uba_giorno, 1),
                "CO₂ trasporti [kg]": round(T.tot_co2, 2),
                "CO₂ deposito [kg]": round(C.tot_co2eq / 1000, 2),
                "Numero viaggi": sum([r['n_viaggi'] for r in T.registro]),
                "Km percorsi": round(sum([r['km_percorsi'] for r in T.registro]), 1),
                "Riempimento medio [%]": round(
                    sum([r['riempimento_medio'] for r in T.registro]) / len(T.registro), 1
                ) if T.registro else 0
            })

            display_results(nome, C, T)
    
    # Tab Summary nell'ultima tab
    with tabs[0]:
        st.dataframe(pd.DataFrame(risultati))