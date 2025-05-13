import os
import dash
from dash import dcc, html, dash_table, Input, Output, State
import plotly.express as px
import pandas as pd
import numpy as np
import sqlite3
import logging
import json
from scripts.analysis import MedicareAnalyzer
from assets.assets_setup import AssetManager
from scripts.insights import InsightsGenerator
from scripts.visualization import provider_distribution_plot, geographic_distribution_plot, high_risk_plot, comparative_plot

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/dashboard.log'),
        logging.StreamHandler()
    ]
)

class MedicareDashboard:
    def __init__(self):
        """Initialize the Medicare Dashboard application"""
        self.app = dash.Dash(
            __name__, 
            title="Medicare Provider Analytics",
            assets_folder="assets",
            suppress_callback_exceptions=True,
            meta_tags=[
                {"name": "viewport", "content": "width=device-width, initial-scale=1"},
                {"name": "description", "content": "Interactive dashboard for Medicare provider data analysis"},
                {"name": "author", "content": "Joshua Chang"}
            ]
        )
        
        self.server = self.app.server
        self.analyzer = MedicareAnalyzer()
        self.asset_manager = AssetManager()
        self.insights_generator = InsightsGenerator(self.analyzer)
        
        # Ensure assets are set up
        if not os.path.exists(os.path.join("assets")):
            logging.info("Setting up dashboard assets...")
            self.asset_manager.setup_all_assets()
        
        # Load settings
        try:
            with open(os.path.join("assets", "settings.json"), "r") as f:
                self.settings = json.load(f)
        except Exception as e:
            logging.error(f"Error loading settings: {e}")
            self.settings = {
                "title": "Medicare Provider Analysis Dashboard",
                "description": "Interactive dashboard for Medicare provider data analysis"
            }
        
        # Connect to database
        if not self.analyzer.connect():
            logging.error("Database connection failed. Dashboard may not function properly.")
            
        # Set up the dashboard layout
        self.setup_layout()
        self.setup_callbacks()
    
    def setup_layout(self):
        """Set up the dashboard layout"""
        self.app.layout = html.Div([
            # Header
            html.Div([
                html.Div([
                    html.H1(self.settings["title"], className="header-title"),
                    html.P(self.settings["description"], className="header-description")
                ], style={"display": "inline-block"})
            ], className="header"),
            
            # Tabs for different analyses
            dcc.Tabs(id="tabs", value="overview", children=[
            dcc.Tab(label="🏠 Overview", value="overview"),
            dcc.Tab(label="👥 Provider Analysis", value="provider"),
            dcc.Tab(label="🗺️ Geographic Analysis", value="geographic"),
            dcc.Tab(label="⚠️ Risk Analysis", value="risk"),
            dcc.Tab(label="📈 Comparative Analysis", value="comparative")
            ], style={
                "margin": "20px",
                "fontSize": "1.1em",
                "fontWeight": "bold",
                "boxShadow": "0 2px 4px rgba(0, 0, 0, 0.1)"
            }),
            
            # Content container
            html.Div(id="tab-content"),
            
            # Footer
            html.Div([
                html.P(f"Medicare Provider Analytics Dashboard • Data refreshed: {self.get_last_updated()}"),
                html.P([
                    "Created by Joshua Chang | ", 
                    html.A("GitHub Repository", href="https://github.com/jshchng/medicare-fraud-analysis", target="_blank")
                ])
            ], style={
                "textAlign": "center",
                "padding": "20px",
                "marginTop": "40px",
                "borderTop": "1px solid #ddd",
                "backgroundColor": "#f9f9f9",
                "color": "#666"
            })
        ])

    def setup_callbacks(self):
        """Set up all callbacks for the dashboard"""
        @self.app.callback(
            Output("tab-content", "children"),
            Input("tabs", "value")
        )
        def render_tab_content(tab):
            """Render content based on selected tab"""
            if tab == "overview":
                return self.create_overview_layout()
            elif tab == "provider":
                return self.create_provider_layout()
            elif tab == "geographic":
                return self.create_geographic_layout()
            elif tab == "risk":
                return self.create_risk_layout()
            elif tab == "comparative":
                return self.create_comparative_layout()
            return html.Div([html.H3("Tab content not available")])
        
        # Provider analysis callbacks
        @self.app.callback(
            Output("provider-visualization", "figure"),
            Input("provider-limit", "value"),
            Input("provider-sort-by", "value")
        )
        def update_provider_visualization(limit, sort_by):
            """Update the provider distribution visualization"""
            try:
                df = self.analyzer.analyze_provider_distribution(limit=limit, sort_by=sort_by)
                if df is None or df.empty:
                    return self.create_empty_figure("No data available for provider analysis.")
                
                fig = provider_distribution_plot(df, limit, sort_by)
                if fig is None:
                    return self.create_empty_figure("No valid figure generated.")

                return fig
            except Exception as e:
                logging.error(f"Error updating provider visualization: {e}")
                return self.create_empty_figure(str(e))
        
        # Provider insights callback
        @self.app.callback(
            Output("provider-insights-content", "children"),
            [Input("provider-limit", "value"),
             Input("provider-sort-by", "value")]
        )
        def update_provider_insights(limit, sort_by):
            """Generate insights for the provider distribution plot"""
            try:
                if not limit or not sort_by:
                    return html.Div("No data available for provider analysis. Please select options.", className="notification-warning")
                df = self.analyzer.analyze_provider_distribution(limit=limit, sort_by=sort_by)
                if df is None or df.empty:
                    return html.Div("No data available for insights generation.", className="notification-warning")

                # Generate insights using InsightsGenerator
                insights = self.insights_generator.generate_provider_insights(df, sort_by, limit)

                # Format insights into Markdown
                return html.Div([
                    dcc.Markdown(f"### Key Findings\n" + "\n".join([f"- {insight}" for insight in insights["key_findings"]]), dangerously_allow_html=True),
                    dcc.Markdown(f"### Distribution Patterns\n" + "\n".join([f"- {insight}" for insight in insights["distribution_patterns"]]), dangerously_allow_html=True),
                    dcc.Markdown(f"### Efficiency Insights\n" + "\n".join([f"- {insight}" for insight in insights["efficiency"]]), dangerously_allow_html=True),
                    dcc.Markdown(f"### Anomalies\n" + "\n".join([f"- {insight}" for insight in insights["anomalies"]]), dangerously_allow_html=True),
                    dcc.Markdown(f"### Recommendations\n" + "\n".join([f"- {insight}" for insight in insights["recommendations"]]), dangerously_allow_html=True),
                ])
            except Exception as e:
                logging.error(f"Error generating provider insights: {e}")
                return html.Div(f"Error generating insights: {str(e)}", className="notification-error")
        
        # Geographic analysis callbacks
        @self.app.callback(
            Output("geographic-visualization", "figure"),
            Input("geographic-metric", "value"),
            Input("geographic-viz-type", "value")
        )
        def update_geographic_visualization(metric, viz_type):
            """Update the geographic distribution visualization"""
            try:
                df = self.analyzer.analyze_geographic_distribution(metric=metric, viz_type=viz_type)
                if df is None or df.empty:
                    return self.create_empty_figure("No data available for geographic analysis.")
                
                fig = geographic_distribution_plot(df, metric, viz_type)
                if fig is None:
                    return self.create_empty_figure("No valid figure generated.")
                
                return fig
            except Exception as e:
                logging.error(f"Error updating geographic visualization: {e}")
                return self.create_empty_figure(str(e))
            
        # Geographic insights callback
        @self.app.callback(
            Output("geographic-insights-content", "children"),
            [Input("geographic-metric", "value"),
             Input("geographic-viz-type", "value")]
        )
        def update_geographic_insights(metric, viz_type):
            """Generate insights for the geographic distribution plot"""
            try:
                if not metric:
                    return html.Div("No data available for geographic analysis. Please select options.", className="notification-warning")
                df = self.analyzer.analyze_geographic_distribution(metric=metric, viz_type=viz_type)
                if df is None or df.empty:
                    return html.Div("No data available for insights generation.", className="notification-warning")

                # Generate insights using InsightsGenerator
                insights = self.insights_generator.generate_geographic_insights(df, metric)

                # Format insights into Markdown
                return html.Div([
                    dcc.Markdown(f"### Key Findings\n" + "\n".join([f"- {insight}" for insight in insights["key_findings"]]), dangerously_allow_html=True),
                    dcc.Markdown(f"### Regional Patterns\n" + "\n".join([f"- {insight}" for insight in insights["regional_patterns"]]), dangerously_allow_html=True),
                    dcc.Markdown(f"### Distribution Patterns\n" + "\n".join([f"- {insight}" for insight in insights["distribution_patterns"]]), dangerously_allow_html=True),
                    dcc.Markdown(f"### Anomalies\n" + "\n".join([f"- {insight}" for insight in insights["anomalies"]]), dangerously_allow_html=True),
                    dcc.Markdown(f"### Recommendations\n" + "\n".join([f"- {insight}" for insight in insights["recommendations"]]), dangerously_allow_html=True),
                ])
            except Exception as e:
                logging.error(f"Error generating geographic insights: {e}")
                return html.Div(f"Error generating insights: {str(e)}", className="notification-error")
                
        # Risk analysis callbacks
        @self.app.callback(
            Output("risk-visualization", "figure"),
            Input("risk-limit", "value"),
            Input("risk-provider-types", "value")
        )
        def update_risk_visualization(limit, provider_types):
            """Update the high-risk providers visualization"""
            try:
                df = self.analyzer.analyze_risk_distribution(limit=limit, provider_types=provider_types)
                if df is None or df.empty:
                    return self.create_empty_figure("No data available for risk analysis.")
                
                fig = high_risk_plot(df, limit, provider_types)
                if fig is None:
                    return self.create_empty_figure("No valid figure generated.")
                
                return fig
            except Exception as e:
                logging.error(f"Error updating risk visualization: {e}")
                return self.create_empty_figure(str(e))
            
        # Risk insights callback
        @self.app.callback(
            Output("risk-insights-content", "children"),
            [Input("risk-limit", "value"),
             Input("risk-provider-types", "value")]
        )
        def update_risk_insights(limit, provider_types):
            """Generate insights for the high-risk providers plot"""
            try:
                df = self.analyzer.analyze_risk_distribution(limit=limit, provider_types=provider_types)
                if df is None or df.empty:
                    return html.Div("No data available for insights generation.", className="notification-warning")

                # Generate insights using InsightsGenerator
                insights = self.insights_generator.generate_risk_insights(df, provider_types, limit)

                # Format insights into HTML
                return html.Div([
                    dcc.Markdown(f"### Key Findings\n" + "\n".join([f"- {insight}" for insight in insights["key_findings"]]), dangerously_allow_html=True),
                    dcc.Markdown(f"### Risk Patterns\n" + "\n".join([f"- {insight}" for insight in insights["risk_patterns"]]), dangerously_allow_html=True),
                    dcc.Markdown(f"### Severity\n" + "\n".join([f"- {insight}" for insight in insights["severity"]]), dangerously_allow_html=True),
                    dcc.Markdown(f"### Financial Impact\n" + "\n".join([f"- {insight}" for insight in insights["financial_impact"]]), dangerously_allow_html=True),
                    dcc.Markdown(f"### Recommendations\n" + "\n".join([f"- {insight}" for insight in insights["recommendations"]]), dangerously_allow_html=True),
                ])
            except Exception as e:
                logging.error(f"Error generating risk insights: {e}")
                return html.Div(f"Error generating insights: {str(e)}", className="notification-error")
            
        # Comparative analysis callbacks
        @self.app.callback(
            Output("comparative-visualization", "figure"),
            Input("comparative-by", "value"),
            Input("comparative-metrics", "value")
        )
        def update_comparative_visualization(compare_by, metrics):
            """Update the comparative analysis visualization"""
            try:
                if not metrics:
                    metrics = ["total_medicare_payments", "payment_per_beneficiary"]
                    
                df = self.analyzer.analyze_comparative(compare_by=compare_by, metrics=metrics)
                if df is None or df.empty:
                    return self.create_empty_figure("No data available for comparative analysis.")
                
                fig = comparative_plot(df, compare_by, metrics)
                if fig is None:
                    return self.create_empty_figure("No valid figure generated.")
                
                return fig
            except Exception as e:
                logging.error(f"Error updating comparative visualization: {e}")
                return self.create_empty_figure(str(e))
            
        # Comparative insights callback
        @self.app.callback(
            Output("comparative-insights-content", "children"),
            [Input("comparative-by", "value"),
            Input("comparative-metrics", "value")]
        )
        def update_comparative_insights(compare_by, metrics):
            """Generate insights for the comparative analysis plot"""
            try:
                if not metrics:
                    metrics = ["total_medicare_payments", "payment_per_beneficiary"]
                    
                df = self.analyzer.analyze_comparative(compare_by=compare_by, metrics=metrics)
                if df is None or df.empty:
                    return html.Div("No data available for insights generation.", className="notification-warning")
        
                # Generate insights using InsightsGenerator
                insights = self.insights_generator.generate_comparative_insights(df, compare_by, metrics)
        
                # Format insights into Markdown
                return html.Div([
                    dcc.Markdown(f"### Correlative Patterns\n" + "\n".join([f"- {insight}" for insight in insights["correlations"]])),
                    dcc.Markdown(f"### Metric Insights\n" + "\n".join([f"- {insight}" for insight in insights["metric_insights"]])),
                    dcc.Markdown(f"### Distribution Patterns\n" + "\n".join([f"- {insight}" for insight in insights["distribution_patterns"]])),
                    dcc.Markdown(f"### Anomalies\n" + "\n".join([f"- {insight}" for insight in insights["anomalies"]])),
                    dcc.Markdown(f"### Efficiency Insights\n" + "\n".join([f"- {insight}" for insight in insights["efficiency"]])),
                    dcc.Markdown(f"### Recommendations\n" + "\n".join([f"- {insight}" for insight in insights["recommendations"]])),
                ])
            except Exception as e:
                logging.error(f"Error generating comparative insights: {e}")
                return html.Div(f"Error generating insights: {str(e)}", className="notification-error")
        
        # Add data table callbacks for each analysis type
        for tab in ["provider", "geographic", "risk", "comparative"]:
            @self.app.callback(
                Output(f"{tab}-data-table-container", "children"),
                Input(f"{tab}-show-data", "n_clicks"),
                State(f"{tab}-data-table-container", "children")
            )
            def toggle_data_table(n_clicks, current_children):
                """Toggle data table visibility"""
                if n_clicks is None:
                    return []
                
                # Get the context to determine which tab triggered the callback
                ctx = dash.callback_context
                if not ctx.triggered:
                    return current_children
                
                trigger_id = ctx.triggered[0]["prop_id"].split(".")[0]
                tab = trigger_id.split("-")[0]
                
                # If table is already shown, hide it
                if current_children:
                    return []
                
                # Otherwise, get data and show table
                try:
                    if tab == "provider":
                        df = self.analyzer.analyze_provider_distribution()
                    elif tab == "geographic":
                        df = self.analyzer.analyze_geographic_distribution()
                    elif tab == "risk":
                        df = self.analyzer.analyze_risk_distribution()
                    elif tab == "comparative":
                        df = self.analyzer.analyze_comparative()
                    else:
                        return []
                    
                    if df is None or df.empty:
                        return html.Div("No data available", className="notification-warning")
                    
                    return [
                        html.H4("Data Table"),
                        dash_table.DataTable(
                            data=df.to_dict("records"),
                            columns=[{"name": col.replace("_", " ").title(), "id": col} for col in df.columns],
                            page_size=10,
                            style_table={"overflowX": "auto"},
                            style_cell={
                                "textAlign": "left",
                                "padding": "10px",
                                "whiteSpace": "normal",
                                "height": "auto"
                            },
                            style_header={
                                "backgroundColor": self.settings["theme"]["primary_color"],
                                "color": "white",
                                "fontWeight": "bold"
                            },
                            style_data_conditional=[
                                {
                                    "if": {"row_index": "odd"},
                                    "backgroundColor": "rgb(248, 248, 248)"
                                }
                            ]
                        ),
                        html.Div([
                            html.Button(
                                "Download CSV", 
                                id=f"{tab}-download-button",
                                className="run-button",
                                style={"marginTop": "10px"}
                            ),
                            dcc.Download(id=f"{tab}-download")
                        ])
                    ]
                except Exception as e:
                    logging.error(f"Error creating data table: {e}")
                    return html.Div(f"Error: {str(e)}", className="notification-error")
                
            @self.app.callback(
                Output(f"{tab}-download", "data"),
                Input(f"{tab}-download-button", "n_clicks"),
                prevent_initial_call=True
            )
            def download_csv(n_clicks):
                """Handle CSV download for the specified tab"""
                try:
                    # Get the context to determine which tab triggered the callback
                    ctx = dash.callback_context
                    if not ctx.triggered:
                        return None

                    trigger_id = ctx.triggered[0]["prop_id"].split(".")[0]
                    tab = trigger_id.split("-")[0]

                    # Fetch the appropriate data based on the tab
                    if tab == "provider":
                        df = self.analyzer.analyze_provider_distribution()
                    elif tab == "geographic":
                        df = self.analyzer.analyze_geographic_distribution()
                    elif tab == "risk":
                        df = self.analyzer.analyze_risk_distribution()
                    elif tab == "comparative":
                        df = self.analyzer.analyze_comparative()
                    else:
                        return None

                    if df is None or df.empty:
                        return None

                    # Return the data as a downloadable CSV
                    return dcc.send_data_frame(df.to_csv, f"{tab}_data.csv", index=False)
                except Exception as e:
                    logging.error(f"Error generating CSV for download: {e}")
                    return None
    
    def create_overview_layout(self):
        """Create the overview tab layout"""
        try:
            # Connect and calculate key metrics
            conn = sqlite3.connect(os.path.join("data", "medicare.db"))

            provider_count = pd.read_sql_query(
                "SELECT COUNT(DISTINCT Rndrng_NPI) FROM medicare_providers", conn
            ).iloc[0, 0]

            beneficiary_count = pd.read_sql_query(
                "SELECT SUM(Tot_Benes) FROM medicare_providers", conn
            ).iloc[0, 0]

            total_payments = pd.read_sql_query(
                "SELECT SUM(Tot_Mdcr_Pymt_Amt) FROM medicare_providers", conn
            ).iloc[0, 0]

            avg_payment_per_provider = pd.read_sql_query("""
                SELECT SUM(Tot_Mdcr_Pymt_Amt) * 1.0 / COUNT(DISTINCT Rndrng_NPI)
                AS avg_payment_per_provider FROM medicare_providers
            """, conn).iloc[0, 0]

            avg_payment_per_beneficiary = pd.read_sql_query("""
                SELECT SUM(Tot_Mdcr_Pymt_Amt) * 1.0 / SUM(Tot_Benes)
                AS avg_payment_per_beneficiary FROM medicare_providers
            """, conn).iloc[0, 0]
            
            # Top 5 states by total Medicare payments
            state_df = pd.read_sql_query("""
                SELECT Rndrng_Prvdr_State_Abrvtn AS state,
                       SUM(Tot_Mdcr_Pymt_Amt) AS total_payments
                FROM medicare_providers
                GROUP BY state
                ORDER BY total_payments DESC
                LIMIT 5
            """, conn)
            
            # Top provider types by count
            provider_type_df = pd.read_sql_query("""
                SELECT Rndrng_Prvdr_Type, COUNT(DISTINCT Rndrng_NPI) 
                AS provider_count FROM medicare_providers
                GROUP BY Rndrng_Prvdr_Type
                ORDER BY provider_count DESC
                LIMIT 6
            """, conn)

            conn.close()
            
            # Generate visualizations
            bar_fig = px.bar(
                state_df,
                x="state",
                y="total_payments",
                title="Top 5 States by Medicare Payments",
                labels={"total_payments": "Total Payments ($)", "state": "State"},
                text_auto=".2s",
                template="plotly_white",
                color_discrete_sequence=["#004b87"]
            )
            bar_fig.update_traces(textfont_size=12, textposition="outside")
            bar_fig.update_layout(
                xaxis_title="State",
                yaxis_title="Total Payments ($)",
                margin=dict(t=40, b=10),
                height=400
            )
            
            donut_fig = px.pie(
                provider_type_df,
                values="provider_count",
                names="Rndrng_Prvdr_Type",
                hole=0.5,
                title="Top Provider Types by Volume",
                color_discrete_sequence=px.colors.sequential.Blues
            )
            donut_fig.update_traces(
                textposition='inside', 
                textinfo='percent+label',
                textfont_size=12
            )
            donut_fig.update_layout(
                margin=dict(t=40, b=10),
                height=400
            )


            # Top provider types
            provider_summary = self.analyzer.analyze_provider_distribution(limit=5)

            return html.Div([

                # Key Metrics Section
                html.Div([
                    html.Div([
                        html.H2(f"{provider_count:,}"),
                        html.P("Unique Providers")
                    ], className="metric-card"),
                    html.Div([
                        html.H2(f"{int(beneficiary_count):,}"),
                        html.P("Medicare Beneficiaries")
                    ], className="metric-card"),
                    html.Div([
                        html.H2(f"${int(total_payments / 1_000_000):,}M"),
                        html.P("Total Medicare Payments")
                    ], className="metric-card"),
                    html.Div([
                        html.H2(f"${int(avg_payment_per_provider):,}"),
                        html.P("Avg. Payment per Provider")
                    ], className="metric-card"),
                    html.Div([
                        html.H2(f"${int(avg_payment_per_beneficiary):,}"),
                        html.P("Avg. Payment per Beneficiary")
                    ], className="metric-card")
                ], style={
                    "display": "flex",
                    "flexWrap": "wrap",
                    "gap": "450px",
                    "justifyContent": "center",
                    "margin": "20px 0"
                }),

                # Welcome Message
                html.Div([
                    html.H3("Medicare Provider Analytics Dashboard", className="insights-title"),
                    html.Div([
                        html.P("This dashboard enables fast, interactive exploration of Medicare provider-level data, payments, and beneficiary trends across the U.S."),
                        html.P("Navigate through provider breakdowns, geographic patterns, risk flags, and comparative metrics for data-driven insights."),
                        html.P("Built with Python, Dash, and SQL — optimized for healthcare operations, fraud detection, and payment efficiency use cases.")
                    ], className="insights-content")
                ], className="insights-panel"),

                # Dashboard Features
                html.Div([
                    html.H3("Dashboard Features", className="insights-title"),
                    html.Div([
                        html.Div([
                            html.H4("Provider Insights"),
                            html.P("Track spending patterns across top provider types.")
                        ], className="feature-card"),
                        html.Div([
                            html.H4("Geographic Breakdown"),
                            html.P("Compare Medicare metrics across all U.S. states.")
                        ], className="feature-card"),
                        html.Div([
                            html.H4("Risk Analysis"),
                            html.P("Identify providers with unusual payment patterns for potential audit.")
                        ], className="feature-card"),
                        html.Div([
                            html.H4("Comparative Analysis"),
                            html.P("Assess performance metrics across providers and states.")
                        ], className="feature-card")
                    ], style={
                        "display": "flex",
                        "flexWrap": "wrap",
                        "gap": "20px",
                        "justifyContent": "space-between"
                    })
                ], className="insights-panel"),
                
                # Add charts
                html.Div([
                    html.H3("Regional and Provider Insights", className="insights-title"),
                    html.Div([
                        dcc.Graph(figure=bar_fig, style={"width": "48%"}),
                        dcc.Graph(figure=donut_fig, style={"width": "48%"})
                    ], style={
                        "display": "flex",
                        "flexWrap": "wrap",
                        "justifyContent": "space-between"
                    })
                ], className="insights-panel"),

                # Top Provider Types
                html.Div([
                    html.H3("Top Provider Types by Medicare Payments", className="insights-title"),
                    dash_table.DataTable(
                        data=provider_summary.to_dict("records") if provider_summary is not None else [],
                        columns=[
                            {"name": "Provider Type", "id": "Rndrng_Prvdr_Type"},
                            {"name": "Provider Count", "id": "provider_count", "type": "numeric", "format": {"specifier": ","}},
                            {"name": "Total Beneficiaries", "id": "total_beneficiaries", "type": "numeric", "format": {"specifier": ","}},
                            {"name": "Total Medicare Payments", "id": "total_medicare_payments", "type": "numeric", "format": {"specifier": "$,.2f"}}
                        ],
                        style_table={"overflowX": "auto"},
                        style_cell={
                            "textAlign": "left",
                            "padding": "10px",
                            "whiteSpace": "normal",
                            "height": "auto"
                        },
                        style_header={
                            "backgroundColor": self.settings["theme"]["primary_color"],
                            "color": "white",
                            "fontWeight": "bold"
                        },
                        style_data_conditional=[
                            {
                                "if": {"row_index": "odd"},
                                "backgroundColor": "rgb(248, 248, 248)"
                            }
                        ]
                    )
                ], className="insights-panel"),

            ])
        except Exception as e:
            logging.error(f"Error creating overview layout: {e}")
            return html.Div([
                html.H3("Error Loading Overview"),
                html.P(f"An error occurred: {str(e)}"),
                html.P("Please check the database connection and try refreshing the page.")
            ], className="notification-error")

    
    def create_provider_layout(self):
        """Create the provider analysis tab layout"""
        return html.Div([
            # Control panel
            html.Div([
                html.H3("Provider Analysis Controls", className="control-title"),
                html.Label("Number of Provider Types:"),
                dcc.Slider(
                    id="provider-limit",
                    min=5,
                    max=25,
                    step=5,
                    value=15,
                    marks={i: str(i) for i in range(5, 30, 5)}
                ),
                html.Label("Sort By:"),
                dcc.Dropdown(
                    id="provider-sort-by",
                    options=[
                        {"label": "Total Medicare Payments", "value": "total_medicare_payments"},
                        {"label": "Provider Count", "value": "provider_count"},
                        {"label": "Total Beneficiaries", "value": "total_beneficiaries"},
                        {"label": "Total Services", "value": "total_services"},
                        {"label": "Payment Per Provider", "value": "avg_payment_per_provider"},
                        {"label": "Payment Per Beneficiary", "value": "avg_payment_per_beneficiary"},
                        {"label": "Payment Per Service", "value": "avg_payment_per_service"}
                    ],
                    value="total_medicare_payments"
                ),
                html.Button(
                    "Show/Hide Data Table", 
                    id="provider-show-data", 
                    className="run-button"
                )
            ], className="control-panel"),
            
            # Visualization panel
            html.Div([
                html.H3("Provider Distribution Analysis"),
                dcc.Graph(id="provider-visualization"),
                html.Div(id="provider-data-table-container")
            ], className="visualization-panel"),
            
            # Insights panel
        html.Div([
            html.H3("Provider Distribution Insights", className="insights-title"),
            html.Div(id="provider-insights-content", className="insights-content")
        ], className="insights-panel")
    ], className="main-content")
    
    def create_geographic_layout(self):
        """Create the geographic analysis tab layout"""
        return html.Div([
            # Control panel
            html.Div([
                html.H3("Geographic Analysis Controls", className="control-title"),
                html.Label("Metric:"),
                dcc.Dropdown(
                    id="geographic-metric",
                    options=[
                        {"label": "Payment Per Beneficiary", "value": "payment_per_beneficiary"},
                        {"label": "Total Medicare Payments", "value": "total_medicare_payments"},
                        {"label": "Provider Count", "value": "provider_count"},
                        {"label": "Total Beneficiaries", "value": "total_beneficiaries"},
                        {"label": "Payment Per Service", "value": "payment_per_service"},
                        {"label": "Standardized Payment Per Beneficiary", "value": "standardized_payment_per_beneficiary"}
                    ],
                    value="payment_per_beneficiary"
                ),
                html.Label("Visualization Type:"),
                dcc.RadioItems(
                    id="geographic-viz-type",
                    options=[
                        {"label": "Map", "value": "map"},
                        {"label": "Bar Chart", "value": "bar"}
                    ],
                    value="map",
                    labelStyle={"display": "inline-block", "marginRight": "20px"}
                ),
                html.Button(
                    "Show/Hide Data Table", 
                    id="geographic-show-data", 
                    className="run-button"
                )
            ], className="control-panel"),
            
            # Visualization panel
            html.Div([
                html.H3("Geographic Distribution Analysis"),
                dcc.Graph(id="geographic-visualization"),
                html.Div(id="geographic-data-table-container")
            ], className="visualization-panel"),
            
            # Insights panel
            html.Div([
                html.H3("Geographic Distribution Insights", className="insights-title"),
                html.Div(id="geographic-insights-content", className="insights-content")
            ], className="insights-panel")
        ], className="main-content")

    def create_risk_layout(self):
        """Create the risk analysis tab layout"""
        return html.Div([
            # Control panel
            html.Div([
                html.H3("Risk Analysis Controls", className="control-title"),
                html.Label("Number of Providers:"),
                dcc.Slider(
                    id="risk-limit",
                    min=10,
                    max=50,
                    step=5,
                    value=25,
                    marks={i: str(i) for i in range(10, 55, 10)}
                ),
                html.Label("Provider Types:"),
                dcc.RadioItems(
                    id="risk-provider-types",
                    options=[
                        {"label": "Top 5 Provider Types", "value": "top5"},
                        {"label": "Top 10 Provider Types", "value": "top10"},
                        {"label": "All Provider Types", "value": "all"}
                    ],
                    value="top5",
                    labelStyle={"display": "block", "marginBottom": "5px"}
                ),
                html.Button(
                    "Show/Hide Data Table", 
                    id="risk-show-data", 
                    className="run-button"
                )
            ], className="control-panel"),
            
            # Visualization panel
            html.Div([
                html.H3("High-Risk Provider Analysis"),
                dcc.Graph(id="risk-visualization"),
                html.Div(id="risk-data-table-container")
            ], className="visualization-panel"),
            
            # Insights panel
            html.Div([
                html.H3("High Risk Provider Insights", className="insights-title"),
                html.Div(id="risk-insights-content", className="insights-content")
            ], className="insights-panel")
        ], className="main-content")
    
    def create_comparative_layout(self):
        """Create the comparative analysis tab layout"""
        return html.Div([
            # Control panel
            html.Div([
                html.H3("Comparative Analysis Controls", className="control-title"),
                html.Label("Compare By:"),
                dcc.RadioItems(
                    id="comparative-by",
                    options=[
                        {"label": "Provider Type", "value": "provider_type"},
                        {"label": "State", "value": "state"}
                    ],
                    value="provider_type",
                    labelStyle={"display": "inline-block", "marginRight": "20px"}
                ),
                html.Label("Metrics:"),
                dcc.Checklist(
                    id="comparative-metrics",
                    options=[
                        {"label": "Total Medicare Payments", "value": "total_medicare_payments"},
                        {"label": "Payment Per Beneficiary", "value": "payment_per_beneficiary"},
                        {"label": "Payment Per Service", "value": "payment_per_service"},
                        {"label": "Provider Count", "value": "provider_count"},
                        {"label": "Total Beneficiaries", "value": "total_beneficiaries"}
                    ],
                    value=["total_medicare_payments", "payment_per_beneficiary"],
                    labelStyle={"display": "block", "marginBottom": "5px"}
                ),
                html.Button(
                    "Show/Hide Data Table", 
                    id="comparative-show-data", 
                    className="run-button"
                )
            ], className="control-panel"),
            
            # Visualization panel
            html.Div([
                html.H3("Comparative Analysis"),
                dcc.Graph(id="comparative-visualization"),
                html.Div(id="comparative-data-table-container")
            ], className="visualization-panel"),
            
            # Insights panel
            html.Div([
                html.H3("Comparative Insights", className="insights-title"),
                html.Div(id="comparative-insights-content", className="insights-content")
            ], className="insights-panel")
        ], className="main-content")
    
    def create_error_figure(self, error_message):
        """Create an error figure with the given message"""
        return {
            "data": [],
            "layout": {
                "xaxis": {"visible": False},
                "yaxis": {"visible": False},
                "annotations": [
                    {
                        "text": f"Error: {error_message}",
                        "xref": "paper",
                        "yref": "paper",
                        "showarrow": False,
                        "font": {
                            "size": 16,
                            "color": "red"
                        }
                    }
                ]
            }
        }
        
    def create_empty_figure(self, message="No data available"):
        return {
            "data": [],
            "layout": {
                "xaxis": {"visible": False},
                "yaxis": {"visible": False},
                "annotations": [
                    {
                        "text": message,
                        "xref": "paper",
                        "yref": "paper",
                        "showarrow": False,
                        "font": {
                            "size": 16,
                            "color": "gray"
                        }
                    }
                ]
            }
    }
        
    def get_last_updated(self):
        """Retrieve the last_updated value from settings.json"""
        settings_path = os.path.join("assets", "settings.json")
        try:
            with open(settings_path, "r") as f:
                settings = json.load(f)
                return settings.get("data_refresh", {}).get("last_updated", "Unknown")
        except Exception as e:
            logging.error(f"Error reading last_updated from settings.json: {e}")
            return "Unknown"
    
    def run(self, debug=False, host="localhost", port=8050):
        """Run the dashboard server"""
        try:
            logging.info(f"Starting dashboard server on {host}:{port}")
            self.app.run(debug=debug, host=host, port=port)
        except Exception as e:
            logging.error(f"Error running dashboard server: {e}")
            raise

# If run directly
if __name__ == "__main__":
    try:
        # Create and run the dashboard
        dashboard = MedicareDashboard()
        dashboard.run(debug=True)
    except Exception as e:
        logging.error(f"Error running dashboard: {e}")