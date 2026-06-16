import streamlit as st
import sqlite3
import os
import pandas as pd

current_dir  = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.abspath(os.path.join(current_dir, '../..'))
db           = os.path.join(project_root, 'data.db')

LABEL_MAP = {
    "liquame":           "Liquame",
    "letame":            "Letame",
    "pollina":           "Pollina",
    "colture":           "Colture",
    "sottoprodotti":     "Sottoprodotti",
    "digestato":         "Digestato",
    "ee_bt":             "Energia Elettrica BT",
    "ee_mt":             "Energia Elettrica MT",
    "calore":            "Calore",
    "biometano":         "Biometano",
    "biolng":            "BioLNG",
    "co2_biogenica":     "CO₂ Biogenica",
    "metano":            "Metano",
    "lng":               "LNG",
    "olio_lubrificante": "Olio Lubrificante",
    "rifiuti":           "Rifiuti",
    "acqua":             "Acqua",
    "scarichi":          "Scarichi",
}

REVERSE_MAP = {v: k for k, v in LABEL_MAP.items()}


def load_data():
    conn = sqlite3.connect(db)
    df = pd.read_sql_query("SELECT * FROM fattori_emissione", conn)
    conn.close()
    return df


def main():
    st.title("Fattori di Emissione")

    df = load_data()

    # Filtra trasporti e resetta indice
    df_filtered = df[df["categoria"] != "trasporti"].copy().reset_index(drop=True)

    # Applica etichette leggibili
    df_filtered["nome"] = df_filtered["nome"].str.lower().map(LABEL_MAP).fillna(df_filtered["nome"])

    # Rinomina colonne e rimuovi id e categoria
    df_display = df_filtered.rename(columns={
        "nome":          "Voce",
        "unita":         "Unità",
        "CO2_fossile":   "CO₂ fossile",
        "CO2_biogenica": "CO₂ biogenica",
        "CO2_dLUC":      "CO₂ dLUC",
        "CO2_TOT":       "CO₂ tot",
    }).drop(columns=["id", "categoria"], errors="ignore").reset_index(drop=True)

    st.write("Fai doppio click su una cella per modificare il valore.")

    edited_df = st.data_editor(
        df_display,
        use_container_width=True,
        num_rows="fixed",
        hide_index=True,
        disabled=["Voce", "Unità"],
    )

    if st.button("Salva modifiche nel database", use_container_width=True):
        try:
            conn = sqlite3.connect(db)
            cursor = conn.cursor()
            changes_made = False

            for index in range(len(edited_df)):
                row          = edited_df.iloc[index]
                original_row = df_display.iloc[index]

                if not row.equals(original_row):
                    changes_made = True
                    nome_display = row["Voce"]
                    nome_db      = REVERSE_MAP.get(nome_display, nome_display.lower())

                    cursor.execute("""
                        UPDATE fattori_emissione
                        SET CO2_fossile = ?, CO2_biogenica = ?, CO2_dLUC = ?, CO2_TOT = ?
                        WHERE LOWER(nome) = LOWER(?)
                    """, (
                        row["CO₂ fossile"],
                        row["CO₂ biogenica"],
                        row["CO₂ dLUC"],
                        row["CO₂ tot"],
                        nome_db
                    ))

            if changes_made:
                conn.commit()
                st.toast("✅ Modifiche salvate con successo nel database!")
                st.rerun()
            else:
                st.info("Nessuna modifica rilevata.")

        except Exception as e:
            conn.rollback()
            st.error(f"❌ Errore durante il salvataggio: {str(e)}")
        finally:
            conn.close()


if __name__ == "__main__":
    main()