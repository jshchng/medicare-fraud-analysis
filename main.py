import argparse
import logging
import subprocess
import webbrowser
import time

from scripts.analysis import MedicareAnalyzer

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/medicare_analysis.log'),
        logging.StreamHandler()
    ]
)

def run_analysis_tasks():
    """Run core Medicare analysis tasks"""
    analyzer = MedicareAnalyzer()
    if not analyzer.connect():
        logging.error("Database connection failed.")
        return

    try:
        provider_results = analyzer.analyze_provider_distribution()
        geographic_results = analyzer.analyze_geographic_distribution()
        risk_results = analyzer.analyze_risk_distribution()
        comparative_results = analyzer.analyze_comparative()

        logging.info("Provider Analysis Results: " + str(provider_results))
        logging.info("Geographic Analysis Results: " + str(geographic_results))
        logging.info("Risk Analysis Results: " + str(risk_results))
        logging.info("Comparative Analysis Results: " + str(comparative_results))
        logging.info("All analyses completed.")
    except Exception as e:
        logging.error(f"Error during analysis tasks: {e}")

def launch_dashboard():
    """Launch the interactive dashboard"""
    logging.info("Launching dashboard...")
    try:
        subprocess.Popen(["python", "dashboard.py"])
        time.sleep(2)
        webbrowser.open("http://localhost:8050")
    except Exception as e:
        logging.error(f"Failed to launch dashboard: {e}")

def main():
    parser = argparse.ArgumentParser(description="Medicare Provider Analysis Runner")
    parser.add_argument("--analyze", action="store_true", help="Run analysis tasks and log the results.")
    parser.add_argument("--dashboard", action="store_true", help="Launch the dashboard in your browser.")

    args = parser.parse_args()

    if args.analyze:
        run_analysis_tasks()
    if args.dashboard:
        launch_dashboard()

if __name__ == "__main__":
    main()
