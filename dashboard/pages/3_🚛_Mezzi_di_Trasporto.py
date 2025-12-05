import streamlit as st
import pandas as pd
import sqlite3
import sys
import os
import time

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

def form_trasporto(conn, dati_esistenti=None, key_prefix="", is_nuovo=False):
    """Form per visualizzare e modificare un trasporto"""

    # Valori di default
    defaults = {
        "id_trasporto": None,
        "tipo": "",
        "capacita_max": None,
        "fattore_emissione": 0.0
    }

    if dati_esistenti:
        defaults.update(dati_esistenti)

    tipo = st.text_input("Nome *", 
                         value=defaults["tipo"], 
                         key=f"{key_prefix}_tipo",
                         disabled=(not is_nuovo and defaults["id_trasporto"] is not None))

    # Gestione capacità massima (può essere NULL per alcuni trasporti)
    if tipo != "tubazione" and tipo != "Tubazione":
        capacita_max = st.number_input("Capacità massima (mc) *", 
                                     value=float(defaults["capacita_max"] or 0.0), 
                                     min_value=0.0, 
                                     step=0.1,
                                     key=f"{key_prefix}_capacita")
    else:
        capacita_max = None

    # Aggiungi campo per il fattore di emissione per entrambi i casi
    if not is_nuovo and defaults["id_trasporto"] is not None:
        # Per trasporti esistenti, mostra sempre il fattore di emissione
        fattore_emissione = st.number_input(
            "Fattore di emissione (kg CO2eq/tkm) *",
            min_value=0.0,
            step=0.01,
            value=float(defaults.get("fattore_emissione", 0.0)),
            help="Emissioni di CO2 equivalenti per tonnellata-chilometro",
            key=f"{key_prefix}_fattore"
        )
    elif is_nuovo:
        # Per nuovi trasporti
        fattore_emissione = st.number_input(
            "Fattore di emissione (kg CO2eq/tkm) *",
            min_value=0.0,
            step=0.01,
            value=0.0,
            help="Emissioni di CO2 equivalenti per tonnellata-chilometro",
            key=f"{key_prefix}_fattore"
        )
    else:
        fattore_emissione = None
    
    # Pulsanti finali
    st.markdown("---")
    
    # CORREZIONE: Mostra i pulsanti per tutti i record esistenti, incluso quelli con id_trasporto = 0
    if defaults["id_trasporto"] is not None and not is_nuovo:  # Solo per trasporti esistenti
        col_update, col_delete = st.columns(2)

        with col_update:
            if st.button("💾 Salva modifiche", key=f"{key_prefix}_salva", use_container_width=True):
                # Validazione
                errori = []
                
                if not tipo:
                    errori.append("❌ Il tipo di trasporto è obbligatorio.")
                
                if errori:
                    for errore in errori:
                        st.error(errore)
                else:
                    try:
                        cursor = conn.cursor()
                        # Aggiorna la tabella trasporti
                        cursor.execute(
                            "UPDATE trasporti SET tipo = ?, capacita_max = ? WHERE id_trasporto = ?",
                            (tipo, capacita_max, defaults["id_trasporto"])
                        )
                        
                        # Aggiorna o inserisce il fattore di emissione
                        cursor.execute("""
                            SELECT COUNT(*) FROM fattori_emissione 
                            WHERE categoria = 'trasporti' AND nome = ?
                        """, (defaults["tipo"],))
                        
                        if cursor.fetchone()[0] > 0:
                            # Aggiorna il fattore esistente
                            cursor.execute("""
                                UPDATE fattori_emissione 
                                SET nome = ?, CO2_fossile = ?, CO2_TOT = ?
                                WHERE categoria = 'trasporti' AND nome = ?
                            """, (
                                tipo,  # nuovo nome
                                float(fattore_emissione),
                                float(fattore_emissione),
                                defaults["tipo"]  # vecchio nome
                            ))
                        else:
                            # Inserisce un nuovo fattore
                            cursor.execute("""
                                INSERT INTO fattori_emissione 
                                (categoria, nome, unita, CO2_fossile, CO2_biogenica, CO2_dLUC, CO2_TOT)
                                VALUES (?, ?, ?, ?, ?, ?, ?)
                            """, (
                                "trasporti",
                                tipo,
                                "kg CO2eq/tkm",
                                float(fattore_emissione),
                                0.0,
                                0.0,
                                float(fattore_emissione)
                            ))
                        
                        conn.commit()
                        st.toast("✅ Modifiche salvate con successo!")
                        time.sleep(1)
                        st.rerun()
                    except sqlite3.IntegrityError as e:
                        st.error(f"❌ Errore di integrità: {str(e)}")
                    except Exception as e:
                        st.error(f"❌ Errore durante il salvataggio: {str(e)}")

        with col_delete:
            # Non permettere l'eliminazione dei trasporti predefiniti (id 0, 1, 2)
            if defaults["id_trasporto"] not in [0, 1, 2]:
                if st.button("🗑️ Elimina", key=f"{key_prefix}_elimina", use_container_width=True):
                    st.session_state[f"{key_prefix}_conferma_elimina"] = True

                if st.session_state.get(f"{key_prefix}_conferma_elimina", False):
                    st.markdown(f"**⚠️ Confermi di voler eliminare il trasporto '{tipo}'?**")
                    col_conf, col_annulla = st.columns([1, 1])

                    with col_conf:
                        if st.button("✅ Conferma", key=f"{key_prefix}_conferma", use_container_width=True):
                            try:
                                cursor = conn.cursor()
                                # Elimina prima il fattore di emissione associato
                                cursor.execute("DELETE FROM fattori_emissione WHERE categoria = 'trasporti' AND nome = ?", 
                                            (tipo,))
                                # Poi elimina il trasporto
                                cursor.execute("DELETE FROM trasporti WHERE id_trasporto = ?", 
                                            (defaults["id_trasporto"],))
                                conn.commit()
                                st.session_state[f"{key_prefix}_conferma_elimina"] = False
                                st.toast("✅ Trasporto eliminato con successo!")
                                time.sleep(1)
                                st.rerun()
                            except sqlite3.IntegrityError as e:
                                st.error("❌ Non è possibile eliminare il trasporto perché è referenziato da altri record.")
                            except Exception as e:
                                st.error(f"❌ Errore durante l'eliminazione: {str(e)}")

                    with col_annulla:
                        if st.button("❌ Annulla", key=f"{key_prefix}_annulla", use_container_width=True):
                            st.session_state[f"{key_prefix}_conferma_elimina"] = False
                            st.rerun()

    # Ritorna i dati per il nuovo trasporto
    return {
        "tipo": tipo,
        "capacita_max": capacita_max,
        "fattore_emissione": fattore_emissione if fattore_emissione is not None else defaults.get("fattore_emissione", 0.0)
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

tab1, tab2 = st.tabs(["✏️ Visualizza e modifica", "➕ Nuovo Trasporto"])

# ---------------------------------------------------------------------------------------- #
# VISUALIZZA E GESTISCI TRASPORTI ESISTENTI - MODIFICATO
# ---------------------------------------------------------------------------------------- #
with tab1:
    # Carica i dati dei trasporti con i fattori di emissione
    trasporti_df = pd.read_sql_query("""
        SELECT t.*, 
               COUNT(a.id_allevatore) as allevatori_associati,
               COALESCE(fe.CO2_TOT, 0) as fattore_emissione
        FROM trasporti t 
        LEFT JOIN allevatore a ON t.id_trasporto = a.id_trasporto
        LEFT JOIN fattori_emissione fe ON t.tipo = fe.nome AND fe.categoria = 'trasporti'
        GROUP BY t.id_trasporto
        ORDER BY t.id_trasporto
    """, conn)

    if len(trasporti_df) == 0:
        st.info("Nessun trasporto trovato nel database.")
    else:
               
        # Seleziona il trasporto da visualizzare/modificare
        trasporti_options = [f"{row['id_trasporto']} - {row['tipo']}" for _, row in trasporti_df.iterrows()]
        
        selected_trasporto = st.selectbox(
            "Seleziona il trasporto da visualizzare/modificare",
            trasporti_options,
            key="select_trasporto"
        )
        
        # Trova i dati del trasporto selezionato
        selected_id = int(selected_trasporto.split(" - ")[0])
        selected_data = trasporti_df[trasporti_df['id_trasporto'] == selected_id].iloc[0].to_dict()
                
        # Mostra il form per il trasporto selezionato
        form_trasporto(conn, dati_esistenti=selected_data, key_prefix="selected", is_nuovo=False)

# ---------------------------------------------------------------------------------------- #
# AGGIUNGI NUOVO TRASPORTO CON FATTORE DI EMISSIONE
# ---------------------------------------------------------------------------------------- #

with tab2:
    
    # Inizializza session_state per il nuovo trasporto
    if 'nuovo_trasporto' not in st.session_state:
        st.session_state.nuovo_trasporto = {}
    
    # Usa il form_trasporto per raccogliere i dati (is_nuovo=True per includere il fattore di emissione)
    with st.form(key="nuovo_trasporto_form"):
        dati_nuovo = form_trasporto(conn, key_prefix="nuovo", is_nuovo=True)
        
        # Pulsante submit
        submitted = st.form_submit_button("💾 Salva Nuovo Trasporto", use_container_width=True)
        
        if submitted:
            # Validazione
            errori = []
            
            if not dati_nuovo["tipo"]:
                errori.append("❌ Il tipo di trasporto è obbligatorio.")
            
            # Correzione: controlla se il fattore di emissione è stato inserito (può essere 0)
            if dati_nuovo["fattore_emissione"] is None:
                errori.append("❌ Il fattore di emissione è obbligatorio.")
            
            # Controlla se esiste già un trasporto con lo stesso tipo
            cursor.execute("SELECT COUNT(*) FROM trasporti WHERE tipo = ?", 
                         (dati_nuovo["tipo"],))
            if cursor.fetchone()[0] > 0:
                errori.append("❌ Esiste già un trasporto con questo tipo.")
            
            # Controlla se esiste già un fattore di emissione con lo stesso nome
            cursor.execute("SELECT COUNT(*) FROM fattori_emissione WHERE categoria = 'trasporti' AND nome = ?", 
                         (dati_nuovo["tipo"],))
            if cursor.fetchone()[0] > 0:
                errori.append("❌ Esiste già un fattore di emissione per questo tipo di trasporto.")
            
            if errori:
                for errore in errori:
                    st.error(errore)
            else:
                try:
                    # Inserimento nel database
                    conn.execute("BEGIN TRANSACTION")
                    
                    # 1. Inserimento nella tabella trasporti
                    cursor.execute("""
                        INSERT INTO trasporti (tipo, capacita_max) 
                        VALUES (?, ?)
                    """, (
                        dati_nuovo["tipo"], 
                        dati_nuovo["capacita_max"]
                    ))
                    
                    # 2. Inserimento nella tabella fattori_emissione
                    cursor.execute("""
                        INSERT INTO fattori_emissione 
                        (categoria, nome, unita, CO2_fossile, CO2_biogenica, CO2_dLUC, CO2_TOT)
                        VALUES (?, ?, ?, ?, ?, ?, ?)
                    """, (
                        "trasporti",                    # categoria
                        dati_nuovo["tipo"],             # nome (stesso nome del trasporto)
                        "kg CO2eq/tkm",                 # unità
                        float(dati_nuovo["fattore_emissione"]),  # CO2_fossile
                        0.0,                            # CO2_biogenica
                        0.0,                            # CO2_dLUC
                        float(dati_nuovo["fattore_emissione"])   # CO2_TOT
                    ))
                    
                    conn.commit()
                    st.success("✅ Trasporto e fattore di emissione creati con successo!")
                    
                    # Reset del form
                    st.session_state.nuovo_trasporto = {}
                    time.sleep(2)
                    st.rerun()
                    
                except sqlite3.IntegrityError as e:
                    conn.rollback()
                    st.error(f"❌ Errore di integrità del database: {str(e)}")
                except sqlite3.Error as e:
                    conn.rollback()
                    st.error(f"❌ Errore SQL durante il salvataggio: {str(e)}")
                except Exception as e:
                    conn.rollback()
                    st.error(f"❌ Errore imprevisto: {str(e)}")
                    import traceback
                    st.error(traceback.format_exc())

conn.close()