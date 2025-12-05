import streamlit as st
import pandas as pd
from db import get_connection, create_tables
import sqlite3
import time 

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
def form_impianto(conn, dati_esistenti=None, key_prefix=""):
    """Form per visualizzare e modificare un impianto con bilancio energetico strutturato e ricettori"""

    # Valori di default allineati alla struttura del DB
    defaults = {
        "id_impianto": None,
        "nome": "",
        "separazione": 0.00,
        "olio_lubrificante": 0.0,
        "rifiuti": 0.0,
        "acqua": 0.0,
        "scarichi": 0.0
    }

    if dati_esistenti:
        for key in defaults:
            val = dati_esistenti.get(key)
            if val is not None:
                defaults[key] = val

    # Creiamo il cursor all'inizio della funzione per assicurarci che sia sempre disponibile
    cursor = conn.cursor()

    # Campi allineati alla struttura del database
    nome = st.text_input("Nome Impianto", value=defaults["nome"], key=f"{key_prefix}_nome")
    separazione = st.number_input("Separazione", value=defaults["separazione"], min_value=0.00, max_value=1.00, step=0.01, help="Percentuale di separazione, 0 = no separazione",
                            key=f"{key_prefix}_separazione")  
                              
    
    # SEZIONE BILANCIO ENERGETICO - STRUTTURA ALLINEATA AL DB
    st.markdown("---")
    
    # Recupera i dati esistenti del bilancio energetico
    bilancio_esistente = {}
    if defaults["id_impianto"]:
        cursor.execute(
            "SELECT categoria, tipo, valore, unita FROM bilancio_energetico WHERE id_impianto = ?",
            (defaults["id_impianto"],)
        )
        for row in cursor.fetchall():
            categoria, tipo, valore, unita = row
            bilancio_esistente[(categoria, tipo)] = {
                "valore": valore,
                "unita": unita
            }
    
    # Struttura riorganizzata con subheader per categoria
    struttura_con_subheader = [
        # Subheader per Energia Elettrica
        ("#### Energia Elettrica", None, None, None),
        ("prodotta", "EE_BT", "kWh", "Energia elettrica prodotta BT"),
        ("prodotta", "EE_MT", "kWh", "Energia elettrica prodotta MT"),
        ("autoconsumata", "EE", "kWh", "di cui autoconsumata"),
        ("autoconsumata", "EE_trasporti_tubazioni", "kWh", "di cui autoconsumata trasporti tubazioni"),
        
        # Subheader per Calore
        ("#### Calore", None, None, None),
        ("prodotta", "calore", "kWh", "Calore prodotto"),
        ("autoconsumata", "calore", "kWh", "di cui autoconsumato"),
        
        # Subheader per Biometano
        ("#### Biometano", None, None, None),
        ("prodotta", "biometano", "Nmc", "Biometano prodotto"),
        ("autoconsumata", "biometano", "Nmc", "di cui offset o autoconsumato"),
        
        # Subheader per BioLNG
        ("#### BioLNG", None, None, None),
        ("prodotta", "bioLNG", "ton", "BioLNG prodotto"),
        ("autoconsumata", "bioLNG", "ton", "di cui offset o autoconsumato"),
        
        # Subheader per CO2
        ("#### CO2 Biogenica", None, None, None),
        ("prodotta", "CO2_biogenica", "ton", "CO2biogenica prodotta"),
        
        # Subheader per Energie Acquistate
        ("#### Energia Acquistate", None, None, None),
        ("acquistata", "EE_BT", "kWh", "Energia elettrica BT acquistata"),
        ("acquistata", "EE_MT", "kWh", "Energia elettrica MT acquistata"),
        ("acquistata", "metano", "kWh", "Metano acquistato"),
        ("acquistata", "LNG", "kWh", "LNG acquistato"),
    ]
    
    # Dizionario per memorizzare i nuovi valori del bilancio
    nuovo_bilancio = {}
    
    # Crea l'interfaccia con subheader
    for elemento in struttura_con_subheader:
        categoria, tipo, unita, descrizione = elemento
        
        # Se è un subheader (categoria inizia con "###")
        if categoria and categoria.startswith("###"):
            st.markdown(categoria)
            continue

        # Altrimenti è una voce normale
        # Valore di default
        key = (categoria, tipo)
        if key in bilancio_esistente:
            default_valore = float(bilancio_esistente[key]["valore"])
        else:
            default_valore = 0.0
        
        col1, col2, col3 = st.columns([3, 2, 1])
        
        with col1:
            # Mostra la descrizione come testo (non modificabile)
            st.text(descrizione)
        
        with col2:
            # Input per il valore (modificabile)
            valore = st.number_input(
                f"Valore {categoria} {tipo}",
                value=default_valore,
                min_value=0.0,
                step=0.1,
                key=f"{key_prefix}_{categoria}_{tipo}_val",
                label_visibility="collapsed"
            )
        
        with col3:
            # Mostra l'unità come testo (non modificabile)
            st.text(unita)
        
        # Salva i valori - SEMPRE, anche se zero
        nuovo_bilancio[key] = {
            "valore": valore,
            "unita": unita,
            "categoria": categoria,
            "tipo": tipo
        }
    
    # SEZIONE RICETTORI
    st.markdown("---")
    st.subheader("Ricettori")
    
    # Recupera i ricettori esistenti
    ricettori_esistenti = []
    if defaults["id_impianto"]:
        cursor.execute("""
            SELECT r.id_ricettore, r.id_trasporto, r.tipo, r.distanza, r.carico, r.nome_ricettore, t.tipo as tipo_trasporto
            FROM ricettori r
            LEFT JOIN trasporti t ON r.id_trasporto = t.id_trasporto
            WHERE r.id_impianto = ?
            ORDER BY r.id_ricettore
        """, (defaults["id_impianto"],))
        ricettori_esistenti = cursor.fetchall()
    
    # Dizionario per memorizzare i valori aggiornati dei ricettori
    ricettori_aggiornati = {}
    
    # Mostra i ricettori esistenti SENZA EXPANDER
    if ricettori_esistenti:
        
        for i, ricettore in enumerate(ricettori_esistenti):
            id_ricettore, id_trasporto, tipo, distanza, carico, nome_ricettore, tipo_trasporto = ricettore
            
            # Crea una card per ogni ricettore
            col1, col2, col3, col4, col5, col6 = st.columns([2, 2, 2, 2, 2, 1])
            
            with col1:
                nome_ricettore_val = st.text_input(
                    "Nome ricettore",
                    value=nome_ricettore or f"Ricettore {i+1}",
                    key=f"{key_prefix}_ric_{id_ricettore}_nome"
                )
            
            with col2:
                # Selezione trasporto
                cursor.execute("SELECT id_trasporto, tipo FROM trasporti")
                trasporti_data = cursor.fetchall()
                trasporti_dict = {row[1]: row[0] for row in trasporti_data}
                trasporti_names = list(trasporti_dict.keys())
                
                # Trova il trasporto corrente
                current_trasporto_name = tipo_trasporto
                trasporto_index = trasporti_names.index(current_trasporto_name) if current_trasporto_name in trasporti_names else 0
                trasporto_selected = st.selectbox(
                    "Trasporto",
                    trasporti_names,
                    index=trasporto_index,
                    key=f"{key_prefix}_ric_{id_ricettore}_trasporto"
                )
                nuovo_id_trasporto = trasporti_dict[trasporto_selected]
            
            with col3:
                tipo_selected = st.selectbox(
                    "Tipo",
                    ["bioLNG", "bioCO2"],
                    index=0 if tipo == "bioLNG" else 1,
                    key=f"{key_prefix}_ric_{id_ricettore}_tipo"
                )
            
            with col4:
                nuova_distanza = st.number_input(
                    "Distanza (km)",
                    value=float(distanza),
                    min_value=0.0,
                    step=0.1,
                    key=f"{key_prefix}_ric_{id_ricettore}_distanza"
                )
            
            with col5:
                nuovo_carico = st.number_input(
                    "Carico (ton)",
                    value=int(carico),
                    min_value=0,
                    step=1,
                    key=f"{key_prefix}_ric_{id_ricettore}_carico"
                )
            
            with col6:
                st.markdown("<br>", unsafe_allow_html=True)
                if st.button("🗑️", key=f"{key_prefix}_ric_{id_ricettore}_elimina"):
                    cursor.execute("DELETE FROM ricettori WHERE id_ricettore = ?", (id_ricettore,))
                    conn.commit()
                    st.toast("Ricettore eliminato")
                    time.sleep(1)
                    st.rerun()
            
            # Memorizza i valori aggiornati per il salvataggio
            ricettori_aggiornati[id_ricettore] = {
                "nome_ricettore": nome_ricettore_val,
                "id_trasporto": nuovo_id_trasporto,
                "tipo": tipo_selected,
                "distanza": nuova_distanza,
                "carico": nuovo_carico
            }
    
    # Inizializza session state per il nuovo ricettore
    if f"{key_prefix}_nuovo_ricettore_attivo" not in st.session_state:
        st.session_state[f"{key_prefix}_nuovo_ricettore_attivo"] = False
    
    # Variabili per il nuovo ricettore
    nuovo_nome_ricettore = ""
    nuovo_id_trasporto = None
    nuovo_tipo = None
    nuova_distanza = 0.0
    nuovo_carico = 0
    
    # Pulsante per mostrare/nascondere i campi del nuovo ricettore
    if not st.session_state[f"{key_prefix}_nuovo_ricettore_attivo"]:
        if st.button("➕ Aggiungi nuovo ricettore", key=f"{key_prefix}_btn_nuovo_ricettore"):
            st.session_state[f"{key_prefix}_nuovo_ricettore_attivo"] = True
            st.rerun()
    else:
        # Mostra i campi per il nuovo ricettore
        col1, col2, col3, col4, col5 = st.columns([2, 2, 2, 2, 2])
        
        with col1:
            nuovo_nome_ricettore = st.text_input(
                "Nome ricettore",
                value="",
                key=f"{key_prefix}_nuovo_nome_ricettore"
            )
        
        with col2:
            # Selezione trasporto per nuovo ricettore
            cursor.execute("SELECT id_trasporto, tipo FROM trasporti")
            trasporti_data = cursor.fetchall()
            trasporti_dict = {row[1]: row[0] for row in trasporti_data}
            trasporti_names = list(trasporti_dict.keys())
            
            nuovo_trasporto = st.selectbox(
                "Trasporto",
                trasporti_names,
                key=f"{key_prefix}_nuovo_trasporto"
            )
            nuovo_id_trasporto = trasporti_dict[nuovo_trasporto]
        
        with col3:
            nuovo_tipo = st.selectbox(
                "Tipo",
                ["bioLNG", "bioCO2"],
                key=f"{key_prefix}_nuovo_tipo"
            )
        
        with col4:
            nuova_distanza = st.number_input(
                "Distanza (km)",
                min_value=0.0,
                step=0.1,
                key=f"{key_prefix}_nuova_distanza"
            )
        
        with col5:
            nuovo_carico = st.number_input(
                "Carico (ton)",
                min_value=0,
                step=1,
                key=f"{key_prefix}_nuovo_carico"
            )
        
        # Pulsante per annullare
        if st.button("❌ Annulla", key=f"{key_prefix}_annulla_nuovo"):
            st.session_state[f"{key_prefix}_nuovo_ricettore_attivo"] = False
            st.rerun()

    # Pulsanti finali
    st.markdown("---")

    st.subheader("Consumi e scarti")
    
    col1, col2 = st.columns(2)
    with col1:
        olio_lubrificante = st.number_input("Olio lubrificante [kg/anno]", value=float(defaults["olio_lubrificante"]), 
                                          min_value=0.0, step=0.1, key=f"{key_prefix}_olio")
        rifiuti = st.number_input("Rifiuti [kg/anno]", value=float(defaults["rifiuti"]), 
                                min_value=0.0, step=0.1, key=f"{key_prefix}_rifiuti")
    with col2:
        acqua = st.number_input("Acqua [mc/anno]", value=float(defaults["acqua"]), 
                              min_value=0.0, step=0.1, key=f"{key_prefix}_acqua")
        scarichi = st.number_input("Scarichi [mc/anno]", value=float(defaults["scarichi"]), 
                                 min_value=0.0, step=0.1, key=f"{key_prefix}_scarichi")

    
    st.markdown("---")
    col_update, col_delete = st.columns(2)
    
    # Solo per impianti esistenti mostra il pulsante "Salva modifiche"
    
    if defaults["id_impianto"]:
        with col_update:
            if st.button("💾 Salva modifiche", key=f"{key_prefix}_salva"):
                cursor = conn.cursor()
                
                # Aggiorna i dati dell'impianto
                cursor.execute(
                    """
                    UPDATE Impianto 
                    SET nome = ?, 
                        separazione = ?, olio_lubrificante = ?, rifiuti = ?, acqua = ?, scarichi = ?
                    WHERE id_impianto = ?
                    """,
                    (nome, separazione, 
                     olio_lubrificante, rifiuti, acqua, scarichi, defaults["id_impianto"])
                )
                
                # PRIMA: Elimina tutti i record esistenti del bilancio energetico per questo impianto
                cursor.execute("DELETE FROM bilancio_energetico WHERE id_impianto = ?", (defaults["id_impianto"],))
                
                # POI: Inserisce i nuovi dati del bilancio energetico - TUTTI i valori, anche zero
                for key, dati in nuovo_bilancio.items():
                    # MODIFICA: Inserisce SEMPRE, anche se il valore è 0
                    cursor.execute(
                        """
                        INSERT INTO bilancio_energetico 
                        (id_impianto, categoria, tipo, valore, unita) 
                        VALUES (?, ?, ?, ?, ?)
                        """,
                        (defaults["id_impianto"], dati["categoria"], dati["tipo"], 
                         dati["valore"], dati["unita"])
                    )
                
                # Aggiorna i ricettori esistenti
                for id_ricettore, dati_ricettore in ricettori_aggiornati.items():
                    cursor.execute("""
                        UPDATE ricettori 
                        SET nome_ricettore = ?, id_trasporto = ?, tipo = ?, distanza = ?, carico = ?
                        WHERE id_ricettore = ?
                    """, (
                        dati_ricettore["nome_ricettore"],
                        dati_ricettore["id_trasporto"], 
                        dati_ricettore["tipo"], 
                        dati_ricettore["distanza"], 
                        dati_ricettore["carico"],
                        id_ricettore
                    ))
                
                # Aggiunge il nuovo ricettore se presente
                if (st.session_state[f"{key_prefix}_nuovo_ricettore_attivo"] and 
                    nuovo_id_trasporto is not None and 
                    nuovo_tipo is not None):
                    
                    cursor.execute("""
                        INSERT INTO ricettori (id_impianto, nome_ricettore, id_trasporto, tipo, distanza, carico)
                        VALUES (?, ?, ?, ?, ?, ?)
                    """, (defaults["id_impianto"], nuovo_nome_ricettore, nuovo_id_trasporto, nuovo_tipo, nuova_distanza, nuovo_carico))
                    st.session_state[f"{key_prefix}_nuovo_ricettore_attivo"] = False
                
                conn.commit()
                st.toast("✅ Modifiche salvate.")
                time.sleep(1)
                st.rerun()

        with col_delete:
            if st.button("🗑️ Elimina impianto", key=f"{key_prefix}_elimina"):
                st.session_state[f"{key_prefix}_conferma_elimina"] = True

            if st.session_state.get(f"{key_prefix}_conferma_elimina", False):
                st.warning(f"**⚠️ Confermi di voler eliminare {nome}?**")
                col_conf, col_annulla = st.columns([1, 1])

                with col_conf:
                    if st.button("✅ Conferma", key=f"{key_prefix}_conferma"):
                        cursor = conn.cursor()
                        # Elimina prima i dati del bilancio energetico
                        cursor.execute("DELETE FROM bilancio_energetico WHERE id_impianto = ?", (defaults["id_impianto"],))
                        # Elimina i ricettori
                        cursor.execute("DELETE FROM ricettori WHERE id_impianto = ?", (defaults["id_impianto"],))
                        # Poi elimina l'impianto
                        cursor.execute("DELETE FROM Impianto WHERE id_impianto = ?", (defaults["id_impianto"],))
                        conn.commit()
                        st.session_state[f"{key_prefix}_conferma_elimina"] = False
                        st.rerun()

                with col_annulla:
                    if st.button("❌ Annulla", key=f"{key_prefix}_annulla"):
                        st.session_state[f"{key_prefix}_conferma_elimina"] = False
                        st.rerun()

    # Ritorna i dati per il nuovo impianto
    return {
        "nome": nome,
        "separazione": separazione,
        "olio_lubrificante": olio_lubrificante,
        "rifiuti": rifiuti,
        "acqua": acqua,
        "scarichi": scarichi,
        "bilancio_energetico": nuovo_bilancio,
        "nuovo_ricettore": {
            "nome_ricettore": nuovo_nome_ricettore,
            "id_trasporto": nuovo_id_trasporto,
            "tipo": nuovo_tipo,
            "distanza": nuova_distanza,
            "carico": nuovo_carico
        } if st.session_state[f"{key_prefix}_nuovo_ricettore_attivo"] else None
    }

# ---------------------------------------------------------------------------------------- #
# MAIN CORRETTO
# ---------------------------------------------------------------------------------------- #

st.title("♻️ Impianti")

conn = get_connection()
cursor = conn.cursor()

tab1, tab2 = st.tabs(["✏️ Visualizza e modifica", "➕ Nuovo"])

# ---------------------------------------------------------------------------------------- #
# VISUALIZZA E GESTISCI IMPIANTI ESISTENTI - MODIFICATO
# ---------------------------------------------------------------------------------------- #
with tab1:
    impianti = pd.read_sql_query("SELECT * FROM impianto", conn)

    if impianti.empty:
        st.info("Nessun impianto presente nel database.")
    else:
        # Seleziona l'impianto da visualizzare/modificare
        impianti_options = [f"{row['id_impianto']} - {row['nome']}" for _, row in impianti.iterrows()]
        
        selected_impianto = st.selectbox(
            "Seleziona l'impianto da visualizzare/modificare",
            impianti_options,
            key="select_impianto"
        )
        
        # Trova i dati dell'impianto selezionato
        selected_id = int(selected_impianto.split(" - ")[0])
        selected_data = impianti[impianti['id_impianto'] == selected_id].iloc[0].to_dict()
        
        # Mostra il form per l'impianto selezionato
        st.markdown("---")
        form_impianto(conn, dati_esistenti=selected_data, key_prefix="selected")

# ---------------------------------------------------------------------------------------- #
# AGGIUNGI NUOVO IMPIANTO - FORM IDENTICO A QUELLO DI MODIFICA
# ---------------------------------------------------------------------------------------- #
with tab2:
    
    # Valori di default per nuovo impianto
    defaults = {
        "nome": "",
        "separazione": 0.00,
        "olio_lubrificante": 0.0,
        "rifiuti": 0.0,
        "acqua": 0.0,
        "scarichi": 0.0
    }
    
    # Usa la stessa funzione form_impianto ma per un nuovo impianto
    dati_nuovo = form_impianto(conn, dati_esistenti=defaults, key_prefix="nuovo_impianto")
    
    # Pulsante per creare il nuovo impianto
    if st.button("💾 Crea Nuovo Impianto", key="crea_nuovo_impianto", use_container_width=True):
        if not dati_nuovo["nome"]:
            st.error("❌ Il campo Nome è obbligatorio.")
        else:
            try:
                cursor = conn.cursor()
                # Inserisce il nuovo impianto
                cursor.execute(
                    """
                    INSERT INTO Impianto (
                        nome, separazione, 
                        olio_lubrificante, rifiuti, acqua, scarichi
                    ) VALUES (?, ?, ?, ?, ?, ?)
                    """,
                    (dati_nuovo["nome"], dati_nuovo["separazione"],
                     dati_nuovo["olio_lubrificante"], dati_nuovo["rifiuti"], 
                     dati_nuovo["acqua"], dati_nuovo["scarichi"])
                )
                
                # Ottiene l'ID dell'impianto appena creato
                id_impianto = cursor.lastrowid
                
                # MODIFICA: Inserisce i dati del bilancio energetico - TUTTI i valori, anche zero
                for key, dati in dati_nuovo.get("bilancio_energetico", {}).items():
                    cursor.execute(
                        """
                        INSERT INTO bilancio_energetico 
                        (id_impianto, categoria, tipo, valore, unita) 
                        VALUES (?, ?, ?, ?, ?)
                        """,
                        (id_impianto, dati["categoria"], dati["tipo"], 
                         dati["valore"], dati["unita"])
                    )
                
                # Aggiunge il nuovo ricettore se presente
                if dati_nuovo.get("nuovo_ricettore") and dati_nuovo["nuovo_ricettore"]["id_trasporto"] is not None:
                    cursor.execute("""
                        INSERT INTO ricettori (id_impianto, nome_ricettore, id_trasporto, tipo, distanza, carico)
                        VALUES (?, ?, ?, ?, ?, ?)
                    """, (
                        id_impianto,
                        dati_nuovo["nuovo_ricettore"]["nome_ricettore"],
                        dati_nuovo["nuovo_ricettore"]["id_trasporto"],
                        dati_nuovo["nuovo_ricettore"]["tipo"],
                        dati_nuovo["nuovo_ricettore"]["distanza"],
                        dati_nuovo["nuovo_ricettore"]["carico"]
                    ))
                
                conn.commit()
                st.toast(f"✅ Impianto '{dati_nuovo['nome']}' creato correttamente!")
                time.sleep(1)
                st.rerun()
                
            except sqlite3.IntegrityError:
                st.error("❌ Errore: esiste già un impianto con questo nome.")
            except Exception as e:
                st.error(f"❌ Errore durante il salvataggio: {str(e)}")