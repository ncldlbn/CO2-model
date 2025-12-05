-- =====================================
-- TABELLA ALLEVATORE
-- =====================================
CREATE TABLE allevatore (
    id_allevatore INTEGER PRIMARY KEY AUTOINCREMENT,
    denominazione_sociale TEXT NOT NULL,
    id_impianto_associato INTEGER NOT NULL,
    tipo_conferimento TEXT NOT NULL CHECK (tipo_conferimento IN ('mezzi', 'tubazione')),
    frequenza_conferimento INTEGER NOT NULL,
    id_trasporto INTEGER NOT NULL,
    distanza_impianto REAL NOT NULL,
    uba_letame INTEGER NOT NULL,
    uba_liquame INTEGER NOT NULL,
    prod_letame REAL NOT NULL,
    prod_liquame REAL NOT NULL,
    deposito_max REAL NOT NULL,
    quota INTEGER,
    portata REAL,
    potenza REAL,
    ore INTEGER,
    FOREIGN KEY(id_impianto_associato) REFERENCES impianto(id_impianto),
    FOREIGN KEY(id_trasporto) REFERENCES trasporti(id_trasporto),
    CHECK (
        (tipo_conferimento = 'tubazione' AND portata IS NOT NULL AND potenza IS NOT NULL AND ore IS NOT NULL)
        OR (tipo_conferimento <> 'tubazione' AND portata IS NULL AND potenza IS NULL AND ore IS NULL)
    )
);

-- =====================================
-- TABELLA TRASPORTI
-- =====================================
CREATE TABLE trasporti (
    id_trasporto INTEGER PRIMARY KEY AUTOINCREMENT,
    tipo TEXT NOT NULL,
    EF REAL NOT NULL,
    capacita_max REAL
);

INSERT INTO trasporti (id_trasporto, tipo, EF, capacita_max) VALUES
(0, 'tubazione', 0, NULL),
(1, 'camion_generico', 0.1487, 25),
(2, 'trattore', 0.3855, NULL);

-- =====================================
-- TABELLA FATTORI EMISSIONE
-- =====================================
CREATE TABLE fattori_emissione (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    categoria TEXT NOT NULL,
    nome TEXT NOT NULL,
    unita TEXT NOT NULL,
    CO2_fossile REAL NOT NULL,
    CO2_biogenica REAL NOT NULL,
    CO2_dLUC REAL NOT NULL,
    CO2_TOT REAL NOT NULL
);

INSERT INTO fattori_emissione (
    categoria,
    nome,
    unita,
    CO2_fossile,
    CO2_biogenica,
    CO2_dLUC,
    CO2_TOT
) VALUES
-- TRASPORTI
('trasporti', 'camion_generico', 'kg CO2eq/tkm', 0.149, 0.0000446, 0.0000726, 0.14870955661),
('trasporti', 'trattore', 'kg CO2eq/tkm', 0.385, 0.000328, 0.000661, 0.38554700566),

-- ENERGIA
('energia', 'EE_BT', 'kg CO2eq/kWh', 0.62, 0.000437, 0.000068002629, 0.62056556662),
('energia', 'EE_MT', 'kg CO2eq/kWh', 0.641, 0.000430, 0.000052093137, 0.64110542286),
('energia', 'calore', 'kg CO2eq/kWh', 0.29183644, 0.000054349638, 0.000035925617, 0.29192671526),
('energia', 'metano', 'kg CO2eq/kWh', 0.29780778, 0.00003139685, 0.000034164567, 0.29787334142),
('energia', 'LNG', 'kg CO2eq/kWh', 0.37301856, 0.0000213559649, 0.000024002979, 0.37306391894),
('energia', 'cogen_EE_BT', 'kg CO2eq/kWh', 0.00550425301323034, 0.00500826530389773, 0, 0.01051251832),
('energia', 'cogen_EE_MT', 'kg CO2eq/kWh', 0.005370896117, 0.004886925185, 0, 0.01025782130),

-- IMPIANTO
('impianto', 'olio_lubrificante', 'kg CO2eq/kg', 1.7753987, 0.0013156124, 0.0011052098, 1.77781952220),
('impianto', 'rifiuti_recupero', 'kg CO2eq/kg', 0, 0, 0, 0.00000000000),
('impianto', 'acqua', 'kg CO2eq/mc', 0.3009549, 0.00057622011, 0.00057831189, 0.30210943200),
('impianto', 'scarichi', 'kg CO2eq/mc', 0.25789571, 0.061163242, 0.00028924199, 0.31934819399),

-- ALTRO
('altro', 'CO2_biogenica', 'kg CO2eq/unit', 0.7358888, 0.0010055334, 0.00049190182, 0.73738623522),
('altro', 'digestato', 'kg CO2eq/tonSS', 0, 16.71, 0, 16.71),
('altro', 'pollina', 'kg CO2eq/ton', 3.5121335, 0.00069309774, 0.01019444, 3.52302103774);


-- =====================================
-- TABELLA IMPIANTO
-- =====================================
CREATE TABLE impianto (
    id_impianto INTEGER PRIMARY KEY AUTOINCREMENT,
    nome TEXT NOT NULL,
    deposito_max REAL, -- mc
    Qout_liq REAL,     -- ton
    Qout_let REAL,     -- ton
    separazione BOOLEAN,
    olio_lubrificante REAL,
    rifiuti REAL,
    acqua REAL,
    scarichi REAL
);

-- =====================================
-- TABELLA RICETTA IMPIANTO
-- =====================================
CREATE TABLE ricetta_impianto (
    id_ricetta INTEGER PRIMARY KEY AUTOINCREMENT,
    id_impianto INTEGER NOT NULL,
    tipo TEXT NOT NULL, -- liquame, letame, sottoprodotti, pollina
    quantita REAL,      -- ton/anno
    FOREIGN KEY (id_impianto) REFERENCES impianto(id_impianto)
);

-- =====================================
-- TABELLA BILANCIO ENERGETICO
-- =====================================
CREATE TABLE bilancio_energetico (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    id_impianto INTEGER NOT NULL,
    categoria TEXT NOT NULL CHECK (categoria IN ('prodotta', 'autoconsumata', 'acquistata')),
    tipo TEXT NOT NULL,
    valore REAL NOT NULL,
    unita TEXT NOT NULL,
    FOREIGN KEY (id_impianto) REFERENCES impianto(id_impianto),
    CHECK (
        (categoria = 'prodotta'      AND tipo IN ('EE_BT','EE_MT','calore','biometano','bioLNG','CO2_biogenica'))
     OR (categoria = 'autoconsumata' AND tipo IN ('EE','EE_trasporti_tubazioni','calore','biometano','bioLNG'))
     OR (categoria = 'acquistata'    AND tipo IN ('EE_BT','EE_MT','metano','LNG'))
    )
);

-- =====================================
-- TABELLA RICETTORI
-- =====================================
CREATE TABLE ricettori (
    id_ricettore INTEGER PRIMARY KEY AUTOINCREMENT,
    id_impianto INTEGER NOT NULL,
    id_trasporto INTEGER NOT NULL,
    tipo TEXT, -- digestato solido / liquido, bioLNG, bioCO2
    distanza REAL NOT NULL, -- km
    FOREIGN KEY(id_impianto) REFERENCES impianto(id_impianto),
    FOREIGN KEY(id_trasporto) REFERENCES trasporti(id_trasporto)
);
