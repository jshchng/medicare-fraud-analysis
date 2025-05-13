import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots

COLUMN_LABELS = {
            'provider_count': 'Total Providers',
            'avg_payment_per_provider': 'Average Payment Per Provider',
            'avg_payment_per_beneficiary': 'Average Payment Per Beneficiary',
            'avg_payment_per_service': 'Average Payment Per Service'
        }

def provider_distribution_plot(df, limit, sort_by):
    # Ensure the DataFrame is sorted and limited
    df = df.sort_values(by=sort_by, ascending=False).head(limit)

    # Determine if the selected metric requires a dollar sign
    dollar_metrics = [
        "total_medicare_payments",
        "avg_payment_per_provider",
        "avg_payment_per_beneficiary",
        "avg_payment_per_service"
    ]
    is_dollar_metric = sort_by in dollar_metrics
    
    coloraxis_title = COLUMN_LABELS.get(sort_by, sort_by.replace("_", " ").title())
    if is_dollar_metric:
        coloraxis_title += " ($)"
    
    # Create a horizontal bar chart with Plotly
    fig = px.bar(
        df,
        y='Rndrng_Prvdr_Type',
        x=sort_by,
        orientation='h',
        title=f'Top {limit} Provider Types by {sort_by.replace("_", " ").title()}',
        labels={
            'Rndrng_Prvdr_Type': 'Provider Type',
            sort_by: sort_by.replace("_", " ").title()
        },
        color='avg_payment_per_beneficiary',
        color_continuous_scale='Viridis',
        text=sort_by,
        hover_data={
            'provider_count': ':.0f',
            'total_beneficiaries': ':.0f',
            'avg_payment_per_provider': ':.2f',
            'avg_payment_per_beneficiary': ':.2f',
            'avg_payment_per_service': ':.2f'
        }
    )
    fig.update_layout(
        height=800,
        xaxis_title=f"{sort_by.replace('_', ' ').title()} {'($)' if is_dollar_metric else ''}",
        yaxis_title='Provider Type',
        coloraxis_colorbar_title=coloraxis_title,
        margin=dict(l=20, r=20, t=50, b=20)
    )
    fig.update_traces(
        texttemplate=f"{'$%{text:.2f}' if is_dollar_metric else '%{text:.0f}'}",
        textposition='outside'
    )
    return fig

def geographic_distribution_plot(df, metric, viz_type):
    coloraxis_title = COLUMN_LABELS.get(metric, metric.replace("_", " ").title())
    if metric in ["payment_per_beneficiary", "standardized_payment_per_beneficiary", "total_medicare_payments", "payment_per_service"]:
        coloraxis_title += " ($)"
        
    if viz_type == "map":
        fig = px.choropleth(
            df,
            locations='Rndrng_Prvdr_State_Abrvtn',
            locationmode='USA-states',
            color=metric,
            scope='usa',
            title=f'Medicare {metric.replace("_", " ").title()} by State',
            color_continuous_scale='Viridis',
            labels={
                'Rndrng_Prvdr_State_Abrvtn': 'State',
                metric: metric.replace("_", " ").title()
            },
            hover_data=[
                'provider_count', 'total_beneficiaries', 
                'total_medicare_payments', 'payment_per_service'
            ]
        )
        fig.update_layout(
            height=600,
            geo=dict(
                showlakes=True,
                lakecolor='rgb(255, 255, 255)'
            ),
            coloraxis_colorbar_title=coloraxis_title,
            margin=dict(l=0, r=0, t=40, b=0)
        )
        return fig
    else:  # Bar chart
        # Sort by the selected metric
        df = df.sort_values(by=metric, ascending=False)
        fig = px.bar(
            df,
            x='Rndrng_Prvdr_State_Abrvtn',
            y=metric,
            title=f'Medicare {metric.replace("_", " ").title()} by State',
            labels={
                'Rndrng_Prvdr_State_Abrvtn': 'State',
                metric: metric.replace("_", " ").title()
            },
            color=metric,
            color_continuous_scale='Viridis',
            hover_data=[
                'provider_count', 'total_beneficiaries', 
                'total_medicare_payments', 'payment_per_service'
            ]
        )
        fig.update_layout(
            xaxis_title='State',
            yaxis_title=f"{metric.replace('_', ' ').title()} {'($)' if metric in ['payment_per_beneficiary', 'total_medicare_payments', 'payment_per_service'] else ''}",
            coloraxis_colorbar_title=coloraxis_title,
            xaxis_tickangle=-45,
            margin=dict(l=20, r=20, t=50, b=80)
        )
        return fig

def high_risk_plot(df, limit, provider_types):
    # Filter by provider types if specified
    if provider_types == "top5":
        top_provider_types = df['Rndrng_Prvdr_Type'].value_counts().nlargest(5).index
        df = df[df['Rndrng_Prvdr_Type'].isin(top_provider_types)]
    elif provider_types == "top10":
        top_provider_types = df['Rndrng_Prvdr_Type'].value_counts().nlargest(10).index
        df = df[df['Rndrng_Prvdr_Type'].isin(top_provider_types)]
    elif provider_types == "all":
        top_provider_types = df['Rndrng_Prvdr_Type'].unique()

    # Limit to top providers
    df = df.nlargest(limit, 'payment_per_service')

    # Convert NPI to string to use as categorical x-axis
    df['Rndrng_NPI'] = df['Rndrng_NPI'].astype(str)

    # Create abbreviated provider IDs for better display
    df['Provider_ID'] = df['Rndrng_NPI'].str[-4:]

    fig = px.bar(
        df,
        x='Provider_ID',
        y='payment_per_service',
        color='Rndrng_Prvdr_Type',
        title=f'Top {limit} High-Risk Providers by Payment per Service',
        labels={
            'payment_per_service': 'Payment per Service ($)',
            'Provider_ID': 'Provider NPI (last 4 digits)',
            'Rndrng_Prvdr_Type': 'Provider Type'
        },
        hover_data={
            'Rndrng_NPI': True,
            'total_payment': ':.2f',
            'Tot_Srvcs': True,
            'Tot_Benes': True,
            'payment_per_beneficiary': ':.2f',
            'Rndrng_Prvdr_State_Abrvtn': True
        },
        height=600
    )

    # Add median reference line
    median_val = df['payment_per_service'].median()
    fig.add_hline(
        y=median_val,
        line_dash="dash",
        line_color="red",
        annotation_text="Median",
        annotation_position="top right"
    )

    fig.update_layout(
        xaxis_tickangle=-45,
        barmode='group',
        legend_title_text='Provider Type',
        bargap=0.15,
        showlegend=True,
        legend=dict(
            orientation='h',
            traceorder='normal',
            yanchor='bottom',
            y=1,
            xanchor='center',
            x=0.5
        ),
        margin=dict(l=50, r=50, t=140, b=100),
        title={
            'text': f'Top {limit} High-Risk Providers by Payment per Service',
            'x': 0.5,
            'y': 0.95,
            'xanchor': 'center',
            'yanchor': 'top'
        }
    )

    fig.update_traces(
        marker=dict(
            line=dict(width=1),
            opacity=0.8
        ),
        width=0.7
    )
    return fig

def comparative_plot(df, compare_by, metrics):
    if metrics is None:
        metrics = ["total_medicare_payments", "payment_per_beneficiary"]

    # Define group by field based on comparison type
    group_by_field = "Rndrng_Prvdr_Type" if compare_by == "provider_type" else "Rndrng_Prvdr_State_Abrvtn"
    df[group_by_field] = df[group_by_field].apply(lambda x: x if len(x) <= 25 else x[:15] + "...")

    # Calculate appropriate vertical spacing based on the number of metrics
    vertical_spacing = 0.3 / len(metrics) if len(metrics) > 1 else 0.2

    # Create subplots
    fig = make_subplots(
        rows=len(metrics),
        cols=1,
        subplot_titles=[metric.replace("_", " ").title() for metric in metrics],
        vertical_spacing=vertical_spacing
    )

    # Add traces for each metric
    for i, metric in enumerate(metrics):
        row = i + 1
        trace = go.Bar(
            x=df[group_by_field],
            y=df[metric],
            name=metric.replace("_", " ").title(),
            marker_color=px.colors.qualitative.Plotly[i % len(px.colors.qualitative.Plotly)]
        )
        fig.add_trace(trace, row=row, col=1)

        # Update axes
        group_by_label = "Provider Type" if compare_by == "provider_type" else "State"
        tick_angle = 30 if compare_by == "provider_type" else 0
        fig.update_xaxes(
            title_text=group_by_label,
            tickangle=tick_angle,
            tickfont=dict(size=10),
            row=row,
            col=1
        )
        fig.update_yaxes(
            title_text=metric.replace("_", " ").title(),
            row=row,
            col=1
        )

    # Dynamically calculate height based on the number of metrics
    plot_height = 500  # Base height per plot
    total_height = plot_height * len(metrics)

    # Update layout
    fig.update_layout(
        height=total_height,
        margin=dict(t=50, b=30, l=30, r=20),
        showlegend=False
    )

    return fig