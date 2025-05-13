import os
from datetime import datetime
import logging
import json

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/assets_setup.log'),
        logging.StreamHandler()
    ]
)

class AssetManager:
    def __init__(self, assets_dir="assets"):
        """Initialize the asset manager with the assets directory path"""
        self.assets_dir = assets_dir
        os.makedirs(assets_dir, exist_ok=True)
        logging.info(f"Assets directory verified at: {assets_dir}")

    def create_css_file(self):
        """Create a CSS file for dashboard styling"""
        try:
            css_content = """
            /* Main dashboard styles */
            body {
                font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
                margin: 0;
                padding: 0;
                background-color: #f5f7fa;
                color: #333;
            }

            .header {
                background-color: #004b87;
                color: white;
                padding: 20px;
                text-align: center;
                box-shadow: 0 2px 5px rgba(0, 0, 0, 0.1);
            }

            .header-title {
                margin: 0;
                font-size: 2.5em;
            }

            .header-description {
                margin: 10px 0 0 0;
                font-size: 1.2em;
                opacity: 0.9;
            }

            .main-content {
                display: flex;
                flex-wrap: wrap;
                margin: 20px;
                gap: 20px;
            }

            .control-panel, .visualization-panel, .insights-panel {
                background-color: white;
                padding: 20px;
                border-radius: 8px;
                box-shadow: 0 2px 5px rgba(0, 0, 0, 0.1);
            }

            .control-panel {
                flex: 1;
                min-width: 300px;
            }

            .visualization-panel {
                flex: 3;
                min-width: 600px;
            }

            .insights-panel {
                margin: 20px;
            }

            .run-button {
                margin-top: 20px;
                padding: 10px 20px;
                background-color: #004b87;
                color: white;
                border: none;
                border-radius: 4px;
                cursor: pointer;
                font-size: 1em;
                transition: background-color 0.3s;
            }

            .run-button:hover {
                background-color: #00376e;
            }

            /* Responsive adjustments */
            @media (max-width: 1000px) {
                .main-content {
                    flex-direction: column;
                }
            }
            """
            css_path = os.path.join(self.assets_dir, 'dashboard.css')
            with open(css_path, 'w') as f:
                f.write(css_content)
            logging.info(f"CSS file created at: {css_path}")
            return css_path
        except Exception as e:
            logging.error(f"Error creating CSS file: {e}")
            return None

    def create_default_settings(self):
        """Create a default settings JSON file for the dashboard"""
        try:
            settings = {
                "title": "Medicare Provider Analysis Dashboard",
                "description": "Analyze patterns in healthcare utilization, spending, and provider demographics",
                "theme": {
                    "primary_color": "#004b87",
                    "secondary_color": "#00376e",
                    "accent_color": "#f5f7fa",
                    "text_color": "#333333"
                },
                "features": {
                    "provider_analysis": True,
                    "geographic_analysis": True,
                    "risk_analysis": True,
                    "comparative_analysis": True,
                    "export_data": True
                },
                "default_views": {
                    "provider_type": "All",
                    "state": "All",
                    "metric": "total_medicare_payments",
                    "visualization": "map"
                },
                "data_refresh": {
                    "last_updated": datetime.now().strftime("%Y-%m-%d")
                }
            }
            settings_path = os.path.join(self.assets_dir, 'settings.json')
            with open(settings_path, 'w') as f:
                json.dump(settings, f, indent=4)
            logging.info(f"Default settings file created at: {settings_path}")
            return settings_path
        except Exception as e:
            logging.error(f"Error creating default settings file: {e}")
            return None
        
    def update_last_updated(self):
        """Update the last_updated field in settings.json"""
        settings_path = os.path.join(self.assets_dir, 'settings.json')
        try:
            # Load the existing settings
            with open(settings_path, 'r') as f:
                settings = json.load(f)
        
            # Update the last_updated field
            settings["data_refresh"]["last_updated"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
            # Save the updated settings back to the file
            with open(settings_path, 'w') as f:
                json.dump(settings, f, indent=4)
        
            logging.info(f"last_updated field updated to {settings['data_refresh']['last_updated']}")
        except Exception as e:
            logging.error(f"Error updating last_updated in settings.json: {e}")

    def setup_all_assets(self):
        """Create all required assets for the dashboard"""
        self.create_css_file()
        self.create_default_settings()
        logging.info("All assets have been set up successfully")

if __name__ == "__main__":
    asset_manager = AssetManager()
    asset_manager.setup_all_assets()