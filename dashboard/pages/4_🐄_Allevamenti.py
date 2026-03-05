import streamlit as st
import pandas as pd
import sqlite3
import sys
import os
import time

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
# FUNZIONI MODIFICATE
# ---------------------------------------------------------------------------------------- #

def form_allevatore(conn, dati_esistenti=None, key_prefix=""):
    """Form per visualizzare e modificare un allevatore - VERSIONE MODIFICATA"""
    
    # Inizializza session state per conferma eliminazione
    if f"{key_prefix}_conferma_elimina" not in st.session_state:
        st.session_state[f"{key_prefix}_conferma_elimina"] = False

    # Valori di default ALLINEATI AL DATABASE
    defaults = {
        "id_allevatore": None,
        "denominazione_sociale": "",
        "id_impianto_associato": None,
        "tipo_conferimento": "Mezzi",
        "frequenza_conferimento_let": 30,
        "frequenza_conferimento_liq": 30,
        "distanza_impianto": 0.0,
        "uba_letame": 0,
        "uba_liquame": 0,
        "prod_letame": 0.0,
        "prod_liquame": 0.0,
        "pollina": None,
        "quota": 0,
        "portata": None,
        "potenza": None,
        "ore": None,
        "sottoprodotti": 0.0,
        "colture": 0.0
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

    st.subheader("Conferimento")
    
    # Tipo conferimento - default sempre "Mezzi"
    tipo_conferimento = st.radio(
        "Tipo Conferimento *",
        ["Mezzi", "Tubazione"],
        index=0 if defaults["tipo_conferimento"].lower() != "tubazione" else 1,
        key=f"{key_prefix}_tipo_conferimento"
    )

    col1, col2 = st.columns(2)
    with col1:
        cursor = conn.cursor()
        cursor.execute("SELECT id_impianto, nome FROM impianto")
        impianti_data = cursor.fetchall()
        impianti_dict = {row[1]: row[0] for row in impianti_data}
        impianti_names = list(impianti_dict.keys())
        
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
        distanza_impianto = st.number_input(
            "Distanza Impianto (km) *", 
            value=defaults["distanza_impianto"], 
            min_value=0.0, 
            step=0.1, 
            key=f"{key_prefix}_distanza"
        )

    col1, col2 = st.columns(2)
    with col1:
        if tipo_conferimento == "Tubazione":
            frequenza_conferimento_let = st.number_input(
                "Freq. Letame (giorni) *", 
                value=0, 
                min_value=0, 
                step=1, 
                key=f"{key_prefix}_frequenza_let",
                disabled=True
            )
        else:
            frequenza_conferimento_let = st.number_input(
                "Freq. Letame (giorni) *", 
                value=defaults["frequenza_conferimento_let"], 
                min_value=1, 
                step=1, 
                key=f"{key_prefix}_frequenza_let"
            )
    with col2:
        frequenza_conferimento_liq = st.number_input(
            "Freq. Liquame (giorni) *", 
            value=defaults["frequenza_conferimento_liq"], 
            min_value=1, 
            step=1, 
            key=f"{key_prefix}_frequenza_liq"
        )

    if tipo_conferimento == "Tubazione":
        st.subheader("Parametri Tubazione")
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

    st.subheader("Dati Zootecnici")
    
    # Modalità inserimento - default sempre "Totali annui assoluti"
    if defaults["uba_letame"] == 1 or defaults["uba_liquame"] == 1:
        modalita_default = "Totali annui assoluti"
    else:
        modalita_default = "Totali annui assoluti"  # default fisso

    modalita_inserimento = st.radio(
        "Modalità di inserimento dati zootecnici:",
        ["Totali annui assoluti", "UBA e produzione annua"],
        index=0 if modalita_default == "Totali annui assoluti" else 1,
        key=f"{key_prefix}_modalita"
    )

    if tipo_conferimento == "Tubazione":
        
        if modalita_inserimento == "Totali annui assoluti":
            col1, col2 = st.columns(2)
            with col1:
                totale_liquame = st.number_input(
                    "Totale Liquame (ton/anno) *", 
                    value=defaults["prod_liquame"] if defaults["uba_liquame"] == 1 else 0.0, 
                    min_value=0.0, 
                    step=0.1,
                    key=f"{key_prefix}_totale_liquame"
                )
            with col2:
                totale_letame = st.number_input(
                    "Totale Letame (ton/anno) *", 
                    value=defaults["prod_letame"] if defaults["uba_letame"] == 1 else 0.0, 
                    min_value=0.0, 
                    step=0.1,
                    key=f"{key_prefix}_totale_letame",
                    disabled=True
                )
            
            uba_letame = 0
            uba_liquame = 1
            prod_letame = 0.0
            prod_liquame = totale_liquame
            
        else:
            col1, col2 = st.columns(2)
            with col1:
                uba_letame = st.number_input(
                    "UBA Letame", 
                    value=0, 
                    min_value=0, 
                    step=1, 
                    key=f"{key_prefix}_uba_letame",
                    disabled=True
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
                    "Prod. Letame (mc/UBA/anno)", 
                    value=0.0, 
                    min_value=0.0, 
                    step=0.1,
                    key=f"{key_prefix}_prod_letame",
                    disabled=True
                )
            with col2:
                prod_liquame = st.number_input(
                    "Prod. Liquame (mc/UBA/anno) *", 
                    value=defaults["prod_liquame"], 
                    min_value=0.0, 
                    step=0.1,
                    key=f"{key_prefix}_prod_liquame"
                )
            
            uba_letame = 0
            prod_letame = 0.0
            
            if uba_liquame > 0 and prod_liquame > 0:
                totale_calc_liquame = uba_liquame * prod_liquame
                st.write(f"**Totale liquame calcolato:** {totale_calc_liquame:.1f} ton/anno")
        
        pollina = 0.0
        st.number_input("Pollina (ton/anno)", value=0.0, min_value=0.0, step=0.1, key=f"{key_prefix}_pollina", disabled=True)
        sottoprodotti = 0.0
        st.number_input("Sottoprodotti (ton/anno)", value=0.0, min_value=0.0, step=0.1, key=f"{key_prefix}_sottoprodotti", disabled=True)
        colture = 0.0
        st.number_input("Colture (ton/anno)", value=0.0, min_value=0.0, step=0.1, key=f"{key_prefix}_colture", disabled=True)
    
    else:
        if modalita_inserimento == "Totali annui assoluti":
            col1, col2 = st.columns(2)
            with col1:
                totale_letame = st.number_input(
                    "Totale Letame (ton/anno) *", 
                    value=defaults["prod_letame"] if defaults["uba_letame"] == 1 else 0.0, 
                    min_value=0.0, 
                    step=0.1,
                    key=f"{key_prefix}_totale_letame"
                )
            with col2:
                totale_liquame = st.number_input(
                    "Totale Liquame (ton/anno) *", 
                    value=defaults["prod_liquame"] if defaults["uba_liquame"] == 1 else 0.0, 
                    min_value=0.0, 
                    step=0.1,
                    key=f"{key_prefix}_totale_liquame"
                )
            
            uba_letame = 1
            uba_liquame = 1
            prod_letame = totale_letame
            prod_liquame = totale_liquame
            
        else:
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
            
            if uba_letame > 0 and prod_letame > 0:
                st.write(f"**Totale letame calcolato:** {uba_letame * prod_letame:.1f} ton/anno")
            if uba_liquame > 0 and prod_liquame > 0:
                st.write(f"**Totale liquame calcolato:** {uba_liquame * prod_liquame:.1f} ton/anno")
        
        pollina = st.number_input("Pollina (ton/anno)", value=defaults["pollina"] or 0.0, min_value=0.0, step=0.1, key=f"{key_prefix}_pollina")
        sottoprodotti = st.number_input("Sottoprodotti (ton/anno)", value=defaults["sottoprodotti"] or 0.0, min_value=0.0, step=0.1, key=f"{key_prefix}_sottoprodotti")
        colture = st.number_input("Colture (ton/anno)", value=defaults["colture"] or 0.0, min_value=0.0, step=0.1, key=f"{key_prefix}_colture")

    st.markdown("---")
    
    if defaults["id_allevatore"]:
        col_update, col_delete = st.columns(2)
        
        with col_update:
            if st.button("💾 Salva modifiche", key=f"{key_prefix}_salva", use_container_width=True):
                try:
                    allevatore_temp = Allevatore(
                        id_allevatore=defaults["id_allevatore"],
                        denominazione_sociale=denominazione_sociale,
                        id_impianto_associato=id_impianto_associato,
                        tipo_conferimento=tipo_conferimento.lower(),
                        frequenza_conferimento_let=frequenza_conferimento_let,
                        frequenza_conferimento_liq=frequenza_conferimento_liq,
                        distanza_impianto=distanza_impianto,
                        uba_letame=uba_letame,
                        uba_liquame=uba_liquame,
                        prod_letame=prod_letame,
                        prod_liquame=prod_liquame,
                        pollina=pollina, 
                        quota=quota,
                        portata=portata,
                        potenza=potenza,
                        ore=ore,
                        sottoprodotti=sottoprodotti,
                        colture=colture
                    )
                    
                    cursor = conn.cursor()
                    cursor.execute("""
                        UPDATE allevatore SET
                            denominazione_sociale = ?, id_impianto_associato = ?, tipo_conferimento = ?,
                            frequenza_conferimento_letame = ?, frequenza_conferimento_liquame = ?, distanza_impianto = ?,
                            uba_letame = ?, uba_liquame = ?, prod_letame = ?, prod_liquame = ?, pollina = ?,
                            quota = ?, portata = ?, potenza = ?, ore = ?, sottoprodotti = ?, colture = ?
                        WHERE id_allevatore = ?
                    """, (
                        denominazione_sociale, id_impianto_associato, tipo_conferimento.lower(),
                        frequenza_conferimento_let, frequenza_conferimento_liq, distanza_impianto,
                        uba_letame, uba_liquame, prod_letame, prod_liquame, pollina,
                        quota, portata, potenza, ore, sottoprodotti, colture,
                        defaults["id_allevatore"]
                    ))
                    
                    conn.commit()
                    st.toast("✅ Modifiche salvate con successo!")
                    time.sleep(1)
                    st.rerun()
                    
                except ValueError as e:
                    st.error(f"❌ Errore di validazione: {str(e)}")
                except Exception as e:
                    st.error(f"❌ Errore durante il salvataggio: {str(e)}")

        with col_delete:
            if st.button("🗑️ Elimina", key=f"{key_prefix}_elimina", use_container_width=True):
                st.session_state[f"{key_prefix}_conferma_elimina"] = True

            if st.session_state[f"{key_prefix}_conferma_elimina"]:
                st.warning(f"**⚠️ Confermi di voler eliminare l'allevatore '{denominazione_sociale}'?**")
                col_conf, col_annulla = st.columns([1, 1])
                with col_conf:
                    if st.button("✅ Conferma", key=f"{key_prefix}_conferma", use_container_width=True):
                        cursor = conn.cursor()
                        cursor.execute("DELETE FROM allevatore WHERE id_allevatore = ?", (defaults["id_allevatore"],))
                        conn.commit()
                        st.session_state[f"{key_prefix}_conferma_elimina"] = False
                        st.toast("✅ Allevatore eliminato con successo!")
                        time.sleep(1)
                        st.rerun()
                with col_annulla:
                    if st.button("❌ Annulla", key=f"{key_prefix}_annulla", use_container_width=True):
                        st.session_state[f"{key_prefix}_conferma_elimina"] = False
                        st.rerun()

    return {
        "denominazione_sociale": denominazione_sociale,
        "id_impianto_associato": id_impianto_associato,
        "tipo_conferimento": tipo_conferimento,
        "frequenza_conferimento_let": frequenza_conferimento_let,
        "frequenza_conferimento_liq": frequenza_conferimento_liq,
        "distanza_impianto": distanza_impianto,
        "uba_letame": uba_letame,
        "uba_liquame": uba_liquame,
        "prod_letame": prod_letame,
        "prod_liquame": prod_liquame,
        "pollina": pollina,
        "quota": quota,
        "portata": portata,
        "potenza": potenza,
        "ore": ore,
        "sottoprodotti": sottoprodotti,
        "colture": colture
    }

# ---------------------------------------------------------------------------------------- #
# MAIN MODIFICATO
# ---------------------------------------------------------------------------------------- #

st.title("🐄 Allevatori")

conn = get_connection()
cursor = conn.cursor()

tab1, tab2 = st.tabs(["✏️ Visualizza e modifica", "➕ Nuovo Allevatore"])

with tab1:
    cursor.execute("SELECT id_impianto, nome FROM impianto")
    impianti_data = cursor.fetchall()
    impianti_options = [("-- Tutti --", None)] + [(row[1], row[0]) for row in impianti_data]
    impianti_names = [row[0] for row in impianti_options]
    
    impianto_sel_name = st.selectbox(
        "Seleziona un impianto per visualizzare gli allevatori associati", 
        impianti_names,
        key="filter_impianto"
    )
    
    impianto_sel_id = None
    for name, id_imp in impianti_options:
        if name == impianto_sel_name:
            impianto_sel_id = id_imp
            break

    if impianto_sel_id is not None:
        query = """
            SELECT a.*, i.nome as nome_impianto
            FROM allevatore a
            LEFT JOIN impianto i ON a.id_impianto_associato = i.id_impianto
            WHERE a.id_impianto_associato = ?
            ORDER BY a.denominazione_sociale
        """
        allevatori_df = pd.read_sql_query(query, conn, params=(impianto_sel_id,))
    else:
        query = """
            SELECT a.*, i.nome as nome_impianto
            FROM allevatore a
            LEFT JOIN impianto i ON a.id_impianto_associato = i.id_impianto
            ORDER BY a.denominazione_sociale
        """
        allevatori_df = pd.read_sql_query(query, conn)

    if len(allevatori_df) == 0:
        st.info("📭 Nessun allevatore trovato nel database.")
    else:
        allevatori_options = [f"{row['id_allevatore']} - {row['denominazione_sociale']}" for _, row in allevatori_df.iterrows()]
        
        selected_allevatore = st.selectbox(
            "Seleziona l'allevatore da visualizzare/modificare",
            allevatori_options,
            key="select_allevatore"
        )
        
        selected_id = int(selected_allevatore.split(" - ")[0])
        selected_data = allevatori_df[allevatori_df['id_allevatore'] == selected_id].iloc[0].to_dict()
        
        st.markdown("---")
        form_allevatore(conn, dati_esistenti=selected_data, key_prefix="selected")

with tab2:

    # Contatore per forzare la ricreazione dei widget dopo il salvataggio
    if "nuovo_allevatore_form_counter" not in st.session_state:
        st.session_state["nuovo_allevatore_form_counter"] = 0

    form_counter = st.session_state["nuovo_allevatore_form_counter"]
    key_prefix_nuovo = f"nuovo_{form_counter}"

    defaults_nuovo = {
        "denominazione_sociale": "",
        "quota": 0,
        "uba_letame": 0,
        "uba_liquame": 0,
        "prod_letame": 16.0,
        "prod_liquame": 22.0,
        "pollina": 0.0,
        "sottoprodotti": 0.0,
        "colture": 0.0,
        "tipo_conferimento": "Mezzi",
        "frequenza_conferimento_let": 30,
        "frequenza_conferimento_liq": 30,
        "distanza_impianto": 0.0,
        "portata": 0.0,
        "potenza": 0.0,
        "ore": 0
    }
    
    dati_nuovo = form_allevatore(conn, dati_esistenti=defaults_nuovo, key_prefix=key_prefix_nuovo)
    
    submitted = st.button("💾 Salva Nuovo Allevatore", use_container_width=True)
    
    if submitted:
        errori = []
        
        if not dati_nuovo["denominazione_sociale"]:
            errori.append("❌ La denominazione sociale è obbligatoria.")
        
        if dati_nuovo["tipo_conferimento"] == "Tubazione":
            if dati_nuovo["uba_liquame"] == 0:
                errori.append("❌ Per il conferimento in tubazione, inserire almeno UBA Liquame.")
            if dati_nuovo["prod_liquame"] == 0:
                errori.append("❌ Per il conferimento in tubazione, inserire almeno la produzione di liquame.")
            if dati_nuovo["portata"] == 0 or dati_nuovo["potenza"] == 0 or dati_nuovo["ore"] == 0:
                errori.append("❌ Per il conferimento in tubazione, portata, potenza e ore sono obbligatorie.")
        else:
            if (dati_nuovo["uba_letame"] == 0 and dati_nuovo["uba_liquame"] == 0 and 
                dati_nuovo["pollina"] == 0 and dati_nuovo["sottoprodotti"] == 0 and dati_nuovo["colture"] == 0):
                errori.append("❌ Inserire almeno UBA Letame, UBA Liquame, Pollina, Sottoprodotti o Colture.")
            if (dati_nuovo["prod_letame"] == 0 and dati_nuovo["prod_liquame"] == 0 and 
                dati_nuovo["pollina"] == 0 and dati_nuovo["sottoprodotti"] == 0 and dati_nuovo["colture"] == 0):
                errori.append("❌ Inserire almeno la produzione di letame, liquame, pollina, sottoprodotti o colture.")
        
        cursor.execute("SELECT COUNT(*) FROM allevatore WHERE denominazione_sociale = ?", 
                     (dati_nuovo["denominazione_sociale"],))
        if cursor.fetchone()[0] > 0:
            errori.append("❌ Esiste già un allevatore con questa denominazione sociale.")
        
        if errori:
            for errore in errori:
                st.error(errore)
        else:
            try:
                nuovo_allevatore = Allevatore(
                    id_allevatore=0,
                    denominazione_sociale=dati_nuovo["denominazione_sociale"],
                    id_impianto_associato=dati_nuovo["id_impianto_associato"],
                    tipo_conferimento=dati_nuovo["tipo_conferimento"].lower(),
                    frequenza_conferimento_let=dati_nuovo["frequenza_conferimento_let"],
                    frequenza_conferimento_liq=dati_nuovo["frequenza_conferimento_liq"],
                    distanza_impianto=dati_nuovo["distanza_impianto"],
                    uba_letame=dati_nuovo["uba_letame"],
                    uba_liquame=dati_nuovo["uba_liquame"],
                    prod_letame=dati_nuovo["prod_letame"],
                    prod_liquame=dati_nuovo["prod_liquame"],
                    pollina=dati_nuovo["pollina"],
                    quota=dati_nuovo["quota"],
                    portata=dati_nuovo["portata"],
                    potenza=dati_nuovo["potenza"],
                    ore=dati_nuovo["ore"],
                    sottoprodotti=dati_nuovo["sottoprodotti"],
                    colture=dati_nuovo["colture"]
                )
                
                cursor.execute("""
                    INSERT INTO allevatore (
                        denominazione_sociale, id_impianto_associato, tipo_conferimento,
                        frequenza_conferimento_letame, frequenza_conferimento_liquame, distanza_impianto,
                        uba_letame, uba_liquame, prod_letame, prod_liquame, pollina, sottoprodotti, colture,
                        quota, portata, potenza, ore
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    dati_nuovo["denominazione_sociale"], 
                    dati_nuovo["id_impianto_associato"], 
                    dati_nuovo["tipo_conferimento"].lower(),
                    dati_nuovo["frequenza_conferimento_let"],
                    dati_nuovo["frequenza_conferimento_liq"],
                    dati_nuovo["distanza_impianto"],
                    dati_nuovo["uba_letame"], 
                    dati_nuovo["uba_liquame"], 
                    dati_nuovo["prod_letame"], 
                    dati_nuovo["prod_liquame"],
                    dati_nuovo["pollina"], 
                    dati_nuovo["sottoprodotti"],
                    dati_nuovo["colture"],
                    dati_nuovo["quota"], 
                    dati_nuovo["portata"], 
                    dati_nuovo["potenza"], 
                    dati_nuovo["ore"]
                ))
                
                conn.commit()
                st.toast("✅ Allevatore creato con successo!")
                time.sleep(1)
                # Incrementa il contatore: Streamlit ricrea tutti i widget da zero
                st.session_state["nuovo_allevatore_form_counter"] += 1
                st.rerun()
                
            except ValueError as e:
                st.error(f"❌ Errore di validazione: {str(e)}")
            except sqlite3.IntegrityError as e:
                st.error(f"❌ Errore di integrità del database: {str(e)}")
            except Exception as e:
                st.error(f"❌ Errore durante il salvataggio: {str(e)}")

conn.close()
