from math import floor
from contextlib import closing
import sqlite3
import os

import pandas as pd

import config

# Calcola il percorso assoluto del file corrente
current_dir = os.path.dirname(os.path.abspath(__file__))
# Torna su di 2 livelli: dashboard/pages -> dashboard -> progetto root
project_root = os.path.abspath(os.path.join(current_dir, '../..'))
# Percorso completo al database
db = os.path.join(project_root, 'data.db')

# ============================================================================
# CO2eq da biomasse con ipotesi di deposito (modello semplificato)
# ============================================================================

def co2eq_simplified(durata_deposito, m, alfa, beta, GWP_N2O=config.GWP_N2O, GWP_CH4=config.GWP_CH4):
    n2o = m * durata_deposito          # g per kg biomassa
    ch4 = alfa * durata_deposito ** beta  # g per kg biomassa
    co2eq = (n2o * GWP_N2O + ch4 * GWP_CH4)  # g per kg biomassa

    return co2eq

def co2_letame_semplificata(allevatore):
    """
    return

    co2eq_evitata_anno: kg CO2 evitata (-)
    n_svuotamenti: numero di volte che il deposito viene svuotato in un anno
    deposito_let: quantità contenuta nel deposito al momento dello svuotamento
    letame_tot_annuo: quantità di biomassa prodotta in un anno
    """

    letame_tot_annuo = allevatore.prod_letame * allevatore.uba_letame  # ton
    deposito_let = (allevatore.prod_letame * allevatore.uba_letame / config.GIORNI_ANNO) * allevatore.frequenza_conferimento_let  # ton
    prod_letame_giorno = (allevatore.prod_letame / config.GIORNI_ANNO) * allevatore.uba_letame  # ton/giorno
    n_svuotamenti = floor(config.GIORNI_ANNO / allevatore.frequenza_conferimento_let)

    st = config.LETAME["st"]
    m = config.LETAME["m"]
    alfa = config.LETAME["alfa"]
    beta = config.LETAME["beta"]

    co2eq = co2eq_simplified(allevatore.frequenza_conferimento_let, m, alfa, beta)
    co2eq_ref = co2eq_simplified(config.GIORNI_RIFERIMENTO, m, alfa, beta)

    co2eq = co2eq * ((prod_letame_giorno * 1000) * allevatore.frequenza_conferimento_let) * st / 1000          # g/kg * ((ton/giorno * 1000) * giorni) * perc_sostanza_secca
    co2eq_ref = co2eq_ref * ((prod_letame_giorno * 1000) * allevatore.frequenza_conferimento_let) * st / 1000  # g/kg * ((ton/giorno * 1000) * giorni) * perc_sostanza_secca

    # Giorni residui a fine anno
    giorni_residui = config.GIORNI_ANNO - n_svuotamenti * allevatore.frequenza_conferimento_let

    co2eq_res = co2eq_simplified(giorni_residui, m, alfa, beta)
    co2eq_res_ref = co2eq_simplified(config.GIORNI_RIFERIMENTO, m, alfa, beta)

    co2eq_res = co2eq_res * ((prod_letame_giorno * 1000) * giorni_residui) * st / 1000
    co2eq_res_ref = co2eq_res_ref * ((prod_letame_giorno * 1000) * giorni_residui) * st / 1000

    # CO2 evitata
    co2eq_evitata_anno = (co2eq - co2eq_ref) * n_svuotamenti + (co2eq_res - co2eq_res_ref)

    return co2eq_evitata_anno, n_svuotamenti, deposito_let, letame_tot_annuo

def co2_liquame_semplificata(allevatore):
    """
    return

    co2eq_evitata_anno: kg CO2 evitata (-)
    n_svuotamenti: numero di volte che il deposito viene svuotato in un anno
    deposito_liq: quantità contenuta nel deposito al momento dello svuotamento
    liquame_tot_annuo: quantità di biomassa prodotta in un anno
    """

    liquame_tot_annuo = allevatore.prod_liquame * allevatore.uba_liquame  # ton
    deposito_liq = (allevatore.prod_liquame * allevatore.uba_liquame / config.GIORNI_ANNO) * allevatore.frequenza_conferimento_liq  # ton
    prod_liquame_giorno = (allevatore.prod_liquame / config.GIORNI_ANNO) * allevatore.uba_liquame  # ton/giorno
    n_svuotamenti = floor(config.GIORNI_ANNO / allevatore.frequenza_conferimento_liq)

    st = config.LIQUAME["st"]
    m = config.LIQUAME["m"]
    alfa = config.LIQUAME["alfa"]
    beta = config.LIQUAME["beta"]

    co2eq = co2eq_simplified(allevatore.frequenza_conferimento_liq, m, alfa, beta)
    co2eq_ref = co2eq_simplified(config.GIORNI_RIFERIMENTO, m, alfa, beta)
    co2eq = co2eq * ((prod_liquame_giorno * 1000) * allevatore.frequenza_conferimento_liq) * st / 1000
    co2eq_ref = co2eq_ref * ((prod_liquame_giorno * 1000) * allevatore.frequenza_conferimento_liq) * st / 1000

    # Giorni residui a fine anno
    giorni_residui = config.GIORNI_ANNO - n_svuotamenti * allevatore.frequenza_conferimento_liq

    co2eq_res = co2eq_simplified(giorni_residui, m, alfa, beta)
    co2eq_res_ref = co2eq_simplified(config.GIORNI_RIFERIMENTO, m, alfa, beta)

    co2eq_res = co2eq_res * ((prod_liquame_giorno * 1000) * giorni_residui) * st / 1000
    co2eq_res_ref = co2eq_res_ref * ((prod_liquame_giorno * 1000) * giorni_residui) * st / 1000

    # CO2 evitata
    co2eq_evitata_anno = (co2eq - co2eq_ref) * n_svuotamenti + (co2eq_res - co2eq_res_ref)

    return co2eq_evitata_anno, n_svuotamenti, deposito_liq, liquame_tot_annuo


# CO2eq NETTA POLLINA
def co2eq_pollina(ton, ef):
    co2eq = ton * ef  # ton x kgCO2/ton
    return co2eq

# CO2eq NETTA SOTTOPRODOTTI
def co2eq_sottoprodotti():
    return 0

# CO2eq NETTA COLTURE
def co2eq_colture(ton, ef):
    co2eq = ton * ef  # ton x kgCO2/ton
    return co2eq


# CO2eq DIGESTATO (ton Sostanza Secca)
def co2eq_digestato(impianto, Q_in, EF, db_path):

    # ---- PARAMETRI MODELLO ----
    perc_digestato = config.DIGESTATO["perc_digestato"]  # resa massa digestato
    perc_liq_sep = config.DIGESTATO["perc_liq_sep"]      # quota liquida dopo separazione
    perc_sol_sep = config.DIGESTATO["perc_sol_sep"]      # quota solida dopo separazione
    ss_digestato = config.DIGESTATO["ss_digestato"]      # sostanza secca digestato
    ss_solido = config.DIGESTATO["ss_solido"]            # sostanza secca frazione solida

    # ---- DIGESTATO TOTALE PRODOTTO ----
    Q_digestato_tot = Q_in * perc_digestato

    if impianto.separazione and impianto.separazione > 0:

        # quota inviata a separazione (es. 0.5)
        perc_sep = impianto.separazione

        Q_sep = Q_digestato_tot * perc_sep
        Q_non_sep = Q_digestato_tot * (1 - perc_sep)

        # prodotti della separazione
        Q_liq_sep = Q_sep * perc_liq_sep
        Q_sol_sep = Q_sep * perc_sol_sep

        # digestato liquido totale = liquido separato + non separato
        digestato_liq = Q_liq_sep + Q_non_sep
        digestato_sol = Q_sol_sep

        # CO2eq calcolata su tonnellate di sostanza secca
        SS_tot = (digestato_liq * ss_digestato) + (digestato_sol * ss_solido)
        co2eq_dig = SS_tot * EF.digestato

    else:
        # nessuna separazione
        digestato_sol = 0
        digestato_liq = Q_digestato_tot

        SS_tot = digestato_liq * ss_digestato
        co2eq_dig = SS_tot * EF.digestato

    componenti = componenti_co2("digestato", co2eq_dig, db_path)

    return digestato_sol, digestato_liq, componenti

# ============================================================================
# CO2eq da bilancio energetico impianto
# ============================================================================

def co2eq_ee_prod_netta(impianto, EF, db):
    ee_bt = impianto.energia['prodotta'].get('EE_BT', 0)
    ee_mt = impianto.energia['prodotta'].get('EE_MT', 0)
    ee_auto = impianto.energia['autoconsumata'].get('EE', 0)

    # CO2 evitata: energia ceduta alla rete (CONTRIBUTO NEGATIVO)
    componenti_ee_bt   = componenti_co2('EE_BT',  ee_bt  * EF.EE_BT,  db)
    componenti_ee_mt   = componenti_co2('EE_MT',  ee_mt  * EF.EE_MT,  db)
    componenti_ee_auto = componenti_co2('EE_BT',  ee_auto * EF.EE_BT, db)

    # Emissioni proprie del cogeneratore (CONTRIBUTO POSITIVO)
    componenti_cogen_bt = componenti_co2('cogen_EE_BT', ee_bt * EF.cogen_EE_BT, db)
    componenti_cogen_mt = componenti_co2('cogen_EE_MT', ee_mt * EF.cogen_EE_MT, db)

    return (
        - (componenti_ee_bt + componenti_ee_mt - componenti_ee_auto)
        + componenti_cogen_bt + componenti_cogen_mt
    )

def co2eq_calore_netta(impianto, EF, db):
    # Calore (CONTRIBUTO NEGATIVO)
    co2eq_calore_prod = impianto.energia['prodotta'].get('calore', 0) * EF.calore
    co2eq_calore_auto = impianto.energia['autoconsumata'].get('calore', 0) * EF.calore
    co2eq_calore_netta = co2eq_calore_prod - co2eq_calore_auto  # kg CO2eq

    return - componenti_co2('calore', co2eq_calore_netta, db)  # kg CO2eq

def co2eq_biometano(impianto, EF, db):
    # Biometano (CONTRIBUTO NEGATIVO)
    co2eq_biomet_prod = impianto.energia['prodotta'].get('biometano', 0) * EF.metano
    co2eq_biomet_auto = impianto.energia['autoconsumata'].get('biometano', 0) * EF.metano
    co2eq_biomet_netta = co2eq_biomet_prod - co2eq_biomet_auto  # kg CO2eq

    return - componenti_co2('metano', co2eq_biomet_netta, db)  # kg CO2eq

def co2eq_biolng(impianto, EF, db):
    # BioLNG (CONTRIBUTO NEGATIVO)
    co2eq_biolng_prod = impianto.energia['prodotta'].get('bioLNG', 0) * EF.LNG
    co2eq_biolng_auto = impianto.energia['autoconsumata'].get('bioLNG', 0) * EF.LNG
    co2eq_biolng_netta = co2eq_biolng_prod - co2eq_biolng_auto  # kg CO2eq

    return - componenti_co2('LNG', co2eq_biolng_netta, db)  # kg CO2eq

def co2eq_biogenica(impianto, EF, db):
    # CO2 Biogenica (CONTRIBUTO NEGATIVO)
    co2eq_biogenica_prod = impianto.energia['prodotta'].get('CO2_biogenica', 0) * EF.CO2_biogenica  # kg CO2eq

    return - componenti_co2('CO2_biogenica', co2eq_biogenica_prod, db)  # kg CO2eq

def co2eq_ee_acquistata(impianto, EF, db):
    # ENERGIA ACQUISTATA (CONTRIBUTO POSITIVO)
    co2eq_ee_bt_acq = impianto.energia['acquistata'].get('EE_BT', 0) * EF.EE_BT  # kg CO2eq
    co2eq_ee_mt_acq = impianto.energia['acquistata'].get('EE_MT', 0) * EF.EE_MT  # kg CO2eq

    componenti_ee_bt = componenti_co2('EE_BT', co2eq_ee_bt_acq, db)
    componenti_ee_mt = componenti_co2('EE_MT', co2eq_ee_mt_acq, db)

    return componenti_ee_bt + componenti_ee_mt

def co2eq_metano_acq(impianto, EF, db):
    # METANO ACQUISTATO (CONTRIBUTO POSITIVO)
    co2eq_met_acq = impianto.energia['acquistata'].get('metano', 0) * EF.metano  # kg CO2eq

    return componenti_co2('metano', co2eq_met_acq, db)

def co2eq_lng_acq(impianto, EF, db):
    # LNG ACQUISTATO (CONTRIBUTO POSITIVO)
    co2eq_lng_acq = impianto.energia['acquistata'].get('LNG', 0) * EF.LNG  # kg CO2eq

    return componenti_co2('LNG', co2eq_lng_acq, db)

# ============================================================================
# CO2eq da trasporti
# ============================================================================

# CO2eq TRASPORTO (VALIDO PER BIOMASSA, DIGESTATO, BIOLNG, ECC...)
def co2eq_trasporto(trasporto, ton_carico, distanza):
    """
    CO2 emessa per il trasporto: EF × ton × km

    return: kg CO2eq emessa (+)
    """
    return trasporto.EF * ton_carico * distanza

# ============================================================================
# CO2eq per funzionamento impianto
# ============================================================================
def co2eq_impianto(impianto, EF, db):
    """
    Calcola le componenti di CO2 per rifiuti, olio lubrificante, acqua e scarichi.
    Restituisce un DataFrame con una riga per ciascuna voce e le colonne:
    nome, co2_fossile, co2_biogenica, co2_dluc, co2_tot.
    """
    # Calcolo dei totali di CO2 per ogni tipologia
    CO2_tot_rifiuti = impianto.rifiuti * EF.rifiuti_recupero
    CO2_tot_olio = impianto.olio_lubrificante * EF.olio_lubrificante
    CO2_tot_acqua = impianto.acqua * EF.acqua
    CO2_tot_scarichi = impianto.scarichi * EF.scarichi

    # Ottenimento delle componenti
    comp_rifiuti = componenti_co2("rifiuti_recupero", CO2_tot_rifiuti, db)
    comp_olio = componenti_co2("olio_lubrificante", CO2_tot_olio, db)
    comp_acqua = componenti_co2("acqua", CO2_tot_acqua, db)
    comp_scarichi = componenti_co2("scarichi", CO2_tot_scarichi, db)

    # Creazione del DataFrame
    df = pd.DataFrame([
        {'nome': 'Rifiuti', **comp_rifiuti.to_dict()},
        {'nome': 'Olio lubrificante', **comp_olio.to_dict()},
        {'nome': 'Acqua', **comp_acqua.to_dict()},
        {'nome': 'Scarichi', **comp_scarichi.to_dict()}
    ])

    # Riordino colonne
    df = df[['nome', 'co2_fossile', 'co2_biogenica', 'co2_dluc', 'co2_tot']]
    return df

# ============================================================================
# CALCOLO COMPONENTI EMISSIONI CO2
# ============================================================================
def componenti_co2(nome, co2_tot, db_path):

    query = """
        SELECT CO2_fossile, CO2_biogenica, CO2_dLUC, CO2_TOT
        FROM fattori_emissione
        WHERE nome = ?
        LIMIT 1;
    """

    try:
        with closing(sqlite3.connect(db_path)) as conn:
            row = conn.execute(query, (nome,)).fetchone()

        if row is None:
            return pd.Series({"co2_fossile": 0, "co2_biogenica": 0, "co2_dluc": 0, "co2_tot": co2_tot})

        co2_fossile_db, co2_biogenica_db, co2_dluc_db, co2_tot_db = row

        if co2_tot_db == 0:
            return pd.Series({
                "co2_fossile": 0,
                "co2_biogenica": 0,
                "co2_dluc": 0,
                "co2_tot": co2_tot
            })
        else:
            # Percentuali sul totale
            perc_fossile = co2_fossile_db / co2_tot_db
            perc_biogenica = co2_biogenica_db / co2_tot_db
            perc_dluc = co2_dluc_db / co2_tot_db

            # Ripartizione del CO2 totale dichiarato dall'utente
            co2_fossile = co2_tot * perc_fossile
            co2_biogenica = co2_tot * perc_biogenica
            co2_dluc = co2_tot * perc_dluc

            return pd.Series({
                "co2_fossile": co2_fossile,
                "co2_biogenica": co2_biogenica,
                "co2_dluc": co2_dluc,
                "co2_tot": co2_tot
            })

    except Exception as e:
        print(f"Errore DB: {e}")
        return pd.Series({"co2_fossile": 0, "co2_biogenica": 0, "co2_dluc": 0, "co2_tot": co2_tot})
