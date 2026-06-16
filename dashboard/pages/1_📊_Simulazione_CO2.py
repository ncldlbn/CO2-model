import streamlit as st
from db import get_connection
import pandas as pd
import sys
import os
import io
import datetime

sys.path.append(os.path.join(os.path.dirname(__file__), '../../src'))

from objects import Allevatore, Impianto, Trasporto, FattoriEmissione
from model import (
    co2_liquame_semplificata,
    co2_letame_semplificata,
    co2eq_trasporto,
    co2eq_digestato,
    co2eq_pollina,
    co2eq_colture,
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

# ---------------------------------------------------------------------------
# PERCORSI
# ---------------------------------------------------------------------------

current_dir  = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.abspath(os.path.join(current_dir, "../.."))
db           = os.path.join(project_root, "data.db")

# ===========================================================================
# FUNZIONI DI SUPPORTO
# ===========================================================================

def carica_impianti():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT id_impianto, nome FROM impianto ORDER BY nome")
    risultato = cursor.fetchall()
    conn.close()
    return risultato


def carica_allevatori(id_impianto):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT id_allevatore, denominazione_sociale
        FROM allevatore
        WHERE id_impianto_associato = ?
        ORDER BY denominazione_sociale
        """,
        (id_impianto,),
    )
    risultato = cursor.fetchall()
    conn.close()
    return risultato

def carica_altri_conferitori(id_impianto, db, id_mezzo_liquido, id_mezzo_solido):
    """
    Estrae dalla tabella 'conferitori' i record per un determinato impianto,
    calcola le emissioni di CO₂ da trasporto per ogni tipologia di biomassa
    (letame, liquame, pollina, colture, sottoprodotti) e restituisce un DataFrame
    con i risultati.

    Parameters
    ----------
    id_impianto : int
        ID dell'impianto da filtrare.

    Returns
    -------
    pd.DataFrame
        DataFrame con colonne: 'tipo', 'distanza', 'carico', 'co2_trasporto_tot'.
        Se non ci sono record, DataFrame vuoto.
    """
    # Apri la connessione (sarà riutilizzata per tutto)
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT tipo, distanza, carico FROM conferitori WHERE id_impianto = ?",
        (id_impianto,)
    )
    risultati = cursor.fetchall()
    df = pd.DataFrame(risultati, columns=['tipo', 'distanza', 'carico'])

    # Se non ci sono dati, chiudi e restituisci dataframe vuoto con le colonne aggiuntive
    if df.empty:
        conn.close()
        return pd.DataFrame(columns=['tipo', 'distanza', 'carico', 'co2_trasporto_tot'])

    # Mapping tipo → id mezzo (liquame usa mezzo liquido, solidi usano mezzo solido)
    mapping = {
        'Liquame':       id_mezzo_liquido,
        'Letame':        id_mezzo_solido,
        'Pollina':       id_mezzo_solido,
        'Colture':       id_mezzo_solido,
        'Sottoprodotti': id_mezzo_solido,
    }

    co2_list = []

    for idx, row in df.iterrows():
        tipo     = row['tipo']
        distanza = row['distanza']
        carico   = row['carico']

        if carico <= 0 or distanza <= 0 or tipo not in mapping:
            co2_list.append(0)
            continue

        try:
            T = Trasporto.from_db(db, mapping[tipo])
            co2_trasporto = co2eq_trasporto(T, carico, distanza)
        except Exception as e:
            print(f"Errore nel calcolo del trasporto per tipo {tipo}: {e}")
            co2_trasporto = 0

        co2_list.append(co2_trasporto)

    df['co2_trasporto_tot'] = co2_list

    conn.close()
    return df

def calcola_risultati_allevatori(db, allevatori_impianto, EF, id_mezzo_liquido, id_mezzo_solido):
    """
    Calcola per ogni allevatore dell'impianto le emissioni di CO₂ (totali)
    e i dati di trasporto per tutte le tipologie di biomassa conferita.
    Gestisce attributi None convertendoli a 0.
    """
    risultati = []

    # I mezzi sono comuni a tutti gli allevatori: carichiamoli una sola volta
    T_liquido = Trasporto.from_db(db, id_mezzo_liquido)
    T_solido = Trasporto.from_db(db, id_mezzo_solido)

    for id_allevatore, nome_allevatore in allevatori_impianto:
        try:
            A = Allevatore.from_db(db, id_allevatore)
        except Exception as e:
            print(f"Errore caricamento allevatore {nome_allevatore}: {e}")
            continue

        def val_or_zero(attr):
            return attr if attr is not None else 0

        prod_liquame = val_or_zero(A.prod_liquame)
        prod_letame = val_or_zero(A.prod_letame)
        pollina = val_or_zero(A.pollina)
        colture = val_or_zero(A.colture)
        sottoprodotti = val_or_zero(A.sottoprodotti)
        distanza = val_or_zero(A.distanza_impianto)
        tipo_conferimento = A.tipo_conferimento

        res = {
            'id_allevatore': id_allevatore,
            'nome_allevatore': nome_allevatore,
            'distanza_impianto': distanza,
        }

        # ------------------ LIQUAME ------------------
        if prod_liquame > 0:
            (co2_evitata_anno_liq, n_svuotamenti_liq,
             deposito_liq, liquame_tot_annuo) = co2_liquame_semplificata(A)

            if tipo_conferimento == "mezzi":
                co2_trasporto_liq = co2eq_trasporto(T_liquido, deposito_liq, distanza)
                co2_trasporto_liq_tot_anno = co2_trasporto_liq * n_svuotamenti_liq
            else:
                co2_trasporto_liq_tot_anno = A.potenza * A.ore * EF.EE_BT # kg CO2 da pompaggio

            res.update({
                'liquame_produzione': liquame_tot_annuo,
                'liquame_evitata_anno': co2_evitata_anno_liq,
                'liquame_trasporto_co2_tot': co2_trasporto_liq_tot_anno,
            })
        else:
            res.update({
                'liquame_produzione': 0,
                'liquame_evitata_anno': 0,
                'liquame_trasporto_co2_tot': 0,
            })

        # ------------------ LETAME ------------------
        if prod_letame > 0:
            (co2_evitata_anno_let, n_svuotamenti_let,
             deposito_let, letame_tot_annuo) = co2_letame_semplificata(A)

            co2_trasporto_let_tot_anno = co2eq_trasporto(T_solido, deposito_let, distanza) * n_svuotamenti_let

            res.update({
                'letame_produzione': letame_tot_annuo,
                'letame_evitata_anno': co2_evitata_anno_let,
                'letame_trasporto_co2_tot': co2_trasporto_let_tot_anno,
            })
        else:
            res.update({
                'letame_produzione': 0,
                'letame_evitata_anno': 0,
                'letame_trasporto_co2_tot': 0,
            })

        # ------------------ POLLINA ------------------
        if pollina > 0:
            co2_pollina = co2eq_pollina(pollina, EF.pollina)
            res.update({
                'pollina_produzione': pollina,
                'pollina_co2_tot': co2_pollina,
                'pollina_trasporto_co2_tot': co2eq_trasporto(T_solido, pollina, distanza),
            })
        else:
            res.update({
                'pollina_produzione': 0,
                'pollina_co2_tot': 0,
                'pollina_trasporto_co2_tot': 0,
            })

        # ------------------ COLTURE ------------------
        if colture > 0:
            co2_colture = co2eq_colture(colture, EF.colture)
            res.update({
                'colture_produzione': colture,
                'colture_co2_tot': co2_colture,
                'colture_trasporto_co2_tot': co2eq_trasporto(T_solido, colture, distanza),
            })
        else:
            res.update({
                'colture_produzione': 0,
                'colture_co2_tot': 0,
                'colture_trasporto_co2_tot': 0,
            })

        # ------------------ SOTTOPRODOTTI ------------------
        if sottoprodotti > 0:
            res.update({
                'sottoprodotti_produzione': sottoprodotti,
                'sottoprodotti_co2_tot': 0,
                'sottoprodotti_trasporto_co2_tot': co2eq_trasporto(T_solido, sottoprodotti, distanza),
            })
        else:
            res.update({
                'sottoprodotti_produzione': 0,
                'sottoprodotti_co2_tot': 0,
                'sottoprodotti_trasporto_co2_tot': 0,
            })

        risultati.append(res)

    return pd.DataFrame(risultati)

def aggrega_risultati_conferitori(df_allevatori, df_altri, db_path, EF):
    """
    Aggrega i dati di biomassa e CO₂ da allevatori e altri conferitori,
    restituendo due dataframe:
      - biomasse totali per tipologia (ton/anno)
      - CO₂ evitate da tutte le tipologie (kg CO₂eq) con totale

    Parameters
    ----------
    df_allevatori : pd.DataFrame
        DataFrame prodotto da calcola_risultati_allevatori.
    df_altri : pd.DataFrame
        DataFrame prodotto da carica_altri_conferitori.
    db_path : str
        Percorso del database SQLite.
    EF : FattoriEmissione
        Fattori di emissione per pollina e colture.

    Returns
    -------
    tuple
        (df_biomasse, df_co2_evitate)
    """
    biomassa = {
        'Liquame':       0.0,
        'Letame':        0.0,
        'Pollina':       0.0,
        'Colture':       0.0,
        'Sottoprodotti': 0.0
    }

    co2_evitate = {
        'Liquame': 0.0,
        'Letame':  0.0,
        'Pollina': 0.0,
        'Colture': 0.0,
    }

    # ------------------ Allevatori ------------------
    if not df_allevatori.empty:
        biomassa['Liquame']       += df_allevatori['liquame_produzione'].sum()
        biomassa['Letame']        += df_allevatori['letame_produzione'].sum()
        biomassa['Pollina']       += df_allevatori['pollina_produzione'].sum()
        biomassa['Colture']       += df_allevatori['colture_produzione'].sum()
        biomassa['Sottoprodotti'] += df_allevatori['sottoprodotti_produzione'].sum()

        co2_evitate['Liquame'] += df_allevatori['liquame_evitata_anno'].sum()
        co2_evitate['Letame']  += df_allevatori['letame_evitata_anno'].sum()
        co2_evitate['Pollina'] += df_allevatori['pollina_co2_tot'].sum()
        co2_evitate['Colture'] += df_allevatori['colture_co2_tot'].sum()

    # ------------------ Altri conferitori ------------------
    if not df_altri.empty:
        grouped = df_altri.groupby('tipo').agg({'carico': 'sum'}).reset_index()

        for _, row in grouped.iterrows():
            tipo       = row['tipo']
            carico_ton = row['carico']

            if tipo in biomassa:
                biomassa[tipo] += carico_ton

            if tipo == 'Pollina' and carico_ton > 0:
                co2_evitate['Pollina'] += co2eq_pollina(carico_ton, EF.pollina)
            elif tipo == 'Colture' and carico_ton > 0:
                co2_evitate['Colture'] += co2eq_colture(carico_ton, EF.colture)

    # ------------------ Costruzione dataframe ------------------
    df_biomasse = pd.DataFrame([
        {'tipologia': k, 'quantita_ton': v} for k, v in biomassa.items()
    ])

    totale_evitate = sum(co2_evitate.values())
    df_co2_evitate = pd.DataFrame([
        {'tipologia': 'Liquame', 'co2_kg': co2_evitate['Liquame']},
        {'tipologia': 'Letame',  'co2_kg': co2_evitate['Letame']},
        {'tipologia': 'Pollina', 'co2_kg': co2_evitate['Pollina']},
        {'tipologia': 'Colture', 'co2_kg': co2_evitate['Colture']},
        {'tipologia': 'Totale',  'co2_kg': totale_evitate}
    ])

    return df_biomasse, df_co2_evitate

def calcola_digestato_allevatori(
    db: str,
    df_allevatori: pd.DataFrame,
    I: Impianto,
    EF: FattoriEmissione,
    id_mezzo_liquido: int,
    id_mezzo_solido: int
) -> pd.DataFrame:
    if df_allevatori.empty:
        return pd.DataFrame()

    T_liq = Trasporto.from_db(db, id_mezzo_liquido)
    T_sol = Trasporto.from_db(db, id_mezzo_solido)

    risultati = []

    for _, row in df_allevatori.iterrows():
        id_allevatore   = row['id_allevatore']
        nome_allevatore = row['nome_allevatore']

        biomassa = (
            row['letame_produzione'] +
            row['liquame_produzione'] +
            row['pollina_produzione'] +
            row['colture_produzione'] +
            row['sottoprodotti_produzione']
        )

        if biomassa == 0:
            risultati.append({
                'id_allevatore':          id_allevatore,
                'nome_allevatore':        nome_allevatore,
                'biomassa_totale':        0.0,
                'digestato_liq':          0.0,
                'digestato_sep':          0.0,
                'co2_trasporto_liq':      0.0,
                'co2_trasporto_sep':      0.0,
                'co2_digestato_fossile':  0.0,
                'co2_digestato_biogenica':0.0,
                'co2_digestato_dluc':     0.0,
                'co2_digestato_tot':      0.0,
            })
            continue

        digestato_sep, digestato_liq, comp_dig = co2eq_digestato(I, biomassa, EF, db)

        distanza = row['distanza_impianto']

        co2_liq = co2eq_trasporto(T_liq, digestato_liq, distanza) if digestato_liq > 0 else 0.0
        co2_sep = co2eq_trasporto(T_sol, digestato_sep, distanza) if digestato_sep > 0 else 0.0

        risultati.append({
            'id_allevatore':           id_allevatore,
            'nome_allevatore':         nome_allevatore,
            'biomassa_totale':         biomassa,
            'digestato_liq':           digestato_liq,
            'digestato_sep':           digestato_sep,
            'co2_trasporto_liq':       co2_liq,
            'co2_trasporto_sep':       co2_sep,
            'co2_digestato_fossile':   comp_dig['co2_fossile']   if comp_dig is not None else 0.0,
            'co2_digestato_biogenica': comp_dig['co2_biogenica'] if comp_dig is not None else 0.0,
            'co2_digestato_dluc':      comp_dig['co2_dluc']      if comp_dig is not None else 0.0,
            'co2_digestato_tot':       comp_dig['co2_tot']       if comp_dig is not None else 0.0,
        })

    return pd.DataFrame(risultati)

def calcola_digestato_da_conferitori(
    df_conferitori: pd.DataFrame,
    impianto: Impianto,
    EF: FattoriEmissione,
    db_path: str
) -> tuple:
    if df_conferitori.empty:
        return 0.0, 0.0, None

    biomassa_tot = df_conferitori['carico'].sum()
    if biomassa_tot == 0:
        return 0.0, 0.0, None

    digestato_sol, digestato_liq, comp_dig = co2eq_digestato(impianto, biomassa_tot, EF, db_path)
    return digestato_liq, digestato_sol, comp_dig


def calcola_componenti_impianto(impianto, EF, db):
    """
    Calcola le componenti di CO2 per ogni voce energetica dell'impianto.
    Restituisce un DataFrame con le singole voci (senza totale).
    """
    voci = [
        (co2eq_ee_prod_netta, 'Energia elettrica netta prodotta'),
        (co2eq_calore_netta,  'Calore netto prodotto'),
        (co2eq_biometano,     'Biometano netto prodotto'),
        (co2eq_biolng,        'BioLNG netto prodotto'),
        (co2eq_biogenica,     'CO₂ biogenica prodotta'),
        (co2eq_ee_acquistata, 'Energia elettrica acquistata'),
        (co2eq_metano_acq,    'Metano acquistato'),
        (co2eq_lng_acq,       'LNG acquistato'),
    ]

    records = []
    for func, nome in voci:
        serie = func(impianto, EF, db)
        records.append({
            'nome': nome,
            'co2_fossile': serie['co2_fossile'],
            'co2_biogenica': serie['co2_biogenica'],
            'co2_dluc': serie['co2_dluc'],
            'co2_tot': serie['co2_tot'],
        })

    return pd.DataFrame(records)

def digestato_altri_ricettori(
    digestato_liq_altri_conf: float,
    digestato_sep_altri_conf: float,
    id_impianto: int,
    db: str,
    id_mezzo_liquido: int,
    id_mezzo_solido: int,
) -> tuple[pd.DataFrame, float, float]:
    """
    Distribuisce il digestato liquido e separato ai ricettori dell'impianto
    in base al loro carico definito nel DB. Segnala l'eventuale residuo
    non trasportato.
    
    Tipi gestiti:
      - "Digestato Liquido": consuma dal residuo liquido, trasporto con trattore
      - "Digestato Separato": consuma dal residuo separato, trasporto con camion
      - "BioCO2" / "BioLNG": solo CO₂ da trasporto (camion, densità 1), non influisce sul residuo

    Parameters
    ----------
    digestato_liq_altri_conf : float
        Quantità totale di digestato liquido (kg) disponibile.
    digestato_sep_altri_conf : float
        Quantità totale di digestato separato (kg) disponibile.
    id_impianto : int
        ID dell'impianto per filtrare i ricettori nel database.
    db : str
        Percorso del database SQLite.

    Returns
    -------
    tuple
        (df_ricettori, residuo_liq, residuo_sep)
        df_ricettori: DataFrame con i dettagli per ogni ricettore.
        residuo_liq: digestato liquido non assegnato (kg).
        residuo_sep: digestato separato non assegnato (kg).
    """
    empty = pd.DataFrame(columns=[
        'id_ricettore', 'nome_ricettore', 'distanza', 'tipo',
        'carico_assegnato', 'digestato_liq', 'digestato_sep',
        'co2_trasporto_liq', 'co2_trasporto_sep', 'co2_trasporto_tot',
    ])

    if digestato_liq_altri_conf <= 0 and digestato_sep_altri_conf <= 0:
        return empty, 0.0, 0.0

    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT id_ricettore, nome_ricettore, distanza, tipo, carico
        FROM ricettori
        WHERE id_impianto = ?
        ORDER BY nome_ricettore
        """,
        (id_impianto,)
    )
    rows = cursor.fetchall()
    conn.close()

    if not rows:
        return empty, digestato_liq_altri_conf, digestato_sep_altri_conf

    T_liq = Trasporto.from_db(db, id_mezzo_liquido)
    T_sol = Trasporto.from_db(db, id_mezzo_solido)

    residuo_liq = digestato_liq_altri_conf
    residuo_sep = digestato_sep_altri_conf
    risultati = []

    for id_ricettore, nome_ricettore, distanza, tipo, carico in rows:
        distanza = distanza or 0
        carico   = carico   or 0

        if tipo == "Digestato Liquido":
            assegnato_liq = min(carico, residuo_liq)
            assegnato_sep = 0.0
            residuo_liq  -= assegnato_liq
            co2_liq = co2eq_trasporto(T_liq, assegnato_liq, distanza) if assegnato_liq > 0 and distanza > 0 else 0.0
            co2_sep = 0.0

        elif tipo == "Digestato Separato":
            assegnato_liq = 0.0
            assegnato_sep = min(carico, residuo_sep)
            residuo_sep  -= assegnato_sep
            co2_liq = 0.0
            co2_sep = co2eq_trasporto(T_sol, assegnato_sep, distanza) if assegnato_sep > 0 and distanza > 0 else 0.0

        elif tipo in ("BioCO2", "BioLNG"):
            assegnato_liq = 0.0
            assegnato_sep = 0.0
            co2_liq = co2eq_trasporto(T_sol, carico, distanza) if carico > 0 and distanza > 0 else 0.0
            co2_sep = 0.0

        else:
            continue

        risultati.append({
            'id_ricettore':      id_ricettore,
            'nome_ricettore':    nome_ricettore,
            'distanza':          distanza,
            'tipo':              tipo,
            'carico_assegnato':  assegnato_liq + assegnato_sep + (carico if tipo in ("BioCO2", "BioLNG") else 0),
            'digestato_liq':     assegnato_liq,
            'digestato_sep':     assegnato_sep,
            'co2_trasporto_liq': co2_liq,
            'co2_trasporto_sep': co2_sep,
            'co2_trasporto_tot': co2_liq + co2_sep,
        })

    return pd.DataFrame(risultati), residuo_liq, residuo_sep

def calcola_co2_trasporti_totale(
    df_allevatori: pd.DataFrame,
    df_conferitori: pd.DataFrame,
    df_digestato_allevatori: pd.DataFrame,
    df_ricettori: pd.DataFrame,
    db: str,
    tipo_mezzo_liquido: str,
    tipo_mezzo_solido: str,
) -> pd.DataFrame:
    """
    Calcola la CO₂ totale dei trasporti suddivisa in:
      - trasporti conferitori → impianto (biomassa)
      - trasporti impianto → ricettori (digestato)
      - totale

    Per ogni macro-voce ripartisce le componenti (fossile, biogenica, dLUC)
    distinguendo tra mezzo liquido (Trattore) e mezzo solido (Camion generico).

    Returns
    -------
    pd.DataFrame
        Colonne: voce, co2_fossile, co2_biogenica, co2_dluc, co2_tot (in kg)
    """

    def componenti(nome_mezzo, co2_tot):
        if co2_tot <= 0:
            return pd.Series({'co2_fossile': 0.0, 'co2_biogenica': 0.0, 'co2_dluc': 0.0, 'co2_tot': 0.0})
        comp = componenti_co2(nome_mezzo, co2_tot, db)
        if comp is None:
            return pd.Series({'co2_fossile': co2_tot, 'co2_biogenica': 0.0, 'co2_dluc': 0.0, 'co2_tot': co2_tot})
        return comp

    # ── CO₂ trasporti CONFERITORI → IMPIANTO ──────────────────────────────────

    # Liquidi (trattore): liquame
    co2_liq_all = df_allevatori["liquame_trasporto_co2_tot"].sum()
    co2_liq_conf = df_conferitori[df_conferitori["tipo"] == "Liquame"]["co2_trasporto_tot"].sum()
    co2_conf_liq = co2_liq_all + co2_liq_conf

    # Solidi (camion): letame, pollina, colture, sottoprodotti
    co2_sol_all = (
        df_allevatori["letame_trasporto_co2_tot"].sum()
        + df_allevatori["pollina_trasporto_co2_tot"].sum()
        + df_allevatori["colture_trasporto_co2_tot"].sum()
        + df_allevatori["sottoprodotti_trasporto_co2_tot"].sum()
    )
    co2_sol_conf = df_conferitori[df_conferitori["tipo"] != "Liquame"]["co2_trasporto_tot"].sum()
    co2_conf_sol = co2_sol_all + co2_sol_conf

    comp_conf_liq = componenti(tipo_mezzo_liquido, co2_conf_liq)
    comp_conf_sol = componenti(tipo_mezzo_solido,  co2_conf_sol)

    co2_conf_tot = pd.Series({
        'co2_fossile':   comp_conf_liq['co2_fossile']   + comp_conf_sol['co2_fossile'],
        'co2_biogenica': comp_conf_liq['co2_biogenica'] + comp_conf_sol['co2_biogenica'],
        'co2_dluc':      comp_conf_liq['co2_dluc']      + comp_conf_sol['co2_dluc'],
        'co2_tot':       comp_conf_liq['co2_tot']       + comp_conf_sol['co2_tot'],
    })

    # ── CO₂ trasporti IMPIANTO → RICETTORI (digestato) ────────────────────────

    # Liquido (trattore): digestato liquido allevatori + ricettori liquido
    co2_dig_liq_all  = df_digestato_allevatori["co2_trasporto_liq"].sum()
    co2_dig_liq_ric  = df_ricettori["co2_trasporto_liq"].sum() if not df_ricettori.empty else 0.0
    co2_ric_liq      = co2_dig_liq_all + co2_dig_liq_ric

    # Solido (camion): digestato separato allevatori + ricettori separato + BioCO2/BioLNG
    co2_dig_sep_all  = df_digestato_allevatori["co2_trasporto_sep"].sum()
    co2_dig_sep_ric  = df_ricettori["co2_trasporto_sep"].sum() if not df_ricettori.empty else 0.0
    co2_ric_sol      = co2_dig_sep_all + co2_dig_sep_ric

    comp_ric_liq = componenti(tipo_mezzo_liquido, co2_ric_liq)
    comp_ric_sol = componenti(tipo_mezzo_solido,  co2_ric_sol)

    co2_ric_tot = pd.Series({
        'co2_fossile':   comp_ric_liq['co2_fossile']   + comp_ric_sol['co2_fossile'],
        'co2_biogenica': comp_ric_liq['co2_biogenica'] + comp_ric_sol['co2_biogenica'],
        'co2_dluc':      comp_ric_liq['co2_dluc']      + comp_ric_sol['co2_dluc'],
        'co2_tot':       comp_ric_liq['co2_tot']       + comp_ric_sol['co2_tot'],
    })

    # ── TOTALE ─────────────────────────────────────────────────────────────────

    co2_totale = pd.Series({
        'co2_fossile':   co2_conf_tot['co2_fossile']   + co2_ric_tot['co2_fossile'],
        'co2_biogenica': co2_conf_tot['co2_biogenica'] + co2_ric_tot['co2_biogenica'],
        'co2_dluc':      co2_conf_tot['co2_dluc']      + co2_ric_tot['co2_dluc'],
        'co2_tot':       co2_conf_tot['co2_tot']       + co2_ric_tot['co2_tot'],
    })

    # ── Costruzione DataFrame risultato ───────────────────────────────────────

    righe = []
    for voce, serie in [
        ("Conferitori → impianto", co2_conf_tot),
        ("Impianto → ricettori",   co2_ric_tot),
        ("Totale trasporti",       co2_totale),
    ]:
        righe.append({
            'voce':          voce,
            'co2_fossile':   serie['co2_fossile'],
            'co2_biogenica': serie['co2_biogenica'],
            'co2_dluc':      serie['co2_dluc'],
            'co2_tot':       serie['co2_tot'],
        })

    return pd.DataFrame(righe)

def genera_pdf(
    nome_impianto, data_simulazione,
    n_allevatori,
    CO2_evitata_letame, CO2_evitata_liquame, pollina_co2_tot, colture_co2_tot,
    CO2_en_el_prodotta, CO2_calore_prodotto, CO2_biometano_prodotto,
    CO2_biolng_prodotto, CO2_biogenica_prodotta, tot_co2_energia_prodotta,
    CO2_en_el_acquistata, CO2_metano_acquistato, CO2_lng_acquistato, tot_co2_energia_acquistata,
    CO2_rifiuti, CO2_olio_lubrificante, CO2_acqua, CO2_scarichi, CO2_attivita_impianto,
    co2_dig_tot,
    co2_tra_conf, co2_tra_ric, co2_tra_tot,
    co2_evitata_biomasse_tot, co2_impianto_tot, co2_bilancio_tot,
    tot_letame, tot_liquame, tot_pollina, tot_sottoprodotti, tot_colture, tot_biomasse,
    tot_dig_liq_totale, tot_dig_sep_totale, tot_digestato, dig_conferito, dig_residuo,
):
    """Genera il PDF dei risultati in memoria e restituisce i bytes."""
    from reportlab.lib.pagesizes import A4
    from reportlab.lib import colors
    from reportlab.lib.units import mm
    from reportlab.lib.styles import ParagraphStyle
    from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_RIGHT
    from reportlab.platypus import (
        SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, KeepTogether
    )

    # ── Palette ──────────────────────────────────────────────────────────────
    NAVY    = colors.HexColor('#1B2A3B')
    GREEN   = colors.HexColor('#2E7D32')
    GREEN_L = colors.HexColor('#E8F5E9')
    GREY    = colors.HexColor('#F4F6F8')
    GREY_M  = colors.HexColor('#CFD8DC')
    TOT_BG  = colors.HexColor('#ECEFF1')
    WHITE   = colors.white
    BLACK   = colors.HexColor('#212121')
    MUTED   = colors.HexColor('#607D8B')
    RED     = colors.HexColor('#C62828')

    W, H = A4
    MAR = 20 * mm

    def _s(name, **kw):
        defaults = dict(fontName='Helvetica', fontSize=9, textColor=BLACK,
                        leading=13, alignment=TA_LEFT)
        defaults.update(kw)
        return ParagraphStyle(name, **defaults)

    st_sec  = _s('sec',  fontName='Helvetica-Bold', fontSize=9,  textColor=WHITE)
    st_lbl  = _s('lbl',  fontSize=8,  textColor=MUTED)
    st_val  = _s('val',  fontName='Helvetica-Bold', fontSize=9,  textColor=BLACK)
    st_val_r= _s('valr', fontName='Helvetica-Bold', fontSize=9,  textColor=BLACK,  alignment=TA_RIGHT)
    st_tot  = _s('tot',  fontName='Helvetica-Bold', fontSize=9,  textColor=GREEN,  alignment=TA_RIGHT)
    st_neg  = _s('neg',  fontName='Helvetica-Bold', fontSize=9,  textColor=GREEN,  alignment=TA_RIGHT)
    st_pos  = _s('pos',  fontName='Helvetica-Bold', fontSize=9,  textColor=RED,    alignment=TA_RIGHT)
    st_kv   = _s('kv',   fontName='Helvetica-Bold', fontSize=14, textColor=GREEN,  alignment=TA_CENTER)
    st_ku   = _s('ku',   fontSize=7, textColor=MUTED, alignment=TA_CENTER)
    st_kl   = _s('kl',   fontSize=7, textColor=MUTED, alignment=TA_CENTER)
    st_hd   = _s('hd',   fontName='Helvetica-Bold', fontSize=7.5, textColor=MUTED)
    st_hdr  = _s('hdr',  fontName='Helvetica-Bold', fontSize=7.5, textColor=MUTED, alignment=TA_RIGHT)

    avail = W - 2 * MAR

    def _fmt(v, d=1):
        try:
            return f'{float(v):.{d}f}'
        except Exception:
            return '—'

    def _p(s):
        """Converte ₂ in pedice piccolo (Helvetica non ha U+2082)."""
        return str(s).replace('₂', '<font size="5">2</font>')

    def sec_hdr(title):
        # upper() non altera ₂ → sostituiamo dopo
        processed = title.upper().replace('₂', '<font size="5">2</font>')
        t = Table([[Paragraph(processed, st_sec)]], colWidths=[avail])
        t.setStyle(TableStyle([
            ('BACKGROUND',    (0,0),(-1,-1), NAVY),
            ('TOPPADDING',    (0,0),(-1,-1), 5),
            ('BOTTOMPADDING', (0,0),(-1,-1), 5),
            ('LEFTPADDING',   (0,0),(-1,-1), 8),
        ]))
        return t

    def data_tbl(rows):
        # rows: [(label, valore_numerico, unità_stringa[, is_total])]
        cells = []
        total_indices = []
        for i, row in enumerate(rows):
            lbl, val, unit = row[0], row[1], row[2]
            is_total = row[3] if len(row) > 3 else False
            num_text = f'{_fmt(val)} <font size="6.5" color="#607D8B">{unit}</font>'
            cells.append([Paragraph(_p(lbl), st_val if is_total else st_lbl),
                          Paragraph(num_text, st_val_r)])
            if is_total:
                total_indices.append(i)
        t = Table(cells, colWidths=[avail * 0.58, avail * 0.42])
        cmd = [
            ('ROWBACKGROUNDS', (0,0),(-1,-1), [WHITE, GREY]),
            ('TOPPADDING',    (0,0),(-1,-1), 5),
            ('BOTTOMPADDING', (0,0),(-1,-1), 5),
            ('LEFTPADDING',   (0,0),(-1,-1), 8),
            ('RIGHTPADDING',  (0,0),(-1,-1), 8),
        ]
        for idx in total_indices:
            cmd.append(('BACKGROUND', (0,idx),(-1,idx), TOT_BG))
        t.setStyle(TableStyle(cmd))
        return t

    def kpi_row(items):
        n = len(items)
        cw = avail / n
        cells = []
        st_kv2 = _s('kv2', fontName='Helvetica-Bold', fontSize=13,
                    textColor=BLACK, alignment=TA_CENTER)
        for label, value, unit in items:
            inner = Table([
                [Paragraph(_p(label), st_kl)],
                [Paragraph(_fmt(value), st_kv2)],
                [Paragraph(_p(unit), st_ku)],
            ], colWidths=[cw - 6*mm])
            inner.setStyle(TableStyle([
                ('TOPPADDING',    (0,0),(-1,-1), 2),
                ('BOTTOMPADDING', (0,0),(-1,-1), 2),
                ('LEFTPADDING',   (0,0),(-1,-1), 0),
                ('RIGHTPADDING',  (0,0),(-1,-1), 0),
            ]))
            cells.append(inner)
        row = Table([cells], colWidths=[cw]*n)
        row.setStyle(TableStyle([
            ('BACKGROUND',    (0,0),(-1,-1), GREY),
            ('TOPPADDING',    (0,0),(-1,-1), 8),
            ('BOTTOMPADDING', (0,0),(-1,-1), 8),
            ('LEFTPADDING',   (0,0),(-1,-1), 4*mm),
            ('RIGHTPADDING',  (0,0),(-1,-1), 4*mm),
            ('LINEBEFORE',    (1,0),(-1,-1), 0.5, GREY_M),
            ('BOX',           (0,0),(-1,-1), 0.5, GREY_M),
        ]))
        return row

    _unit = 'ton CO<font size="5">2</font>eq/anno'

    def detail_tbl(rows, show_total_last=True):
        cells = []
        for i, (lbl, val) in enumerate(rows):
            is_last = show_total_last and i == len(rows) - 1
            lbl_sty = st_val  if is_last else st_lbl
            val_sty = st_val_r
            num_text = f'{_fmt(val)} <font size="6.5" color="#607D8B">{_unit}</font>'
            cells.append([Paragraph(_p(lbl), lbl_sty), Paragraph(num_text, val_sty)])
        cw = [avail * 0.58, avail * 0.42]
        t = Table(cells, colWidths=cw)
        cmd = [
            ('ROWBACKGROUNDS', (0,0),(-1,-1), [WHITE, GREY]),
            ('TOPPADDING',    (0,0),(-1,-1), 5),
            ('BOTTOMPADDING', (0,0),(-1,-1), 5),
            ('LEFTPADDING',   (0,0),(-1,-1), 8),
            ('RIGHTPADDING',  (0,0),(-1,-1), 8),
        ]
        if show_total_last:
            cmd.append(('BACKGROUND', (0,-1),(-1,-1), TOT_BG))
        t.setStyle(TableStyle(cmd))
        return t

    # ── Canvas callback (tutte le pagine) ───────────────────────────────────
    def on_page(c, doc):
        c.saveState()
        c.setFillColor(NAVY)
        c.rect(0, H - 11*mm, W, 11*mm, fill=1, stroke=0)
        c.setFillColor(GREEN)
        c.rect(0, H - 12*mm, W, 1*mm, fill=1, stroke=0)
        c.setFillColor(WHITE)
        c.setFont('Helvetica-Bold', 7.5)
        c.drawString(MAR, H - 7*mm, 'REPORT EMISSIONI CO2')
        c.setFont('Helvetica', 7.5)
        c.setFillColor(GREY_M)
        c.drawRightString(W - MAR, H - 7*mm, f'Pag. {doc.page}  -  {nome_impianto}')
        c.restoreState()

    # ── Document ─────────────────────────────────────────────────────────────
    buf = io.BytesIO()
    doc = SimpleDocTemplate(
        buf, pagesize=A4,
        leftMargin=MAR, rightMargin=MAR,
        topMargin=17*mm, bottomMargin=15*mm,
        title='Report emissioni CO2',
    )

    story = []

    # ── Intestazione ─────────────────────────────────────────────────────────
    from reportlab.platypus import HRFlowable
    story.append(Paragraph(
        'Report emissioni CO<font size="12">2</font>',
        _s('main_title', fontName='Helvetica-Bold', fontSize=20, textColor=NAVY, leading=26),
    ))
    story.append(Spacer(1, 2*mm))
    story.append(Paragraph(
        f'Impianto "{nome_impianto}"',
        _s('subtitle', fontSize=9, textColor=MUTED, leading=13),
    ))
    story.append(Spacer(1, 1*mm))
    story.append(Paragraph(
        f'Simulazione {data_simulazione}',
        _s('subtitle2', fontSize=9, textColor=MUTED, leading=13),
    ))
    story.append(Spacer(1, 3*mm))
    story.append(HRFlowable(width=avail, thickness=1.5, color=GREEN, spaceAfter=5*mm))

    # ── KPI riepilogative ────────────────────────────────────────────────────
    story.append(sec_hdr('Riepilogo — Bilancio CO₂ Totale'))
    story.append(Spacer(1, 3*mm))
    story.append(kpi_row([
        ('CO₂eq totale', co2_bilancio_tot, 'ton CO₂eq/anno'),
    ]))
    story.append(Spacer(1, 2*mm))
    story.append(kpi_row([
        ('CO₂ biomasse',  co2_evitata_biomasse_tot, 'ton CO₂eq/anno'),
        ('CO₂ impianto',  co2_impianto_tot,         'ton CO₂eq/anno'),
        ('CO₂ digestato', co2_dig_tot,              'ton CO₂eq/anno'),
        ('CO₂ trasporti', co2_tra_tot,              'ton CO₂eq/anno'),
    ]))
    story.append(Spacer(1, 6*mm))

    # ── CO2 BIOMASSE ─────────────────────────────────────────────────────────
    story.append(KeepTogether([
        sec_hdr('1 · CO₂ evitata da biomasse'),
        Spacer(1, 2*mm),
        detail_tbl([
            ('Letame',   CO2_evitata_letame),
            ('Liquame',  CO2_evitata_liquame),
            ('Pollina',  pollina_co2_tot),
            ('Colture',  colture_co2_tot),
            ('Totale',   co2_evitata_biomasse_tot),
        ]),
        Spacer(1, 6*mm),
    ]))

    # ── CO2 ENERGIA PRODOTTA ─────────────────────────────────────────────────
    story.append(KeepTogether([
        sec_hdr('2 · CO₂ impianto — energia prodotta'),
        Spacer(1, 2*mm),
        detail_tbl([
            ('Energia elettrica netta prodotta', CO2_en_el_prodotta),
            ('Calore netto prodotto',            CO2_calore_prodotto),
            ('Biometano netto prodotto',         CO2_biometano_prodotto),
            ('BioLNG netto prodotto',            CO2_biolng_prodotto),
            ('CO₂ biogenica prodotta',           CO2_biogenica_prodotta),
            ('Totale',                           tot_co2_energia_prodotta),
        ]),
        Spacer(1, 6*mm),
    ]))

    # ── CO2 ENERGIA ACQUISTATA ───────────────────────────────────────────────
    story.append(KeepTogether([
        sec_hdr('3 · CO₂ impianto — energia acquistata'),
        Spacer(1, 2*mm),
        detail_tbl([
            ('Energia elettrica acquistata', CO2_en_el_acquistata),
            ('Metano acquistato',            CO2_metano_acquistato),
            ('LNG acquistato',               CO2_lng_acquistato),
            ('Totale',                       tot_co2_energia_acquistata),
        ]),
        Spacer(1, 6*mm),
    ]))

    # ── CO2 ALTRE EMISSIONI IMPIANTO ─────────────────────────────────────────
    story.append(KeepTogether([
        sec_hdr('4 · CO₂ impianto — altre emissioni'),
        Spacer(1, 2*mm),
        detail_tbl([
            ('Rifiuti',           CO2_rifiuti),
            ('Olio lubrificante', CO2_olio_lubrificante),
            ('Acqua',             CO2_acqua),
            ('Scarichi',          CO2_scarichi),
            ('Totale',            CO2_attivita_impianto),
        ]),
        Spacer(1, 6*mm),
    ]))

    # ── CO2 DIGESTATO ────────────────────────────────────────────────────────
    story.append(KeepTogether([
        sec_hdr('5 · CO₂ digestato'),
        Spacer(1, 2*mm),
        detail_tbl([('Totale', co2_dig_tot)], show_total_last=False),
        Spacer(1, 6*mm),
    ]))

    # ── CO2 TRASPORTI ────────────────────────────────────────────────────────
    story.append(KeepTogether([
        sec_hdr('6 · CO₂ trasporti'),
        Spacer(1, 2*mm),
        detail_tbl([
            ('Conferitori → impianto', co2_tra_conf),
            ('Impianto → ricettori',   co2_tra_ric),
            ('Totale',                 co2_tra_tot),
        ]),
        Spacer(1, 6*mm),
    ]))

    # ── BILANCIO CO2 ─────────────────────────────────────────────────────────
    story.append(sec_hdr('7 · Bilancio CO₂'))
    story.append(Spacer(1, 2*mm))
    story.append(detail_tbl([
        ('CO₂ biomasse',  co2_evitata_biomasse_tot),
        ('CO₂ impianto',  co2_impianto_tot),
        ('CO₂ digestato', co2_dig_tot),
        ('CO₂ trasporti', co2_tra_tot),
        ('Totale',        co2_bilancio_tot),
    ]))
    story.append(Spacer(1, 6*mm))

    # ── BILANCIO DI MASSA ────────────────────────────────────────────────────
    story.append(sec_hdr('8 · Bilancio di massa'))
    story.append(Spacer(1, 2*mm))

    def _sub_hdr(title):
        t = Table(
            [[Paragraph(title.upper(), _s('sh', fontSize=7, textColor=MUTED,
                                          fontName='Helvetica-Bold'))]],
            colWidths=[avail],
        )
        t.setStyle(TableStyle([
            ('BACKGROUND',    (0,0),(-1,-1), colors.HexColor('#ECEFF1')),
            ('TOPPADDING',    (0,0),(-1,-1), 3),
            ('BOTTOMPADDING', (0,0),(-1,-1), 3),
            ('LEFTPADDING',   (0,0),(-1,-1), 8),
        ]))
        return t

    story.append(_sub_hdr('Biomassa'))
    story.append(data_tbl([
        ('Letame',          tot_letame,        'ton/anno'),
        ('Liquame',         tot_liquame,       'ton/anno'),
        ('Pollina',         tot_pollina,       'ton/anno'),
        ('Sottoprodotti',   tot_sottoprodotti, 'ton/anno'),
        ('Colture',         tot_colture,       'ton/anno'),
        ('Totale biomassa', tot_biomasse,      'ton/anno', True),
    ]))
    story.append(Spacer(1, 2*mm))
    story.append(_sub_hdr('Digestato'))
    story.append(data_tbl([
        ('Liquido',            tot_dig_liq_totale, 'ton/anno'),
        ('Separato',           tot_dig_sep_totale, 'ton/anno'),
        ('Totale digestato',   tot_digestato,      'ton/anno', True),
        ('  di cui conferito', dig_conferito,      'ton/anno'),
        ('  residuo',          dig_residuo,        'ton/anno'),
    ]))
    story.append(Spacer(1, 6*mm))

    doc.build(story, onFirstPage=on_page, onLaterPages=on_page)
    return buf.getvalue()


def genera_excel(dfs):
    """Genera un file Excel con un foglio per ogni DataFrame. Restituisce bytes."""
    buf = io.BytesIO()
    with pd.ExcelWriter(buf, engine='xlsxwriter') as writer:
        for sheet_name, df in dfs.items():
            if df is not None and not df.empty:
                df.to_excel(writer, sheet_name=sheet_name[:31], index=False)
    return buf.getvalue()


def result(label: str, value, unit: str = "") -> str:
    unit_html = (
        f'<span style="font-size:0.75rem;opacity:0.5;margin-left:0.3rem;">{unit}</span>'
        if unit else ""
    )
    return (
        f'<div style="display:flex;justify-content:space-between;align-items:baseline;padding:0.35rem 0;">'
        f'<span style="font-size:0.82rem;opacity:0.5;">{label}</span>'
        f'<span style="display:flex;align-items:baseline;">'
        f'<span style="font-size:0.92rem;">{value}</span>'
        f'{unit_html}'
        f'</span></div>'
    )


def section(title: str, rows: list):
    html = f'<div style="font-size:1rem;font-weight:600;margin-bottom:0.5rem;margin-top:0.25rem;">{title}</div>'
    html += "".join(result(*row) for row in rows)
    st.markdown(html, unsafe_allow_html=True)

def subsection(title: str, rows: list):
    html = f'<div style="font-size:0.85rem;font-weight:600;opacity:0.6;margin-bottom:0.4rem;margin-top:0.75rem;text-transform:uppercase;letter-spacing:0.05em;">{title}</div>'
    html += "".join(result(*row) for row in rows)
    st.markdown(html, unsafe_allow_html=True)

def render_results(df_allevatori, df_conferitori, df_biomasse, df_co2_evitate, df_impianto, df_impianto_scarichi, df_digestato_allevatori, digestato_liq_altri_conf, digestato_sep_altri_conf, df_co2_trasporti, dig_residuo_sep, dig_residuo_liq, co2_dig_altri_conf, nome_impianto=""):

    KG_TO_TON = 1 / 1000

    # GENERALE
    n_allevatori = len(df_allevatori)

    # BIOMASSE (ton)
    tot_letame        = df_allevatori["letame_produzione"].sum()        + df_conferitori[df_conferitori["tipo"] == "Letame"]["carico"].sum()
    tot_liquame       = df_allevatori["liquame_produzione"].sum()       + df_conferitori[df_conferitori["tipo"] == "Liquame"]["carico"].sum()
    tot_pollina       = df_allevatori["pollina_produzione"].sum()       + df_conferitori[df_conferitori["tipo"] == "Pollina"]["carico"].sum()
    tot_sottoprodotti = df_allevatori["sottoprodotti_produzione"].sum() + df_conferitori[df_conferitori["tipo"] == "Sottoprodotti"]["carico"].sum()
    tot_colture       = df_allevatori["colture_produzione"].sum()       + df_conferitori[df_conferitori["tipo"] == "Colture"]["carico"].sum()
    tot_biomasse      = tot_letame + tot_liquame + tot_pollina + tot_sottoprodotti + tot_colture

    # CO2 EVITATA BIOMASSE
    def _ev(tipologia):
        return df_co2_evitate[df_co2_evitate["tipologia"] == tipologia]["co2_kg"].sum() * KG_TO_TON

    CO2_evitata_letame    = _ev("Letame")
    CO2_evitata_liquame   = _ev("Liquame")
    pollina_co2_tot       = _ev("Pollina")
    colture_co2_tot       = _ev("Colture")

    # CO2 IMPIANTO
    def _imp(nome):
        return df_impianto[df_impianto["nome"] == nome]["co2_tot"].sum() * KG_TO_TON

    CO2_en_el_prodotta     = _imp("Energia elettrica netta prodotta")
    CO2_calore_prodotto    = _imp("Calore netto prodotto")
    CO2_biometano_prodotto = _imp("Biometano netto prodotto")
    CO2_biolng_prodotto    = _imp("BioLNG netto prodotto")
    CO2_biogenica_prodotta = _imp("CO₂ biogenica prodotta")
    CO2_en_el_acquistata   = _imp("Energia elettrica acquistata")
    CO2_metano_acquistato  = _imp("Metano acquistato")
    CO2_lng_acquistato     = _imp("LNG acquistato")

    tot_co2_energia_prodotta   = CO2_en_el_prodotta + CO2_calore_prodotto + CO2_biometano_prodotto + CO2_biolng_prodotto + CO2_biogenica_prodotta
    tot_co2_energia_acquistata = CO2_en_el_acquistata + CO2_metano_acquistato + CO2_lng_acquistato

    # CO2 SCARICHI IMPIANTO
    def _sca(nome):
        return df_impianto_scarichi[df_impianto_scarichi["nome"] == nome]["co2_tot"].sum() * KG_TO_TON

    CO2_rifiuti           = _sca("Rifiuti")
    CO2_olio_lubrificante = _sca("Olio lubrificante")
    CO2_acqua             = _sca("Acqua")
    CO2_scarichi          = _sca("Scarichi")
    CO2_attivita_impianto = CO2_rifiuti + CO2_olio_lubrificante + CO2_acqua + CO2_scarichi

    # DIGESTATO
    tot_dig_liq        = df_digestato_allevatori["digestato_liq"].sum()
    tot_dig_sep        = df_digestato_allevatori["digestato_sep"].sum()
    tot_dig_liq_totale = tot_dig_liq + digestato_liq_altri_conf
    tot_dig_sep_totale = tot_dig_sep + digestato_sep_altri_conf
    tot_digestato      = tot_dig_liq_totale + tot_dig_sep_totale

    # CO2 DIGESTATO
    co2_dig_all   = df_digestato_allevatori["co2_digestato_tot"].sum() * KG_TO_TON
    co2_dig_altri = co2_dig_altri_conf['co2_tot'] * KG_TO_TON if co2_dig_altri_conf is not None else 0.0
    co2_dig_tot   = co2_dig_all + co2_dig_altri

    # CO2 TRASPORTI
    def _tra(voce):
        return df_co2_trasporti[df_co2_trasporti["voce"] == voce]["co2_tot"].sum() * KG_TO_TON

    co2_tra_conf = _tra("Conferitori → impianto")
    co2_tra_ric  = _tra("Impianto → ricettori")
    co2_tra_tot  = _tra("Totale trasporti")

    # BILANCIO CO2
    co2_evitata_biomasse_tot = (
        CO2_evitata_letame + CO2_evitata_liquame +
        pollina_co2_tot + colture_co2_tot
    )
    co2_impianto_tot = tot_co2_energia_prodotta + tot_co2_energia_acquistata + CO2_attivita_impianto
    co2_bilancio_tot = co2_evitata_biomasse_tot + co2_impianto_tot + co2_tra_tot + co2_dig_tot

    # DIGESTATO BILANCIO MASSA
    dig_conferito = tot_digestato - dig_residuo_liq - dig_residuo_sep
    dig_residuo   = dig_residuo_liq + dig_residuo_sep

    r = lambda v: round(v)

    # ── Render ─────────────────────────────────────────────────────────────────

    section("Generale", [
        ("Numero allevatori", n_allevatori),
    ])

    st.divider()

    section("CO₂ evitata biomasse", [
        ("Letame",  r(CO2_evitata_letame),  "ton/anno"),
        ("Liquame", r(CO2_evitata_liquame), "ton/anno"),
        ("Pollina", r(pollina_co2_tot),      "ton/anno"),
        ("Colture", r(colture_co2_tot),      "ton/anno"),
    ])
    
    st.write("")
    with st.expander("Dettaglio CO₂ evitata — per allevatore"):
        df_ev_display = df_allevatori[[
            'nome_allevatore',
            'letame_produzione',
            'letame_evitata_anno',
            'liquame_produzione',
            'liquame_evitata_anno',
            'pollina_produzione',
            'pollina_co2_tot',
            'colture_produzione',
            'colture_co2_tot',
            'sottoprodotti_produzione',
        ]].copy()

        for col in [
            'letame_produzione', 'letame_evitata_anno',
            'liquame_produzione', 'liquame_evitata_anno',
            'pollina_produzione', 'pollina_co2_tot',
            'colture_produzione', 'colture_co2_tot',
            'sottoprodotti_produzione',
        ]:
            df_ev_display[col] = (df_ev_display[col] * KG_TO_TON).round(1)

        df_ev_display['co2_tot'] = (
            df_ev_display['letame_evitata_anno'] +
            df_ev_display['liquame_evitata_anno'] +
            df_ev_display['pollina_co2_tot'] +
            df_ev_display['colture_co2_tot']
        ).round(1)

        df_ev_display.columns = [
            'Allevatore',
            'Letame (ton)',        'CO₂ letame (ton)',
            'Liquame (ton)',       'CO₂ liquame (ton)',
            'Pollina (ton)',       'CO₂ pollina (ton)',
            'Colture (ton)',       'CO₂ colture (ton)',
            'Sottoprodotti (ton)',
            'CO₂ totale (ton)',
        ]

        st.dataframe(df_ev_display, hide_index=True, use_container_width=True)

    st.divider()

    section("CO₂ impianto — energia prodotta", [
        ("Energia elettrica netta prodotta", r(CO2_en_el_prodotta),       "ton/anno"),
        ("Calore netto prodotto",            r(CO2_calore_prodotto),      "ton/anno"),
        ("Biometano netto prodotto",         r(CO2_biometano_prodotto),   "ton/anno"),
        ("BioLNG netto prodotto",            r(CO2_biolng_prodotto),      "ton/anno"),
        ("CO₂ biogenica prodotta",           r(CO2_biogenica_prodotta),   "ton/anno"),
        ("Totale",                           r(tot_co2_energia_prodotta), "ton/anno"),
    ])

    st.write("")
    with st.expander("Dettaglio componenti CO₂ — energia prodotta"):
        df_imp_display = df_impianto.copy()
        df_imp_display[["co2_fossile", "co2_biogenica", "co2_dluc", "co2_tot"]] = (
            df_imp_display[["co2_fossile", "co2_biogenica", "co2_dluc", "co2_tot"]] * KG_TO_TON
        ).round(1)
        df_imp_display.columns = ["Voce", "CO₂ fossile (ton)", "CO₂ biogenica (ton)", "CO₂ dLUC (ton)", "CO₂ tot (ton)"]
        st.dataframe(df_imp_display, hide_index=True, use_container_width=True)

    st.divider()

    section("CO₂ impianto — energia acquistata", [
        ("Energia elettrica acquistata", r(CO2_en_el_acquistata),       "ton/anno"),
        ("Metano acquistato",            r(CO2_metano_acquistato),      "ton/anno"),
        ("LNG acquistato",               r(CO2_lng_acquistato),         "ton/anno"),
        ("Totale",                       r(tot_co2_energia_acquistata), "ton/anno"),
    ])

    st.write("")
    with st.expander("Dettaglio componenti CO₂ — energia acquistata"):
        df_acq_display = df_impianto[df_impianto["nome"].isin([
            "Energia elettrica acquistata", "Metano acquistato", "LNG acquistato"
        ])].copy()
        df_acq_display[["co2_fossile", "co2_biogenica", "co2_dluc", "co2_tot"]] = (
            df_acq_display[["co2_fossile", "co2_biogenica", "co2_dluc", "co2_tot"]] * KG_TO_TON
        ).round(1)
        df_acq_display.columns = ["Voce", "CO₂ fossile (ton)", "CO₂ biogenica (ton)", "CO₂ dLUC (ton)", "CO₂ tot (ton)"]
        st.dataframe(df_acq_display, hide_index=True, use_container_width=True)

    st.divider()

    section("CO₂ impianto — altre emissioni", [
        ("Rifiuti",           r(CO2_rifiuti),           "ton/anno"),
        ("Olio lubrificante", r(CO2_olio_lubrificante), "ton/anno"),
        ("Acqua",             r(CO2_acqua),             "ton/anno"),
        ("Scarichi",          r(CO2_scarichi),          "ton/anno"),
        ("Totale",            r(CO2_attivita_impianto), "ton/anno"),
    ])

    st.write("")
    with st.expander("Dettaglio componenti CO₂ — altre emissioni"):
        df_sca_display = df_impianto_scarichi.copy()
        df_sca_display[["co2_fossile", "co2_biogenica", "co2_dluc", "co2_tot"]] = (
            df_sca_display[["co2_fossile", "co2_biogenica", "co2_dluc", "co2_tot"]] * KG_TO_TON
        ).round(1)
        df_sca_display.columns = ["Voce", "CO₂ fossile (ton)", "CO₂ biogenica (ton)", "CO₂ dLUC (ton)", "CO₂ tot (ton)"]
        st.dataframe(df_sca_display, hide_index=True, use_container_width=True)

    st.divider()

    section("CO₂ digestato", [
        ("Totale",      r(co2_dig_tot),  "ton/anno"),
    ])

    st.write("")
    with st.expander("Dettaglio componenti CO₂ — digestato"):
        co2_dig_fossile   = df_digestato_allevatori['co2_digestato_fossile'].sum()   * KG_TO_TON
        co2_dig_biogenica = df_digestato_allevatori['co2_digestato_biogenica'].sum() * KG_TO_TON
        co2_dig_dluc      = df_digestato_allevatori['co2_digestato_dluc'].sum()      * KG_TO_TON

        if co2_dig_altri_conf is not None:
            co2_dig_fossile   += co2_dig_altri_conf['co2_fossile']   * KG_TO_TON
            co2_dig_biogenica += co2_dig_altri_conf['co2_biogenica'] * KG_TO_TON
            co2_dig_dluc      += co2_dig_altri_conf['co2_dluc']      * KG_TO_TON

        df_dig_display = pd.DataFrame([{
            'Voce':                'Digestato',
            'CO₂ fossile (ton)':   round(co2_dig_fossile,   1),
            'CO₂ biogenica (ton)': round(co2_dig_biogenica, 1),
            'CO₂ dLUC (ton)':      round(co2_dig_dluc,      1),
            'CO₂ tot (ton)':       round(co2_dig_tot,       1),
        }])
        st.dataframe(df_dig_display, hide_index=True, use_container_width=True)

    st.divider()

    section("CO₂ trasporti", [
        ("Conferitori → impianto", r(co2_tra_conf), "ton/anno"),
        ("Impianto → ricettori",   r(co2_tra_ric),  "ton/anno"),
        ("Totale",                 r(co2_tra_tot),  "ton/anno"),
    ])

    st.write("")
    with st.expander("Dettaglio componenti CO₂ — trasporti"):
        df_tra_display = df_co2_trasporti.copy()
        df_tra_display[["co2_fossile", "co2_biogenica", "co2_dluc", "co2_tot"]] = (
            df_tra_display[["co2_fossile", "co2_biogenica", "co2_dluc", "co2_tot"]] * KG_TO_TON
        ).round(1)
        df_tra_display.columns = ["Voce", "CO₂ fossile (ton)", "CO₂ biogenica (ton)", "CO₂ dLUC (ton)", "CO₂ tot (ton)"]
        st.dataframe(df_tra_display, hide_index=True, use_container_width=True)

    st.divider()

    st.markdown('<div style="font-size:1rem;font-weight:600;margin-bottom:0.25rem;margin-top:0.25rem;">Bilancio CO₂</div>', unsafe_allow_html=True)

    section("", [
        ("CO₂ biomasse",  r(co2_evitata_biomasse_tot), "ton/anno"),
        ("CO₂ impianto",  r(co2_impianto_tot),         "ton/anno"),
        ("CO₂ digestato", r(co2_dig_tot),              "ton/anno"),
        ("CO₂ trasporti", r(co2_tra_tot),              "ton/anno"),
        ("Totale",        r(co2_bilancio_tot),          "ton/anno"),
    ])

    st.divider()

    st.markdown('<div style="font-size:1rem;font-weight:600;margin-bottom:0.25rem;margin-top:0.25rem;">Bilancio di massa</div>', unsafe_allow_html=True)

    subsection("Biomassa", [
        ("Letame",        r(tot_letame),        "ton/anno"),
        ("Liquame",       r(tot_liquame),        "ton/anno"),
        ("Pollina",       r(tot_pollina),        "ton/anno"),
        ("Sottoprodotti", r(tot_sottoprodotti),  "ton/anno"),
        ("Colture",       r(tot_colture),        "ton/anno"),
        ("Totale",        r(tot_biomasse),       "ton/anno"),
    ])

    subsection("Digestato", [
        ("Liquido",             r(tot_dig_liq_totale), "ton/anno"),
        ("Separato",            r(tot_dig_sep_totale), "ton/anno"),
        ("Totale",              r(tot_digestato),      "ton/anno"),
        (" - di cui conferito", r(dig_conferito),      "ton/anno"),
        (" - residuo",          r(dig_residuo),        "ton/anno"),
    ])

    st.divider()

    # ── Download ────────────────────────────────────────────────────────────
    data_sim = datetime.date.today().strftime("%d/%m/%Y")
    nome_file = f"co2_{nome_impianto}_{datetime.date.today().strftime('%Y%m%d')}"

    pdf_bytes = genera_pdf(
        nome_impianto, data_sim,
        n_allevatori,
        CO2_evitata_letame, CO2_evitata_liquame, pollina_co2_tot, colture_co2_tot,
        CO2_en_el_prodotta, CO2_calore_prodotto, CO2_biometano_prodotto,
        CO2_biolng_prodotto, CO2_biogenica_prodotta, tot_co2_energia_prodotta,
        CO2_en_el_acquistata, CO2_metano_acquistato, CO2_lng_acquistato, tot_co2_energia_acquistata,
        CO2_rifiuti, CO2_olio_lubrificante, CO2_acqua, CO2_scarichi, CO2_attivita_impianto,
        co2_dig_tot,
        co2_tra_conf, co2_tra_ric, co2_tra_tot,
        co2_evitata_biomasse_tot, co2_impianto_tot, co2_bilancio_tot,
        tot_letame, tot_liquame, tot_pollina, tot_sottoprodotti, tot_colture, tot_biomasse,
        tot_dig_liq_totale, tot_dig_sep_totale, tot_digestato, dig_conferito, dig_residuo,
    )

    excel_dfs = {
        "Allevatori":          df_allevatori,
        "Conferitori":         df_conferitori,
        "Biomasse":            df_biomasse,
        "CO2 evitate biomasse": df_co2_evitate,
        "Impianto - Energia":  df_impianto,
        "Impianto - Scarichi": df_impianto_scarichi,
        "Digestato":           df_digestato_allevatori,
        "CO2 trasporti":       df_co2_trasporti,
    }
    excel_bytes = genera_excel(excel_dfs)

    col_pdf, col_xls = st.columns(2)
    with col_pdf:
        st.download_button(
            "📄 Scarica PDF risultati",
            data=pdf_bytes,
            file_name=f"{nome_file}.pdf",
            mime="application/pdf",
            use_container_width=True,
        )
    with col_xls:
        st.download_button(
            "📊 Scarica Excel dettagli",
            data=excel_bytes,
            file_name=f"{nome_file}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            use_container_width=True,
        )

# ---------------------------------------------------------------------------
# MAIN
# ---------------------------------------------------------------------------

impianti = carica_impianti()
opzioni  = [nome for _, nome in impianti]

impianto_selezionato    = st.selectbox("Seleziona un impianto:", opzioni)
id_impianto_selezionato = next((id_imp for id_imp, nome in impianti if nome == impianto_selezionato), None)
allevatori_impianto     = carica_allevatori(id_impianto_selezionato) if id_impianto_selezionato else []

if st.button("Esegui simulazione", use_container_width=True):
    
    if not id_impianto_selezionato:
        st.error("Seleziona un impianto prima di eseguire la simulazione.")
        st.stop()
    if not allevatori_impianto:
        st.error("Nessun allevatore associato a questo impianto.")
        st.stop()

    try:
        I  = Impianto.from_db(db, id_impianto_selezionato)
        EF = FattoriEmissione(db)
    except Exception as e:
        st.error(f"Errore caricamento dati impianto: {e}")
        st.stop()

    # Carica i mezzi configurati per questo impianto
    T_mezzo_liq = Trasporto.from_db(db, I.id_mezzo_liquido)
    T_mezzo_sol = Trasporto.from_db(db, I.id_mezzo_solido)

    # 1- CALCOLO CO₂ BIOMASSA e TRASPORTO ALLEVATORI -> IMPIANTO
    try:
        df_allevatori = calcola_risultati_allevatori(db, allevatori_impianto, EF, I.id_mezzo_liquido, I.id_mezzo_solido)
    except Exception as e:
        st.error(f"Errore nel calcolo della CO₂: {e}")
        st.stop()

    # Biomasse e CO₂ trasporto da altri conferitori
    df_conferitori = carica_altri_conferitori(I.id_impianto, db, I.id_mezzo_liquido, I.id_mezzo_solido)

    df_biomasse, df_co2_evitate = aggrega_risultati_conferitori(df_allevatori, df_conferitori, db, EF)

    # 2- CALCOLO CO₂ IMPIANTO
    df_impianto = calcola_componenti_impianto(I, EF, db)
    df_impianto_scarichi = co2eq_impianto(I, EF, db)

    # 3- BILANCIO DI MASSA E DIGESTATO
    df_digestato_allevatori = calcola_digestato_allevatori(db, df_allevatori, I, EF, I.id_mezzo_liquido, I.id_mezzo_solido)

    digestato_liq_altri_conf, digestato_sep_altri_conf, co2_dig_altri_conf = calcola_digestato_da_conferitori(df_conferitori, I, EF, db)

    df_ricettori, residuo_liq, residuo_sep = digestato_altri_ricettori(
        digestato_liq_altri_conf,
        digestato_sep_altri_conf,
        id_impianto_selezionato,
        db,
        I.id_mezzo_liquido,
        I.id_mezzo_solido,
    )

    # 4- TRASPORTI
    co2_trasporti = calcola_co2_trasporti_totale(
        df_allevatori, df_conferitori, df_digestato_allevatori, df_ricettori,
        db, T_mezzo_liq.tipo, T_mezzo_sol.tipo
    )

    # 5- DISPLAY RISULTATI
    render_results(df_allevatori, df_conferitori, df_biomasse, df_co2_evitate, df_impianto, df_impianto_scarichi, df_digestato_allevatori, digestato_liq_altri_conf, digestato_sep_altri_conf, co2_trasporti, residuo_sep, residuo_liq, co2_dig_altri_conf, nome_impianto=I.nome)
