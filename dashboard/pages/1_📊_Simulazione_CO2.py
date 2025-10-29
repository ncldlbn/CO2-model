import streamlit as st
import pandas as pd
import sqlite3

sys.path.append(os.path.join(os.path.dirname(__file__), '../../src'))
from objects import Allevatore  # Importa la tua classe Allevatore

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
        "frequenza_conferimento": 0,
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
            "Denominazione Sociale", 
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
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        uba_letame = st.number_input(
            "UBA Letame", 
            value=defaults["uba_letame"], 
            min_value=0, 
            step=1, 
            key=f"{key_prefix}_uba_letame"
        )
    with col2:
        uba_liquame = st.number_input(
            "UBA Liquame", 
            value=defaults["uba_liquame"], 
            min_value=0, 
            step=1, 
            key=f"{key_prefix}_uba_liquame"
        )
    with col3:
        prod_letame = st.number_input(
            "Prod. Letame (mc/UBA/anno)", 
            value=defaults["prod_letame"], 
            min_value=0.0, 
            step=0.1, 
            key=f"{key_prefix}_prod_letame"
        )
    with col4:
        prod_liquame = st.number_input(
            "Prod. Liquame (mc/UBA/anno)", 
            value=defaults["prod_liquame"], 
            min_value=0.0, 
            step=0.1, 
            key=f"{key_prefix}_prod_liquame"
        )

    deposito_max = st.number_input(
        "Capacità max deposito (mc)", 
        value=defaults["deposito_max"], 
        min_value=0.0, 
        step=1.0, 
        key=f"{key_prefix}_deposito_max"
    )

    st.subheader("Conferimento e Trasporto")
    
    # Tipo conferimento
    tipo_conferimento = st.radio(
        "Tipo Conferimento",
        ["mezzi", "tubazione"],
        index=0 if defaults["tipo_conferimento"] == "mezzi" else 1,
        key=f"{key_prefix}_tipo_conferimento"
    )

    col1, col2 = st.columns(2)
    with col1:
        # Selezione impianto
        cursor = conn.cursor()
        cursor.execute("SELECT id_impianto, nome FROM Impianto")
        impianti_data = cursor.fetchall()
        impianti_dict = {row[1]: row[0] for row in impianti_data}
        impianti_names = list(impianti_dict.keys())
        
        # Trova il nome dell'impianto corrente
        current_impianto_name = None
        if defaults["id_impianto_associato"]:
            cursor.execute("SELECT nome FROM Impianto WHERE id_impianto = ?", (defaults["id_impianto_associato"],))
            current_impianto = cursor.fetchone()
            current_impianto_name = current_impianto[0] if current_impianto else None
        
        impianto_index = impianti_names.index(current_impianto_name) if current_impianto_name in impianti_names else 0
        impianto_selected = st.selectbox(
            "Impianto Associato",
            impianti_names,
            index=impianto_index,
            key=f"{key_prefix}_impianto"
        )
        id_impianto_associato = impianti_dict[impianto_selected]

    with col2:
        # Selezione trasporto
        cursor.execute("SELECT id_trasporto, nome FROM Trasporto")
        trasporti_data = cursor.fetchall()
        trasporti_dict = {row[1]: row[0] for row in trasporti_data}
        trasporti_names = list(trasporti_dict.keys())
        
        # Trova il nome del trasporto corrente
        current_trasporto_name = None
        if defaults["id_trasporto"]:
            cursor.execute("SELECT nome FROM Trasporto WHERE id_trasporto = ?", (defaults["id_trasporto"],))
            current_trasporto = cursor.fetchone()
            current_trasporto_name = current_trasporto[0] if current_trasporto else None
        
        trasporto_index = trasporti_names.index(current_trasporto_name) if current_trasporto_name in trasporti_names else 0
        trasporto_selected = st.selectbox(
            "Mezzo di Trasporto",
            trasporti_names,
            index=trasporto_index,
            key=f"{key_prefix}_trasporto"
        )
        id_trasporto = trasporti_dict[trasporto_selected]

    col1, col2 = st.columns(2)
    with col1:
        frequenza_conferimento = st.number_input(
            "Frequenza Conferimento (giorni)", 
            value=defaults["frequenza_conferimento"], 
            min_value=1, 
            step=1, 
            key=f"{key_prefix}_frequenza"
        )
    with col2:
        distanza_impianto = st.number_input(
            "Distanza Impianto (km)", 
            value=defaults["distanza_impianto"], 
            min_value=0.0, 
            step=0.1, 
            key=f"{key_prefix}_distanza"
        )

    # Campi condizionali per tubazione
    if tipo_conferimento == "tubazione":
        st.subheader("Dati Tubazione")
        col1, col2, col3 = st.columns(3)
        with col1:
            portata = st.number_input(
                "Portata (mc/h)", 
                value=defaults["portata"] or 0.0, 
                min_value=0.0, 
                step=0.1, 
                key=f"{key_prefix}_portata"
            )
        with col2:
            potenza = st.number_input(
                "Potenza (kW)", 
                value=defaults["potenza"] or 0.0, 
                min_value=0.0, 
                step=0.1, 
                key=f"{key_prefix}_potenza"
            )
        with col3:
            ore = st.number_input(
                "Ore di funzionamento", 
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
    col_update, col_delete = st.columns(2)
    
    with col_update:
        if st.button("💾 Salva modifiche", key=f"{key_prefix}_salva"):
            try:
                cursor = conn.cursor()
                if defaults["id_allevatore"]:  # Modifica
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
                else:  # Nuovo
                    cursor.execute("""
                        INSERT INTO allevatore (
                            denominazione_sociale, id_impianto_associato, tipo_conferimento,
                            frequenza_conferimento, id_trasporto, distanza_impianto,
                            uba_letame, uba_liquame, prod_letame, prod_liquame,
                            deposito_max, quota, portata, potenza, ore
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """, (
                        denominazione_sociale, id_impianto_associato, tipo_conferimento,
                        frequenza_conferimento, id_trasporto, distanza_impianto,
                        uba_letame, uba_liquame, prod_letame, prod_liquame,
                        deposito_max, quota, portata, potenza, ore
                    ))
                
                conn.commit()
                st.toast("✅ Modifiche salvate.")
                st.rerun()
                
            except Exception as e:
                st.error(f"❌ Errore durante il salvataggio: {str(e)}")

    with col_delete:
        if defaults["id_allevatore"]:  # Solo per record esistenti
            if st.button("🗑️ Elimina", key=f"{key_prefix}_elimina"):
                st.session_state[f"{key_prefix}_conferma_elimina"] = True

            if st.session_state.get(f"{key_prefix}_conferma_elimina", False):
                st.markdown(f"**⚠️ Confermi di voler eliminare l'allevatore '{denominazione_sociale}'?**")
                col_conf, col_annulla = st.columns([1, 1])
                with col_conf:
                    if st.button("✅ Conferma", key=f"{key_prefix}_conferma"):
                        cursor = conn.cursor()
                        cursor.execute("DELETE FROM allevatore WHERE id_allevatore = ?", (defaults["id_allevatore"],))
                        conn.commit()
                        st.session_state[f"{key_prefix}_conferma_elimina"] = False
                        st.rerun()
                with col_annulla:
                    if st.button("❌ Annulla", key=f"{key_prefix}_annulla"):
                        st.session_state[f"{key_prefix}_conferma_elimina"] = False
                        st.rerun()

# ---------------------------------------------------------------------------------------- #
# MAIN
# ---------------------------------------------------------------------------------------- #

st.title("🐄 Allevatori")
st.markdown("In questa pagina è possibile visualizzare e modificare i dati relativi agli allevatori, oltre che inserirne di nuovi.")

conn = sqlite3.connect('your_database.db')  # Sostituisci con il tuo percorso DB
cursor = conn.cursor()

tab1, tab2 = st.tabs(["✏️ Visualizza e modifica", "➕ Nuovo Allevatore"])

# ---------------------------------------------------------------------------------------- #
# VISUALIZZA E GESTISCI ALLEVATORI ESISTENTI
# ---------------------------------------------------------------------------------------- #

with tab1:
    # Seleziona l'impianto per filtrare
    cursor.execute("SELECT id_impianto, nome FROM Impianto")
    impianti_data = cursor.fetchall()
    impianti_options = [("-- Tutti --", None)] + [(row[1], row[0]) for row in impianti_data]
    impianti_names = [row[0] for row in impianti_options]
    
    impianto_sel_name = st.selectbox(
        "Seleziona un impianto per visualizzare gli allevatori associati", 
        impianti_names
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
            SELECT a.*, i.nome as nome_impianto, t.nome as nome_trasporto
            FROM allevatore a
            LEFT JOIN Impianto i ON a.id_impianto_associato = i.id_impianto
            LEFT JOIN Trasporto t ON a.id_trasporto = t.id_trasporto
            WHERE a.id_impianto_associato = ?
        """
        allevatori = pd.read_sql_query(query, conn, params=(impianto_sel_id,))
    else:
        query = """
            SELECT a.*, i.nome as nome_impianto, t.nome as nome_trasporto
            FROM allevatore a
            LEFT JOIN Impianto i ON a.id_impianto_associato = i.id_impianto
            LEFT JOIN Trasporto t ON a.id_trasporto = t.id_trasporto
        """
        allevatori = pd.read_sql_query(query, conn)

    st.markdown("---")
    
    if len(allevatori) == 0:
        st.info("Nessun allevatore trovato per i criteri selezionati.")
    else:
        # Visualizza schede allevatori
        for i, row in allevatori.iterrows():
            expander_title = f"🐄 {row['denominazione_sociale']} - Impianto: {row['nome_impianto']}"
            with st.expander(expander_title):
                dati = row.to_dict()
                form_allevatore(conn, dati_esistenti=dati, key_prefix=f"allev_{i}")

# ---------------------------------------------------------------------------------------- #
# AGGIUNGI NUOVO ALLEVATORE
# ---------------------------------------------------------------------------------------- #

with tab2:
    st.subheader("Inserisci Nuovo Allevatore")
    
    # Usa session_state per mantenere i valori durante il rerun
    if 'nuovo_allevatore' not in st.session_state:
        st.session_state.nuovo_allevatore = {
            "denominazione_sociale": "",
            "quota": 0,
            "uba_letame": 0,
            "uba_liquame": 0,
            "prod_letame": 0.0,
            "prod_liquame": 0.0,
            "deposito_max": 0.0,
            "tipo_conferimento": "mezzi",
            "frequenza_conferimento": 7,
            "distanza_impianto": 0.0,
            "portata": None,
            "potenza": None,
            "ore": None
        }

    with st.form(key="nuovo_allevatore_form"):
        # Anagrafica
        st.subheader("Anagrafica Allevatore")
        col1, col2 = st.columns(2)
        with col1:
            denominazione_sociale = st.text_input(
                "Denominazione Sociale *",
                value=st.session_state.nuovo_allevatore["denominazione_sociale"]
            )
        with col2:
            quota = st.number_input(
                "Quota [m slm]",
                value=st.session_state.nuovo_allevatore["quota"],
                min_value=0,
                step=1
            )

        # Dati Zootecnici
        st.subheader("Dati Zootecnici")
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            uba_letame = st.number_input(
                "UBA Letame *",
                value=st.session_state.nuovo_allevatore["uba_letame"],
                min_value=0,
                step=1
            )
        with col2:
            uba_liquame = st.number_input(
                "UBA Liquame *",
                value=st.session_state.nuovo_allevatore["uba_liquame"],
                min_value=0,
                step=1
            )
        with col3:
            prod_letame = st.number_input(
                "Prod. Letame (mc/UBA/anno) *",
                value=st.session_state.nuovo_allevatore["prod_letame"],
                min_value=0.0,
                step=0.1
            )
        with col4:
            prod_liquame = st.number_input(
                "Prod. Liquame (mc/UBA/anno) *",
                value=st.session_state.nuovo_allevatore["prod_liquame"],
                min_value=0.0,
                step=0.1
            )

        deposito_max = st.number_input(
            "Capacità max deposito (mc) *",
            value=st.session_state.nuovo_allevatore["deposito_max"],
            min_value=0.0,
            step=1.0
        )

        # Conferimento e Trasporto
        st.subheader("Conferimento e Trasporto")
        
        tipo_conferimento = st.radio(
            "Tipo Conferimento *",
            ["mezzi", "tubazione"],
            index=0 if st.session_state.nuovo_allevatore["tipo_conferimento"] == "mezzi" else 1
        )

        col1, col2 = st.columns(2)
        with col1:
            # Selezione impianto
            cursor.execute("SELECT id_impianto, nome FROM Impianto")
            impianti_data = cursor.fetchall()
            impianti_dict = {row[1]: row[0] for row in impianti_data}
            impianto_selected = st.selectbox(
                "Impianto Associato *",
                list(impianti_dict.keys())
            )
            id_impianto_associato = impianti_dict[impianto_selected]

        with col2:
            # Selezione trasporto
            cursor.execute("SELECT id_trasporto, nome FROM Trasporto")
            trasporti_data = cursor.fetchall()
            trasporti_dict = {row[1]: row[0] for row in trasporti_data}
            trasporto_selected = st.selectbox(
                "Mezzo di Trasporto *",
                list(trasporti_dict.keys())
            )
            id_trasporto = trasporti_dict[trasporto_selected]

        col1, col2 = st.columns(2)
        with col1:
            frequenza_conferimento = st.number_input(
                "Frequenza Conferimento (giorni) *",
                value=st.session_state.nuovo_allevatore["frequenza_conferimento"],
                min_value=1,
                step=1
            )
        with col2:
            distanza_impianto = st.number_input(
                "Distanza Impianto (km) *",
                value=st.session_state.nuovo_allevatore["distanza_impianto"],
                min_value=0.0,
                step=0.1
            )

        # Campi condizionali per tubazione
        if tipo_conferimento == "tubazione":
            st.subheader("Dati Tubazione")
            col1, col2, col3 = st.columns(3)
            with col1:
                portata = st.number_input(
                    "Portata (mc/h) *",
                    value=st.session_state.nuovo_allevatore["portata"] or 0.0,
                    min_value=0.0,
                    step=0.1
                )
            with col2:
                potenza = st.number_input(
                    "Potenza (kW) *",
                    value=st.session_state.nuovo_allevatore["potenza"] or 0.0,
                    min_value=0.0,
                    step=0.1
                )
            with col3:
                ore = st.number_input(
                    "Ore di funzionamento *",
                    value=st.session_state.nuovo_allevatore["ore"] or 0,
                    min_value=0,
                    step=1
                )
        else:
            portata = None
            potenza = None
            ore = None

        # Pulsante submit
        submitted = st.form_submit_button("💾 Salva Nuovo Allevatore")
        
        if submitted:
            # Validazione
            if not denominazione_sociale:
                st.error("❌ La denominazione sociale è obbligatoria.")
            elif uba_letame == 0 and uba_liquame == 0:
                st.error("❌ Inserire almeno UBA Letame o UBA Liquame.")
            elif prod_letame == 0 and prod_liquame == 0:
                st.error("❌ Inserire almeno la produzione di letame o liquame.")
            elif deposito_max == 0:
                st.error("❌ La capacità del deposito è obbligatoria.")
            elif tipo_conferimento == "tubazione" and (portata == 0 or potenza == 0 or ore == 0):
                st.error("❌ Per il conferimento in tubazione, portata, potenza e ore sono obbligatorie.")
            else:
                try:
                    # Crea l'oggetto Allevatore per validazione
                    nuovo_allevatore = Allevatore(
                        id_allevatore=0,  # Temporaneo, sarà auto-increment dal DB
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
                    
                    # Inserimento nel database
                    cursor.execute("""
                        INSERT INTO allevatore (
                            denominazione_sociale, id_impianto_associato, tipo_conferimento,
                            frequenza_conferimento, id_trasporto, distanza_impianto,
                            uba_letame, uba_liquame, prod_letame, prod_liquame,
                            deposito_max, quota, portata, potenza, ore
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """, (
                        denominazione_sociale, id_impianto_associato, tipo_conferimento,
                        frequenza_conferimento, id_trasporto, distanza_impianto,
                        uba_letame, uba_liquame, prod_letame, prod_liquame,
                        deposito_max, quota, portata, potenza, ore
                    ))
                    
                    conn.commit()
                    st.success("✅ Allevatore creato con successo!")
                    
                    # Reset del form
                    st.session_state.nuovo_allevatore = {
                        "denominazione_sociale": "",
                        "quota": 0,
                        "uba_letame": 0,
                        "uba_liquame": 0,
                        "prod_letame": 0.0,
                        "prod_liquame": 0.0,
                        "deposito_max": 0.0,
                        "tipo_conferimento": "mezzi",
                        "frequenza_conferimento": 7,
                        "distanza_impianto": 0.0,
                        "portata": None,
                        "potenza": None,
                        "ore": None
                    }
                    st.rerun()
                    
                except ValueError as e:
                    st.error(f"❌ Errore di validazione: {str(e)}")
                except sqlite3.IntegrityError:
                    st.error("❌ Errore: esiste già un allevatore con questa denominazione sociale.")
                except Exception as e:
                    st.error(f"❌ Errore durante il salvataggio: {str(e)}")

conn.close()