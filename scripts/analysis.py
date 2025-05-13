import pandas as pd
import sqlite3
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/analysis.log'),
        logging.StreamHandler()
    ]
)

class MedicareAnalyzer:
    def __init__(self, db_path="data/medicare.db"):
        """Initialize the analyzer with the database path"""
        self.db_path = db_path
        
    def connect(self):
        """Connect to the SQLite database"""
        try:
            self.conn = sqlite3.connect(self.db_path)
            logging.info(f"Connected to database: {self.db_path}")
            return True
        except Exception as e:
            logging.error(f"Error connecting to database: {e}")
            return False
    
    def disconnect(self):
        """Close the database connection"""
        if self.conn:
            self.conn.close()
            logging.info("Database connection closed")
    
    def execute_query(self, query):
        """Execute a SQL query and return results as a pandas DataFrame"""
        if not self.conn:
            if not self.connect():
                return None
        
        try:
            logging.info(f"Executing query: {query[:100]}...")
            conn = sqlite3.connect('data/medicare.db')
            return pd.read_sql_query(query, conn)
        except Exception as e:
            logging.error(f"Error executing query: {e}")
            return None
    
    def execute_query_from_file(self, sql_file, query_name=None):
        """Execute a SQL query from a file and return results as a pandas DataFrame"""
        try:
            with open(sql_file, 'r') as file:
                sql_content = file.read()
                
            # Split file into individual queries if necessary
            if query_name:
                queries = {}
                current_query = ""
                current_name = ""
                
                for line in sql_content.split('\n'):
                    if line.strip().startswith('--'):
                        if 'Analysis' in line or 'analysis' in line:
                            if current_name and current_query:
                                queries[current_name] = current_query.strip()
                            current_name = line.strip('- ').split('.')[0].strip()
                            current_query = ""
                        continue
                    current_query += line + "\n"
                
                if current_name and current_query:
                    queries[current_name] = current_query.strip()
                
                # Find the requested query
                for name, query in queries.items():
                    if query_name.lower() in name.lower():
                        return self.execute_query(query)
                
                logging.error(f"Query '{query_name}' not found in {sql_file}")
                return None
            else:
                # Execute the entire file as a single query
                return self.execute_query(sql_content)
                
        except Exception as e:
            logging.error(f"Error executing query from file: {e}")
            return None
    
    def analyze_provider_distribution(self, limit=15, sort_by="total_medicare_payments"):
        """Analyze provider distribution and create visualizations"""
        query = f"""
        SELECT 
            Rndrng_Prvdr_Type,
            COUNT(DISTINCT Rndrng_NPI) AS provider_count,
            SUM(Tot_Benes) AS total_beneficiaries,
            SUM(Tot_Srvcs) AS total_services,
            ROUND(SUM(Tot_Mdcr_Pymt_Amt), 2) AS total_medicare_payments,
            ROUND(SUM(Tot_Mdcr_Pymt_Amt) / COUNT(DISTINCT Rndrng_NPI), 2) AS avg_payment_per_provider,
            ROUND(SUM(Tot_Mdcr_Pymt_Amt) / SUM(Tot_Benes), 2) AS avg_payment_per_beneficiary,
            ROUND(SUM(Tot_Mdcr_Pymt_Amt) / SUM(Tot_Srvcs), 2) AS avg_payment_per_service
        FROM medicare_providers
        WHERE Tot_Benes > 0
        GROUP BY Rndrng_Prvdr_Type
        ORDER BY {sort_by} DESC
        LIMIT {limit};
        """
        
        df = self.execute_query(query)
        if df is None or df.empty:
            logging.warning("No data returned for provider distribution analysis")
            return None
        
        logging.info("Provider distribution analysis completed")
        return df
    
    def analyze_geographic_distribution(self, metric="payment_per_beneficiary", viz_type="map"):
        """Analyze geographic distribution of Medicare spending"""
        query = """
        SELECT 
            Rndrng_Prvdr_State_Abrvtn,
            COUNT(DISTINCT Rndrng_NPI) AS provider_count,
            SUM(Tot_Benes) AS total_beneficiaries,
            SUM(Tot_Srvcs) AS total_services,
            ROUND(SUM(Tot_Mdcr_Pymt_Amt), 2) AS total_medicare_payments,
            ROUND(SUM(Tot_Mdcr_Pymt_Amt) / SUM(Tot_Benes), 2) AS payment_per_beneficiary,
            ROUND(SUM(Tot_Mdcr_Pymt_Amt) / SUM(Tot_Srvcs), 2) AS payment_per_service,
            ROUND(SUM(Tot_Mdcr_Stdzd_Amt), 2) AS total_standardized_payments,
            ROUND(SUM(Tot_Mdcr_Stdzd_Amt) / SUM(Tot_Benes), 2) AS standardized_payment_per_beneficiary
        FROM medicare_providers
        WHERE Rndrng_Prvdr_State_Abrvtn IN (
            'AL', 'AK', 'AZ', 'AR', 'CA', 'CO', 'CT', 'DE', 'FL', 'GA',
            'HI', 'ID', 'IL', 'IN', 'IA', 'KS', 'KY', 'LA', 'ME', 'MD',
            'MA', 'MI', 'MN', 'MS', 'MO', 'MT', 'NE', 'NV', 'NH', 'NJ',
            'NM', 'NY', 'NC', 'ND', 'OH', 'OK', 'OR', 'PA', 'RI', 'SC',
            'SD', 'TN', 'TX', 'UT', 'VT', 'VA', 'WA', 'WV', 'WI', 'WY', 'DC'
        )
        AND Tot_Benes > 0
        GROUP BY Rndrng_Prvdr_State_Abrvtn
        ORDER BY {0} DESC;
        """.format(metric)
        
        df = self.execute_query(query)
        if df is None or df.empty:
            logging.warning("No data returned for geographic distribution analysis")
            return None
        
        logging.info("Geographic distribution analysis completed")
        return df

    def analyze_risk_distribution(self, limit=25, provider_types="top5"):
        """Identify providers with unusually high payment-to-service ratios"""
        query = """
        SELECT 
            Rndrng_NPI,
            Rndrng_Prvdr_Type,
            Rndrng_Prvdr_State_Abrvtn,
            Tot_Benes,
            Tot_Srvcs,
            ROUND(Tot_Mdcr_Pymt_Amt, 2) AS total_payment,
            ROUND(Tot_Mdcr_Stdzd_Amt, 2) AS total_standardized_payment,
            ROUND(Tot_Mdcr_Pymt_Amt / Tot_Srvcs, 2) AS payment_per_service,
            ROUND(Tot_Mdcr_Pymt_Amt / Tot_Benes, 2) AS payment_per_beneficiary
        FROM medicare_providers
        WHERE Tot_Srvcs > 10
        ORDER BY payment_per_service DESC
        """

        df = self.execute_query(query)
        if df is None or df.empty:
            logging.warning("No data returned for high-risk provider analysis")
            return None
        
        # Filter by provider types and apply limits per type
        if provider_types in ["top5", "top10"]:
            top_n = int(provider_types.replace("top", ""))
            top_provider_types = df['Rndrng_Prvdr_Type'].value_counts().nlargest(top_n).index
            df = df[df['Rndrng_Prvdr_Type'].isin(top_provider_types)]
            df = df.sort_values(by="payment_per_service", ascending=False)
            df = df.groupby("Rndrng_Prvdr_Type").head(limit // top_n)
        elif provider_types == "all":
            df = df.sort_values(by="payment_per_service", ascending=False)
            num_types = df['Rndrng_Prvdr_Type'].nunique()
            per_type_limit = max(1, limit // num_types)
            df = df.groupby("Rndrng_Prvdr_Type").head(per_type_limit)


        # Convert NPI to string to use as categorical x-axis
        df['Rndrng_NPI'] = df['Rndrng_NPI'].astype(str)
    
        # Create abbreviated provider IDs for better display
        df['Provider_ID'] = df['Rndrng_NPI'].str[-4:]

        logging.info("High-risk provider analysis completed")
        return df

    def analyze_comparative(self, compare_by="provider_type", metrics=None):
        """Perform comparative analysis between provider types or states"""
        if metrics is None:
            metrics = ["total_medicare_payments", "payment_per_beneficiary"]
            
        # Define group by field based on comparison type
        group_by_field = "Rndrng_Prvdr_Type" if compare_by == "provider_type" else "Rndrng_Prvdr_State_Abrvtn"
        
        query = f"""
        SELECT 
            {group_by_field},
            COUNT(DISTINCT Rndrng_NPI) AS provider_count,
            SUM(Tot_Benes) AS total_beneficiaries,
            SUM(Tot_Srvcs) AS total_services,
            ROUND(SUM(Tot_Mdcr_Pymt_Amt), 2) AS total_medicare_payments,
            ROUND(SUM(Tot_Mdcr_Pymt_Amt) / SUM(Tot_Benes), 2) AS payment_per_beneficiary,
            ROUND(SUM(Tot_Mdcr_Pymt_Amt) / SUM(Tot_Srvcs), 2) AS payment_per_service
        FROM medicare_providers
        WHERE Tot_Benes > 0 AND Tot_Srvcs > 0
        GROUP BY {group_by_field}
        ORDER BY total_medicare_payments DESC
        LIMIT 25;
        """
        
        df = self.execute_query(query)
        if df is None or df.empty:
            logging.warning("No data returned for comparative analysis")
            return None
            
        logging.info("Comparative analysis completed")
        return df

    def __enter__(self):
        """Support for 'with' statement"""
        self.connect()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Clean up connection when exiting 'with' statement"""
        self.disconnect()


# If run directly, connect and execute all analyses
if __name__ == "__main__":
    with MedicareAnalyzer() as analyzer:
        analyzer.analyze_provider_distribution()
        analyzer.analyze_geographic_distribution()
        analyzer.analyze_risk_distribution()
        analyzer.analyze_comparative()