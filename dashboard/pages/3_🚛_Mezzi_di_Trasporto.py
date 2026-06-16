import streamlit as st
import pandas as pd
import sqlite3
import os

st.markdown("""
<style>
div.stButton > button {
    width: 100%;
}
</style>
""", unsafe_allow_html=True)

# ---------------------------------------------------------------------------------------- #
# FUNZIONI
# ---------------------------------------------------------------------------------------- #

def form_trasporto(conn, dati_esistenti=None, key_prefix="", is_nuovo=False):
    """Form per visualizzare e modificare un trasporto"""

    # Valori di default
    defaults = {
        "id_trasporto": None,
        "tipo": "",
        "co2_fossile": 0.0,
        "co2_biogenica": 0.0,
        "co2_dluc": 0.0,
        "co2_tot": 0.0
    }

    if dati_esistenti:
        defaults.update(dati_esistenti)
    
    # Calcola il totale se non è già presente
    if "co2_fossile" in defaults and "co2_biogenica" in defaults and "co2_dluc" in defaults:
        defaults["co2_tot"] = defaults.get("co2_tot", 
                                          defaults["co2_fossile"] + defaults["co2_biogenica"] + defaults["co2_dluc"])

    # Mostra il materiale trasportato in base all'ID
    if defaults["id_trasporto"] == 0:
        st.write("**Materiale trasportato:** Liquame")
    elif defaults["id_trasporto"] == 1:
        st.write("**Materiale trasportato:** Letame / digestato solido")
    elif defaults["id_trasporto"] == 2:
        st.write("**Materiale trasportato:** Liquame / digestato liquido")
    elif defaults["id_trasporto"] is not None:
        st.write("**Materiale trasportato:** Non specificato")

    # Sezione per i fattori di emissione
    st.subheader("Fattori di Emissione (kg CO2eq/tkm)")
    
    # Crea tre colonne per le componenti di CO2
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        co2_fossile = st.number_input(
            "CO₂ Fossile",
            min_value=0.000,
            step=0.001,
            value=float(defaults.get("co2_fossile", 0.000)),
            format="%.3f",  # Mostra 3 decimali
            key=f"{key_prefix}_co2_fossile"
        )
    
    with col2:
        co2_biogenica = st.number_input(
            "CO₂ Biogenica",
            min_value=0.000,
            step=0.001,
            value=float(defaults.get("co2_biogenica", 0.000)),
            format="%.3f",  # Mostra 3 decimali
            key=f"{key_prefix}_co2_biogenica"
        )
    
    with col3:
        co2_dluc = st.number_input(
            "CO₂ dLUC",
            min_value=0.000,
            step=0.001,
            value=float(defaults.get("co2_dluc", 0.000)),
            format="%.3f",  # Mostra 3 decimali
            key=f"{key_prefix}_co2_dluc"
        )

    with col4:
        # Calcola il totale
        co2_tot = co2_fossile + co2_biogenica + co2_dluc

        st.metric(
            "EF Totale kg CO2eq/tkm", 
            f"{co2_tot:.3f}",
            help="Somma di tutte le componenti di emissione"
        )
    
    # Pulsanti finali
    st.markdown("---")
    
    if defaults["id_trasporto"] is not None and not is_nuovo:  # Solo per trasporti esistenti

        if st.button("💾 Salva modifiche", key=f"{key_prefix}_salva", use_container_width=True):
            try:
                cursor = conn.cursor()
                # Aggiorna o inserisce il fattore di emissione con tutte le componenti
                cursor.execute("""
                    SELECT COUNT(*) FROM fattori_emissione
                    WHERE categoria = 'trasporti' AND nome = ?
                """, (defaults["tipo"],))

                if cursor.fetchone()[0] > 0:
                    # Aggiorna il fattore esistente con tutte le componenti
                    cursor.execute("""
                        UPDATE fattori_emissione
                        SET unita = ?,
                            CO2_fossile = ?,
                            CO2_biogenica = ?,
                            CO2_dLUC = ?,
                            CO2_TOT = ?
                        WHERE categoria = 'trasporti' AND nome = ?
                    """, (
                        "kg CO2eq/tkm",
                        float(co2_fossile),
                        float(co2_biogenica),
                        float(co2_dluc),
                        float(co2_tot),
                        defaults["tipo"]  # nome non modificato
                    ))
                else:
                    # Inserisce un nuovo fattore con tutte le componenti
                    cursor.execute("""
                        INSERT INTO fattori_emissione
                        (categoria, nome, unita, CO2_fossile, CO2_biogenica, CO2_dLUC, CO2_TOT)
                        VALUES (?, ?, ?, ?, ?, ?, ?)
                    """, (
                        "trasporti",
                        defaults["tipo"],  # usa il nome esistente
                        "kg CO2eq/tkm",
                        float(co2_fossile),
                        float(co2_biogenica),
                        float(co2_dluc),
                        float(co2_tot)
                    ))

                conn.commit()
                st.toast("✅ Modifiche salvate con successo!")
                st.rerun()
            except sqlite3.IntegrityError as e:
                st.error(f"❌ Errore di integrità: {str(e)}")
            except Exception as e:
                st.error(f"❌ Errore durante il salvataggio: {str(e)}")

    # Ritorna i dati per il nuovo trasporto
    return {
        "tipo": defaults["tipo"],
        "co2_fossile": co2_fossile,
        "co2_biogenica": co2_biogenica,
        "co2_dluc": co2_dluc,
        "co2_tot": co2_tot
    }

# ---------------------------------------------------------------------------------------- #
# MAIN
# ---------------------------------------------------------------------------------------- #

st.title("🚛 Mezzi di Trasporto")

# Configurazione del database
# Calcola il percorso assoluto del file corrente
current_dir = os.path.dirname(os.path.abspath(__file__))
# Torna su di 2 livelli: dashboard/pages -> dashboard -> progetto root
project_root = os.path.abspath(os.path.join(current_dir, '../..'))
# Percorso completo al database
DB_PATH = os.path.join(project_root, 'data.db')

conn = sqlite3.connect(DB_PATH)
cursor = conn.cursor()

# ---------------------------------------------------------------------------------------- #
# VISUALIZZA E GESTISCI TRASPORTI ESISTENTI
# ---------------------------------------------------------------------------------------- #

# Carica i dati dei trasporti con TUTTI i campi dei fattori di emissione
trasporti_df = pd.read_sql_query("""
    SELECT t.*, 
           COALESCE(fe.CO2_fossile, 0) as co2_fossile,
           COALESCE(fe.CO2_biogenica, 0) as co2_biogenica,
           COALESCE(fe.CO2_dLUC, 0) as co2_dluc,
           COALESCE(fe.CO2_TOT, 0) as co2_tot
    FROM trasporti t 
    LEFT JOIN fattori_emissione fe ON t.tipo = fe.nome AND fe.categoria = 'trasporti'
    ORDER BY t.id_trasporto
""", conn)

if len(trasporti_df) == 0:
    st.info("Nessun trasporto trovato nel database.")
else:          
    # Seleziona il trasporto da visualizzare
    trasporti_options = [f"{row['id_trasporto']} - {row['tipo']}" for _, row in trasporti_df.iterrows()]
    
    selected_trasporto = st.selectbox(
        "Seleziona il trasporto da visualizzare",
        trasporti_options,
        key="select_trasporto"
    )
    
    # Trova i dati del trasporto selezionato
    selected_id = int(selected_trasporto.split(" - ")[0])
    selected_data = trasporti_df[trasporti_df['id_trasporto'] == selected_id].iloc[0].to_dict()
        
    # Mostra il form per il trasporto selezionato
    form_trasporto(conn, dati_esistenti=selected_data, key_prefix="selected", is_nuovo=False)

conn.close()