import sys
import os
import pandas as pd
import sqlite3
import logging
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from assets.assets_setup import AssetManager

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/data_processing.log'),
        logging.StreamHandler()
    ]
)

def load_to_sqlite(csv_path, db_path="data/medicare.db"):
    """
    Load manually downloaded CSV data into SQLite database
    """
    try:
        logging.info("Loading data into SQLite database...")
        chunksize = 100000
        conn = sqlite3.connect(db_path)
        
        for i, chunk in enumerate(pd.read_csv(csv_path, chunksize=chunksize)):
            chunk.columns = [col.strip().replace(' ', '_').replace('(', '').replace(')', '').replace('%', 'Pct').replace('/', '_') for col in chunk.columns]
            if_exists = 'replace' if i == 0 else 'append'
            chunk.to_sql('medicare_providers', conn, if_exists=if_exists, index=False)
            logging.info(f"Processed chunk {i+1}")
        
        # Create indexes
        conn.execute("CREATE INDEX IF NOT EXISTS idx_npi ON medicare_providers(Rndrng_NPI)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_provider_type ON medicare_providers(Rndrng_Prvdr_Type)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_state ON medicare_providers(Rndrng_Prvdr_State_Abrvtn)")
        
        conn.commit()
        conn.close()

        logging.info(f"Data successfully loaded into SQLite database: {db_path}")
        return db_path

    except Exception as e:
        logging.error(f"Error loading data to SQLite: {e}")
        return None

def verify_data(db_path="data/medicare.db"):
    """
    Verify the data was loaded correctly and provide basic stats
    """
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        stats = {
            "total_records": cursor.execute("SELECT COUNT(*) FROM medicare_providers").fetchone()[0],
            "unique_providers": cursor.execute("SELECT COUNT(DISTINCT Rndrng_NPI) FROM medicare_providers").fetchone()[0],
            "provider_types": cursor.execute("SELECT COUNT(DISTINCT Rndrng_Prvdr_Type) FROM medicare_providers").fetchone()[0],
            "states": cursor.execute("SELECT COUNT(DISTINCT Rndrng_Prvdr_State_Abrvtn) FROM medicare_providers").fetchone()[0],
        }

        conn.close()
        logging.info("Verification complete: " + str(stats))
        return stats

    except Exception as e:
        logging.error(f"Verification error: {e}")
        return None

if __name__ == "__main__":
    csv_path = "data/medicare_providers_2023.csv"
    asset_manager = AssetManager()
    if os.path.exists(csv_path):
        db_path = load_to_sqlite(csv_path)
        if db_path:
            verify_data(db_path)
            asset_manager.update_last_updated()
    else:
        logging.error(f"CSV file not found at path: {csv_path}")
