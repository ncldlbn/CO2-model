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

def form_trasporto(conn, dati_esistenti=None, key_prefix=""):
    """Form per visualizzare e modificare un trasporto"""

    # Valori di default
    defaults = {
        "id_trasporto": None,
        "nome": "",
        "EF": 0,
        "capacita_max": 0
    }

    if dati_esistenti:
        for key in defaults:
            val = dati_esistenti.get(key)
            if val is not None:
                defaults[key] = int(val) if key in ["capacita_max", "EF"] else val

    nome = st.text_input("Nome mezzo di trasporto", value=defaults["nome"], key=f"{key_prefix}_nome")
    EF = st.number_input("Fattore di emissione (g/km)", value=defaults["EF"], min_value=0, step=1, key=f"{key_prefix}_EF")
    capacita_max = st.number_input("Capacità (t)", value=defaults["capacita_max"], min_value=0, step=1, key=f"{key_prefix}_capacita")

    # Pulsanti finali
    st.markdown("---")
    col_update, col_delete = st.columns(2)

    with col_update:
        if st.button("💾 Salva modifiche", key=f"{key_prefix}_salva"):
            cursor = conn.cursor()
            cursor.execute(
                "UPDATE Trasporto SET nome = ?, EF = ?, capacita_max = ? WHERE id_trasporto= ?",
                (nome, EF, capacita_max, defaults["id_trasporto"])
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
                    cursor.execute("DELETE FROM Trasporto WHERE nome = ?", (defaults["nome"],))
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

st.title("🚛 Mezzi di trasporto")

conn = get_connection()
cursor = conn.cursor()

tab1, tab2 = st.tabs(["✏️ Visualizza e modifica", "➕ Nuovo"])

# ---------------------------------------------------------------------------------------- #
# VISUALIZZA E GESTISCI trasportI ESISTENTI
# ---------------------------------------------------------------------------------------- #
with tab1:
    trasporti = pd.read_sql_query("SELECT * FROM Trasporto", conn)

    # Visualizza schede trasporti
    for i, row in trasporti.iterrows():
        with st.expander(f"🚛 {row['nome']}"):
            dati = row.to_dict()
            form_trasporto(conn, dati_esistenti=dati, key_prefix=f"trasp_{i}")

# ---------------------------------------------------------------------------------------- #
# AGGIUNGI NUOVO trasportO
# ---------------------------------------------------------------------------------------- #

# MOSTRA TOAST SE FLAG ATTIVA (fuori da tab2 o all'inizio)
if st.session_state.get("show_toast_nuovo_trasporto", False):
    st.toast(f"✅ '{st.session_state.get('last_nuovo_nome', '')}' salvato correttamente!")
    st.session_state.show_toast_nuovo_trasporto = False
    st.session_state.last_nuovo_nome = ""

# Funzione per resettare i campi del nuovo impianot
def reset_nuovo_trasporto():
    st.session_state["nuovo_nome"] = ""
    st.session_state["nuova_EF"] = 0
    st.session_state["nuova_capacita"] = 0

# TAB2: Inserimento nuovo trasporto
with tab2:
    # Reset prima di creare i widget
    if st.session_state.get("reset_nuovo_trasporto", False):
        reset_nuovo_trasporto()
        st.session_state.reset_nuovo_trasporto = False

    with st.container():
        # Widget con chiavi fissate
        st.text_input("Nome trasporto", key="nuovo_nome")
        EF = st.number_input("Fattore di emissione (g/km)", min_value=0, step=1, key="nuovo_EF")
        capacita_max = st.number_input("Capacità (t)", min_value=0, step=1, key="nuova_capacita")

        # Pulsanti finali
        st.markdown("---")
        col_save, col_cancel = st.columns([1, 1])

        with col_save:
            if st.button("💾 Salva", use_container_width=True, key="save_new"):
                dati = {
                    "nome": st.session_state["nuovo_nome"],
                    "EF": st.session_state["nuovo_EF"],
                    "capacita_max": st.session_state["nuova_capacita"]
                }
                if (dati["nome"] == "" or dati["EF"] == 0 or  dati["capacita_max"] == 0):
                    st.error("❌ Compila tutti i campi obbligatori.")
                else:
                    try:
                        cursor = conn.cursor()
                        cursor.execute("INSERT INTO Trasporto (nome, EF, capacita_max) VALUES (?, ?, ?)", 
                                       (dati["nome"], dati["EF"], dati["capacita_max"]))
                        conn.commit()
                        st.session_state.last_nuovo_nome = dati["nome"]
                        st.session_state.show_toast_nuovo_trasporto = True
                        st.session_state.reset_nuovo_trasporto = True
                        st.rerun()
                    except sqlite3.IntegrityError:
                        st.error("❌ Errore: esiste già un trasporto con questo nome.")
                    except Exception as e:
                        st.error(f"❌ Errore durante il salvataggio: {str(e)}")

        with col_cancel:
            if st.button("❌ Annulla", use_container_width=True, key="cancel_new"):
                st.session_state.reset_nuovo_trasporto = True
                st.rerun()