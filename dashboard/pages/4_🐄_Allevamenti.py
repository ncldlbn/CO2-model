import streamlit as st
import pandas as pd
import sqlite3
import sys
import os

from db import get_connection, create_tables

sys.path.append(os.path.join(os.path.dirname(__file__), '../../src'))
from objects import Allevatore 

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

def form_allevatore(conn, dati_esistenti=None, key_prefix=""):
    """Form per visualizzare e modificare un allevatore"""
    
    # Valori di default
    defaults = {
        "id_allevatore": None,
        "denominazione_sociale": "",
        "id_impianto_associato": None,
        "tipo_conferimento": "mezzi",
        "frequenza_conferimento": 7,
        "id_trasporto": None,
        "distanza_impianto": 0.0,
        "uba_letame": 0,
        "uba_liquame": 0,
        "prod_letame": 0.0,
        "prod_liquame": 0.0,
        "deposito_max": 0.0,
        "quota": 0,
        "portata": None,
        "potenza": None,
        "ore": None
    }

    if dati_esistenti:
        defaults.update(dati_esistenti)

    st.subheader("Anagrafica Allevatore")
    col1, col2 = st.columns(2)
    with col1:
        denominazione_sociale = st.text_input(
            "Denominazione Sociale *", 
            value=defaults["denominazione_sociale"], 
            key=f"{key_prefix}_denominazione"
        )
    with col2:
        quota = st.number_input(
            "Quota [m slm]", 
            value=defaults["quota"], 
            min_value=0, 
            step=1, 
            key=f"{key_prefix}_quota"
        )

    st.subheader("Dati Zootecnici")
    col1, col2 = st.columns(2)
    with col1:
        uba_letame = st.number_input(
            "UBA Letame *", 
            value=defaults["uba_letame"], 
            min_value=0, 
            step=1, 
            key=f"{key_prefix}_uba_letame"
        )
    with col2:
        uba_liquame = st.number_input(
            "UBA Liquame *", 
            value=defaults["uba_liquame"], 
            min_value=0, 
            step=1, 
            key=f"{key_prefix}_uba_liquame"
        )
    col1, col2 = st.columns(2)
    with col1:
        prod_letame = st.number_input(
            "Prod. Letame (mc/UBA/anno) *", 
            value=defaults["prod_letame"], 
            min_value=0.0, 
            step=0.1,
            key=f"{key_prefix}_prod_letame"
        )
    with col2:
        prod_liquame = st.number_input(
            "Prod. Liquame (mc/UBA/anno) *", 
            value=defaults["prod_liquame"], 
            min_value=0.0, 
            step=0.1,
            key=f"{key_prefix}_prod_liquame"
        )

    deposito_max = st.number_input(
        "Capacità max deposito (mc) *", 
        value=defaults["deposito_max"], 
        min_value=0.0, 
        step=1.0, 
        key=f"{key_prefix}_deposito_max"
    )

    st.subheader("Conferimento")
    
    # Tipo conferimento
    tipo_conferimento = st.radio(
        "Tipo Conferimento *",
        ["mezzi", "tubazione"],
        index=0 if defaults["tipo_conferimento"] == "mezzi" else 1,
        key=f"{key_prefix}_tipo_conferimento"
    )

    col1, col2 = st.columns(2)
    with col1:
        # Selezione impianto
        cursor = conn.cursor()
        cursor.execute("SELECT id_impianto, nome FROM impianto")
        impianti_data = cursor.fetchall()
        impianti_dict = {row[1]: row[0] for row in impianti_data}
        impianti_names = list(impianti_dict.keys())
        
        # Trova il nome dell'impianto corrente
        current_impianto_name = None
        if defaults["id_impianto_associato"]:
            cursor.execute("SELECT nome FROM impianto WHERE id_impianto = ?", (defaults["id_impianto_associato"],))
            current_impianto = cursor.fetchone()
            current_impianto_name = current_impianto[0] if current_impianto else None
        
        impianto_index = impianti_names.index(current_impianto_name) if current_impianto_name in impianti_names else 0
        impianto_selected = st.selectbox(
            "Impianto Associato *",
            impianti_names,
            index=impianto_index,
            key=f"{key_prefix}_impianto"
        )
        id_impianto_associato = impianti_dict[impianto_selected]

    with col2:
        # Selezione trasporto - condizionale in base al tipo di conferimento
        cursor.execute("SELECT id_trasporto, tipo FROM trasporti")
        trasporti_data = cursor.fetchall()
        trasporti_dict = {row[1]: row[0] for row in trasporti_data}
        
        if tipo_conferimento == "tubazione":
            # Per tubazione, imposta automaticamente il trasporto a "tubazione"
            id_trasporto = 0  # ID fisso per tubazione
            trasporto_selected = "tubazione"
            st.selectbox(
                "Tipo trasporto *",
                ["tubazione"],
                index=0,
                key=f"{key_prefix}_trasporto",
                disabled=True
            )
        else:
            # Per mezzi, mostra solo i trasporti che non sono tubazione
            trasporti_mezzi = {name: id for name, id in trasporti_dict.items() if name != "tubazione"}
            trasporti_names = list(trasporti_mezzi.keys())
            
            # Trova il tipo del trasporto corrente (escludendo tubazione)
            current_trasporto_name = None
            if defaults["id_trasporto"] and defaults["id_trasporto"] != 0:
                cursor.execute("SELECT tipo FROM trasporti WHERE id_trasporto = ?", (defaults["id_trasporto"],))
                current_trasporto = cursor.fetchone()
                current_trasporto_name = current_trasporto[0] if current_trasporto else None
            
            trasporto_index = trasporti_names.index(current_trasporto_name) if current_trasporto_name in trasporti_names else 0
            trasporto_selected = st.selectbox(
                "Tipo trasporto *",
                trasporti_names,
                index=trasporto_index,
                key=f"{key_prefix}_trasporto"
            )
            id_trasporto = trasporti_mezzi[trasporto_selected]

    # Mostra frequenza e distanza solo per conferimento con mezzi
    if tipo_conferimento == "mezzi":
        col1, col2 = st.columns(2)
        with col1:
            frequenza_conferimento = st.number_input(
                "Frequenza Conferimento (giorni) *", 
                value=defaults["frequenza_conferimento"], 
                min_value=1, 
                step=1, 
                key=f"{key_prefix}_frequenza"
            )
        with col2:
            distanza_impianto = st.number_input(
                "Distanza Impianto (km) *", 
                value=defaults["distanza_impianto"], 
                min_value=0.0, 
                step=0.1, 
                key=f"{key_prefix}_distanza"
            )
    else:
        # Per tubazione, usa valori predefiniti
        frequenza_conferimento = 1  # Valore predefinito
        distanza_impianto = 0.0     # Valore predefinito

    # Campi condizionali per tubazione
    if tipo_conferimento == "tubazione":
        col1, col2, col3 = st.columns(3)
        with col1:
            portata = st.number_input(
                "Portata (mc/h) *", 
                value=defaults["portata"] or 0.0, 
                min_value=0.0, 
                step=0.1, 
                key=f"{key_prefix}_portata"
            )
        with col2:
            potenza = st.number_input(
                "Potenza (kW) *", 
                value=defaults["potenza"] or 0.0, 
                min_value=0.0, 
                step=0.1, 
                key=f"{key_prefix}_potenza"
            )
        with col3:
            ore = st.number_input(
                "Ore di funzionamento *", 
                value=defaults["ore"] or 0, 
                min_value=0, 
                step=1, 
                key=f"{key_prefix}_ore"
            )
    else:
        portata = None
        potenza = None
        ore = None

    # Pulsanti finali
    st.markdown("---")
    
    if defaults["id_allevatore"]:  # Solo per record esistenti
        col_update, col_delete = st.columns(2)
        
        with col_update:
            if st.button("💾 Salva modifiche", key=f"{key_prefix}_salva", use_container_width=True):
                try:
                    # Validazione usando la classe Allevatore
                    allevatore_temp = Allevatore(
                        id_allevatore=defaults["id_allevatore"],
                        denominazione_sociale=denominazione_sociale,
                        id_impianto_associato=id_impianto_associato,
                        tipo_conferimento=tipo_conferimento,
                        frequenza_conferimento=frequenza_conferimento,
                        id_trasporto=id_trasporto,
                        distanza_impianto=distanza_impianto,
                        uba_letame=uba_letame,
                        uba_liquame=uba_liquame,
                        prod_letame=prod_letame,
                        prod_liquame=prod_liquame,
                        deposito_max=deposito_max,
                        quota=quota,
                        portata=portata,
                        potenza=potenza,
                        ore=ore
                    )
                    
                    cursor = conn.cursor()
                    cursor.execute("""
                        UPDATE allevatore SET
                            denominazione_sociale = ?, id_impianto_associato = ?, tipo_conferimento = ?,
                            frequenza_conferimento = ?, id_trasporto = ?, distanza_impianto = ?,
                            uba_letame = ?, uba_liquame = ?, prod_letame = ?, prod_liquame = ?,
                            deposito_max = ?, quota = ?, portata = ?, potenza = ?, ore = ?
                        WHERE id_allevatore = ?
                    """, (
                        denominazione_sociale, id_impianto_associato, tipo_conferimento,
                        frequenza_conferimento, id_trasporto, distanza_impianto,
                        uba_letame, uba_liquame, prod_letame, prod_liquame,
                        deposito_max, quota, portata, potenza, ore,
                        defaults["id_allevatore"]
                    ))
                    
                    conn.commit()
                    st.success("✅ Modifiche salvate con successo!")
                    st.rerun()
                    
                except ValueError as e:
                    st.error(f"❌ Errore di validazione: {str(e)}")
                except Exception as e:
                    st.error(f"❌ Errore durante il salvataggio: {str(e)}")

        with col_delete:
            if st.button("🗑️ Elimina", key=f"{key_prefix}_elimina", use_container_width=True):
                st.session_state[f"{key_prefix}_conferma_elimina"] = True

            if st.session_state.get(f"{key_prefix}_conferma_elimina", False):
                st.markdown(f"**⚠️ Confermi di voler eliminare l'allevatore '{denominazione_sociale}'?**")
                col_conf, col_annulla = st.columns([1, 1])
                with col_conf:
                    if st.button("✅ Conferma", key=f"{key_prefix}_conferma", use_container_width=True):
                        cursor = conn.cursor()
                        cursor.execute("DELETE FROM allevatore WHERE id_allevatore = ?", (defaults["id_allevatore"],))
                        conn.commit()
                        st.session_state[f"{key_prefix}_conferma_elimina"] = False
                        st.success("✅ Allevatore eliminato con successo!")
                        st.rerun()
                with col_annulla:
                    if st.button("❌ Annulla", key=f"{key_prefix}_annulla", use_container_width=True):
                        st.session_state[f"{key_prefix}_conferma_elimina"] = False
                        st.rerun()
    else:
        # Per nuovo allevatore, il salvataggio è gestito nel form principale
        pass

    # Ritorna i dati per il nuovo allevatore
    return {
        "denominazione_sociale": denominazione_sociale,
        "id_impianto_associato": id_impianto_associato,
        "tipo_conferimento": tipo_conferimento,
        "frequenza_conferimento": frequenza_conferimento,
        "id_trasporto": id_trasporto,
        "distanza_impianto": distanza_impianto,
        "uba_letame": uba_letame,
        "uba_liquame": uba_liquame,
        "prod_letame": prod_letame,
        "prod_liquame": prod_liquame,
        "deposito_max": deposito_max,
        "quota": quota,
        "portata": portata,
        "potenza": potenza,
        "ore": ore
    }

# ---------------------------------------------------------------------------------------- #
# MAIN
# ---------------------------------------------------------------------------------------- #

st.title("🐄 Allevatori")
st.markdown("In questa pagina è possibile visualizzare e modificare i dati relativi agli allevatori, oltre che inserirne di nuovi.")

# Configurazione del database
DB_PATH = "../data.db"  # Modifica con il percorso corretto
conn = sqlite3.connect(DB_PATH)
cursor = conn.cursor()

tab1, tab2 = st.tabs(["✏️ Visualizza e modifica", "➕ Nuovo Allevatore"])

# ---------------------------------------------------------------------------------------- #
# VISUALIZZA E GESTISCI ALLEVATORI ESISTENTI
# ---------------------------------------------------------------------------------------- #

with tab1:
    # Seleziona l'impianto per filtrare
    cursor.execute("SELECT id_impianto, nome FROM impianto")
    impianti_data = cursor.fetchall()
    impianti_options = [("-- Tutti --", None)] + [(row[1], row[0]) for row in impianti_data]
    impianti_names = [row[0] for row in impianti_options]
    
    impianto_sel_name = st.selectbox(
        "Seleziona un impianto per visualizzare gli allevatori associati", 
        impianti_names,
        key="filter_impianto"
    )
    
    # Trova l'ID dell'impianto selezionato
    impianto_sel_id = None
    for name, id_imp in impianti_options:
        if name == impianto_sel_name:
            impianto_sel_id = id_imp
            break

    # Query al database
    if impianto_sel_id is not None:
        query = """
            SELECT a.*, i.nome as nome_impianto, t.tipo as tipo_trasporto
            FROM allevatore a
            LEFT JOIN impianto i ON a.id_impianto_associato = i.id_impianto
            LEFT JOIN trasporti t ON a.id_trasporto = t.id_trasporto
            WHERE a.id_impianto_associato = ?
            ORDER BY a.denominazione_sociale
        """
        allevatori_df = pd.read_sql_query(query, conn, params=(impianto_sel_id,))
    else:
        query = """
            SELECT a.*, i.nome as nome_impianto, t.tipo as tipo_trasporto
            FROM allevatore a
            LEFT JOIN impianto i ON a.id_impianto_associato = i.id_impianto
            LEFT JOIN trasporti t ON a.id_trasporto = t.id_trasporto
            ORDER BY a.denominazione_sociale
        """
        allevatori_df = pd.read_sql_query(query, conn)
        
        # Visualizza schede allevatori
        for i, row in allevatori_df.iterrows():
            expander_title = f"🐄 {row['denominazione_sociale']}"
            with st.expander(expander_title):
                dati = row.to_dict()
                form_allevatore(conn, dati_esistenti=dati, key_prefix=f"allev_{i}")

# ---------------------------------------------------------------------------------------- #
# AGGIUNGI NUOVO ALLEVATORE
# ---------------------------------------------------------------------------------------- #

with tab2:
    st.subheader("Inserisci Nuovo Allevatore")
    
    # Inizializza session_state per il nuovo allevatore con valori di default
    if 'nuovo_allevatore' not in st.session_state:
        st.session_state.nuovo_allevatore = {
            "denominazione_sociale": "",
            "quota": 0,
            "uba_letame": 0,
            "uba_liquame": 0,
            "prod_letame": 16.0,
            "prod_liquame": 22.0,
            "deposito_max": 0.0,
            "tipo_conferimento": "mezzi",
            "frequenza_conferimento": 1,
            "distanza_impianto": 0.0,
            "portata": 0.0,
            "potenza": 0.0,
            "ore": 0
        }
    
    # Usa il form_allevatore per raccogliere i dati
    with st.form(key="nuovo_allevatore_form"):
        dati_nuovo = form_allevatore(conn, dati_esistenti=st.session_state.nuovo_allevatore, key_prefix="nuovo")
        
        # Pulsante submit
        submitted = st.form_submit_button("💾 Salva Nuovo Allevatore", use_container_width=True)
        
        if submitted:
            # Validazione
            errori = []
            
            if not dati_nuovo["denominazione_sociale"]:
                errori.append("❌ La denominazione sociale è obbligatoria.")
            
            if dati_nuovo["uba_letame"] == 0 and dati_nuovo["uba_liquame"] == 0:
                errori.append("❌ Inserire almeno UBA Letame o UBA Liquame.")
            
            if dati_nuovo["prod_letame"] == 0 and dati_nuovo["prod_liquame"] == 0:
                errori.append("❌ Inserire almeno la produzione di letame o liquame.")
            
            if dati_nuovo["deposito_max"] == 0:
                errori.append("❌ La capacità del deposito è obbligatoria.")
            
            if dati_nuovo["tipo_conferimento"] == "tubazione":
                if dati_nuovo["portata"] == 0 or dati_nuovo["potenza"] == 0 or dati_nuovo["ore"] == 0:
                    errori.append("❌ Per il conferimento in tubazione, portata, potenza e ore sono obbligatorie.")
            else:
                # Per conferimento con mezzi, valida frequenza e distanza
                if dati_nuovo["frequenza_conferimento"] == 0:
                    errori.append("❌ La frequenza di conferimento è obbligatoria per il conferimento con mezzi.")
                if dati_nuovo["distanza_impianto"] == 0:
                    errori.append("❌ La distanza dall'impianto è obbligatoria per il conferimento con mezzi.")
            
            # Controlla se esiste già un allevatore con lo stesso nome
            cursor.execute("SELECT COUNT(*) FROM allevatore WHERE denominazione_sociale = ?", 
                         (dati_nuovo["denominazione_sociale"],))
            if cursor.fetchone()[0] > 0:
                errori.append("❌ Esiste già un allevatore con questa denominazione sociale.")
            
            if errori:
                for errore in errori:
                    st.error(errore)
            else:
                try:
                    # Validazione con la classe Allevatore
                    nuovo_allevatore = Allevatore(
                        id_allevatore=0,  # Temporaneo, sarà auto-increment dal DB
                        denominazione_sociale=dati_nuovo["denominazione_sociale"],
                        id_impianto_associato=dati_nuovo["id_impianto_associato"],
                        tipo_conferimento=dati_nuovo["tipo_conferimento"],
                        frequenza_conferimento=dati_nuovo["frequenza_conferimento"],
                        id_trasporto=dati_nuovo["id_trasporto"],
                        distanza_impianto=dati_nuovo["distanza_impianto"],
                        uba_letame=dati_nuovo["uba_letame"],
                        uba_liquame=dati_nuovo["uba_liquame"],
                        prod_letame=dati_nuovo["prod_letame"],
                        prod_liquame=dati_nuovo["prod_liquame"],
                        deposito_max=dati_nuovo["deposito_max"],
                        quota=dati_nuovo["quota"],
                        portata=dati_nuovo["portata"],
                        potenza=dati_nuovo["potenza"],
                        ore=dati_nuovo["ore"]
                    )
                    
                    # Inserimento nel database
                    cursor.execute("""
                        INSERT INTO allevatore (
                            denominazione_sociale, id_impianto_associato, tipo_conferimento,
                            frequenza_conferimento, id_trasporto, distanza_impianto,
                            uba_letame, uba_liquame, prod_letame, prod_liquame,
                            deposito_max, quota, portata, potenza, ore
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """, (
                        dati_nuovo["denominazione_sociale"], 
                        dati_nuovo["id_impianto_associato"], 
                        dati_nuovo["tipo_conferimento"],
                        dati_nuovo["frequenza_conferimento"], 
                        dati_nuovo["id_trasporto"], 
                        dati_nuovo["distanza_impianto"],
                        dati_nuovo["uba_letame"], 
                        dati_nuovo["uba_liquame"], 
                        dati_nuovo["prod_letame"], 
                        dati_nuovo["prod_liquame"],
                        dati_nuovo["deposito_max"], 
                        dati_nuovo["quota"], 
                        dati_nuovo["portata"], 
                        dati_nuovo["potenza"], 
                        dati_nuovo["ore"]
                    ))
                    
                    conn.commit()
                    st.success("✅ Allevatore creato con successo!")
                    
                    # Reset del form con valori di default
                    st.session_state.nuovo_allevatore = {
                        "denominazione_sociale": "",
                        "quota": 0,
                        "uba_letame": 0,
                        "uba_liquame": 0,
                        "prod_letame": 16.0,
                        "prod_liquame": 22.0,
                        "deposito_max": 0.0,
                        "tipo_conferimento": "mezzi",
                        "frequenza_conferimento": 0,
                        "distanza_impianto": 0.0,
                        "portata": 0.0,
                        "potenza": 0.0,
                        "ore": 0
                    }
                    st.rerun()
                    
                except ValueError as e:
                    st.error(f"❌ Errore di validazione: {str(e)}")
                except sqlite3.IntegrityError as e:
                    st.error(f"❌ Errore di integrità del database: {str(e)}")
                except Exception as e:
                    st.error(f"❌ Errore durante il salvataggio: {str(e)}")

conn.close()