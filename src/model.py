import sys
from math import ceil, floor, exp, log
import sqlite3
import pandas as pd
import os

# Calcola il percorso assoluto del file corrente
current_dir = os.path.dirname(os.path.abspath(__file__))
# Torna su di 2 livelli: dashboard/pages -> dashboard -> progetto root
project_root = os.path.abspath(os.path.join(current_dir, '../..'))
# Percorso completo al database
db = os.path.join(project_root, 'data.db')

# ============================================================================
# CO2eq da biomasse con ipotesi deposito lineare
# ============================================================================

# # Funzioni per il calcolo delle emissioni di CO2eq cumulate ad un certo giorno
# def co2_liquame(giorni, deposito):
#     n2o = giorni / 500
#     ch4 = exp(0.6164 * log(giorni) + 0.4517)
#     co2 = (n2o * 265 + ch4 * 28) / 1000 # kg co2eq per kg biomassa
#     return (deposito * 1000) * co2 # deposito è in ton, trasformo in kg così ottengo kg CO2eq

# def co2_letame(giorni, deposito):
#     n2o = giorni / 272.727
#     ch4 = exp(0.6142 * log(giorni) - 3.008)
#     co2 = (n2o * 265 + ch4 * 28) / 1000  # kg CO2eq per kg biomassa
#     return (deposito * 1000) * co2 # deposito è in ton, trasformo in kg così ottengo kg CO2eq


# # CO2eq LETAME E LIQUAME
# def co2eq_liquame(allevatore):

#     #####
#     # CALCOLO CO2 EMESSA
#     ####

#     liquame_tot_annuo = allevatore.prod_liquame * allevatore.uba_liquame # ton
#     deposito_liq = (allevatore.prod_liquame * allevatore.uba_liquame / 365) * allevatore.frequenza_conferimento_liq # ton
#     prod_liquame_giorno = (allevatore.prod_liquame / 365) * allevatore.uba_liquame # ton/giorno - produzione di biomassa in kg al giorno

#     # Quanti svuotamenti?
#     n_svuotamenti = floor(365 / allevatore.frequenza_conferimento_liq)

#     # Emissioni di CO2eq cumulate al momento dello svuotamento 
#     co2eq_liq_cum = 0
#     for i in range (1, allevatore.frequenza_conferimento_liq + 1):
#         co2eq_liq = co2_liquame(i, prod_liquame_giorno)
#         co2eq_liq_cum = co2eq_liq_cum + co2eq_liq # kg co2 per kg di liquame

#     # Poi potrebbero rimanere dei giorni verso la fine dell'anno in cui c'è ancora accumulo ma senza arrivare ad uno svuotamento:
#     giorni_residui = 365 - (n_svuotamenti * allevatore.frequenza_conferimento_liq)
#     co2eq_liq_res = 0
#     for i in range (1, giorni_residui + 1):
#         co2eq_liq = co2_liquame(i, prod_liquame_giorno)
#         co2eq_liq_res = co2eq_liq_res + co2eq_liq # kg co2 per kg di liquame
    
#     ####
#     # CALCOLO CO2 RIFERIMENTO A 180 GIORNI
#     ####

#     co2eq_ref = co2_liquame(180, deposito_liq)
#     co2eq_ref_res = co2_liquame(180, giorni_residui*allevatore.prod_liquame)
    
#     ####
#     # CALCOLO CO2 EVITATA
#     ####

#     co2eq_liq_evitata = (co2eq_liq_cum - co2eq_ref) * n_svuotamenti + (co2eq_liq_res - co2eq_ref_res)

    
    
#     return co2eq_liq_evitata, n_svuotamenti, deposito_liq, liquame_tot_annuo

# def co2eq_letame(allevatore):

#     #####
#     # CALCOLO CO2 EMESSA
#     ####

#     letame_tot_annuo = allevatore.prod_letame * allevatore.uba_letame # ton
#     deposito_let = (allevatore.prod_letame * allevatore.uba_letame / 365) * allevatore.frequenza_conferimento_let # mc
#     prod_letame_giorno = (allevatore.prod_letame / 365) * allevatore.uba_letame # ton/giorno - produzione di biomassa in kg al giorno

#     # Quanti svuotamenti?
#     n_svuotamenti = floor(365 / allevatore.frequenza_conferimento_let)

#     # Emissioni di CO2eq cumulate al momento dello svuotamento 
#     co2eq_let_cum = 0
#     for i in range (1, allevatore.frequenza_conferimento_let + 1):
#         co2eq_let = co2_letame(i, prod_letame_giorno)
#         co2eq_let_cum = co2eq_let_cum + co2eq_let # kg co2 per kg di letame

#     # Poi potrebbero rimanere dei giorni verso la fine dell'anno in cui c'è ancora accumulo ma senza arrivare ad uno svuotamento:
#     giorni_residui = 365 - (n_svuotamenti * allevatore.frequenza_conferimento_let)
#     co2eq_let_res = 0
#     for i in range (1, giorni_residui + 1):
#         co2eq_let = co2_letame(i, prod_letame_giorno)
#         co2eq_let_res = co2eq_let_res + co2eq_let # kg co2 per kg di letame

#     ####
#     # CALCOLO CO2 RIFERIMENTO A 180 GIORNI
#     ####

#     co2eq_ref = co2_letame(180, deposito_let)
#     co2eq_ref_res = co2_letame(180, giorni_residui*allevatore.prod_letame)

#     ####
#     # CALCOLO CO2 EVITATA
#     ####

#     co2eq_let_evitata = (co2eq_let_cum - co2eq_ref) * n_svuotamenti + (co2eq_let_res - co2eq_ref_res)

#     if allevatore.id_allevatore == 1:
#         print(f"co2eq_let_evitata: {co2eq_let_evitata} kg")
#         print(f"co2eq_ref: {co2eq_ref} kg")
    
#     return co2eq_let_evitata, n_svuotamenti, deposito_let, letame_tot_annuo

# # ============================================================================
# # CO2eq da biomasse con ipotesi deposito costante
# # ============================================================================

# # CO2eq LIQUAME
# from math import exp, log, floor

# def co2eq_liquame_ipotesi2(allevatore):
#     """
#     Calcola la CO2 equivalente evitata dal conferimento periodico dei letame.
    
#     Ritorna:
#         co2eq_liq_evitata: CO2eq evitata (kg)
#         n_svuotamenti: numero di svuotamenti annui
#         deposito_liq: volume massimo di liquame accumulato per ciclo (mc)
#         liquame_tot_annuo: volume totale annuo di liquame prodotto (mc)
#     """

#     # Volume totale e deposito massimo
#     liquame_tot_annuo = allevatore.prod_liquame * allevatore.uba_liquame  # ton/anno
#     deposito_liq = (liquame_tot_annuo / 365) * allevatore.frequenza_conferimento_liq  # ton
#     n_svuotamenti = floor(365 / allevatore.frequenza_conferimento_liq)

#     # Emissioni per un ciclo di accumulo liquami
#     co2eq = co2_liquame(allevatore.frequenza_conferimento_liq, deposito_liq)
#     co2eq_ref = co2_liquame(180, deposito_liq)  # riferimento senza impianto

#     # Giorni residui a fine anno
#     giorni_residui = 365 - n_svuotamenti * allevatore.frequenza_conferimento_liq
#     deposito_residuo = (liquame_tot_annuo / 365) * giorni_residui
#     co2eq_res = co2_liquame(giorni_residui, deposito_residuo)
#     co2eq_res_ref = co2_liquame(180, deposito_residuo)  # riferimento residuo

#     # CO2eq evitata totale
#     co2eq_liq_evitata = (co2eq - co2eq_ref) * n_svuotamenti + (co2eq_res - co2eq_res_ref)

#     # stampa
#     print(f"co2eq_liq_evitata: {co2eq_liq_evitata} kg")


#     return co2eq_liq_evitata, n_svuotamenti, deposito_liq, liquame_tot_annuo


# def co2eq_letame_ipotesi2(allevatore):
#     """
#     Calcola la CO2 equivalente evitata dal conferimento periodico dei liquami.
    
#     Ritorna:
#         co2eq_liq_evitata: CO2eq evitata (kg)
#         n_svuotamenti: numero di svuotamenti annui
#         deposito_liq: volume massimo di letame accumulato per ciclo (mc)
#         letame_tot_annuo: volume totale annuo di letame prodotto (mc)
#     """

#     def emissioni_letame(giorni, deposito):
#         """
#         Calcola CO2eq per un accumulo di letame.
        
#         Parametri:
#         - giorni   : giorni di accumulo
#         - deposito : tonnellate di biomassa presenti
        
#         Ritorna:
#         - kg di CO2eq
#         """
#         n2o = giorni / 272.727
#         ch4 = exp(0.6142 * log(giorni) - 3.008)
#         co2 = (n2o * allevatore.GWP_N2O + ch4 * allevatore.GWP_CH4) / 1000  # kg CO2eq per kg biomassa
#         return (deposito * 1000) * co2 # deposito è in ton, trasformo in kg così ottengo kg CO2eq


#     # Volume totale e deposito massimo
#     letame_tot_annuo = allevatore.prod_letame * allevatore.uba_letame  # mc/anno
#     deposito_let = (letame_tot_annuo / 365) * allevatore.frequenza_conferimento_let  # mc per ciclo
#     n_svuotamenti = floor(365 / allevatore.frequenza_conferimento_let)

#     # Emissioni per ciclo
#     co2eq = emissioni_letame(allevatore.frequenza_conferimento_let, deposito_let)
#     co2eq_ref = emissioni_letame(180, deposito_let)  # riferimento senza impianto

#     # Giorni residui a fine anno
#     giorni_residui = 365 - n_svuotamenti * allevatore.frequenza_conferimento_let
#     deposito_residuo = (letame_tot_annuo / 365) * giorni_residui
#     co2eq_res = emissioni_letame(giorni_residui, deposito_residuo)
#     co2eq_res_ref = emissioni_letame(180, deposito_residuo) # riferimento residuo

#     # CO2eq evitata totale
#     co2eq_let_evitata = (co2eq - co2eq_ref) * n_svuotamenti + (co2eq_res - co2eq_res_ref)
#     print(f"co2eq_let_evitata: {co2eq_let_evitata} kg")

#     return co2eq_let_evitata, n_svuotamenti, deposito_let, letame_tot_annuo

def co2eq_simplified(durata_deposito, m, alfa, beta, GWP_N2O = 265, GWP_CH4 = 28):
    n2o = m * durata_deposito # g per kg biomassa 
    ch4 = alfa * durata_deposito ** beta # g per kg biomassa 
    co2eq = (n2o * GWP_N2O + ch4 * GWP_CH4) # g per kg biomassa 

    return co2eq

def co2_letame_semplificata(allevatore):

    """
    return

    co2eq_evitata_anno: kg CO2 evitata (-)
    n_svuotamenti: numero di volte che il deposito viene svuotato in un anno
    deposito_let: quantità contenuta nel deposito al momento dello svuotamento
    letame_tot_annuo: quantità di biomassa prodotta in un anno

    """

    letame_tot_annuo = allevatore.prod_letame * allevatore.uba_letame # ton
    deposito_let = (allevatore.prod_letame * allevatore.uba_letame / 365) * allevatore.frequenza_conferimento_let # ton
    prod_letame_giorno = (allevatore.prod_letame / 365) * allevatore.uba_letame # ton/giorno
    n_svuotamenti = floor(365 / allevatore.frequenza_conferimento_let)

    letame_st = 0.214
    m = 0.0036
    alfa = 0.04939
    beta = 0.6142

    n2o = m * allevatore.frequenza_conferimento_let # g per kg di solido totale
    ch4 = alfa * allevatore.frequenza_conferimento_let ** beta # g per kg di solido totale

    co2eq = co2eq_simplified(allevatore.frequenza_conferimento_let, m, alfa, beta)
    co2eq_ref = co2eq_simplified(180, m, alfa, beta)
    
    co2eq = co2eq * ( ( prod_letame_giorno * 1000 ) * allevatore.frequenza_conferimento_let) * letame_st / 1000 # g/kg * (( ton/giorno * 1000 ) * giorni) * perc_sostanza_secca
    co2eq_ref = co2eq_ref * ( ( prod_letame_giorno * 1000 ) * allevatore.frequenza_conferimento_let) * letame_st / 1000 # g/kg * (( ton/giorno * 1000 ) * giorni) * perc_sostanza_secca

    # Giorni residui a fine anno
    giorni_residui = 365 - n_svuotamenti * allevatore.frequenza_conferimento_let
    deposito_residuo = (letame_tot_annuo / 365) * giorni_residui

    co2eq_res = co2eq_simplified(giorni_residui, m, alfa, beta)
    co2eq_res_ref = co2eq_simplified(180, m, alfa, beta)

    co2eq_res = co2eq_res * ( ( prod_letame_giorno * 1000 ) * giorni_residui) * letame_st / 1000 # g/kg * (( ton/giorno / 1000 ) * giorni) * perc_sostanza_secca
    co2eq_res_ref = co2eq_res_ref * ( ( prod_letame_giorno * 1000 ) * giorni_residui) * letame_st / 1000 # g/kg * (( ton/giorno / 1000 ) * giorni) * perc_sostanza_secca

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

    liquame_tot_annuo = allevatore.prod_liquame * allevatore.uba_liquame # ton
    deposito_liq = (allevatore.prod_liquame * allevatore.uba_liquame / 365) * allevatore.frequenza_conferimento_liq # ton
    prod_liquame_giorno = (allevatore.prod_liquame / 365) * allevatore.uba_liquame # ton/giorno
    n_svuotamenti = floor(365 / allevatore.frequenza_conferimento_liq)

    liquame_st = 0.073
    m = 0.00192
    alfa = 1.57095
    beta = 0.61641

    co2eq = co2eq_simplified(allevatore.frequenza_conferimento_liq, m, alfa, beta)
    co2eq_ref = co2eq_simplified(180, m, alfa, beta)
    co2eq = co2eq * ( ( prod_liquame_giorno * 1000 ) * allevatore.frequenza_conferimento_liq) * liquame_st / 1000 # g/kg * (( ton/giorno * 1000 ) * giorni) * perc_sostanza_secca / 1000
    co2eq_ref = co2eq_ref * ( ( prod_liquame_giorno * 1000 ) * allevatore.frequenza_conferimento_liq) * liquame_st / 1000 # g/kg * (( ton/giorno * 1000 ) * giorni) * perc_sostanza_secca / 1000

    # Giorni residui a fine anno
    giorni_residui = 365 - n_svuotamenti * allevatore.frequenza_conferimento_liq
    deposito_residuo = (liquame_tot_annuo / 365) * giorni_residui

    co2eq_res = co2eq_simplified(giorni_residui, m, alfa, beta)
    co2eq_res_ref = co2eq_simplified(180, m, alfa, beta)

    co2eq_res = co2eq_res * ( ( prod_liquame_giorno * 1000 ) * giorni_residui) * liquame_st / 1000 # g/kg * (( ton/giorno * 1000 ) * giorni) * perc_sostanza_secca / 1000 --> kg CO2
    co2eq_res_ref = co2eq_res_ref * ( ( prod_liquame_giorno * 1000 ) * giorni_residui) * liquame_st / 1000 # g/kg * (( ton/giorno * 1000 ) * giorni) * perc_sostanza_secca / 1000 --> kg CO2

    # CO2 evitata
    co2eq_evitata_anno = (co2eq - co2eq_ref) * n_svuotamenti + (co2eq_res - co2eq_res_ref)

    return co2eq_evitata_anno, n_svuotamenti, deposito_liq, liquame_tot_annuo


# CO2eq NETTA POLLINA
def co2eq_pollina(ton, ef):
    co2eq = ton * ef # ton x kgCO2/ton
    return co2eq

# CO2eq NETTA SOTTOPRODOTTI
def co2eq_sottoprodotti():
    return 0

# CO2eq NETTA COLTURE
def co2eq_colture(ton, ef):
    co2eq = ton * ef # ton x kgCO2/ton
    return co2eq


# CO2eq DIGESTATO (ton Sostanza Secca)
def co2eq_digestato(impianto, Q_in, EF, db_path):
    
    # ---- PARAMETRI MODELLO ----
    perc_digestato = 0.95      # resa massa digestato
    perc_liq_sep = 0.80        # quota liquida dopo separazione
    perc_sol_sep = 0.20        # quota solida dopo separazione
    ss_digestato = 0.052    # 5.2% sostanza secca
    ss_solido = 0.20        # 20% sostanza secca frazione solida
    
    # ---- DIGESTATO TOTALE PRODOTTO ----
    Q_digestato_tot = Q_in * perc_digestato
    
    if impianto.separazione > 0:
        
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
    # Energia elettrica (CONTRIBUTO NEGATIVO)
    co2eq_ee_bt_prod = impianto.energia['prodotta']['EE_BT'] * EF.EE_BT
    co2eq_ee_mt_prod = impianto.energia['prodotta']['EE_MT'] * EF.EE_MT
    co2eq_ee_auto = impianto.energia['autoconsumata']['EE'] * EF.EE_BT

    componenti_ee_bt = componenti_co2('EE_BT', co2eq_ee_bt_prod, db)
    componenti_ee_mt = componenti_co2('EE_MT', co2eq_ee_mt_prod, db)
    componenti_ee_auto = componenti_co2('EE_BT', co2eq_ee_auto, db)
    co2eq_ee_netta = co2eq_ee_bt_prod + co2eq_ee_mt_prod - co2eq_ee_auto # kg CO2eq
    
    return - (componenti_ee_bt + componenti_ee_mt - componenti_ee_auto) # kg CO2eq

def co2eq_calore_netta(impianto, EF, db):
    # Calore (CONTRIBUTO NEGATIVO)
    co2eq_calore_prod = impianto.energia['prodotta']['calore'] * EF.calore
    co2eq_calore_auto = impianto.energia['autoconsumata']['calore'] * EF.calore
    co2eq_calore_netta = co2eq_calore_prod - co2eq_calore_auto # kg CO2eq

    return - componenti_co2('calore', co2eq_calore_netta, db) # kg CO2eq

def co2eq_biometano(impianto, EF, db):
    # Biometano (CONTRIBUTO NEGATIVO)
    co2eq_biomet_prod = impianto.energia['prodotta']['biometano'] * EF.metano
    co2eq_biomet_auto = impianto.energia['autoconsumata']['biometano'] * EF.metano
    co2eq_biomet_netta = co2eq_biomet_prod - co2eq_biomet_auto # kg CO2eq

    return - componenti_co2('metano', co2eq_biomet_netta, db) # kg CO2eq

def co2eq_biolng(impianto, EF, db):
    # BioLNG (CONTRIBUTO NEGATIVO)
    co2eq_biolng_prod = impianto.energia['prodotta']['bioLNG'] * EF.LNG
    co2eq_biolng_auto = impianto.energia['autoconsumata']['bioLNG'] * EF.LNG
    co2eq_biolng_netta = co2eq_biolng_prod - co2eq_biolng_auto # kg CO2eq

    return - componenti_co2('LNG', co2eq_biolng_netta, db) # kg CO2eq

def co2eq_biogenica(impianto, EF, db):
    # CO2 Biogenica (CONTRIBUTO NEGATIVO)
    co2eq_biogenica_prod = impianto.energia['prodotta']['CO2_biogenica'] * EF.CO2_biogenica # kg CO2eq

    return - componenti_co2('CO2_biogenica', co2eq_biogenica_prod, db) # kg CO2eq

def co2eq_ee_acquistata(impianto, EF, db):
    # ENERGIA ACQUISTATA (CONTRIBUTO POSITIVO)
    co2eq_ee_bt_acq = impianto.energia['acquistata']['EE_BT'] * EF.EE_BT # kg CO2eq
    co2eq_ee_mt_acq = impianto.energia['acquistata']['EE_MT'] * EF.EE_MT # kg CO2eq

    componenti_ee_bt = componenti_co2('EE_BT', co2eq_ee_bt_acq, db)
    componenti_ee_mt = componenti_co2('EE_MT', co2eq_ee_mt_acq, db)

    return componenti_ee_bt + componenti_ee_mt

def co2eq_metano_acq(impianto, EF, db):
    # METANO ACQUISTATO (CONTRIBUTO POSITIVO)
    co2eq_met_acq = impianto.energia['acquistata']['metano'] * EF.metano # kg CO2eq

    return componenti_co2('metano', co2eq_met_acq, db)

def co2eq_lng_acq(impianto, EF, db):
    # LNG ACQUISTATO (CONTRIBUTO POSITIVO)
    co2eq_lng_acq = impianto.energia['acquistata']['LNG'] * EF.LNG # kg CO2eq

    return componenti_co2('LNG', co2eq_lng_acq, db)

# ============================================================================
# CO2eq da trasporti
# ============================================================================

# CO2eq TRASPORTO (VALIDO PER BIOMASSA, DIGESTATO, BIOLNG, ECC...)
def co2eq_trasporto(trasporto, ton_carico, densita_carico, distanza):

    """
    return

    co2eq_trasporto: kg CO2 emessa per il trasporto (+)
    n_viaggi: numero viaggi necessari per fare uno svuotamento completo del deposito

    """

    mc_carico = ton_carico / densita_carico

    n_viaggi_pieno_carico = floor(mc_carico / trasporto.capacita_max)
    n_viaggi = n_viaggi_pieno_carico + 1 # viaggi solo andata da allevatore a impianto

    massa_pieno_carico = trasporto.capacita_max * densita_carico # ton
    massa_viaggio_carico_parziale = ton_carico - (n_viaggi_pieno_carico * massa_pieno_carico)

    co2eq_trasporto = trasporto.EF * distanza * (n_viaggi_pieno_carico * massa_pieno_carico + 1 * massa_viaggio_carico_parziale)

    return co2eq_trasporto, n_viaggi

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
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute(query, (nome,))
        row = cursor.fetchone()
        conn.close()

        if row is None:
            return None  # nome non trovato

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
        return None
