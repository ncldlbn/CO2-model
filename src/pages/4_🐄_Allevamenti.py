import streamlit as st
import pandas as pd
from db import get_connection, create_tables
import sqlite3

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
def form_allevamento(conn, dati_esistenti=None, key_prefix=""):
    """Form per visualizzare e modificare un allevamento"""

    # Valori di default
    defaults = {
        "id_allevamento": None,
        "nome": "",
        "quota": 0,
        "tipo_biomassa": "-",
        "uba": 0,
        "biomassa_uba_giorno": 0.0,
        "alfa": 0.0,
        "beta": 0.0,
        "deposito_max": 0,
        "impianto": "-",
        "trasporto": "-",
        "distanza_impianto": 0,
        "modalita_svuotamento": "-",
        "svuotamenti": 0
    }

    if dati_esistenti:
        for key in defaults:
            val = dati_esistenti.get(key)
            if val is not None:
                if key in ["quota", "uba", "deposito_max"]:
                    defaults[key] = int(val)
                elif key in ["biomassa_uba_giorno", "distanza_impianto", "alfa", "beta"]:
                    defaults[key] = float(val)
                elif key == "svuotamenti" and dati_esistenti["modalita_svuotamento"] == "Imposta frequenza":
                    defaults[key] = int(val)
                else:
                    defaults[key] = val

    st.subheader("Anagrafica")
    col1, col2 = st.columns(2)
    with col1:
        nome = st.text_input("Nome allevamento", value=defaults["nome"], key=f"{key_prefix}_nome")
    with col2:
        quota = st.number_input("Quota allevamento [m slm]", value=defaults["quota"], min_value=0, step=1, key=f"{key_prefix}_quota")

    st.subheader("Dati zootecnici")
    tipo_options = ["-", "Liquame", "Letame"]
    tipo_index = tipo_options.index(defaults["tipo_biomassa"]) if defaults["tipo_biomassa"] in tipo_options else 0
    tipo = st.selectbox("Tipologia biomassa prevalente", tipo_options, index=tipo_index, key=f"{key_prefix}_tipo")

    col1, col2 = st.columns(2)
    with col1:
        uba = st.number_input("UBA", value=defaults["uba"], min_value=0, step=1, key=f"{key_prefix}_uba")
    with col2:
        biomassa_uba_giorno = st.number_input("kg biomassa / UBA / Giorno", value=defaults["biomassa_uba_giorno"], min_value=0.0, step=0.1, key=f"{key_prefix}_biomassa")

    col1, col2 = st.columns(2)
    with col1:
        alfa = st.number_input("Coefficiente Alpha", value=defaults["alfa"], min_value=0.0, step=0.1, key=f"{key_prefix}_alfa")
    with col2:
        beta = st.number_input("Coefficiente Beta", value=defaults["beta"], min_value=0.0, step=0.1, key=f"{key_prefix}_beta")

    deposito_max = st.number_input("Capacità max deposito (t)", value=defaults["deposito_max"], min_value=0, step=1, key=f"{key_prefix}_deposito")

    st.subheader("Impianto")
    cursor = conn.cursor()
    cursor.execute("SELECT nome FROM Impianto")
    impianti = ["-"] + [row[0] for row in cursor.fetchall()]
    impianto_index = impianti.index(defaults["impianto"]) if defaults["impianto"] in impianti else 0
    impianto = st.selectbox("Nome impianto associato all'allevamento", impianti, index=impianto_index, key=f"{key_prefix}_impianto")

    st.subheader("Trasporto")
    cursor.execute("SELECT nome FROM Trasporto")
    trasporti = ["-"] + [row[0] for row in cursor.fetchall()]

    col1, col2 = st.columns(2)
    with col1:
        trasporto_index = trasporti.index(defaults["trasporto"]) if defaults["trasporto"] in trasporti else 0
        trasporto = st.selectbox("Mezzo di trasporto", trasporti, index=trasporto_index, key=f"{key_prefix}_trasporto")
    with col2:
        distanza_impianto = st.number_input("Distanza allevamento - impianto [km]", value=int(defaults["distanza_impianto"]), min_value=0, step=1, key=f"{key_prefix}_distanza")

    col1, col2 = st.columns(2)
    with col1:
        modalita_options = ["-", "Imposta frequenza", "Riempimento totale camion"]
        modalita_index = modalita_options.index(defaults["modalita_svuotamento"]) if defaults["modalita_svuotamento"] in modalita_options else 0
        modalita_svuotamento = st.selectbox(
            "Modalità di svuotamento",
            modalita_options,
            index=modalita_index,
            key=f"{key_prefix}_modalita"
        )
    with col2:
        if modalita_svuotamento == "Imposta frequenza":
            svuotamenti = st.number_input("Frequenza svuotamenti (giorni)", value=defaults["svuotamenti"], min_value=0, step=1, key=f"{key_prefix}_svuotamenti")
        else:
            svuotamenti = None

    # Pulsanti finali
    st.markdown("---")
    col_update, col_delete = st.columns(2)
    with col_update:
        if st.button("💾 Salva modifiche", key=f"{key_prefix}_salva"):
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE Allevamento SET
                    nome = ?, quota = ?, tipo_biomassa = ?, uba = ?, biomassa_uba_giorno = ?,
                    alfa = ?, beta = ?, deposito_max = ?, impianto = ?, trasporto = ?,
                    distanza_impianto = ?, modalita_svuotamento = ?, svuotamenti = ?
                WHERE id_allevamento = ?
            """, (
                nome, quota, tipo, uba, biomassa_uba_giorno, alfa, beta, deposito_max,
                impianto, trasporto, distanza_impianto, modalita_svuotamento, svuotamenti,
                defaults["id_allevamento"]
            ))
            conn.commit()
            st.toast("✅ Modifiche salvate.")

    with col_delete:
        if st.button("🗑️ Elimina", key=f"{key_prefix}_elimina"):
            st.session_state[f"{key_prefix}_conferma_elimina"] = True

        if st.session_state.get(f"{key_prefix}_conferma_elimina", False):
            st.markdown(f"**⚠️ Confermi di voler eliminare l'allevamento '{nome}'?**")
            col_conf, col_annulla = st.columns([1, 1])
            with col_conf:
                if st.button("✅ Conferma", key=f"{key_prefix}_conferma"):
                    cursor = conn.cursor()
                    cursor.execute("DELETE FROM Allevamento WHERE nome = ?", (defaults["nome"],))
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

st.title("🐄 Allevamenti")
st.markdown("In questa pagina è possibile visualizzare e modificare i dati relativi agli allevamenti, oltre che inserirne di nuovi. Ogni allevamento è associato ad un impianto e ad un mezzo di trasporto.")

conn = get_connection()
cursor = conn.cursor()

tab1, tab2 = st.tabs(["✏️ Visualizza e modifica", "➕ Nuovo"])

# ---------------------------------------------------------------------------------------- #
# VISUALIZZA E GESTISCI ALLEVAMENTI ESISTENTI
# ---------------------------------------------------------------------------------------- #

with tab1:
    # Seleziona l'impianto
    cursor.execute("SELECT nome FROM Impianto")
    impianti = ["-- Tutti --"] + [row[0] for row in cursor.fetchall()]
    impianto_sel = st.selectbox("Seleziona un impianto per visualizzare gli allevamenti associati", impianti)

    # Query al database per restituire tutti gli allevamenti associati all'impianto.
    if impianto_sel != "-- Tutti --":
        allevamenti = pd.read_sql_query("SELECT * FROM Allevamento WHERE impianto = ?", conn, params=(impianto_sel,))
    else:
        allevamenti = pd.read_sql_query("SELECT * FROM Allevamento", conn)

    st.markdown("---")
    # Visualizza schede allevamenti
    for i, row in allevamenti.iterrows():
        with st.expander(f"🐄 {row['nome']}"):
            dati = row.to_dict()
            form_allevamento(conn, dati_esistenti=dati, key_prefix=f"allev_{i}")

# ---------------------------------------------------------------------------------------- #
# AGGIUNGI NUOVO ALLEVAMENTO
# ---------------------------------------------------------------------------------------- #

# MOSTRA TOAST SE FLAG ATTIVA (fuori da tab2 o all'inizio)
if st.session_state.get("show_toast_nuovo_allevamento", False):
    st.toast(f"✅ Impianto '{st.session_state.get('last_nuovo_nome', '')}' salvato correttamente!")
    st.session_state.show_toast_nuovo_allevamento = False
    st.session_state.last_nuovo_nome = ""

# Funzione per resettare i campi del nuovo allevamento
def reset_nuovo_allevamento():
    st.session_state["nuovo_nome"] = ""
    st.session_state["nuovo_quota"] = 0
    st.session_state["nuovo_tipo"] = "-"
    st.session_state["nuovo_uba"] = 0
    st.session_state["nuovo_biomassa"] = 0.0
    st.session_state["nuovo_alfa"] = 0.0
    st.session_state["nuovo_beta"] = 0.0
    st.session_state["nuovo_deposito"] = 0
    st.session_state["nuovo_impianto"] = "-"
    st.session_state["nuovo_trasporto"] = "-"
    st.session_state["nuovo_distanza"] = 0
    st.session_state["nuovo_modalita"] = "-"
    st.session_state["nuovo_svuotamenti"] = 0

# Reset prima di creare i widget
if st.session_state.get("reset_nuovo_allevamento", False):
    reset_nuovo_allevamento()
    st.session_state.reset_nuovo_allevamento = False

# TAB2: Inserimento nuovo allevamento
with tab2:

    with st.container():
        st.subheader("Anagrafica")
        col1, col2 = st.columns(2)
        with col1:
            nome = st.text_input("Nome allevamento", key="nuovo_nome")
        with col2:
            quota = st.number_input("Quota allevamento [m slm]", min_value=0, step=1, key="nuovo_quota")

        st.subheader("Dati zootecnici")
        tipo_options = ["-", "Liquame", "Letame"]
        tipo = st.selectbox("Tipologia biomassa prevalente", tipo_options, key="nuovo_tipo")

        col1, col2 = st.columns(2)
        with col1:
            uba = st.number_input("UBA", min_value=0, step=1, key="nuovo_uba")
        with col2:
            biomassa_uba_giorno = st.number_input("kg biomassa / UBA / Giorno", min_value=0.0, step=0.1, key="nuovo_biomassa")

        col1, col2 = st.columns(2)
        with col1:
            alfa = st.number_input("Coefficiente Alpha", min_value=0.0, step=0.1, key="nuovo_alfa")
        with col2:
            beta = st.number_input("Coefficiente Beta", min_value=0.0, step=0.1, key="nuovo_beta")

        deposito_max = st.number_input("Capacità max deposito (t)", min_value=0, step=1, key="nuovo_deposito")

        st.subheader("Impianto")
        cursor = conn.cursor()
        cursor.execute("SELECT nome FROM Impianto")
        impianti = ["-"] + [row[0] for row in cursor.fetchall()]
        impianto = st.selectbox("Nome impianto associato all'allevamento", impianti, key="nuovo_impianto")

        st.subheader("Trasporto")
        col1, col2 = st.columns(2)
        with col1:
            cursor.execute("SELECT nome FROM Trasporto")
            trasporti = ["-"] + [row[0] for row in cursor.fetchall()]
            trasporto = st.selectbox("Mezzo di trasporto", trasporti, key="nuovo_trasporto")
        with col2:
            distanza_impianto = st.number_input("Distanza allevamento - impianto [km]", min_value=0, step=1, key="nuovo_distanza")

        col1, col2 = st.columns(2)
        with col1:
            modalita_options = ["-", "Imposta frequenza", "Riempimento totale camion"]
            modalita_svuotamento = st.selectbox("Modalità di svuotamento", modalita_options, key="nuovo_modalita")
        with col2:
            if modalita_svuotamento == "Imposta frequenza":
                svuotamenti = st.number_input("Frequenza svuotamenti (giorni)", min_value=0, step=1, key="nuovo_svuotamenti")
            else:
                svuotamenti = None

        # Pulsanti finali
        st.markdown("---")
        col_save, col_cancel = st.columns([1, 1])

        with col_save:
            if st.button("💾 Salva", use_container_width=True, key="save_new"):
                dati = {
                    "nome": nome,
                    "quota": quota,
                    "tipo_biomassa": tipo,
                    "uba": uba,
                    "biomassa_uba_giorno": biomassa_uba_giorno,
                    "alfa": alfa,
                    "beta": beta,
                    "deposito_max": deposito_max,
                    "impianto": impianto,
                    "trasporto": trasporto,
                    "distanza_impianto": distanza_impianto,
                    "modalita_svuotamento": modalita_svuotamento,
                    "svuotamenti": svuotamenti
                }

                # Validazione
                if (
                    dati["nome"] == "" or dati["tipo_biomassa"] == "-" or dati["trasporto"] == "-" or
                    dati["modalita_svuotamento"] == "-" or dati["impianto"] == "-" or dati["distanza_impianto"] == 0 or
                    dati["biomassa_uba_giorno"] == 0 or dati["uba"] == 0 or dati["deposito_max"] == 0
                ):
                    st.error("❌ Compila tutti i campi obbligatori.")
                else:
                    try:
                        cursor = conn.cursor()
                        cursor.execute("""
                            INSERT INTO Allevamento (
                                nome, quota, tipo_biomassa, uba, biomassa_uba_giorno, alfa, beta,
                                deposito_max, impianto, trasporto, distanza_impianto,
                                modalita_svuotamento, svuotamenti
                            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                        """, (
                            dati["nome"], dati["quota"], dati["tipo_biomassa"], dati["uba"], dati["biomassa_uba_giorno"],
                            dati["alfa"], dati["beta"], dati["deposito_max"], dati["impianto"], dati["trasporto"],
                            dati["distanza_impianto"], dati["modalita_svuotamento"], dati["svuotamenti"]
                        ))
                        conn.commit()
                        st.session_state.last_nuovo_nome = dati["nome"]
                        st.session_state.show_toast_nuovo_allevamento = True
                        st.session_state.reset_nuovo_allevamento = True
                        st.rerun()

                    except sqlite3.IntegrityError:
                        st.error("❌ Errore: esiste già un allevamento con questo nome.")
                    except Exception as e:
                        st.error(f"❌ Errore durante il salvataggio: {str(e)}")

        with col_cancel:
            if st.button("❌ Annulla", use_container_width=True, key="cancel_new"):
                st.session_state.reset_nuovo_allevamento = True
                st.rerun()



