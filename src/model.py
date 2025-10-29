import sys
from math import ceil, floor, exp, log

# ============================================================================
# CO2eq da biomasse
# ============================================================================

# CO2eq LETAME E LIQUAME
def co2eq_let_liq(allevatore):

    # Volume max (mc) di reflui presenti nel deposito, da confrontare con la capacità max del deposito.
    # Se il volume di reflui eccede la capacita massima del deposito, aumentare la frequenza di svuotamento
    deposito_liq = (allevatore.prod_liquame * allevatore.uba_liquame / 365) * allevatore.frequenza_conferimento # mc
    deposito_let = (allevatore.prod_letame * allevatore.uba_letame / 365) * allevatore.frequenza_conferimento # mc

    if (deposito_liq + deposito_let) > allevatore.deposito_max:
            print(f"ATTENZIONE, il deposito di {allevatore.denominazione_sociale} non è sufficiente a contenere tutti i reflui! Aumenta la frequenza di svuotamento.")
            sys.exit()

    # Produzione di biomassa in kg al giorno
    prod_liquame_giorno = (allevatore.prod_liquame / 365 * 1000) * allevatore.uba_liquame # kg/giorno
    prod_letame_giorno = (allevatore.prod_letame / 365 * 700) * allevatore.uba_letame # kg/giorno

    # Funzione per il calcolo delle emissioni di CO2eq cumulate di 1 kg di letame e liquame ad un certo giorno.
    def co2eq_per_kg(giorno, GWP_n2o, GWP_ch4):
        n2o_let = giorno/272.727
        n2o_liq = giorno/500
        ch4_let = exp(0.6142 * log(giorno) - 3.008)
        ch4_liq = exp(0.6164 * log(giorno) + 0.4517) 
        co2eq_let = (n2o_let*GWP_n2o + ch4_let*GWP_ch4)/1000 # kg co2eq per kg biomassa
        co2eq_liq = (n2o_liq*GWP_n2o + ch4_liq*GWP_ch4)/1000 # kg co2eq per kg biomassa
        return co2eq_let, co2eq_liq

    # Emissioni di CO2eq cumulate al momento dello svuotamento 
    co2eq_let_cum = 0
    co2eq_liq_cum = 0
    for i in range (1, allevatore.frequenza_conferimento + 1):
        co2eq_let, co2eq_liq = co2eq_per_kg(i, allevatore.GWP_N2O, allevatore.GWP_CH4)
        co2eq_let_cum = co2eq_let_cum + co2eq_let # kg co2 per kg di letame
        co2eq_liq_cum = co2eq_liq_cum + co2eq_liq # kg co2 per kg di liquame
    co2eq_let_tot = co2eq_let_cum * prod_letame_giorno
    co2eq_liq_tot = co2eq_liq_cum * prod_liquame_giorno
    co2eq_tot = co2eq_let_tot + co2eq_liq_tot
    print(f"CO2eq cumulata su {allevatore.frequenza_conferimento} giorni: {co2eq_tot:.0f} kg")

    # Quanti svuotamenti?
    n_svuotamenti = floor(365 / allevatore.frequenza_conferimento)
    # Allora devo moltiplicare le emissioni calcolate prima per ogni ciclo di riempimento/svuotamento
    co2eq_let_tot = co2eq_let_tot * n_svuotamenti
    co2eq_liq_tot = co2eq_liq_tot * n_svuotamenti
    co2eq_tot = co2eq_tot * n_svuotamenti

    # Poi potrebbero rimanere dei giorni verso la fine dell'anno in cui c'è ancora accumulo ma senza arrivare ad uno svuotamento:
    giorni_residui = 365 - (n_svuotamenti * allevatore.frequenza_conferimento)
    co2eq_let_cum = 0
    co2eq_liq_cum = 0
    for i in range (1, giorni_residui + 1):
        co2eq_let, co2eq_liq = co2eq_per_kg(i, allevatore.GWP_N2O, allevatore.GWP_CH4)
        co2eq_let_cum = co2eq_let_cum + co2eq_let # kg co2 per kg di letame
        co2eq_liq_cum = co2eq_liq_cum + co2eq_liq # kg co2 per kg di liquame
    co2eq_let_tot = co2eq_let_tot + co2eq_let_cum * prod_letame_giorno
    co2eq_liq_tot = co2eq_liq_tot + co2eq_liq_cum * prod_liquame_giorno

    return co2eq_let_tot, co2eq_liq_tot, co2eq_tot, n_svuotamenti, deposito_liq, deposito_let

# CO2eq NETTA POLLINA
def co2eq_pollina(ton, ef):
    co2eq = ton * ef
    return co2eq

# CO2eq NETTA SOTTOPRODOTTI
def co2eq_sottoprodotti():
    return 0


# CO2eq DIGESTATO (ton Sostanza Secca)
def co2eq_digestato(impianto, tot_let, tot_liq):
    # Stima sostanza secca
    if impianto.separazione:
        digestato_liq = tot_liq * (1 - 0.90)
        digestato_sep = (tot_liq * 0.90) * (100 - 20) / 100
        # ! NON È CHIARO COME FUNZIONA QUI -- DA RIVEDERE
    else:
        digestato = 0.95 * tot_liq # ton
        co2eq = 0 # ! CORRETTO?
    return digestato, co2eq


# ============================================================================
# CO2eq da bilancio energetico impianto
# ============================================================================

def co2eq_netta_energia(impianto, ef):

    # Energia elettrica (CONTRIBUTO NEGATIVO "-EMISSIONI")
    co2eq_ee_prod = impianto.energia['prodotta']['EE_BT'] * EF.EE_BT + impianto.energia['prodotta']['EE_MT'] * EF.EE_MT
    co2eq_ee_auto = impianto.energia['autoconsumata']['EE'] * EF.EE_BT
    co2eq_ee_netta = co2eq_ee_prod - co2eq_ee_auto # kg CO2eq

    # Calore (CONTRIBUTO NEGATIVO)
    co2eq_calore_prod = impianto.energia['prodotta']['calore'] * EF.calore
    co2eq_calore_auto = impianto.energia['autoconsumata']['calore'] * EF.calore 
    co2eq_calore_netta = co2eq_calore_prod - co2eq_calore_auto # kg CO2eq

    # Biometano (CONTRIBUTO NEGATIVO)
    co2eq_biomet_prod = impianto.energia['prodotta']['metano'] * EF.metano
    co2eq_biomet_auto = impianto.energia['autoconsumata']['metano'] * EF.metano 
    co2eq_biomet_netta = co2eq_biomet_prod - co2eq_biomet_auto # kg CO2eq

    # BioLNG (CONTRIBUTO NEGATIVO)
    co2eq_biolng_prod = impianto.energia['prodotta']['biolng'] * EF.LNG
    co2eq_biolng_auto = impianto.energia['autoconsumata']['biolng'] * EF.LNG 
    co2eq_biolng_netta = co2eq_biolng_prod - co2eq_biolng_auto # kg CO2eq

    # CO2 Biogenica (CONTRIBUTO NEGATIVO)
    co2eq_biogenica_prod = impianto.energia['prodotta']['CO2_biogenica'] * EF.CO2_biogenica # kg CO2eq

    # ENERGIA ACQUISTATA (CONTRIBUTO POSITIVO "+EMISSIONI")
    co2eq_ee_acq = impianto.energia['acquistata']['EE_BT'] * EF.EE_BT + impianto.energia['acquistata']['EE_MT'] * EF.EE_MT # kg CO2eq

    # METANO ACQUISTATO (CONTRIBUTO POSITIVO)
    co2eq_met_acq = impianto.energia['acquistata']['metano'] * EF.metano # kg CO2eq

    # LNG ACQUISTATO (CONTRIBUTO POSITIVO)
    co2eq_lng_acq = impianto.energia['acquistata']['LNG'] * EF.LNG # kg CO2eq

    return co2eq_ee_netta, co2eq_calore_netta, co2eq_biomet_netta, co2eq_biolng_netta, co2eq_biogenica_prod, co2eq_ee_acq, co2eq_met_acq, co2eq_lng_acq

# ============================================================================
# CO2eq da trasporti
# ============================================================================

# CO2eq TRASPORTO (VALIDO PER BIOMASSA, DIGESTATO, BIOLNG, ECC...)
# ! ATTENZIONE ! # se EF è in [kg CO2eq per ton*km], vuol dire che il camion vuoto emette 0???
# ! Per ora NON tengo conto del viaggio a vuoto del camion
# ! QUESTO PROBLEMA SI RIPERCUOTE SU TUTTI I TRASPORTI
def co2eq_trasporto(trasporto, ton_carico, mc_carico, distanza):

    n_viaggi_pieno_carico = floor(mc_carico / trasporto.capacita_max)

    densita_media = ton_carico / mc_carico if mc_carico > 0 else 0
    massa_pieno_carico = trasporto.capacita_max * densita_media # ton
    massa_viaggio_carico_parziale = ton_carico - (n_viaggi_pieno_carico * ton_carico)

    co2eq = trasporto.EF * distanza * (n_viaggi_pieno_carico * massa_pieno_carico + 1 * massa_viaggio_carico_parziale)

    return co2eq

# ============================================================================
# CO2eq per funzionamento impianto
# ============================================================================
def co2eq_impianto(impianto):
    # ! serve la potenza nominale dell'impianto per determinare il consumo delle risorse (e quindi le emissioni). È un dato da inputare o desumibile da qualcos'altro?
    # ! in caso bisogna inserire la potenza nominale nel database, nella funzione di Input e nella classe Impianto

    # CO2eq OLIO LUBRIFICANTE

    # CO2eq RIFIUTI PERICOLOSI

    # CO2eq ACQUA

    # CO2eq SCARICHI

    pass




