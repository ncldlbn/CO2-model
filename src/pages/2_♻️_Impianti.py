import streamlit as st
import pandas as pd
from db import get_connection, create_tables


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

def form_impianto(conn, dati_esistenti=None, key_prefix=""):
    """Form per visualizzare e modificare un impianto"""

    # Valori di default
    defaults = {
        "id_impianto": None,
        "nome": "",
        "deposito_max": 0,
        "perc_effluenti_zootecnici": 0,
        "perc_colture_scarti": 0,
        "perc_trasporti": 0,
        "energia_kw": 0
    }

    if dati_esistenti:
        for key in defaults:
            val = dati_esistenti.get(key)
            if val is not None:
                defaults[key] = int(val) if key == "deposito_max" else val

    nome = st.text_input("Nome Impianto", value=defaults["nome"], key=f"{key_prefix}_nome")
    deposito_max = st.number_input("Capacità max deposito (t)", value=defaults["deposito_max"], min_value=0, step=1, key=f"{key_prefix}_deposito")
    energia_kw = st.number_input("Energia prodotta (kW)", value=float(defaults["energia_kw"]), min_value=0.0, step=1.0, key=f"{key_prefix}_energia")

    col1, col2, col3 = st.columns(3)
    with col1:
        perc_eff = st.number_input("Effluenti zootecnici [%]", value=float(defaults["perc_effluenti_zootecnici"]), min_value=0.0, max_value=100.0, step=1.0, key=f"{key_prefix}_perc_eff")
    with col2:
        perc_scarti = st.number_input("Colture e scarti [%]", value=float(defaults["perc_colture_scarti"]), min_value=0.0, max_value=100.0, step=1.0, key=f"{key_prefix}_perc_scarti")
    with col3:
        perc_trasporti = st.number_input("Trasporti [%]", value=float(defaults["perc_trasporti"]), min_value=0.0, max_value=100.0, step=1.0, key=f"{key_prefix}_perc_trasporti")
    
    # Pulsanti finali
    st.markdown("---")
    col_update, col_delete = st.columns(2)

    with col_update:
        if st.button("💾 Salva modifiche", key=f"{key_prefix}_salva"):
            cursor = conn.cursor()
            cursor.execute(
                """
                UPDATE Impianto 
                SET nome = ?, deposito_max = ?, perc_effluenti_zootecnici = ?, perc_colture_scarti = ?, perc_trasporti = ?, energia_kw = ?
                WHERE id_impianto = ?
                """,
                (nome, deposito_max, perc_eff, perc_scarti, perc_trasporti, energia_kw, defaults["id_impianto"])
            )
            conn.commit()
            st.toast("✅ Modifiche salvate.")

    with col_delete:
        if st.button("🗑️ Elimina", key=f"{key_prefix}_elimina"):
            st.session_state[f"{key_prefix}_conferma_elimina"] = True

        if st.session_state.get(f"{key_prefix}_conferma_elimina", False):
            st.markdown(f"**⚠️ Confermi di voler eliminare {nome}?**")
            col_conf, col_annulla = st.columns([1, 1])

            with col_conf:
                if st.button("✅ Conferma", key=f"{key_prefix}_conferma"):
                    cursor = conn.cursor()
                    cursor.execute("DELETE FROM Impianto WHERE nome = ?", (defaults["nome"],))
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

st.title("♻️ Impianti")

conn = get_connection()
cursor = conn.cursor()

tab1, tab2 = st.tabs(["✏️ Visualizza e modifica", "➕ Nuovo"])

# ---------------------------------------------------------------------------------------- #
# VISUALIZZA E GESTISCI IMPIANTI ESISTENTI
# ---------------------------------------------------------------------------------------- #
with tab1:
    impianti = pd.read_sql_query("SELECT * FROM Impianto", conn)

    # Visualizza schede impianti
    for i, row in impianti.iterrows():
        with st.expander(f"♻️ {row['nome']}"):
            dati = row.to_dict()
            form_impianto(conn, dati_esistenti=dati, key_prefix=f"imp_{i}")

# ---------------------------------------------------------------------------------------- #
# AGGIUNGI NUOVO IMPIANTO
# ---------------------------------------------------------------------------------------- #

# MOSTRA TOAST SE FLAG ATTIVA (fuori da tab2 o all'inizio)
if st.session_state.get("show_toast_nuovo_impianto", False):
    st.toast(f"✅ Impianto '{st.session_state.get('last_nuovo_nome', '')}' salvato correttamente!")
    st.session_state.show_toast_nuovo_impianto = False
    st.session_state.last_nuovo_nome = ""

# Funzione per resettare i campi del nuovo impianot
def reset_nuovo_impianto():
    st.session_state["nuovo_nome"] = ""
    st.session_state["nuovo_deposito"] = 0
    st.session_state["nuovo_perc_eff"] = 0.0
    st.session_state["nuovo_perc_scarti"] = 0.0
    st.session_state["nuovo_perc_trasporti"] = 0.0
    st.session_state["nuovo_energia"] = 0.0

# TAB2: Inserimento nuovo impianto
with tab2:
    # Reset prima di creare i widget
    if st.session_state.get("reset_nuovo_impianto", False):
        reset_nuovo_impianto()
        st.session_state.reset_nuovo_impianto = False

    with st.container():
        # Widget con chiavi fissate
        st.text_input("Nome impianto", key="nuovo_nome")
        st.number_input("Capacità max deposito (t)", min_value=0, step=1, key="nuovo_deposito")
        st.number_input("Energia prodotta (kW)", min_value=0.0, step=1.0, key="nuovo_energia")
        col1, col2, col3 = st.columns(3)
        with col1:
            st.number_input("Effluenti zootecnici [%]", min_value=0.0, max_value=100.0, step=1.0, key="nuovo_perc_eff")
        with col2:
            st.number_input("Colture e scarti [%]", min_value=0.0, max_value=100.0, step=1.0, key="nuovo_perc_scarti")
        with col2:
            st.number_input("Trasporti [%]", min_value=0.0, max_value=100.0, step=1.0, key="nuovo_perc_trasporti")
        

        # Pulsanti finali
        st.markdown("---")
        col_save, col_cancel = st.columns([1, 1])

        with col_save:
            if st.button("💾 Salva", use_container_width=True, key="save_new"):
                dati = {
                    "nome": st.session_state["nuovo_nome"],
                    "deposito_max": st.session_state["nuovo_deposito"],
                    "perc_effluenti_zootecnici": st.session_state["nuovo_perc_eff"],
                    "perc_colture_scarti": st.session_state["nuovo_perc_scarti"],
                    "perc_trasporti": st.session_state["nuovo_perc_trasporti"],
                    "energia_kw": st.session_state["nuovo_energia"]
                }
                if dati["nome"] == "" or dati["deposito_max"] == 0:
                    st.error("❌ Compila tutti i campi obbligatori.")
                else:
                    try:
                        cursor = conn.cursor()
                        cursor.execute(
                            """
                            INSERT INTO Impianto (nome, deposito_max, perc_effluenti_zootecnici, perc_colture_scarti, perc_trasporti, energia_kw)
                            VALUES (?, ?, ?, ?, ?, ?)
                            """,
                            (dati["nome"], dati["deposito_max"], dati["perc_effluenti_zootecnici"],
                            dati["perc_colture_scarti"], dati["perc_trasporti"], dati["energia_kw"])
                        )
                        conn.commit()
                        st.session_state.last_nuovo_nome = dati["nome"]
                        st.session_state.show_toast_nuovo_impianto = True
                        st.session_state.reset_nuovo_impianto = True
                        st.rerun()
                    except sqlite3.IntegrityError:
                        st.error("❌ Errore: esiste già un impianto con questo nome.")
                    except Exception as e:
                        st.error(f"❌ Errore durante il salvataggio: {str(e)}")

        with col_cancel:
            if st.button("❌ Annulla", use_container_width=True, key="cancel_new"):
                st.session_state.reset_nuovo_impianto = True
                st.rerun()