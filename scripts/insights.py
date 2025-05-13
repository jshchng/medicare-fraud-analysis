import numpy as np
import logging
from collections import defaultdict

COLUMN_LABELS = {
            'provider_count': 'total providers',
            'avg_payment_per_provider': 'average payment per provider',
            'avg_payment_per_beneficiary': 'average payment per beneficiary',
            'avg_payment_per_service': 'average payment per service'
        }

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/insights.log'),
        logging.StreamHandler()
    ]
)

class InsightsGenerator:
    """
    A class to automatically generate data-driven insights for Medicare provider analysis.
    This enhances the dashboard with actionable intelligence that highlights significant patterns,
    anomalies, and potential fraud indicators in the Medicare data.
    """
    
    def __init__(self, analyzer):
        """
        Initialize the insights generator with the Medicare analyzer
        
        Parameters:
        -----------
        analyzer : MedicareAnalyzer
            The analyzer object that provides data for insights generation
        """
        self.analyzer = analyzer
        self.cache = {}
    
    def generate_provider_insights(self, df, sort_by="total_medicare_payments", limit=15):
        insights = defaultdict(list)
        
        if df is None or df.empty:
            insights["errors"].append("No data available for provider analysis.")
            return dict(insights)
        
        insights["key_findings"] = []
        insights["distribution_patterns"] = []
        insights["efficiency"] = []
        insights["anomalies"] = []
        insights["recommendations"] = []
        
        # Top and bottom provider insights
        df = df.sort_values(by=sort_by, ascending=False).head(limit)
        top_provider = df.iloc[0]
        bottom_provider = df.iloc[-1]
        
        # Top provider
        median_val = df[sort_by].median()
        pct_diff = (top_provider[sort_by] / median_val - 1) * 100
        sort_label = COLUMN_LABELS.get(sort_by, sort_by.replace('_', ' ').title())
        insights["key_findings"].append(
            f"**{top_provider['Rndrng_Prvdr_Type']}** ranks highest in {sort_label.lower()}, "
            f"receiving ${top_provider[sort_by]:,.2f} — {pct_diff:.1f}% above median."
        )
        
        # Concentration analysis
        top_3_pct = df.iloc[:3][sort_by].sum() / df[sort_by].sum() * 100
        insights["distribution_patterns"].append(
            f"Top 3 provider types account for {top_3_pct:.1f}% of {sort_label.lower()}."
        )
        
        # Efficiency analysis if applicable metrics exist
        if {"total_medicare_payments", "total_beneficiaries"}.issubset(df.columns):
            df["cost_per_beneficiary"] = df["total_medicare_payments"] / df["total_beneficiaries"]
            efficient = df.sort_values("cost_per_beneficiary").iloc[0]
            inefficient = df.sort_values("cost_per_beneficiary", ascending=False).iloc[0]

            insights["efficiency"].append(
                f"Most efficient: **{efficient['Rndrng_Prvdr_Type']}** "
                f"(${efficient['cost_per_beneficiary']:.2f} per beneficiary)."
            )
            insights["efficiency"].append(
                f"Least efficient: **{inefficient['Rndrng_Prvdr_Type']}** "
                f"(${inefficient['cost_per_beneficiary']:.2f} per beneficiary)."
            )
        
        # Anomaly detection
        mean, std = df[sort_by].mean(), df[sort_by].std()
        logging.info(f"Anomaly detection for {sort_by}: mean={mean:.2f}, std={std:.2f}")

        if std == 0:
            logging.warning(f"Standard deviation for {sort_by} is zero. Skipping anomaly detection.")
            insights["anomalies"].append(f"No variation detected for {sort_by.replace('_', ' ')} due to zero variance.")
        else:
            outliers = df[np.abs(df[sort_by] - mean) > 2 * std]
            if not outliers.empty:
                insights["anomalies"].append(
                    f"Detected {len(outliers)} provider type(s) with statistically significant deviations."
                )
                for _, row in outliers.iterrows():
                    z_score = (row[sort_by] - mean) / std
                    insights["anomalies"].append(
                            f"**{row['Rndrng_Prvdr_Type']}** is {abs(z_score):.1f} standard deviations "
                            f"{'above' if z_score > 0 else 'below'} the mean."
                    )
            else:
                insights["anomalies"].append(f"No significant anomalies detected for {sort_by.replace('_', ' ')}.")
        
        # Recommendations based on insights
        insights["recommendations"].append(
            f"Investigate high reimbursements to **{top_provider['Rndrng_Prvdr_Type']}** for cost justification."
        )
        
        if insights["anomalies"]:
            insights["recommendations"].append(
                "Flag and audit outlier provider types for compliance review."
            )
        
        return dict(insights)
    
    def generate_geographic_insights(self, df, metric="payment_per_beneficiary"):
        insights = defaultdict(list)
        
        if df is None or df.empty:
            insights["errors"].append("No data available for geographic analysis.")
            return dict(insights)
        
        # Ensure all keys exist
        insights["key_findings"] = []
        insights["regional_patterns"] = []
        insights["distribution_patterns"] = []
        insights["anomalies"] = []
        insights["recommendations"] = []
        
        # Normalize column name for state
        state_col = next((col for col in df.columns if 'state' in col.lower()), None)
        if not state_col:
            insights["errors"].append("State column not found in geographic data.")
            return dict(insights)
        
        # Ensure metric exists in dataframe
        if metric not in df.columns:
            insights["errors"].append(f"Metric '{metric}' not found in geographic data.")
            return dict(insights)
        
        # Sort dataframe by metric for easier analysis
        df_sorted = df.sort_values(by=metric, ascending=False)
        
        # Top and bottom states
        top_state = df_sorted.iloc[0]
        bottom_state = df_sorted.iloc[-1]
        pct_diff = (top_state[metric] / bottom_state[metric] - 1) * 100
        
        insights["key_findings"].append(
            f"**{top_state[state_col]}** has the highest {metric.replace('_', ' ')} (${top_state[metric]:,.2f}), "
            f"{pct_diff:.1f}% above **{bottom_state[state_col]}** (${bottom_state[metric]:,.2f})."
        )
        
        # Regional analysis
        regions = {
            'Northeast': ['ME','NH','VT','MA','RI','CT','NY','NJ','PA'],
            'Midwest': ['OH','MI','IN','IL','WI','MN','IA','MO','ND','SD','NE','KS'],
            'South': ['DE','MD','DC','VA','WV','NC','SC','GA','FL','KY','TN','AL','MS','AR','LA','OK','TX'],
            'West': ['MT','ID','WY','CO','NM','AZ','UT','NV','WA','OR','CA','AK','HI']
        }

        region_averages = {
            name: df[df[state_col].isin(states)][metric].mean()
            for name, states in regions.items()
            if not df[df[state_col].isin(states)].empty
        }

        if region_averages:
            high = max(region_averages, key=region_averages.get)
            low = min(region_averages, key=region_averages.get)
            insights["regional_patterns"].append(
                f"**{high}** has the highest regional average "
                f"(${region_averages[high]:,.2f}); **{low}** has the lowest (${region_averages[low]:,.2f})."
            )
        
        # Variability analysis
        cv = df[metric].std() / df[metric].mean() * 100
        variability = "minimal" if cv < 10 else "moderate" if cv < 25 else "significant"
        insights["distribution_patterns"].append(
            f"{variability.title()} variability in {metric.replace('_', ' ')} across states (CV = {cv:.1f}%)."
        )
        
        # Anomaly detection
        mean, std = df[metric].mean(), df[metric].std()
        outliers = df[np.abs(df[metric] - mean) > 2 * std]
        
        if not outliers.empty:
            insights["anomalies"].append(
                f"**{len(outliers)}** states show statistically significant deviation in {metric.replace('_', ' ')}."
            )
            for _, outlier in outliers.iterrows():
                z_score = (outlier[metric] - mean) / std
                insights["anomalies"].append(
                    f"**{outlier[state_col]}** is {abs(z_score):.1f} standard deviations "
                    f"{'above' if z_score > 0 else 'below'} the mean."
                )
        
        # Recommendations
        if "anomalies" in insights and insights["anomalies"]:
            insights["recommendations"].append(
                "Focus compliance audits on states with significantly higher than average payments."
            )
            
        insights["recommendations"].append(
            f"Investigate the underlying factors behind the {metric.replace('_', ' ')} "
            f"disparities between {top_state[state_col]} and {bottom_state[state_col]}."
        )
        
        return dict(insights)
    
    def generate_risk_insights(self, df, provider_types="top5", limit=25):
        insights = defaultdict(list)
        
        if df is None or df.empty:
            insights["errors"].append("No data available for risk analysis.")
            return dict(insights)
        
        insights["key_findings"] = []
        insights["risk_patterns"] = []
        insights["severity"] = []
        insights["financial_impact"] = []
        insights["recommendations"] = []
        
        # Log the DataFrame columns
        logging.info(f"Columns in DataFrame: {df.columns}")
        
        # Get key columns
        provider_col = next((col for col in df.columns if 'npi' in col.lower()), None)
        provider_type_col = next((col for col in df.columns if 'provider_type' in col.lower() or 'Rndrng_Prvdr_Type' in col), None)
        payment_col = next((col for col in df.columns if 'total_standardized_payment' in col.lower()), None)
        payment_per_service_col = next((col for col in df.columns if 'payment_per_service' in col.lower()), None)
        
        logging.info(f"Identified columns: provider_col={provider_col}, provider_type_col={provider_type_col}, payment_col={payment_col}, payment_per_service_col={payment_per_service_col}")
        
        if not all([provider_col, provider_type_col, payment_col, payment_per_service_col]):
            logging.error("Required columns missing in risk analysis data.")
            insights["errors"].append("Required columns missing in risk analysis data.")
            return dict(insights)
        
        # Top risk providers
        top_risk_provider = df.iloc[0]
        median_pps = df[payment_per_service_col].median()
        uplift_pct = ((top_risk_provider[payment_per_service_col] / median_pps) - 1) * 100

        insights["key_findings"].append(
            f"**Provider {top_risk_provider[provider_col]}** ({top_risk_provider[provider_type_col]}) has the highest per-service payment "
            f"at **${top_risk_provider[payment_per_service_col]:,.2f}**, which is **{uplift_pct:.1f}% above the median**. "
            f"This flags it as a primary fraud risk candidate."
        )
        
        # Risk pattern: dominant provider type
        top_type = df[provider_type_col].value_counts().idxmax()
        pct = df[provider_type_col].value_counts(normalize=True)[top_type] * 100
        insights["risk_patterns"].append(
            f"**{top_type}** providers comprise **{pct:.1f}%** of high-risk cases, suggesting concentrated risk exposure."
        )
        
        # Severity analysis
        median_payment = df[payment_per_service_col].median()
        severe_cases = df[df[payment_per_service_col] > 3 * median_payment]
        
        if not severe_cases.empty:
            insights["severity"].append(
                f"**{len(severe_cases)}** providers have payment per service more than 3x the median, "
                f"indicating potential severe cases for immediate investigation."
            )
        
        # Payment impact analysis
        total_payment = df[payment_col].sum()
        top_3_payment = df.iloc[:3][payment_col].sum()
        top_3_pct = top_3_payment / total_payment * 100
        
        insights["financial_impact"].append(
            f"The top 3 high-risk providers account for ${top_3_payment:,.2f} ({top_3_pct:.1f}%) "
            f"of total payments among the high-risk group."
        )
        
        # Recommendations
        insights["recommendations"] += [
            f"Flag **{top_risk_provider[provider_col]}** ({top_risk_provider[provider_type_col]}) for immediate audit due to anomalous payment patterns.",
            f"Initiate targeted review of **{top_type}** providers to investigate structural billing risks."
        ]
        
        return dict(insights)
    
    def generate_comparative_insights(self, df, compare_by="Rndrng_Prvdr_Type", metrics=None):
        insights = defaultdict(list)
        
        if df is None or df.empty:
            insights["errors"].append("No data available for comparative analysis.")
            return dict(insights)
        
        insights["errors"] = []
        insights["correlations"] = []
        insights["metric_insights"] = []
        insights["distribution_patterns"] = []
        insights["anomalies"] = []
        insights["efficiency"] = []
        insights["recommendations"] = []
        
        if metrics is None:
            metrics = ["total_medicare_payments", "payment_per_beneficiary"]
            
        # Log the DataFrame columns for debugging
        logging.info(f"Columns in comparative DataFrame: {df.columns.tolist()}")
        logging.info(f"compare_by parameter: {compare_by}")

        # Define a mapping for common column aliases
        column_aliases = {
            "provider_type": "Rndrng_Prvdr_Type",
            "state": "Rndrng_Prvdr_State_Abrvtn",
        }
    
        # Resolve the actual column name
        compare_by_resolved = column_aliases.get(compare_by.lower(), compare_by)
        category_col = next((col for col in df.columns if col.strip().lower() == compare_by_resolved.strip().lower()), None)
        
        logging.info(f"Matched column for compare_by: {category_col}")
        
        # Check if metrics exist in dataframe
        missing_metrics = [m for m in metrics if m not in df.columns]
        if missing_metrics:
            insights["errors"].append(f"Metrics {', '.join(missing_metrics)} not found in comparative data.")
            metrics = [m for m in metrics if m in df.columns]
            if not metrics:
                return dict(insights)
        
        # Cross-metric correlations
        if len(metrics) >= 2:

            correlations = {}
            for i in range(len(metrics)):
                for j in range(i+1, len(metrics)):
                    metric1, metric2 = metrics[i], metrics[j]
                    if metric1 in df.columns and metric2 in df.columns:
                        corr = df[metric1].corr(df[metric2])
                        correlations[(metric1, metric2)] = corr
                        
            logging.info(f"All metric correlations for compare_by={compare_by}: {correlations}")
            
            # Report strong correlations
            strong_corrs = {k: v for k, v in correlations.items() if abs(v) > 0.7}
            for (m1, m2), corr in strong_corrs.items():
                direction = "positive" if corr > 0 else "negative"
                insights["correlations"].append(
                    f"Strong **{direction} correlation** ({corr:.2f}) between "
                    f"**{m1.replace('_', ' ')}** and **{m2.replace('_', ' ')}**."
                )
        
        # Analyze each metric individually
        for metric in metrics:
            if metric not in df.columns:
                continue
                
            df_sorted = df.sort_values(by=metric, ascending=False)
            top_category = df_sorted.iloc[0]
            bottom_category = df_sorted.iloc[-1]
            
            insights["metric_insights"].append(
                f"**{top_category[category_col]}** leads in {metric.replace('_', ' ')} "
                f"(${top_category[metric]:,.2f}), {(top_category[metric]/bottom_category[metric] - 1) * 100:.1f}% "
                f"greater than **{bottom_category[category_col]}** (${bottom_category[metric]:,.2f})."
            )
            
            # Distribution analysis
            cv = df[metric].std() / df[metric].mean() * 100  # Coefficient of variation
            if cv > 50:
                insights["distribution_patterns"].append(
                    f"High variability in **{metric.replace('_', ' ')}** (CV: {cv:.1f}%) suggests inconsistent performance. "
                )
            
            # Anomaly detection
            mean, std = df[metric].mean(), df[metric].std()
            outliers = df[np.abs(df[metric] - mean) > 2 * std]
            
            if len(outliers) <= 3 and not outliers.empty:  # Only report if there are just a few outliers
                for _, outlier in outliers.iterrows():
                    z_score = (outlier[metric] - mean) / std
                    insights["anomalies"].append(
                        f"**{outlier[category_col]}** is an outlier for {metric.replace('_', ' ')}, "
                        f"{abs(z_score):.1f} standard deviations {'above' if z_score > 0 else 'below'} the mean."
                    )
        
        # If comparing provider types, look for efficiency insights
        if all(m in df.columns for m in ["total_medicare_payments", "total_beneficiaries"]):
            df_eff = df.copy()
            df_eff["cost_efficiency"] = df_eff["total_medicare_payments"] / df_eff["total_beneficiaries"]
            
            efficient = df_eff.sort_values("cost_efficiency").iloc[0]
            inefficient = df_eff.sort_values("cost_efficiency", ascending=False).iloc[0]
            
            insights["efficiency"].append(
                f"**{efficient[category_col]}** has the best cost efficiency "
                f"(${efficient['cost_efficiency']:.2f} per beneficiary), while "
                f"**{inefficient[category_col]}** is least efficient "
                f"(${inefficient['cost_efficiency']:.2f} per beneficiary)."
            )
        else:
            logging.warning("Required metrics for efficiency insights are missing.")
            insights["efficiency"].append("Efficiency insights could not be generated due to missing metrics.")
        
        # Recommendations
        if insights["anomalies"]:
            insights["recommendations"].append(
                f"Audit flagged outliers to assess potential fraud or operational issues."
            )
        if insights["correlations"]:
            insights["recommendations"].append(
                "Use strong metric correlations to optimize care delivery and payment models."
            )
        if insights["metric_insights"]:
            top_metric = metrics[0].replace('_', ' ')
            insights["recommendations"].append(
                f"Benchmark high-performing categories to inform targeted interventions."
            )
        if insights["distribution_patterns"]:
            insights["recommendations"].append(
                f"Reduce operational inconsistencies by enforcing standard billing protocols for {metrics[0].replace('_', ' ')} "
                f"across all {compare_by.replace('_', ' ')}s with excessive variability."
            )
        if insights["efficiency"]:
            insights["recommendations"].append(
                f"Investigate practices of **{efficient[category_col]}** for scalable cost-saving strategies."
            )
        
        # Fallback for missing insights
        if not insights["efficiency"]:
            insights["efficiency"].append("No efficiency insights available for the selected data.")
        if not insights["correlations"]:
            insights["correlations"].append("No significant correlations found between the selected metrics.")
        if not insights["recommendations"]:
            insights["recommendations"].append("No specific recommendations available for the selected data.")
        
        return dict(insights)
    
    def format_insights_html(self, insights_dict, title="Data Insights"):
        """
        Format insights dictionary as HTML content
        
        Parameters:
        -----------
        insights_dict : dict
            Dictionary of insights with categories as keys and insight lists as values
        title : str
            Title for the insights panel
            
        Returns:
        --------
        str
            HTML formatted insights
        """
        if not insights_dict:
            return f"<h3>{title}</h3><p>No insights available for the current data selection.</p>"
        
        # Order categories for consistent display
        category_order = [
            "key_findings", 
            "distribution_patterns", 
            "regional_patterns",
            "correlations",
            "metric_insights",
            "risk_patterns",
            "severity",
            "financial_impact",
            "efficiency",
            "anomalies",
            "recommendations",
            "errors"
        ]
        
        # Category display names
        category_names = {
            "key_findings": "Key Findings",
            "distribution_patterns": "Distribution Patterns",
            "regional_patterns": "Regional Patterns",
            "correlations": "Metric Correlations",
            "metric_insights": "Metric Analysis",
            "risk_patterns": "Risk Patterns",
            "severity": "Severity Assessment",
            "financial_impact": "Financial Impact",
            "efficiency": "Efficiency Analysis",
            "anomalies": "Statistical Anomalies",
            "recommendations": "Recommendations",
            "errors": "Data Issues"
        }
        
        html = f"<h3>{title}</h3>"
        
        # Add insights by category in specified order
        for category in category_order:
            if category in insights_dict and insights_dict[category]:
                html += f"<h4>{category_names.get(category, category.replace('_', ' ').title())}</h4>"
                html += "<ul>"
                for insight in insights_dict[category]:
                    html += f"<li>{insight}</li>"
                html += "</ul>"
        
        # Add any remaining categories not in the predefined order
        remaining_categories = set(insights_dict.keys()) - set(category_order)
        for category in remaining_categories:
            if insights_dict[category]:
                html += f"<h4>{category.replace('_', ' ').title()}</h4>"
                html += "<ul>"
                for insight in insights_dict[category]:
                    html += f"<li>{insight}</li>"
                html += "</ul>"
        
        return html