"""
Costanti e parametri di configurazione del modello CO2eq.

Tutti i valori di processo, i fattori di Global Warming Potential e i parametri
empirici dei modelli di emissione sono centralizzati qui per evitare costanti
"magiche" sparse nel codice.
"""

# ---------------------------------------------------------------------------
# Global Warming Potential (GWP100, IPCC AR5)
# ---------------------------------------------------------------------------
GWP_CH4 = 28   # kg CO2eq / kg CH4
GWP_N2O = 265  # kg CO2eq / kg N2O

# ---------------------------------------------------------------------------
# Parametri temporali
# ---------------------------------------------------------------------------
GIORNI_ANNO = 365
GIORNI_RIFERIMENTO = 180  # durata di deposito di riferimento (scenario senza impianto)

# ---------------------------------------------------------------------------
# Parametri empirici delle emissioni da deposito di biomassa
#   n2o = m * giorni              [g / kg sostanza secca]
#   ch4 = alfa * giorni ** beta   [g / kg sostanza secca]
#   st  = frazione di sostanza secca della biomassa
# ---------------------------------------------------------------------------
LETAME = {
    "st":   0.214,
    "m":    0.0036,
    "alfa": 0.04939,
    "beta": 0.6142,
}

LIQUAME = {
    "st":   0.073,
    "m":    0.00192,
    "alfa": 1.57095,
    "beta": 0.61641,
}

# ---------------------------------------------------------------------------
# Parametri di processo del digestato
# ---------------------------------------------------------------------------
DIGESTATO = {
    "perc_digestato": 0.95,  # resa massa digestato sul totale in ingresso
    "perc_liq_sep":   0.80,  # quota liquida dopo separazione
    "perc_sol_sep":   0.20,  # quota solida dopo separazione
    "ss_digestato":   0.052,  # 5.2% sostanza secca digestato liquido
    "ss_solido":      0.20,   # 20% sostanza secca frazione solida
}

# ---------------------------------------------------------------------------
# Mezzi di trasporto di default per un impianto
# ---------------------------------------------------------------------------
ID_MEZZO_LIQUIDO_DEFAULT = 2  # Trattore
ID_MEZZO_SOLIDO_DEFAULT = 1   # Camion generico
