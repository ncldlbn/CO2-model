import streamlit as st
import sqlite3
from db import get_connection
import pandas as pd
import sys
import os
import datetime

sys.path.append(os.path.join(os.path.dirname(__file__), '../../src'))

from objects import Allevatore, Impianto, Trasporto, FattoriEmissione
from model import (
    co2_liquame_semplificata,
    co2_letame_semplificata,
    co2eq_trasporto,
    co2eq_digestato,
    co2eq_pollina,
    componenti_co2,
    co2eq_ee_prod_netta,
    co2eq_calore_netta,
    co2eq_biometano,
    co2eq_biolng,
    co2eq_biogenica,
    co2eq_ee_acquistata,
    co2eq_metano_acq,
    co2eq_lng_acq,
    co2eq_impianto
)

# Calcola il percorso assoluto del file corrente
current_dir = os.path.dirname(os.path.abspath(__file__))
# Torna su di 2 livelli: dashboard/pages -> dashboard -> progetto root
project_root = os.path.abspath(os.path.join(current_dir, '../..'))
# Percorso completo al database
db = os.path.join(project_root, 'data.db')


# ---------------------------------------------------------
# Connessione DB e selezione impianto
# ---------------------------------------------------------
conn = get_connection()
cursor = conn.cursor()
cursor.execute("SELECT id_impianto, nome FROM impianto ORDER BY nome")
impianti = cursor.fetchall()
conn.close()

opzioni_impianti = [nome for _, nome in impianti]
impianto_selezionato = st.selectbox("Seleziona un impianto:", opzioni_impianti)

id_impianto_selezionato = next((id_imp for id_imp, nome in impianti if nome == impianto_selezionato), None)

# Recupera allevatori associati
conn = get_connection()
cursor = conn.cursor()
cursor.execute("""
    SELECT id_allevatore, denominazione_sociale 
    FROM allevatore 
    WHERE id_impianto_associato = ? 
    ORDER BY denominazione_sociale
""", (id_impianto_selezionato,))
allevatori_impianto = cursor.fetchall()
conn.close()

# ---------------------------------------------------------
# Esecuzione simulazione
# ---------------------------------------------------------
if st.button("Esegui simulazione", use_container_width=True):

    if not id_impianto_selezionato:
        st.error("Seleziona un impianto prima di eseguire la simulazione")
        st.stop()

    if not allevatori_impianto:
        st.error("Nessun allevatore associato a questo impianto")
        st.stop()

    # Carica impianto e fattori di emissione
    try:
        I = Impianto.from_db(db, id_impianto_selezionato)
        EF = FattoriEmissione(db)
    except Exception as e:
        st.error(f"Errore caricamento dati impianto: {str(e)}")
        st.stop()

    # Calcolo energia netta con le nuove funzioni
    try:
        # Chiama direttamente le funzioni del modello
        co2eq_ee_prod_netta_series = co2eq_ee_prod_netta(I, EF, db)
        co2eq_calore_netta_series = co2eq_calore_netta(I, EF, db)
        co2eq_biometano_series = co2eq_biometano(I, EF, db)
        co2eq_biolng_series = co2eq_biolng(I, EF, db)
        co2eq_biogenica_series = co2eq_biogenica(I, EF, db)
        co2eq_ee_acq_series = co2eq_ee_acquistata(I, EF, db)
        co2eq_metano_acq_series = co2eq_metano_acq(I, EF, db)
        co2eq_lng_acq_series = co2eq_lng_acq(I, EF, db)
        
        # Estrai i totali per la visualizzazione
        co2eq_ee_netta = co2eq_ee_prod_netta_series['co2_tot']
        co2eq_calore_netta = co2eq_calore_netta_series['co2_tot']
        co2eq_biomet_netta = co2eq_biometano_series['co2_tot']
        co2eq_biolng_netta = co2eq_biolng_series['co2_tot']
        co2eq_biogenica_prod = co2eq_biogenica_series['co2_tot']
        co2eq_ee_acq = co2eq_ee_acq_series['co2_tot']
        co2eq_met_acq = co2eq_metano_acq_series['co2_tot']
        co2eq_lng_acq = co2eq_lng_acq_series['co2_tot']
        
    except Exception as e:
        st.error(f"Errore calcolo energia: {str(e)}")
        co2eq_ee_netta = co2eq_calore_netta = co2eq_biomet_netta = co2eq_biolng_netta = 0
        co2eq_biogenica_prod = co2eq_ee_acq = co2eq_met_acq = co2eq_lng_acq = 0
        co2eq_ee_prod_netta_series = co2eq_calore_netta_series = co2eq_biometano_series = \
        co2eq_biolng_series = co2eq_biogenica_series = co2eq_ee_acq_series = \
        co2eq_metano_acq_series = co2eq_lng_acq_series = pd.Series({
            "co2_fossile": 0, "co2_biogenica": 0, "co2_dluc": 0, "co2_tot": 0
        })

    # Calcolo emissioni impianto (ora restituisce Series)
    try:
        co2eq_olio_series, co2eq_rifiuti_series, co2eq_acqua_series, co2eq_scarichi_series = co2eq_impianto(I, EF, db)
        
        # Estrai i totali dalle Series per la visualizzazione
        co2eq_olio_val = co2eq_olio_series['co2_tot'] if isinstance(co2eq_olio_series, pd.Series) else 0
        co2eq_rifiuti_val = co2eq_rifiuti_series['co2_tot'] if isinstance(co2eq_rifiuti_series, pd.Series) else 0
        co2eq_acqua_val = co2eq_acqua_series['co2_tot'] if isinstance(co2eq_acqua_series, pd.Series) else 0
        co2eq_scarichi_val = co2eq_scarichi_series['co2_tot'] if isinstance(co2eq_scarichi_series, pd.Series) else 0
        
    except Exception as e:
        st.error(f"Errore calcolo emissioni impianto: {str(e)}")
        co2eq_olio_val = co2eq_rifiuti_val = co2eq_acqua_val = co2eq_scarichi_val = 0
        co2eq_olio_series = co2eq_rifiuti_series = co2eq_acqua_series = co2eq_scarichi_series = pd.Series({
            "co2_fossile": 0, "co2_biogenica": 0, "co2_dluc": 0, "co2_tot": 0
        })

    risultati_allevatori = []

    # Totali aggregati
    tot_let = tot_liq = tot_poll = 0
    tot_tlet = tot_tliq = tot_tdig = 0
    tot_digestato = 0
    tot_co2_dig = 0
    
    # Dati per la tabella dei trasporti
    trasporti_data = {
        'letame': {'co2_fossile': 0, 'co2_biogenica': 0, 'co2_dluc': 0, 'co2_tot': 0, 'n_viaggi': 0, 'tipo_trasporto': ''},
        'liquame': {'co2_fossile': 0, 'co2_biogenica': 0, 'co2_dluc': 0, 'co2_tot': 0, 'n_viaggi': 0, 'tipo_trasporto': ''},
        'digestato': {'co2_fossile': 0, 'co2_biogenica': 0, 'co2_dluc': 0, 'co2_tot': 0, 'n_viaggi': 0, 'tipo_trasporto': ''}
    }
    
    # Dati per la tabella della pollina
    pollina_data = {
        'co2_fossile': 0, 
        'co2_biogenica': 0, 
        'co2_dluc': 0, 
        'co2_tot': 0,
        'quantita_tot': 0  # tonnellate totali di pollina
    }
    
    # Dati per la tabella del digestato
    digestato_data = {
        'co2_fossile': 0, 
        'co2_biogenica': 0, 
        'co2_dluc': 0, 
        'co2_tot': 0,
        'quantita_tot': 0  # tonnellate totali di digestato
    }

    progress = st.progress(0)

    for idx, (id_allevatore, denom) in enumerate(allevatori_impianto):
        try:
            A = Allevatore.from_db(db, id_allevatore)
            T = Trasporto.from_db(db, A.id_trasporto)
        except Exception as e:
            st.warning(f"Errore caricamento allevatore {denom}: {str(e)}")
            continue

        # Inizializza variabili per questo allevatore
        co2_liq = co2_let = 0
        dep_liq = dep_let = liq_annuo = let_annuo = 0
        digestato_quantita = 0
        digestato = 0
        co2_dig = 0
        poll = 0
        co2_poll = 0
        tr_liq = tr_let = tr_dig = 0

        # CO2 biomasse - deposito costante
        try:
            co2_liq, _, dep_liq, liq_annuo = co2_liquame_semplificata(A)
        except:
            co2_liq = dep_liq = liq_annuo = 0

        try:
            co2_let, _, dep_let, let_annuo = co2_letame_semplificata(A)
        except:
            co2_let = dep_let = let_annuo = 0

        # --- TRASPORTI ---

        # Trasporto liquame
        try:
            tr_liq_result = co2eq_trasporto(T, dep_liq, dep_liq, A.distanza_impianto)
            
            # Verifica il tipo di risultato restituito
            if isinstance(tr_liq_result, tuple) and len(tr_liq_result) == 2:
                # Vecchio formato: (tipo_trasporto, co2_tot), n_viaggi
                tr_liq_componenti, n_viaggi_liq = tr_liq_result
                tipo_trasporto_liq, co2_liq_tot = tr_liq_componenti
                
                # Calcola componenti CO2 per il trasporto
                componenti_liq = componenti_co2(tipo_trasporto_liq, co2_liq_tot, db)
                
                # Aggiorna dati trasporti
                if componenti_liq is not None:
                    trasporti_data['liquame']['co2_fossile'] += componenti_liq['co2_fossile']
                    trasporti_data['liquame']['co2_biogenica'] += componenti_liq['co2_biogenica']
                    trasporti_data['liquame']['co2_dluc'] += componenti_liq['co2_dluc']
                    trasporti_data['liquame']['co2_tot'] += co2_liq_tot
                else:
                    trasporti_data['liquame']['co2_fossile'] += co2_liq_tot
                    trasporti_data['liquame']['co2_tot'] += co2_liq_tot
                
                tr_liq = co2_liq_tot
                trasporti_data['liquame']['tipo_trasporto'] = tipo_trasporto_liq
            else:
                # Nuovo formato: pd.Series, n_viaggi
                componenti_liq, n_viaggi_liq = tr_liq_result
                
                if componenti_liq is not None:
                    trasporti_data['liquame']['co2_fossile'] += componenti_liq.get('co2_fossile', 0)
                    trasporti_data['liquame']['co2_biogenica'] += componenti_liq.get('co2_biogenica', 0)
                    trasporti_data['liquame']['co2_dluc'] += componenti_liq.get('co2_dluc', 0)
                    trasporti_data['liquame']['co2_tot'] += componenti_liq.get('co2_tot', 0)
                    tr_liq = componenti_liq.get('co2_tot', 0)
                    trasporti_data['liquame']['tipo_trasporto'] = componenti_liq.get('tipo_trasporto', T.tipo)
                else:
                    tr_liq = 0
                    trasporti_data['liquame']['tipo_trasporto'] = T.tipo
            
            trasporti_data['liquame']['n_viaggi'] += n_viaggi_liq

        except Exception as e:
            st.warning(f"Errore calcolo trasporto liquame per {denom}: {str(e)}")
            tr_liq = 0

        # Trasporto letame
        try:
            tr_let_result = co2eq_trasporto(T, dep_let, dep_let * 0.7, A.distanza_impianto)
            
            # Verifica il tipo di risultato restituito
            if isinstance(tr_let_result, tuple) and len(tr_let_result) == 2:
                # Vecchio formato: (tipo_trasporto, co2_tot), n_viaggi
                tr_let_componenti, n_viaggi_let = tr_let_result
                tipo_trasporto_let, co2_let_tot = tr_let_componenti
                
                # Calcola componenti CO2 per il trasporto
                componenti_let = componenti_co2(tipo_trasporto_let, co2_let_tot, db)
                
                # Aggiorna dati trasporti
                if componenti_let is not None:
                    trasporti_data['letame']['co2_fossile'] += componenti_let['co2_fossile']
                    trasporti_data['letame']['co2_biogenica'] += componenti_let['co2_biogenica']
                    trasporti_data['letame']['co2_dluc'] += componenti_let['co2_dluc']
                    trasporti_data['letame']['co2_tot'] += co2_let_tot
                else:
                    trasporti_data['letame']['co2_fossile'] += co2_let_tot
                    trasporti_data['letame']['co2_tot'] += co2_let_tot
                
                tr_let = co2_let_tot
                trasporti_data['letame']['tipo_trasporto'] = tipo_trasporto_let
            else:
                # Nuovo formato: pd.Series, n_viaggi
                componenti_let, n_viaggi_let = tr_let_result
                
                if componenti_let is not None:
                    trasporti_data['letame']['co2_fossile'] += componenti_let.get('co2_fossile', 0)
                    trasporti_data['letame']['co2_biogenica'] += componenti_let.get('co2_biogenica', 0)
                    trasporti_data['letame']['co2_dluc'] += componenti_let.get('co2_dluc', 0)
                    trasporti_data['letame']['co2_tot'] += componenti_let.get('co2_tot', 0)
                    tr_let = componenti_let.get('co2_tot', 0)
                    trasporti_data['letame']['tipo_trasporto'] = componenti_let.get('tipo_trasporto', T.tipo)
                else:
                    tr_let = 0
                    trasporti_data['letame']['tipo_trasporto'] = T.tipo
            
            trasporti_data['letame']['n_viaggi'] += n_viaggi_let

        except Exception as e:
            st.warning(f"Errore calcolo trasporto letame per {denom}: {str(e)}")
            tr_let = 0

        # --- DIGESTATO ---
        try:
            digestato_quantita, componenti_digestato = co2eq_digestato(I, let_annuo, liq_annuo, EF, db)
            co2_dig = componenti_digestato["co2_tot"] if componenti_digestato is not None else 0

            # Dati digestato (produzione)
            if componenti_digestato is not None:
                digestato_data['co2_fossile'] += componenti_digestato.get('co2_fossile', 0)
                digestato_data['co2_biogenica'] += componenti_digestato.get('co2_biogenica', 0)
                digestato_data['co2_dluc'] += componenti_digestato.get('co2_dluc', 0)
            else:
                digestato_data['co2_fossile'] += co2_dig
            
            digestato_data['co2_tot'] += co2_dig
            digestato_data['quantita_tot'] += digestato_quantita
            
            digestato = digestato_quantita

            # Trasporto digestato
            if digestato > 0:
                tr_dig_result = co2eq_trasporto(T, digestato, digestato, A.distanza_impianto)
                
                # Verifica il tipo di risultato restituito
                if isinstance(tr_dig_result, tuple) and len(tr_dig_result) == 2:
                    # Vecchio formato: (tipo_trasporto, co2_tot), n_viaggi
                    tr_dig_componenti, n_viaggi_dig = tr_dig_result
                    tipo_trasporto_dig, co2_dig_tot = tr_dig_componenti
                    
                    # Calcola componenti CO2 per il trasporto
                    componenti_dig = componenti_co2(tipo_trasporto_dig, co2_dig_tot, db)
                    
                    # Aggiorna dati trasporti
                    if componenti_dig is not None:
                        trasporti_data['digestato']['co2_fossile'] += componenti_dig['co2_fossile']
                        trasporti_data['digestato']['co2_biogenica'] += componenti_dig['co2_biogenica']
                        trasporti_data['digestato']['co2_dluc'] += componenti_dig['co2_dluc']
                        trasporti_data['digestato']['co2_tot'] += co2_dig_tot
                    else:
                        trasporti_data['digestato']['co2_fossile'] += co2_dig_tot
                        trasporti_data['digestato']['co2_tot'] += co2_dig_tot
                    
                    tr_dig = co2_dig_tot
                    trasporti_data['digestato']['tipo_trasporto'] = tipo_trasporto_dig
                else:
                    # Nuovo formato: pd.Series, n_viaggi
                    componenti_dig, n_viaggi_dig = tr_dig_result
                    
                    if componenti_dig is not None:
                        trasporti_data['digestato']['co2_fossile'] += componenti_dig.get('co2_fossile', 0)
                        trasporti_data['digestato']['co2_biogenica'] += componenti_dig.get('co2_biogenica', 0)
                        trasporti_data['digestato']['co2_dluc'] += componenti_dig.get('co2_dluc', 0)
                        trasporti_data['digestato']['co2_tot'] += componenti_dig.get('co2_tot', 0)
                        tr_dig = componenti_dig.get('co2_tot', 0)
                        trasporti_data['digestato']['tipo_trasporto'] = componenti_dig.get('tipo_trasporto', T.tipo)
                    else:
                        tr_dig = 0
                        trasporti_data['digestato']['tipo_trasporto'] = T.tipo
                
                trasporti_data['digestato']['n_viaggi'] += n_viaggi_dig
            else:
                tr_dig = 0

        except Exception as e:
            st.warning(f"Errore calcolo digestato per {denom}: {str(e)}")
            digestato = 0
            co2_dig = 0
            tr_dig = 0

        # Pollina - Calcolo con componenti CO2
        try:
            poll = A.pollina or 0
            if poll > 0:
                # Calcola componenti CO2 della pollina
                co2_poll_series = co2eq_pollina(poll, EF.pollina)
                
                # Aggiorna dati pollina
                if co2_poll_series is not None:
                    pollina_data['co2_fossile'] += co2_poll_series.get('co2_fossile', 0)
                    pollina_data['co2_biogenica'] += co2_poll_series.get('co2_biogenica', 0)
                    pollina_data['co2_dluc'] += co2_poll_series.get('co2_dluc', 0)
                    pollina_data['co2_tot'] += co2_poll_series.get('co2_tot', 0)
                    co2_poll = co2_poll_series.get('co2_tot', 0)
                else:
                    co2_poll = 0
                
                pollina_data['quantita_tot'] += poll
            else:
                co2_poll = 0
        except Exception as e:
            st.warning(f"Errore calcolo pollina per {denom}: {str(e)}")
            co2_poll = 0

        # Aggiorna totali
        tot_let += co2_let
        tot_liq += co2_liq
        tot_poll += co2_poll
        tot_tlet += tr_let
        tot_tliq += tr_liq
        tot_tdig += tr_dig
        tot_digestato += digestato
        tot_co2_dig += co2_dig

        # Salva risultati allevatore
        risultati_allevatori.append({
            "id_allevatore": A.id_allevatore,
            "denominazione_sociale": A.denominazione_sociale,
            "pollina_ton": poll,
            "letame_tot_annuo_ton": let_annuo,
            "liquame_tot_annuo_ton": liq_annuo,
            "co2eq_letame_kg": co2_let,
            "co2eq_liquame_kg": co2_liq,
            "co2eq_pollina_kg": co2_poll,
            "co2eq_trasporto_letame_kg": tr_let,
            "co2eq_trasporto_liquame_kg": tr_liq,
            "co2eq_digestato_kg": co2_dig,
            "co2eq_trasporto_digestato_kg": tr_dig,
            "data_simulazione": datetime.datetime.now()
        })

        progress.progress((idx + 1) / len(allevatori_impianto))

    # Calcoli finali per il bilancio
    co2_biomasse = tot_let + tot_liq + tot_poll
    co2_energia_prodotta = co2eq_ee_netta + co2eq_calore_netta + co2eq_biomet_netta + co2eq_biolng_netta + co2eq_biogenica_prod
    co2_energia_acq = co2eq_ee_acq + co2eq_met_acq + co2eq_lng_acq
    co2_energia_netta = co2_energia_prodotta + co2_energia_acq
    co2_trasporti = tot_tlet + tot_tliq + tot_tdig
    co2_impianto = co2eq_olio_val + co2eq_rifiuti_val + co2eq_acqua_val + co2eq_scarichi_val
    bilancio_finale = co2_biomasse + co2_energia_netta + co2_trasporti + tot_co2_dig + co2_impianto

    # Preparazione timestamp e nome pulito per i file
    timestamp = datetime.datetime.now().strftime('%Y%m%d_%H%M')
    nome_clean = "".join(c for c in I.nome if c.isalnum() or c in " -_")

    # =========================================================
    # SEZIONE 1: CO₂ DA BIOMASSE
    # =========================================================
    st.write("---")
    st.write("### 🌱 CO₂ da Biomasse [ton/anno]")

    # Calcola i totali di letame e liquame prodotti
    totale_letame_prodotto = sum(allevatore["letame_tot_annuo_ton"] for allevatore in risultati_allevatori)
    totale_liquame_prodotto = sum(allevatore["liquame_tot_annuo_ton"] for allevatore in risultati_allevatori)
    tot_biomasse = totale_letame_prodotto + totale_liquame_prodotto

    # Metriche delle quantità prodotte
    st.write("#### Quantità Prodotte")
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Letame prodotto", f"{totale_letame_prodotto:.1f}")
    with col2:
        st.metric("Liquame prodotto", f"{totale_liquame_prodotto:.1f}")
    with col3:
        st.metric("Pollina", f"{pollina_data['quantita_tot']:.1f}" if pollina_data['quantita_tot'] > 0 else "0.0")
    with col4:
        st.metric("Totale", f"{tot_biomasse:.1f}")
    
    st.write("#### Emissioni CO₂")
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("CO₂ letame", f"{tot_let/1000:.1f}")
    with col2:
        st.metric("CO₂ liquame", f"{tot_liq/1000:.1f}")
    with col3:
        st.metric("CO₂ pollina", f"{-tot_poll/1000:.1f}" if tot_poll > 0 else "0.0")
    with col4:
        st.metric("Totale", f"{co2_biomasse/1000:.1f}")
    
    # Tabella dettaglio per allevatore
    if risultati_allevatori:
        df_allevatori = pd.DataFrame(risultati_allevatori)
        st.dataframe(df_allevatori, use_container_width=True, hide_index=True)
        
        # Pulsante download per questa sezione
        csv_allevatori = df_allevatori.to_csv(index=False, encoding="utf-8-sig")
        nome_file_allevatori = f"co2_biomasse_allevatori_{nome_clean}_{timestamp}.csv"
        
        st.download_button(
            label="📥 Scarica dettaglio CO₂ biomasse per allevatore (CSV)",
            data=csv_allevatori,
            file_name=nome_file_allevatori,
            mime="text/csv",
            key="download_biomasse",
            use_container_width=True
        )

    # =========================================================
    # SEZIONE 2: CO₂ IMPIANTO
    # =========================================================
    st.write("---")
    st.write("### ⚙️ CO₂ Impianto [ton/anno]")
    
    # Sottosezione 2.1: Bilancio energetico
    st.write("#### Bilancio Energetico")
    
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Elettrica netta prodotta", f"{co2eq_ee_netta/1000:.1f}")
    with col2:
        st.metric("Calore netto", f"{co2eq_calore_netta/1000:.1f}")
    with col3:
        st.metric("Biometano netto", f"{co2eq_biomet_netta/1000:.1f}")
    
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("BioLNG netto", f"{co2eq_biolng_netta/1000:.1f}")
    with col2:
        st.metric("CO₂ biogenica", f"{co2eq_biogenica_prod/1000:.1f}")
    with col3:
        st.metric("Energia acquistata", f"{co2_energia_acq/1000:.1f}")
    
    st.metric("Totale CO₂ energia netta", f"{co2_energia_netta/1000:.1f}")
    
    # Tabella dettaglio componenti CO₂ produzione energetica
    componenti_data = []
    voci_energia = [
        ("Elettricità prodotta netta", co2eq_ee_prod_netta_series),
        ("Calore netto", co2eq_calore_netta_series),
        ("Biometano netto", co2eq_biometano_series),
        ("BioLNG netto", co2eq_biolng_series),
        ("CO₂ biogenica prodotta", co2eq_biogenica_series),
        ("Elettricità acquistata", co2eq_ee_acq_series),
        ("Metano acquistato", co2eq_metano_acq_series),
        ("LNG acquistato", co2eq_lng_acq_series),
    ]
    
    for nome, serie in voci_energia:
        if isinstance(serie, pd.Series) and 'co2_tot' in serie:
            componenti_data.append({
                "Voce": nome,
                "CO₂ Fossile [ton]": serie.get('co2_fossile', 0)/1000,
                "CO₂ Biogenica [ton]": serie.get('co2_biogenica', 0)/1000,
                "CO₂ DLUC [ton]": serie.get('co2_dluc', 0)/1000,
                "CO₂ Totale [ton]": serie.get('co2_tot', 0)/1000
            })
        else:
            componenti_data.append({
                "Voce": nome,
                "CO₂ Fossile [ton]": 0,
                "CO₂ Biogenica [ton]": 0,
                "CO₂ DLUC [ton]": 0,
                "CO₂ Totale [ton]": 0
            })
    
    if componenti_data:
        df_componenti = pd.DataFrame(componenti_data)
        st.dataframe(df_componenti, use_container_width=True, hide_index=True)
        
        # Pulsante download per questa sottosezione
        csv_componenti = df_componenti.to_csv(index=False, encoding="utf-8-sig")
        nome_file_componenti = f"co2_bilancio_energetico_{nome_clean}_{timestamp}.csv"
        
        st.download_button(
            label="📥 Scarica dettaglio bilancio energetico (CSV)",
            data=csv_componenti,
            file_name=nome_file_componenti,
            mime="text/csv",
            key="download_energia",
            use_container_width=True
        )
    
    # Sottosezione 2.2: Consumi impianto (acqua, scarichi, rifiuti, ecc.)
    st.write("#### Consumi Impianto")
    
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Olio lubrificante", f"{co2eq_olio_val/1000:.1f}")
    with col2:
        st.metric("Rifiuti recupero", f"{co2eq_rifiuti_val/1000:.1f}")
    with col3:
        st.metric("Acqua", f"{co2eq_acqua_val/1000:.1f}")
    with col4:
        st.metric("Scarichi", f"{co2eq_scarichi_val/1000:.1f}")
    
    # Tabella dettaglio impianto
    impianto_table_data = []
    voci_impianto = [
        ("Olio lubrificante", co2eq_olio_series),
        ("Rifiuti recupero", co2eq_rifiuti_series),
        ("Acqua", co2eq_acqua_series),
        ("Scarichi", co2eq_scarichi_series),
    ]
    
    for nome, serie in voci_impianto:
        if isinstance(serie, pd.Series) and 'co2_tot' in serie:
            impianto_table_data.append({
                "Voce": nome,
                "CO₂ Fossile [ton]": serie.get('co2_fossile', 0)/1000,
                "CO₂ Biogenica [ton]": serie.get('co2_biogenica', 0)/1000,
                "CO₂ DLUC [ton]": serie.get('co2_dluc', 0)/1000,
                "CO₂ Totale [ton]": serie.get('co2_tot', 0)/1000
            })
        else:
            impianto_table_data.append({
                "Voce": nome,
                "CO₂ Fossile [ton]": 0,
                "CO₂ Biogenica [ton]": 0,
                "CO₂ DLUC [ton]": 0,
                "CO₂ Totale [ton]": 0
            })
    
    if impianto_table_data:
        df_impianto = pd.DataFrame(impianto_table_data)
        st.dataframe(df_impianto, use_container_width=True, hide_index=True)
        
        # Pulsante download per questa sottosezione
        csv_impianto = df_impianto.to_csv(index=False, encoding="utf-8-sig")
        nome_file_impianto = f"co2_consumi_impianto_{nome_clean}_{timestamp}.csv"
        
        st.download_button(
            label="📥 Scarica dettaglio consumi impianto (CSV)",
            data=csv_impianto,
            file_name=nome_file_impianto,
            mime="text/csv",
            key="download_impianto",
            use_container_width=True
        )
    
    # Sottosezione 2.3: Digestato (se presente)
    if digestato_data['quantita_tot'] > 0:
        st.write("#### Digestato")
        
        col1, col2 = st.columns(2)
        with col1:
            st.metric("CO₂ totale [ton]", f"{digestato_data['co2_tot']/1000:.1f}")
        with col2:
            st.metric("Quantità totale [ton]", f"{digestato_data['quantita_tot']:.1f}")
        
        # Tabella dettaglio digestato
        digestato_table_data = [{
            "Voce": "Digestato",
            "CO₂ Fossile [ton]": digestato_data['co2_fossile']/1000,
            "CO₂ Biogenica [ton]": digestato_data['co2_biogenica']/1000,
            "CO₂ DLUC [ton]": digestato_data['co2_dluc']/1000,
            "CO₂ Totale [ton]": digestato_data['co2_tot']/1000,
            "Quantità [ton]": digestato_data['quantita_tot']
        }]
        
        df_digestato = pd.DataFrame(digestato_table_data)
        st.dataframe(df_digestato, use_container_width=True, hide_index=True)
        
        # Pulsante download per questa sottosezione
        csv_digestato = df_digestato.to_csv(index=False, encoding="utf-8-sig")
        nome_file_digestato = f"co2_digestato_{nome_clean}_{timestamp}.csv"
        
        st.download_button(
            label="📥 Scarica dettaglio digestato (CSV)",
            data=csv_digestato,
            file_name=nome_file_digestato,
            mime="text/csv",
            key="download_digestato",
            use_container_width=True
        )

    # =========================================================
    # SEZIONE 3: CO₂ TRASPORTI
    # =========================================================
    st.write("---")
    st.write("### 🚚 CO₂ Trasporti [ton/anno]")
    
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Trasporto letame", f"{tot_tlet/1000:.1f}")
    with col2:
        st.metric("Trasporto liquame", f"{tot_tliq/1000:.1f}")
    with col3:
        st.metric("Trasporto digestato", f"{tot_tdig/1000:.1f}")
    with col4:
        st.metric("Totale", f"{co2_trasporti/1000:.1f}")
    
    # Tabella dettaglio trasporti
    trasporti_table_data = []
    for materiale, dati in trasporti_data.items():
        if dati['n_viaggi'] > 0:
            trasporti_table_data.append({
                "Materiale": materiale.capitalize(),
                "Tipo Trasporto": dati['tipo_trasporto'],
                "CO₂ Fossile [ton]": dati['co2_fossile']/1000,
                "CO₂ Biogenica [ton]": dati['co2_biogenica']/1000,
                "CO₂ DLUC [ton]": dati['co2_dluc']/1000,
                "CO₂ Totale [ton]": dati['co2_tot']/1000,
                "N. Viaggi": dati['n_viaggi']
            })
    
    if trasporti_table_data:
        df_trasporti = pd.DataFrame(trasporti_table_data)
        st.dataframe(df_trasporti, use_container_width=True, hide_index=True)
        
        # Pulsante download per questa sezione
        csv_trasporti = df_trasporti.to_csv(index=False, encoding="utf-8-sig")
        nome_file_trasporti = f"co2_trasporti_{nome_clean}_{timestamp}.csv"
        
        st.download_button(
            label="📥 Scarica dettaglio trasporti (CSV)",
            data=csv_trasporti,
            file_name=nome_file_trasporti,
            mime="text/csv",
            key="download_trasporti",
            use_container_width=True
        )
    else:
        st.info("Nessun trasporto registrato.")

    # =========================================================
    # SEZIONE 4: BILANCIO NETTO TOTALE
    # =========================================================
    st.write("---")
    st.write("### 🎯 Bilancio Netto Totale CO₂ [ton/anno]")
    st.metric("**Bilancio Netto CO₂**", f"{bilancio_finale/1000:.1f}")