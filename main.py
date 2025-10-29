import sqlite3
import pandas as pd
import sys
from math import ceil

from src.objects import Allevatore, Impianto, Trasporto, FattoriEmissione
from src.model import co2eq_let_liq, co2eq_trasportO, co2eq_netta_energia

db = './data.db'

# -----------------------------------------------------------------
# DATI INPUT
# -----------------------------------------------------------------
A = Allevatore.from_db(db, 1)
I = Impianto.from_db(db, A.id_impianto_associato)
T = Trasporto.from_db(db, A.id_trasporto)
EF = FattoriEmissione('./data.db')

print(A)
print(I)
print(T)

# -----------------------------------------------------------------
# CO2eq DA STOCCAGGIO BIOMASSA
# -----------------------------------------------------------------
co2eq_let_tot, co2eq_liq_tot, co2eq_biomassa, n_svuotamenti, deposito_liq, deposito_let = co2eq_let_liq(A) # CONTRIBUTO POSITIVO

let_tot = A.produzione_giornaliera_letame * A.uba_letame * 365
liq_tot = A.produzione_giornaliera_liquame * A.uba_liquame * 365

print(f"CO2eq da letame: {co2eq_let_tot:.0f} kg")
print(f"CO2eq da liquame: {co2eq_liq_tot:.0f} kg")
print(f"CO2eq totale: {co2eq_biomassa:.0f} kg") 
print(f"N° svuotamenti: {n_svuotamenti}")
print(f"Deposito liq: {deposito_liq:.0f} mc") 
print(f"Deposito let: {deposito_let:.0f} mc")

# CO2eq stoccaggio digestato

# -----------------------------------------------------------------
# CO2eq DA TRASPORTO
# -----------------------------------------------------------------

# BIOMASSA
volume_conferimento = deposito_let + deposito_liq
massa_conferimento = deposito_let * 0.7 + deposito_liq * 1
co2eq_trasporto_biomassa = co2eq_trasporto(T, massa_conferimento, volume_conferimento, A.distanza_impianto) # CONTRIBUTO POSITIVO
print(f"CO2eq da trasporto biomassa: {co2eq_trasporto_biomassa:.0f} kg")

# DIGESTATO
co2eq_trasporto_digestato = co2eq_trasporto(T, 0.95*massa_conferimento, 0.95*volume_conferimento, A.distanza_impianto) # CONTRIBUTO POSITIVO

# bioLNG (OPZIONALE)

# CO2 biogenica (OPZIONALE)

# -----------------------------------------------------------------
# CO2eq DA PRODUZIONE ENERGETICA IMPIANTO
# -----------------------------------------------------------------
co2eq_ee_netta, co2eq_calore_netta, co2eq_biomet_netta, co2eq_biolng_netta, co2eq_biogenica_prod, co2eq_ee_acq, co2eq_met_acq, co2eq_lng_acq = co2eq_netta_energia(I, EF)

co2eq_energia_prodotta_netta = co2eq_ee_netta + co2eq_calore_netta + co2eq_biomet_netta + co2eq_biolng_netta + co2eq_biogenica_prod # CONTRIBUTO NEGATIVO
co2eq_energia_acquistata = co2eq_ee_acq + co2eq_met_acq + co2eq_lng_acq # CONTRIBUTO POSITIVO

# CO2eq consumo acqua, olio e produzione reflui e scarti


# -----------------------------------------------------------------
# CO2eq EMISSIONE TOTALE ANNUA
# -----------------------------------------------------------------
co2eq_tot_anno = co2eq_biomassa + co2eq_trasporto_biomassa - co2eq_energia_prodotta_netta + co2eq_energia_acquistata + co2eq_trasporto_digestato #



