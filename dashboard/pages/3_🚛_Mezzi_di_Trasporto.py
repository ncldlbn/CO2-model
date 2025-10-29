import streamlit as st
import pandas as pd
import sqlite3
import sys
import os

sys.path.append(os.path.join(os.path.dirname(__file__), '../../src'))
from objects import Trasporto 

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

def form_trasporto(conn, dati_esistenti=None, key_prefix=""):
    """Form per visualizzare e modificare un trasporto"""

    # Valori di default
    defaults = {
        "id_trasporto": None,
        "tipo": "",
        "EF": 0.0,
        "capacita_max": None
    }

    if dati_esistenti:
        defaults.update(dati_esistenti)

    st.subheader("Dati Trasporto")
    
    col1, col2 = st.columns(2)
    with col1:
        tipo = st.text_input("Tipo mezzo di trasporto *", 
                           value=defaults["tipo"], 
                           key=f"{key_prefix}_tipo")
    with col2:
        EF = st.number_input("Fattore di emissione (kg CO₂/km) *", 
                           value=float(defaults["EF"]), 
                           min_value=0.0, 
                           step=0.0001, 
                           format="%.4f",
                           key=f"{key_prefix}_EF")

    # Gestione capacità massima (può essere NULL per alcuni trasporti)
    st.subheader("Capacità")
    use_capacity = st.checkbox("Specifica capacità massima", 
                              value=defaults["capacita_max"] is not None,
                              key=f"{key_prefix}_use_capacity")
    
    if use_capacity:
        capacita_max = st.number_input("Capacità massima (t) *", 
                                     value=float(defaults["capacita_max"] or 0.0), 
                                     min_value=0.0, 
                                     step=0.1,
                                     key=f"{key_prefix}_capacita")
    else:
        capacita_max = None

    # Pulsanti finali
    st.markdown("---")
    
    if defaults["id_trasporto"]:  # Solo per record esistenti
        col_update, col_delete = st.columns(2)

        with col_update:
            if st.button("💾 Salva modifiche", key=f"{key_prefix}_salva", use_container_width=True):
                # Validazione
                if not tipo:
                    st.error("❌ Il tipo di trasporto è obbligatorio.")
                elif EF <= 0:
                    st.error("❌ Il fattore di emissione deve essere maggiore di 0.")
                else:
                    try:
                        cursor = conn.cursor()
                        cursor.execute(
                            "UPDATE trasporti SET tipo = ?, EF = ?, capacita_max = ? WHERE id_trasporto = ?",
                            (tipo, EF, capacita_max, defaults["id_trasporto"])
                        )
                        conn.commit()
                        st.success("✅ Modifiche salvate con successo!")
                        st.rerun()
                    except sqlite3.IntegrityError:
                        st.error("❌ Errore: esiste già un trasporto con questo tipo.")
                    except Exception as e:
                        st.error(f"❌ Errore durante il salvataggio: {str(e)}")

        with col_delete:
            # Non permettere l'eliminazione dei trasporti predefiniti (id 0, 1, 2)
            if defaults["id_trasporto"] in [0, 1, 2]:
                st.warning("⚠️ Trasporto predefinito - non eliminabile")
            else:
                if st.button("🗑️ Elimina", key=f"{key_prefix}_elimina", use_container_width=True):
                    st.session_state[f"{key_prefix}_conferma_elimina"] = True

                if st.session_state.get(f"{key_prefix}_conferma_elimina", False):
                    st.markdown(f"**⚠️ Confermi di voler eliminare il trasporto '{tipo}'?**")
                    col_conf, col_annulla = st.columns([1, 1])

                    with col_conf:
                        if st.button("✅ Conferma", key=f"{key_prefix}_conferma", use_container_width=True):
                            # Verifica se il trasporto è utilizzato da qualche allevatore
                            cursor = conn.cursor()
                            cursor.execute("SELECT COUNT(*) FROM allevatore WHERE id_trasporto = ?", 
                                         (defaults["id_trasporto"],))
                            count = cursor.fetchone()[0]
                            
                            if count > 0:
                                st.error(f"❌ Impossibile eliminare: {count} allevatore(i) utilizzano questo trasporto.")
                            else:
                                cursor.execute("DELETE FROM trasporti WHERE id_trasporto = ?", 
                                            (defaults["id_trasporto"],))
                                conn.commit()
                                st.session_state[f"{key_prefix}_conferma_elimina"] = False
                                st.success("✅ Trasporto eliminato con successo!")
                                st.rerun()

                    with col_annulla:
                        if st.button("❌ Annulla", key=f"{key_prefix}_annulla", use_container_width=True):
                            st.session_state[f"{key_prefix}_conferma_elimina"] = False
                            st.rerun()

    # Ritorna i dati per il nuovo trasporto
    return {
        "tipo": tipo,
        "EF": EF,
        "capacita_max": capacita_max
    }


# ---------------------------------------------------------------------------------------- #
# MAIN
# ---------------------------------------------------------------------------------------- #

st.title("🚛 Mezzi di Trasporto")
st.markdown("Gestione dei mezzi di trasporto per il conferimento delle biomasse.")

# Configurazione del database
DB_PATH = "../data.db"  # Modifica con il percorso corretto
conn = sqlite3.connect(DB_PATH)
cursor = conn.cursor()

tab1, tab2 = st.tabs(["✏️ Visualizza e modifica", "➕ Nuovo Trasporto"])

# ---------------------------------------------------------------------------------------- #
# VISUALIZZA E GESTISCI TRASPORTI ESISTENTI
# ---------------------------------------------------------------------------------------- #
with tab1:
    # Carica i dati dei trasporti
    trasporti_df = pd.read_sql_query("""
        SELECT t.*, COUNT(a.id_allevatore) as allevatori_associati
        FROM trasporti t 
        LEFT JOIN allevatore a ON t.id_trasporto = a.id_trasporto
        GROUP BY t.id_trasporto
        ORDER BY t.id_trasporto
    """, conn)

    if len(trasporti_df) == 0:
        st.info("Nessun trasporto trovato nel database.")
    else:
        # Visualizza schede trasporti
        for i, row in trasporti_df.iterrows():
            expander_title = f"🚛 {row['tipo']}"
            with st.expander(expander_title):
                dati = row.to_dict()
                form_trasporto(conn, dati_esistenti=dati, key_prefix=f"trasp_{i}")

# ---------------------------------------------------------------------------------------- #
# AGGIUNGI NUOVO TRASPORTO
# ---------------------------------------------------------------------------------------- #

with tab2:
    st.subheader("Inserisci Nuovo Trasporto")
    
    # Inizializza session_state per il nuovo trasporto
    if 'nuovo_trasporto' not in st.session_state:
        st.session_state.nuovo_trasporto = {}
    
    # Usa il form_trasporto per raccogliere i dati
    with st.form(key="nuovo_trasporto_form"):
        dati_nuovo = form_trasporto(conn, key_prefix="nuovo")
        
        # Pulsante submit
        submitted = st.form_submit_button("💾 Salva Nuovo Trasporto", use_container_width=True)
        
        if submitted:
            # Validazione
            errori = []
            
            if not dati_nuovo["tipo"]:
                errori.append("❌ Il tipo di trasporto è obbligatorio.")
            
            if dati_nuovo["EF"] <= 0:
                errori.append("❌ Il fattore di emissione deve essere maggiore di 0.")
            
            # Controlla se esiste già un trasporto con lo stesso tipo
            cursor.execute("SELECT COUNT(*) FROM trasporti WHERE tipo = ?", 
                         (dati_nuovo["tipo"],))
            if cursor.fetchone()[0] > 0:
                errori.append("❌ Esiste già un trasporto con questo tipo.")
            
            if errori:
                for errore in errori:
                    st.error(errore)
            else:
                try:
                    # Inserimento nel database
                    cursor.execute("""
                        INSERT INTO trasporti (tipo, EF, capacita_max) 
                        VALUES (?, ?, ?)
                    """, (
                        dati_nuovo["tipo"], 
                        dati_nuovo["EF"], 
                        dati_nuovo["capacita_max"]
                    ))
                    
                    conn.commit()
                    st.success("✅ Trasporto creato con successo!")
                    
                    # Reset del form
                    st.session_state.nuovo_trasporto = {}
                    st.rerun()
                    
                except sqlite3.IntegrityError as e:
                    st.error(f"❌ Errore di integrità del database: {str(e)}")
                except Exception as e:
                    st.error(f"❌ Errore durante il salvataggio: {str(e)}")

    # Informazioni sui trasporti predefiniti
    st.markdown("---")
    with st.expander("ℹ️ Informazioni sui trasporti predefiniti"):
        st.markdown("""
        **Trasporti predefiniti (non eliminabili):**
        
        - **Tubazione** (ID: 0): EF = 0 kg CO₂/km, Capacità non specificata
        - **Camion Generico** (ID: 1): EF = 0.1487 kg CO₂/km, Capacità = 25 t
        - **Trattore** (ID: 2): EF = 0.3855 kg CO₂/km, Capacità non specificata
        
        Questi trasporti sono utilizzati dal sistema e non possono essere modificati o eliminati.
        """)

conn.close()