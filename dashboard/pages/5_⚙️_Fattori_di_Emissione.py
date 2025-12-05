import streamlit as st
import sqlite3
import sys
import os
import pandas as pd
import time
sys.path.append(os.path.join(os.path.dirname(__file__), '../../src'))

from objects import FattoriEmissione

# Calcola il percorso assoluto del file corrente
current_dir = os.path.dirname(os.path.abspath(__file__))
# Torna su di 2 livelli: dashboard/pages -> dashboard -> progetto root
project_root = os.path.abspath(os.path.join(current_dir, '../..'))
# Percorso completo al database
db = os.path.join(project_root, 'data.db')


def main():

    st.title("Fattori di Emissione")
    
    # Recupera tutti i dati dalla tabella originale
    conn = sqlite3.connect(db)
    df = pd.read_sql_query("SELECT * FROM fattori_emissione", conn)
    conn.close()
    
    # Mostra la tabella con editor
    st.write("Fai doppio click su una cella per modificare il valore")
    
    # Crea un data editor
    edited_df = st.data_editor(df, use_container_width=True, num_rows="fixed", hide_index=True)
    
    # Bottone per salvare le modifiche
    if st.button("Salva modifiche nel database", use_container_width=True):
        try:
            conn = sqlite3.connect(db)
            cursor = conn.cursor()
            changes_made = False
            
            for index, row in edited_df.iterrows():
                original_row = df.iloc[index]
                
                # Verifica se ci sono differenze
                if not row.equals(original_row):
                    changes_made = True
                    
                    # Prepara e esegui l'update senza updated_at
                    cursor.execute("""
                        UPDATE fattori_emissione 
                        SET CO2_TOT = ?
                        WHERE nome = ?
                    """, (row['CO2_TOT'], row['nome']))
            
            if changes_made:
                conn.commit()
                st.toast("✅ Modifiche salvate con successo nel database!")
                time.sleep(1)
                
                # Ricarica i dati aggiornati
                df = pd.read_sql_query("SELECT * FROM fattori_emissione", conn)
                st.rerun()  # Ricarica la pagina per mostrare i dati aggiornati
            else:
                st.info("Nessuna modifica rilevata.")
                
        except Exception as e:
            conn.rollback()
            st.error(f"❌ Errore durante il salvataggio: {str(e)}")
        finally:
            conn.close()

if __name__ == "__main__":
    main()