import streamlit as st
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
# COSTANTI
# ---------------------------------------------------------------------------

ID_TRASPORTO_TUBAZIONE = 0  # Nessun mezzo (conferimento via tubazione)
ID_TRASPORTO_CAMION    = 1  # Camion generico (letame, digestato solido)
ID_TRASPORTO_TRATTORE  = 2  # Trattore       (liquame, digestato liquido)

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

def carica_altri_conferitori(id_impianto, db):
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
        DataFrame con colonne: 'tipo', 'distanza', 'carico', 'co2_trasporto_tot', 'n_viaggi'.
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
        return pd.DataFrame(columns=['tipo', 'distanza', 'carico', 'co2_trasporto_tot', 'n_viaggi'])

    # Mapping per ogni tipo: (id_mezzo, densità)
    mapping = {
        'Liquame': (ID_TRASPORTO_TRATTORE, 1.0),
        'Letame': (ID_TRASPORTO_CAMION, 0.7),
        'Pollina': (ID_TRASPORTO_CAMION, 0.7),
        'Colture': (ID_TRASPORTO_CAMION, 2.0),
        'Sottoprodotti': (ID_TRASPORTO_CAMION, 1.5)
    }

    co2_list = []
    viaggi_list = []
    
    for idx, row in df.iterrows():
        tipo = row['tipo']
        distanza = row['distanza']
        carico = row['carico']

        # Se carico o distanza sono zero/null, oppure tipo non riconosciuto -> nessun trasporto
        if carico <= 0 or distanza <= 0 or tipo not in mapping:
            co2_list.append(0)
            viaggi_list.append(0)
            continue

        id_mezzo, densita = mapping[tipo]

        try:
            # Recupera l'oggetto Trasporto usando la connessione ancora aperta
            T = Trasporto.from_db(db, id_mezzo)
            co2_trasporto, n_viaggi = co2eq_trasporto(T, carico, densita, distanza)
        except Exception as e:
            print(f"Errore nel calcolo del trasporto per tipo {tipo}: {e}")
            co2_trasporto, n_viaggi = 0, 0

        co2_list.append(co2_trasporto)
        viaggi_list.append(n_viaggi)

    df['co2_trasporto_tot'] = co2_list
    df['n_viaggi'] = viaggi_list

    conn.close()
    return df

def calcola_risultati_allevatori(db, allevatori_impianto, EF, id_trasporto_trattore, id_trasporto_camion):
    """
    Calcola per ogni allevatore dell'impianto le emissioni di CO₂ (totali)
    e i dati di trasporto per tutte le tipologie di biomassa conferita.
    Gestisce attributi None convertendoli a 0.
    """
    risultati = []

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
            'nome_allevatore': nome_allevatore
        }

        # ------------------ LIQUAME ------------------
        if prod_liquame > 0:
            (co2_evitata_anno_liq, n_svuotamenti_liq,
             deposito_liq, liquame_tot_annuo) = co2_liquame_semplificata(A)

            if tipo_conferimento == "mezzi":
                T = Trasporto.from_db(db, id_trasporto_trattore)
                co2_trasporto_liq, n_viaggi_liq = co2eq_trasporto(
                    T, deposito_liq, 1, distanza
                )
                co2_trasporto_liq_tot_anno = co2_trasporto_liq * n_svuotamenti_liq
                n_viaggi_liq_tot_anno = n_viaggi_liq * n_svuotamenti_liq
            else:
                n_viaggi_liq_tot_anno = 0
                co2_trasporto_liq_tot_anno = A.potenza * A.ore * EF.EE_BT # kg CO2 da pompaggio

            res.update({
                'liquame_produzione': liquame_tot_annuo,
                'liquame_evitata_anno': co2_evitata_anno_liq,
                'liquame_trasporto_co2_tot': co2_trasporto_liq_tot_anno,
                'liquame_trasporto_viaggi': n_viaggi_liq_tot_anno
            })
        else:
            res.update({
                'liquame_produzione': 0,
                'liquame_evitata_anno': 0,
                'liquame_trasporto_co2_tot': 0,
                'liquame_trasporto_viaggi': 0
            })

        # ------------------ LETAME ------------------
        if prod_letame > 0:
            (co2_evitata_anno_let, n_svuotamenti_let,
             deposito_let, letame_tot_annuo) = co2_letame_semplificata(A)

            T = Trasporto.from_db(db, id_trasporto_camion)
            co2_trasporto_let, n_viaggi_let = co2eq_trasporto(
                T, deposito_let, 0.7, distanza
            )
            co2_trasporto_let_tot_anno = co2_trasporto_let * n_svuotamenti_let
            n_viaggi_let_tot_anno = n_viaggi_let * n_svuotamenti_let

            res.update({
                'letame_produzione': letame_tot_annuo,
                'letame_evitata_anno': co2_evitata_anno_let,
                'letame_trasporto_co2_tot': co2_trasporto_let_tot_anno,
                'letame_trasporto_viaggi': n_viaggi_let_tot_anno
            })
        else:
            res.update({
                'letame_produzione': 0,
                'letame_evitata_anno': 0,
                'letame_trasporto_co2_tot': 0,
                'letame_trasporto_viaggi': 0
            })

        # ------------------ POLLINA ------------------
        if pollina > 0:
            co2_pollina = co2eq_pollina(pollina, EF.pollina)

            T = Trasporto.from_db(db, id_trasporto_camion)
            co2_trasporto_pol, n_viaggi_pol = co2eq_trasporto(
                T, pollina, 0.7, distanza
            )

            res.update({
                'pollina_produzione': pollina,
                'pollina_co2_tot': co2_pollina,
                'pollina_trasporto_co2_tot': co2_trasporto_pol,
                'pollina_trasporto_viaggi': n_viaggi_pol
            })
        else:
            res.update({
                'pollina_produzione': 0,
                'pollina_co2_tot': 0,
                'pollina_trasporto_co2_tot': 0,
                'pollina_trasporto_viaggi': 0
            })

        # ------------------ COLTURE ------------------
        if colture > 0:
            co2_colture = co2eq_colture(colture, EF.colture)

            T = Trasporto.from_db(db, id_trasporto_camion)
            co2_trasporto_col, n_viaggi_col = co2eq_trasporto(
                T, colture, 2, distanza
            )

            res.update({
                'colture_produzione': colture,
                'colture_co2_tot': co2_colture,
                'colture_trasporto_co2_tot': co2_trasporto_col,
                'colture_trasporto_viaggi': n_viaggi_col
            })
        else:
            res.update({
                'colture_produzione': 0,
                'colture_co2_tot': 0,
                'colture_trasporto_co2_tot': 0,
                'colture_trasporto_viaggi': 0
            })

        # ------------------ SOTTOPRODOTTI ------------------
        if sottoprodotti > 0:
            T = Trasporto.from_db(db, id_trasporto_camion)
            co2_trasporto_prod, n_viaggi_prod = co2eq_trasporto(
                T, sottoprodotti, 1.5, distanza
            )

            res.update({
                'sottoprodotti_produzione': sottoprodotti,
                'sottoprodotti_co2_tot': 0,
                'sottoprodotti_trasporto_co2_tot': co2_trasporto_prod,
                'sottoprodotti_trasporto_viaggi': n_viaggi_prod
            })
        else:
            res.update({
                'sottoprodotti_produzione': 0,
                'sottoprodotti_co2_tot': 0,
                'sottoprodotti_trasporto_co2_tot': 0,
                'sottoprodotti_trasporto_viaggi': 0
            })

        risultati.append(res)

    return pd.DataFrame(risultati)

def aggrega_risultati_conferitori(df_allevatori, df_altri, db_path, EF):
    """
    Aggrega i dati di biomassa e CO₂ da allevatori e altri conferitori,
    restituendo due dataframe:
      - biomasse totali per tipologia (kg)
      - CO₂ evitate da tutte le tipologie (kg CO₂) con totale

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
            tipo      = row['tipo']
            carico_kg = row['carico']

            if tipo in biomassa:
                biomassa[tipo] += carico_kg

            if tipo == 'Pollina' and carico_kg > 0:
                co2_evitate['Pollina'] += co2eq_pollina(carico_kg, EF.pollina)
            elif tipo == 'Colture' and carico_kg > 0:
                co2_evitate['Colture'] += co2eq_colture(carico_kg, EF.colture)

    # ------------------ Costruzione dataframe ------------------
    df_biomasse = pd.DataFrame([
        {'tipologia': k, 'quantita_kg': v} for k, v in biomassa.items()
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
    id_trasporto_trattore: int,
    id_trasporto_camion: int
) -> pd.DataFrame:
    if df_allevatori.empty:
        return pd.DataFrame()

    T_trattore = Trasporto.from_db(db, id_trasporto_trattore)
    T_camion   = Trasporto.from_db(db, id_trasporto_camion)

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
                'n_viaggi_liq':           0,
                'n_viaggi_sep':           0,
                'co2_digestato_fossile':  0.0,
                'co2_digestato_biogenica':0.0,
                'co2_digestato_dluc':     0.0,
                'co2_digestato_tot':      0.0,
            })
            continue

        digestato_sep, digestato_liq, comp_dig = co2eq_digestato(I, biomassa, EF, db)

        A        = Allevatore.from_db(db, id_allevatore)
        distanza = A.distanza_impianto

        if digestato_liq > 0:
            co2_liq, n_viaggi_liq = co2eq_trasporto(T_trattore, digestato_liq, 1.0, distanza)
        else:
            co2_liq, n_viaggi_liq = 0.0, 0

        if digestato_sep > 0:
            co2_sep, n_viaggi_sep = co2eq_trasporto(T_camion, digestato_sep, 0.7, distanza)
        else:
            co2_sep, n_viaggi_sep = 0.0, 0

        risultati.append({
            'id_allevatore':           id_allevatore,
            'nome_allevatore':         nome_allevatore,
            'biomassa_totale':         biomassa,
            'digestato_liq':           digestato_liq,
            'digestato_sep':           digestato_sep,
            'co2_trasporto_liq':       co2_liq,
            'co2_trasporto_sep':       co2_sep,
            'n_viaggi_liq':            n_viaggi_liq,
            'n_viaggi_sep':            n_viaggi_sep,
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
    records = []

    serie = co2eq_ee_prod_netta(impianto, EF, db)
    records.append({
        'nome': 'Energia elettrica netta prodotta',
        'co2_fossile': serie['co2_fossile'],
        'co2_biogenica': serie['co2_biogenica'],
        'co2_dluc': serie['co2_dluc'],
        'co2_tot': serie['co2_tot']
    })

    serie = co2eq_calore_netta(impianto, EF, db)
    records.append({
        'nome': 'Calore netto prodotto',
        'co2_fossile': serie['co2_fossile'],
        'co2_biogenica': serie['co2_biogenica'],
        'co2_dluc': serie['co2_dluc'],
        'co2_tot': serie['co2_tot']
    })

    serie = co2eq_biometano(impianto, EF, db)
    records.append({
        'nome': 'Biometano netto prodotto',
        'co2_fossile': serie['co2_fossile'],
        'co2_biogenica': serie['co2_biogenica'],
        'co2_dluc': serie['co2_dluc'],
        'co2_tot': serie['co2_tot']
    })

    serie = co2eq_biolng(impianto, EF, db)
    records.append({
        'nome': 'BioLNG netto prodotto',
        'co2_fossile': serie['co2_fossile'],
        'co2_biogenica': serie['co2_biogenica'],
        'co2_dluc': serie['co2_dluc'],
        'co2_tot': serie['co2_tot']
    })

    serie = co2eq_biogenica(impianto, EF, db)
    records.append({
        'nome': 'CO₂ biogenica prodotta',
        'co2_fossile': serie['co2_fossile'],
        'co2_biogenica': serie['co2_biogenica'],
        'co2_dluc': serie['co2_dluc'],
        'co2_tot': serie['co2_tot']
    })

    serie = co2eq_ee_acquistata(impianto, EF, db)
    records.append({
        'nome': 'Energia elettrica acquistata',
        'co2_fossile': serie['co2_fossile'],
        'co2_biogenica': serie['co2_biogenica'],
        'co2_dluc': serie['co2_dluc'],
        'co2_tot': serie['co2_tot']
    })

    serie = co2eq_metano_acq(impianto, EF, db)
    records.append({
        'nome': 'Metano acquistato',
        'co2_fossile': serie['co2_fossile'],
        'co2_biogenica': serie['co2_biogenica'],
        'co2_dluc': serie['co2_dluc'],
        'co2_tot': serie['co2_tot']
    })

    serie = co2eq_lng_acq(impianto, EF, db)
    records.append({
        'nome': 'LNG acquistato',
        'co2_fossile': serie['co2_fossile'],
        'co2_biogenica': serie['co2_biogenica'],
        'co2_dluc': serie['co2_dluc'],
        'co2_tot': serie['co2_tot']
    })

    df = pd.DataFrame(records)
    return df

def digestato_altri_ricettori(
    digestato_liq_altri_conf: float,
    digestato_sep_altri_conf: float,
    id_impianto: int,
    db: str
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
        'n_viaggi_liq', 'n_viaggi_sep'
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

    T_trattore = Trasporto.from_db(db, ID_TRASPORTO_TRATTORE)
    T_camion   = Trasporto.from_db(db, ID_TRASPORTO_CAMION)

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

            if assegnato_liq > 0 and distanza > 0:
                co2_liq, n_viaggi_liq = co2eq_trasporto(T_trattore, assegnato_liq, 1.0, distanza)
            else:
                co2_liq, n_viaggi_liq = 0.0, 0
            co2_sep, n_viaggi_sep = 0.0, 0

        elif tipo == "Digestato Separato":
            assegnato_liq = 0.0
            assegnato_sep = min(carico, residuo_sep)
            residuo_sep  -= assegnato_sep

            if assegnato_sep > 0 and distanza > 0:
                co2_sep, n_viaggi_sep = co2eq_trasporto(T_camion, assegnato_sep, 0.7, distanza)
            else:
                co2_sep, n_viaggi_sep = 0.0, 0
            co2_liq, n_viaggi_liq = 0.0, 0

        elif tipo in ("BioCO2", "BioLNG"):
            # Solo CO₂ da trasporto, non influisce sul residuo
            assegnato_liq = 0.0
            assegnato_sep = 0.0

            if carico > 0 and distanza > 0:
                co2_liq, n_viaggi_liq = co2eq_trasporto(T_camion, carico, 1.0, distanza)
            else:
                co2_liq, n_viaggi_liq = 0.0, 0
            co2_sep, n_viaggi_sep = 0.0, 0

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
            'n_viaggi_liq':      n_viaggi_liq,
            'n_viaggi_sep':      n_viaggi_sep
        })

    return pd.DataFrame(risultati), residuo_liq, residuo_sep

def calcola_co2_trasporti_totale(
    df_allevatori: pd.DataFrame,
    df_conferitori: pd.DataFrame,
    df_digestato_allevatori: pd.DataFrame,
    df_ricettori: pd.DataFrame,
    db: str
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

    comp_conf_liq = componenti("Trattore",       co2_conf_liq)
    comp_conf_sol = componenti("Camion generico", co2_conf_sol)

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

    comp_ric_liq = componenti("Trattore",       co2_ric_liq)
    comp_ric_sol = componenti("Camion generico", co2_ric_sol)

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

def render_results(df_allevatori, df_conferitori, df_biomasse, df_co2_evitate, df_impianto, df_impianto_scarichi, df_digestato_allevatori, digestato_liq_altri_conf, digestato_sep_altri_conf, df_co2_trasporti, dig_residuo_sep, dig_residuo_liq, co2_dig_altri_conf):

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
        ("Pollina", r(-pollina_co2_tot),     "ton/anno"),
        ("Colture", r(-colture_co2_tot),     "ton/anno"),
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
    if not allevatori_impianto:
        st.error("Nessun allevatore associato a questo impianto.")
    
    try:
        I  = Impianto.from_db(db, id_impianto_selezionato)
        EF = FattoriEmissione(db)
    except Exception as e:
        st.error(f"Errore caricamento dati impianto: {e}")

    # 1- CALCOLO CO₂ BIOMASSA e TRASPORTO ALLEVATORI -> IMPIANTO
    try:
        df_allevatori = calcola_risultati_allevatori(db, allevatori_impianto, EF, ID_TRASPORTO_TRATTORE, ID_TRASPORTO_CAMION)
    except Exception as e:
        st.error(f"Errore nel calcolo della CO₂: {e}")

    # Biomasse e CO₂ trasporto da altri conferitori
    df_conferitori = carica_altri_conferitori(I.id_impianto, db)

    df_biomasse, df_co2_evitate = aggrega_risultati_conferitori(df_allevatori, df_conferitori, db, EF)

    # 2- CALCOLO CO₂ IMPIANTO
    df_impianto = calcola_componenti_impianto(I, EF, db)
    df_impianto_scarichi = co2eq_impianto(I, EF, db)

    # 3- BILANCIO DI MASSA E DIGESTATO
    df_digestato_allevatori = calcola_digestato_allevatori(db, df_allevatori, I, EF, ID_TRASPORTO_TRATTORE, ID_TRASPORTO_CAMION)

    digestato_liq_altri_conf, digestato_sep_altri_conf, co2_dig_altri_conf = calcola_digestato_da_conferitori(df_conferitori, I, EF, db)

    df_ricettori, residuo_liq, residuo_sep = digestato_altri_ricettori(
        digestato_liq_altri_conf,
        digestato_sep_altri_conf,
        id_impianto_selezionato,
        db
    )

    # 4- TRASPORTI
    co2_trasporti = calcola_co2_trasporti_totale(df_allevatori, df_conferitori, df_digestato_allevatori, df_ricettori, db) 

    # 5- DISPLAY RISULTATI
    render_results(df_allevatori, df_conferitori, df_biomasse, df_co2_evitate, df_impianto, df_impianto_scarichi, df_digestato_allevatori, digestato_liq_altri_conf, digestato_sep_altri_conf, co2_trasporti, residuo_sep, residuo_liq, co2_dig_altri_conf)
