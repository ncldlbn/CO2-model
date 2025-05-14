from math import ceil, exp, log

import altair as alt
import pandas as pd

def calcola_svuotamenti(frequenza_giorni):
    """
    Genera un dizionario con i giorni dell'anno (1-365) associati a True/False,
    in base alla frequenza di svuotamento espressa in giorni.
    Il primo giorno è sempre False, il primo True avviene dopo `frequenza_giorni`.

    :param frequenza_giorni: ogni quanti giorni avviene uno svuotamento (es. 30)
    :return: dizionario {giorno: True/False}
    """
    svuotamenti = {giorno: False for giorno in range(1, 366)}

    for giorno in range(frequenza_giorni, 366, frequenza_giorni):
        svuotamenti[giorno] = True

    return svuotamenti
class Contadino:
    def __init__(self, id, distanza, uba, biomassa_uba_giorno, perc_letame, deposito_0, deposito_max, GWP_CH4, GWP_NO2):
        """
        id_contadino (int): Identificativo univoco del contadino.
        id_impianto (int): Identificativo dell’impianto a cui è associato il contadino.
        distanza (float): distanza in km tra contadino e impianto.
        uba (float): Numero di Unità di Bovino Adulto (UBA).
        biomassa_uba_giorno (float): Biomassa prodotta giornalmente da una UBA (in kg/giorno).
        perc_letame (float) [0-1]: percentuale letame vs liquame. 
        deposito_0 (int): Quantità iniziale di biomassa presente nel deposito (in kg).
        deposito_max (int): Capacità massima del deposito di stoccaggio (in kg).
        stock (dict): Livello di biomassa stoccata per ciascun giorno.
        """
        self.id = id
        self.distanza_impianto = distanza
        self.uba = uba
        self.biomassa_uba_giorno = biomassa_uba_giorno
        self.perc_letame = perc_letame/100
        self.deposito_0 = deposito_0
        self.deposito_max = deposito_max
        self.deposito = {}
        self.tot_co2eq = 0
        self.GWP_CH4 = GWP_CH4
        self.GWP_NO2 = GWP_NO2

        self.produzione_giornaliera = self.uba * self.biomassa_uba_giorno

    def aggiorna_deposito(self, giorno):
        """
        Calcola lo stock dopo un certo numero di giorni.
        Se supera lo stock massimo, viene limitato a stock_max.
        """

        if not self.deposito:
            self.deposito[giorno] = self.deposito_0 + self.produzione_giornaliera
        else:
            self.deposito[giorno] = self.deposito[giorno-1] + self.produzione_giornaliera

    def calcola_co2eq(self, giorno, giorno_rel):
        no2liq = giorno_rel/500
        no2let = giorno_rel/272.727
        ch4liq = exp(0.6164 * log(giorno_rel) + 0.4517)
        ch4let = exp(0.6142 * log(giorno_rel) - 3.008)

        no2tot = no2liq*self.perc_letame + no2let*(1-self.perc_letame)
        ch4tot = ch4liq*self.perc_letame + ch4let*(1-self.perc_letame)

        co2eq_kg_biomassa = no2tot*self.GWP_NO2 + ch4tot*self.GWP_CH4
        co2eq = co2eq_kg_biomassa * self.deposito[giorno] / 1000

        self.tot_co2eq = self.tot_co2eq + co2eq

        if not hasattr(self, 'co2_data'):
            self.co2_data = pd.DataFrame(columns=['giorno', 'co2eq_biomassa'])
            self.co2_data.loc[len(self.co2_data)] = [giorno, co2eq/1000]
        else:
            self.co2_data.loc[len(self.co2_data)] = [giorno, co2eq/1000]

        return co2eq

    def svuota_deposito(self, giorno):
        """
        
        """
        self.deposito[giorno] = 0

class Trasporto:
    def __init__(self, capacita, ef):
        """
        :param distanza: distanza percorsa in km
        :param massa_vuoto: massa a vuoto del camion
        :param ef: emission factor in kg CO2/km
        :param capacita: capacità del mezzo in tonnellate
        """
        
        self.capacita = capacita*1000 #in kg
        self.ef = ef
        self.tot_co2 = 0
        self.registro = []

    def svuota(self, contadino, giorno):
        # calcola numero di trasporti impianto-contadino
        n_viaggi = ceil(contadino.deposito[giorno]/self.capacita)
        riempimento_medio = contadino.deposito[giorno]/(self.capacita*n_viaggi)
        # Distanza percorsa per effettuare tutti i trasporti x2 (andata e ritorno)
        km_tot = n_viaggi * contadino.distanza_impianto * 2
        # CO2 prodotta per lo svuotamento in kg
        co2 = km_tot * self.ef / 1000
        self.tot_co2 = self.tot_co2 + co2
        # Update registro svuotamenti
        self.registro.append({
            'giorno': giorno,
            'n_viaggi': n_viaggi,
            'km_percorsi': km_tot,
            'quantita': round(contadino.deposito[giorno]/1000,2),
            'riempimento_medio': round(riempimento_medio*100),
            'co2_emessa': round(co2, 2)
        })

        # # Trasferisci la biomassa dal deposito del contadino al deposito dell'impianto
        # impianto.deposito[giorno] = contadino.deposito[giorno]
        contadino.deposito[giorno] = 0


    

class Impianto:
    def __init__(self, id, deposito_0, deposito_max):
        """
        :param ricetta: dict
        :param energia_target: obiettivo di energia da produrre (es. kWh)
        :param deposito_0: deposito iniziale (kg)
        :param deposito_max: deposito massimo (kg)
        """
        self.id = id
        # self.ricetta = ricetta
        # self.energia_target = energia_target
        # self.ef = ef
        self.deposito_0 = deposito_0
        self.deposito_max = deposito_max
        self.deposito = {}
