import streamlit as st
import pandas as pd
from db import get_connection
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
    """Form per visualizzare e modificare un impianto con bilancio energetico strutturato e ricettori"""

    # Valori di default allineati alla struttura del DB
    defaults = {
        "id_impianto": None,
        "nome": "",
        "separazione": 0.00,
        "olio_lubrificante": 0.0,
        "rifiuti": 0.0,
        "acqua": 0.0,
        "scarichi": 0.0,
        "id_mezzo_liquido": 2,
        "id_mezzo_solido": 1,
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
                              
    # RIASSUNTO MASSA CONFERITA
    if defaults["id_impianto"]:
        st.markdown("---")
        st.markdown('<div style="font-size:1rem;font-weight:600;margin-bottom:0.5rem;margin-top:0.25rem;">📊 Ricetta impianto</div>', unsafe_allow_html=True)

        cursor.execute("""
            SELECT 
                SUM(CASE WHEN uba_letame = 1 THEN prod_letame ELSE uba_letame * prod_letame END) as totale_letame,
                SUM(CASE WHEN uba_liquame = 1 THEN prod_liquame ELSE uba_liquame * prod_liquame END) as totale_liquame,
                SUM(pollina) as totale_pollina,
                SUM(sottoprodotti) as totale_sottoprodotti,
                SUM(colture) as totale_colture
            FROM allevatore 
            WHERE id_impianto_associato = ?
        """, (defaults["id_impianto"],))
        risultato_allevatori = cursor.fetchone()

        cursor.execute("""
            SELECT tipo, SUM(carico) as totale_carico
            FROM conferitori
            WHERE id_impianto = ?
            GROUP BY tipo
        """, (defaults["id_impianto"],))
        risultati_conferitori = cursor.fetchall()

        totale_letame = totale_liquame = totale_pollina = totale_sottoprodotti = totale_colture = 0

        if risultato_allevatori:
            totale_letame        += risultato_allevatori[0] or 0
            totale_liquame       += risultato_allevatori[1] or 0
            totale_pollina       += risultato_allevatori[2] or 0
            totale_sottoprodotti += risultato_allevatori[3] or 0
            totale_colture       += risultato_allevatori[4] or 0

        for tipo, carico in risultati_conferitori:
            if tipo == "Letame":          totale_letame        += carico or 0
            elif tipo == "Liquame":       totale_liquame       += carico or 0
            elif tipo == "Pollina":       totale_pollina       += carico or 0
            elif tipo == "Sottoprodotti": totale_sottoprodotti += carico or 0
            elif tipo == "Colture":       totale_colture       += carico or 0

        totale_generale = totale_letame + totale_liquame + totale_pollina + totale_sottoprodotti + totale_colture

        def result_ricetta(label, value, unit=""):
            unit_html = f'<span style="font-size:0.75rem;opacity:0.5;margin-left:0.3rem;">{unit}</span>' if unit else ""
            return (
                f'<div style="display:flex;justify-content:space-between;align-items:baseline;padding:0.35rem 0;">'
                f'<span style="font-size:0.82rem;opacity:0.5;">{label}</span>'
                f'<span style="display:flex;align-items:baseline;">'
                f'<span style="font-size:0.92rem;">{value:,.1f}</span>'
                f'{unit_html}'
                f'</span></div>'
            )

        html = ""
        html += result_ricetta("Letame",        totale_letame,        "ton/anno")
        html += result_ricetta("Liquame",        totale_liquame,       "ton/anno")
        html += result_ricetta("Pollina",        totale_pollina,       "ton/anno")
        html += result_ricetta("Sottoprodotti",  totale_sottoprodotti, "ton/anno")
        html += result_ricetta("Colture",        totale_colture,       "ton/anno")
        html += f'<div style="height:1px;background:rgba(128,128,128,0.2);margin:0.4rem 0;"></div>'
        html += result_ricetta("Totale",         totale_generale,      "ton/anno")

        st.markdown(html, unsafe_allow_html=True)
                
    else:
        st.info("ℹ️ Nessun allevatore associato a questo impianto o nessuna massa conferita registrata.")
    
    # SEZIONE BILANCIO ENERGETICO
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

    # SEZIONE MEZZI DI TRASPORTO
    st.markdown("---")
    st.subheader("Mezzi di trasporto")

    cursor.execute("SELECT id_trasporto, tipo FROM trasporti WHERE id_trasporto != 0 ORDER BY tipo")
    mezzi_rows = cursor.fetchall()
    mezzi_dict = {row[1]: row[0] for row in mezzi_rows}
    mezzi_nomi = list(mezzi_dict.keys())

    def _mezzo_index(id_mezzo):
        tipo = next((t for t, i in mezzi_dict.items() if i == id_mezzo), None)
        return mezzi_nomi.index(tipo) if tipo in mezzi_nomi else 0

    col1, col2 = st.columns(2)
    with col1:
        mezzo_liq_nome = st.selectbox(
            "Trasporto biomassa liquida",
            mezzi_nomi,
            index=_mezzo_index(defaults["id_mezzo_liquido"]),
            key=f"{key_prefix}_mezzo_liquido"
        )
        id_mezzo_liquido = mezzi_dict[mezzo_liq_nome]
    with col2:
        mezzo_sol_nome = st.selectbox(
            "Trasporto biomassa solida",
            mezzi_nomi,
            index=_mezzo_index(defaults["id_mezzo_solido"]),
            key=f"{key_prefix}_mezzo_solido"
        )
        id_mezzo_solido = mezzi_dict[mezzo_sol_nome]

    # SEZIONE CONSUMI E SCARTI
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
    
    # SEZIONE CONFERITORI
    st.markdown("---")
    st.subheader("Altri conferitori")

    if not defaults["id_impianto"]:
        st.info("ℹ️ Sarà possibile aggiungere conferitori e ricettori solo dopo aver creato l'impianto.")
    else:
        # Recupera i conferitori esistenti
        conferitori_esistenti = []
        cursor.execute("""
            SELECT c.id_conferitore, c.tipo, c.distanza, c.carico, c.nome_conferitore
            FROM conferitori c
            WHERE c.id_impianto = ?
            ORDER BY c.id_conferitore
        """, (defaults["id_impianto"],))
        conferitori_esistenti = cursor.fetchall()

        # Dizionario per memorizzare i valori aggiornati dei conferitori
        conferitori_aggiornati = {}

        # Mostra i conferitori esistenti
        if conferitori_esistenti:
            for i, conferitore in enumerate(conferitori_esistenti):
                id_conferitore, tipo, distanza, carico, nome_conferitore = conferitore
                
                col1, col2, col3, col4, col5 = st.columns([2, 2, 2, 2, 1])
                
                with col1:
                    nome_conferitore_val = st.text_input(
                        "Nome conferitore",
                        value=nome_conferitore or f"Conferitore {i+1}",
                        key=f"{key_prefix}_conf_{id_conferitore}_nome"
                    )
                
                with col2:
                    tipo_selected = st.selectbox(
                        "Tipo",
                        ["Liquame", "Letame", "Pollina", "Sottoprodotti", "Colture"],
                        index=["Liquame", "Letame", "Pollina", "Sottoprodotti", "Colture"].index(tipo) if tipo in ["Liquame", "Letame", "Pollina", "Sottoprodotti", "Colture"] else 0,
                        key=f"{key_prefix}_conf_{id_conferitore}_tipo"
                    )
                
                with col3:
                    nuova_distanza = st.number_input(
                        "Distanza (km)",
                        value=float(distanza),
                        min_value=0.0,
                        step=0.1,
                        key=f"{key_prefix}_conf_{id_conferitore}_distanza"
                    )
                
                with col4:
                    nuovo_carico = st.number_input(
                        "Carico (ton)",
                        value=int(carico or 0),
                        min_value=0,
                        step=1,
                        key=f"{key_prefix}_conf_{id_conferitore}_carico"
                    )
                
                with col5:
                    st.markdown("<br>", unsafe_allow_html=True)
                    if st.button("🗑️", key=f"{key_prefix}_conf_{id_conferitore}_elimina"):
                        cursor.execute("DELETE FROM conferitori WHERE id_conferitore = ?", (id_conferitore,))
                        conn.commit()
                        st.toast("Conferitore eliminato")
                        st.rerun()
                
                conferitori_aggiornati[id_conferitore] = {
                    "nome_conferitore": nome_conferitore_val,
                    "tipo": tipo_selected,
                    "distanza": nuova_distanza,
                    "carico": nuovo_carico
                }

        # Inizializza session state per il nuovo conferitore
        if f"{key_prefix}_nuovo_conferitore_attivo" not in st.session_state:
            st.session_state[f"{key_prefix}_nuovo_conferitore_attivo"] = False

        if not st.session_state[f"{key_prefix}_nuovo_conferitore_attivo"]:
            if st.button("➕ Aggiungi nuovo conferitore", key=f"{key_prefix}_btn_nuovo_conferitore"):
                st.session_state[f"{key_prefix}_nuovo_conferitore_attivo"] = True
                st.rerun()
        else:
            st.markdown("**Nuovo conferitore:**")
            col1, col2, col3, col4, col5 = st.columns([2, 2, 2, 2, 2])
            
            with col1:
                nuovo_nome_conferitore = st.text_input(
                    "Nome conferitore",
                    value="",
                    key=f"{key_prefix}_nuovo_nome_conferitore"
                )
            
            with col2:
                nuovo_tipo = st.selectbox(
                    "Tipo",
                    ["Liquame", "Letame", "Pollina", "Sottoprodotti", "Colture"],
                    key=f"{key_prefix}_nuovo_tipo_conferitore"
                )
            
            with col3:
                nuova_distanza = st.number_input(
                    "Distanza (km)",
                    min_value=0.0,
                    step=0.1,
                    value=0.0,
                    key=f"{key_prefix}_nuova_distanza_conferitore"
                )
            
            with col4:
                nuovo_carico = st.number_input(
                    "Carico (ton)",
                    min_value=0,
                    step=1,
                    value=0,
                    key=f"{key_prefix}_nuovo_carico_conferitore"
                )
            
            with col5:
                st.markdown("<br>", unsafe_allow_html=True)
                col_salva, col_annulla = st.columns(2)
                with col_salva:
                    if st.button("💾 Salva", key=f"{key_prefix}_salva_nuovo_conferitore"):
                        if nuovo_nome_conferitore:
                            cursor.execute("""
                                INSERT INTO conferitori (id_impianto, nome_conferitore, tipo, distanza, carico)
                                VALUES (?, ?, ?, ?, ?)
                            """, (defaults["id_impianto"], nuovo_nome_conferitore, nuovo_tipo, nuova_distanza, nuovo_carico))
                            conn.commit()
                            st.toast("Conferitore aggiunto")
                            st.session_state[f"{key_prefix}_nuovo_conferitore_attivo"] = False
                            st.rerun()
                        else:
                            st.error("Il nome del conferitore è obbligatorio")
                
                with col_annulla:
                    if st.button("❌ Annulla", key=f"{key_prefix}_annulla_nuovo_conferitore"):
                        st.session_state[f"{key_prefix}_nuovo_conferitore_attivo"] = False
                        st.rerun()

    # SEZIONE RICETTORI
    st.markdown("---")
    st.subheader("Altri ricettori")

    if not defaults["id_impianto"]:
        st.info("ℹ️ Sarà possibile aggiungere conferitori e ricettori solo dopo aver creato l'impianto.")
    else:
        # Recupera i ricettori esistenti
        ricettori_esistenti = []
        cursor.execute("""
            SELECT r.id_ricettore, r.tipo, r.distanza, r.carico, r.nome_ricettore
            FROM ricettori r
            WHERE r.id_impianto = ?
            ORDER BY r.id_ricettore
        """, (defaults["id_impianto"],))
        ricettori_esistenti = cursor.fetchall()

        # Dizionario per memorizzare i valori aggiornati dei ricettori
        ricettori_aggiornati = {}

        if ricettori_esistenti:
            for i, ricettore in enumerate(ricettori_esistenti):
                id_ricettore, tipo, distanza, carico, nome_ricettore = ricettore
                
                col1, col2, col3, col4, col5 = st.columns([2, 2, 2, 2, 1])
                
                with col1:
                    nome_ricettore_val = st.text_input(
                        "Nome ricettore",
                        value=nome_ricettore or f"Ricettore {i+1}",
                        key=f"{key_prefix}_ric_{id_ricettore}_nome"
                    )
                
                with col2:
                    tipo_selected = st.selectbox(
                        "Tipo",
                        ["BioLNG", "BioCO2", "Digestato Liquido", "Digestato Separato"],
                        index=["BioLNG", "BioCO2", "Digestato Liquido", "Digestato Separato"].index(tipo) if tipo in ["BioLNG", "BioCO2", "Digestato Liquido", "Digestato Separato"] else 0,
                        key=f"{key_prefix}_ric_{id_ricettore}_tipo"
                    )
                
                with col3:
                    nuova_distanza = st.number_input(
                        "Distanza (km)",
                        value=float(distanza),
                        min_value=0.0,
                        step=0.1,
                        key=f"{key_prefix}_ric_{id_ricettore}_distanza"
                    )
                
                with col4:
                    nuovo_carico = st.number_input(
                        "Carico (ton)",
                        value=int(carico or 0),
                        min_value=0,
                        step=1,
                        key=f"{key_prefix}_ric_{id_ricettore}_carico"
                    )
                
                with col5:
                    st.markdown("<br>", unsafe_allow_html=True)
                    if st.button("🗑️", key=f"{key_prefix}_ric_{id_ricettore}_elimina"):
                        cursor.execute("DELETE FROM ricettori WHERE id_ricettore = ?", (id_ricettore,))
                        conn.commit()
                        st.toast("Ricettore eliminato")
                        st.rerun()
                
                ricettori_aggiornati[id_ricettore] = {
                    "nome_ricettore": nome_ricettore_val,
                    "tipo": tipo_selected,
                    "distanza": nuova_distanza,
                    "carico": nuovo_carico
                }

        if f"{key_prefix}_nuovo_ricettore_attivo" not in st.session_state:
            st.session_state[f"{key_prefix}_nuovo_ricettore_attivo"] = False

        if not st.session_state[f"{key_prefix}_nuovo_ricettore_attivo"]:
            if st.button("➕ Aggiungi nuovo ricettore", key=f"{key_prefix}_btn_nuovo_ricettore"):
                st.session_state[f"{key_prefix}_nuovo_ricettore_attivo"] = True
                st.rerun()
        else:
            st.markdown("**Nuovo ricettore:**")
            col1, col2, col3, col4, col5 = st.columns([2, 2, 2, 2, 2])
            
            with col1:
                nuovo_nome_ricettore = st.text_input(
                    "Nome ricettore",
                    value="",
                    key=f"{key_prefix}_nuovo_nome_ricettore"
                )
            
            with col2:
                nuovo_tipo = st.selectbox(
                    "Tipo",
                    ["BioLNG", "BioCO2", "Digestato Liquido", "Digestato Separato"],
                    key=f"{key_prefix}_nuovo_tipo_ricettore"
                )
            
            with col3:
                nuova_distanza = st.number_input(
                    "Distanza (km)",
                    min_value=0.0,
                    step=0.1,
                    value=0.0,
                    key=f"{key_prefix}_nuova_distanza_ricettore"
                )
            
            with col4:
                nuovo_carico = st.number_input(
                    "Carico (ton)",
                    min_value=0,
                    step=1,
                    value=0,
                    key=f"{key_prefix}_nuovo_carico_ricettore"
                )
            
            with col5:
                st.markdown("<br>", unsafe_allow_html=True)
                col_salva, col_annulla = st.columns(2)
                with col_salva:
                    if st.button("💾 Salva", key=f"{key_prefix}_salva_nuovo_ricettore"):
                        if nuovo_nome_ricettore:
                            cursor.execute("""
                                INSERT INTO ricettori (id_impianto, nome_ricettore, tipo, distanza, carico)
                                VALUES (?, ?, ?, ?, ?)
                            """, (defaults["id_impianto"], nuovo_nome_ricettore, nuovo_tipo, nuova_distanza, nuovo_carico))
                            conn.commit()
                            st.toast("Ricettore aggiunto")
                            st.session_state[f"{key_prefix}_nuovo_ricettore_attivo"] = False
                            st.rerun()
                        else:
                            st.error("Il nome del ricettore è obbligatorio")
                
                with col_annulla:
                    if st.button("❌ Annulla", key=f"{key_prefix}_annulla_nuovo_ricettore"):
                        st.session_state[f"{key_prefix}_nuovo_ricettore_attivo"] = False
                        st.rerun()
    
    st.markdown("---")
    col_update, col_delete = st.columns(2)
    
    if defaults["id_impianto"]:
        with col_update:
            if st.button("💾 Salva modifiche", key=f"{key_prefix}_salva"):
                cursor = conn.cursor()
                
                cursor.execute(
                    """
                    UPDATE Impianto
                    SET nome = ?, separazione = ?, olio_lubrificante = ?, rifiuti = ?, acqua = ?, scarichi = ?,
                        id_mezzo_liquido = ?, id_mezzo_solido = ?
                    WHERE id_impianto = ?
                    """,
                    (nome, separazione,
                     olio_lubrificante, rifiuti, acqua, scarichi,
                     id_mezzo_liquido, id_mezzo_solido, defaults["id_impianto"])
                )
                
                cursor.execute("DELETE FROM bilancio_energetico WHERE id_impianto = ?", (defaults["id_impianto"],))
                
                for key, dati in nuovo_bilancio.items():
                    cursor.execute(
                        """
                        INSERT INTO bilancio_energetico 
                        (id_impianto, categoria, tipo, valore, unita) 
                        VALUES (?, ?, ?, ?, ?)
                        """,
                        (defaults["id_impianto"], dati["categoria"], dati["tipo"], 
                         dati["valore"], dati["unita"])
                    )
                
                for id_ricettore, dati_ricettore in ricettori_aggiornati.items():
                    cursor.execute("""
                        UPDATE ricettori 
                        SET nome_ricettore = ?, tipo = ?, distanza = ?, carico = ?
                        WHERE id_ricettore = ?
                    """, (
                        dati_ricettore["nome_ricettore"],
                        dati_ricettore["tipo"], 
                        dati_ricettore["distanza"], 
                        dati_ricettore["carico"],
                        id_ricettore
                    ))
                
                if (st.session_state[f"{key_prefix}_nuovo_ricettore_attivo"] and
                    nuovo_tipo is not None):
                    
                    cursor.execute("""
                        INSERT INTO ricettori (id_impianto, nome_ricettore, tipo, distanza, carico)
                        VALUES (?, ?, ?, ?, ?)
                    """, (defaults["id_impianto"], nuovo_nome_ricettore, nuovo_tipo, nuova_distanza, nuovo_carico))
                    st.session_state[f"{key_prefix}_nuovo_ricettore_attivo"] = False
                
                conn.commit()
                st.toast("✅ Modifiche salvate.")
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
                        cursor.execute("DELETE FROM bilancio_energetico WHERE id_impianto = ?", (defaults["id_impianto"],))
                        cursor.execute("DELETE FROM ricettori WHERE id_impianto = ?", (defaults["id_impianto"],))
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
        "id_mezzo_liquido": id_mezzo_liquido,
        "id_mezzo_solido": id_mezzo_solido,
        "bilancio_energetico": nuovo_bilancio,
        "nuovo_ricettore": None
    }

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
    impianti = pd.read_sql_query("SELECT * FROM impianto", conn)

    if impianti.empty:
        st.info("Nessun impianto presente nel database.")
    else:
        impianti_options = [f"{row['id_impianto']} - {row['nome']}" for _, row in impianti.iterrows()]
        
        selected_impianto = st.selectbox(
            "Seleziona l'impianto da visualizzare/modificare",
            impianti_options,
            key="select_impianto"
        )
        
        selected_id = int(selected_impianto.split(" - ")[0])
        selected_data = impianti[impianti['id_impianto'] == selected_id].iloc[0].to_dict()
        
        st.markdown("---")
        form_impianto(conn, dati_esistenti=selected_data, key_prefix=f"selected_{selected_id}")

# ---------------------------------------------------------------------------------------- #
# AGGIUNGI NUOVO IMPIANTO
# ---------------------------------------------------------------------------------------- #
with tab2:
    
    # Contatore per forzare la ricreazione dei widget dopo il salvataggio
    if "nuovo_impianto_form_counter" not in st.session_state:
        st.session_state["nuovo_impianto_form_counter"] = 0

    form_counter = st.session_state["nuovo_impianto_form_counter"]
    key_prefix_nuovo = f"nuovo_impianto_{form_counter}"

    defaults = {
        "nome": "",
        "separazione": 0.00,
        "olio_lubrificante": 0.0,
        "rifiuti": 0.0,
        "acqua": 0.0,
        "scarichi": 0.0
    }
    
    dati_nuovo = form_impianto(conn, dati_esistenti=defaults, key_prefix=key_prefix_nuovo)
    
    if st.button("💾 Crea Nuovo Impianto", key="crea_nuovo_impianto", use_container_width=True):
        if not dati_nuovo["nome"]:
            st.error("❌ Il campo Nome è obbligatorio.")
        else:
            try:
                cursor = conn.cursor()
                cursor.execute(
                    """
                    INSERT INTO Impianto (
                        nome, separazione,
                        olio_lubrificante, rifiuti, acqua, scarichi,
                        id_mezzo_liquido, id_mezzo_solido
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (dati_nuovo["nome"], dati_nuovo["separazione"],
                     dati_nuovo["olio_lubrificante"], dati_nuovo["rifiuti"],
                     dati_nuovo["acqua"], dati_nuovo["scarichi"],
                     dati_nuovo["id_mezzo_liquido"], dati_nuovo["id_mezzo_solido"])
                )
                
                id_impianto = cursor.lastrowid
                
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
                
                conn.commit()
                st.toast(f"✅ Impianto '{dati_nuovo['nome']}' creato correttamente!")
                # Incrementa il contatore: Streamlit ricrea tutti i widget da zero
                st.session_state["nuovo_impianto_form_counter"] += 1
                st.rerun()
                
            except sqlite3.IntegrityError:
                st.error("❌ Errore: esiste già un impianto con questo nome.")
            except Exception as e:
                st.error(f"❌ Errore durante il salvataggio: {str(e)}")
