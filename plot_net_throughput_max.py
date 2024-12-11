import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import os
from scipy.signal import medfilt
from peak_speed_detect import max_peak_speed_detect
from sklearn.metrics import confusion_matrix, classification_report

# Define folder paths
OUTPUT_FOLDER = 'extracted_data'

def calculate_peak_detection_accuracy(time, throughput, ground_truth, window_size=1000):
    """
    Calculate confusion matrix and metrics for peak detection vs ground truth.
    """
    # Get peak detection results
    peaking, peaks, filtered = max_peak_speed_detect(time, throughput, [100, window_size])
    
    # Calculate confusion matrix
    cm = confusion_matrix(ground_truth, peaking)
    
    # Calculate metrics
    report = classification_report(ground_truth, peaking, output_dict=True)
    
    return cm, report, peaking, peaks, filtered

def plot_confusion_matrix(cm, title="Confusion Matrix"):
    """Create a plotly heatmap for confusion matrix visualization."""
    fig = go.Figure(data=go.Heatmap(
        z=cm,
        x=['No Peak', 'Peak'],
        y=['No Peak', 'Peak'],
        text=cm,
        texttemplate="%{text}",
        textfont={"size": 16},
        colorscale='Blues'
    ))
    
    fig.update_layout(
        title=title,
        xaxis_title="Predicted",
        yaxis_title="Actual",
        height=400
    )
    
    return fig

def load_processed_data(file_path):
    """Load processed CSV data"""
    return pd.read_csv(file_path)

def create_throughput_figures(df, is_downstream=True, show_peak_detection=False, window_size=1000):
    """Create throughput visualization figures"""
    direction = "Downstream" if is_downstream else "Upstream"
    
    # Use data starting from the second row
    t = df['relative_time'].values
    interval = np.mean(np.diff(t))
    
    figures = []
    
    # Calculate packet rates (following MATLAB implementation)
    tx_packet_rate = df['tx_packets'].values / interval
    rx_packet_rate = df['rx_packets'].values / interval
    
    # Packets/sec figure
    fig1 = go.Figure()
    fig1.add_trace(go.Scatter(x=t, 
                             y=tx_packet_rate, 
                             name='Tx',
                             line=dict(color='blue'),
                             showlegend=is_downstream))
    fig1.add_trace(go.Scatter(x=t, 
                             y=rx_packet_rate, 
                             name='Rx',
                             line=dict(color='red'),
                             showlegend=is_downstream))
    fig1.update_layout(
        title=f'{direction} Throughput (packets/s)',
        xaxis_title='Time (seconds)',
        yaxis_title=f'{direction} throughput (packets/s)',
        template='plotly_white',
        height=500,
        xaxis=dict(showgrid=True),
        yaxis=dict(showgrid=True),
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="center",
            x=0.5
        )
    )
    
    if show_peak_detection:
        peaking, peaks, filtered = max_peak_speed_detect(t, tx_packet_rate, [100, window_size])
        max_val = np.max(tx_packet_rate)
        fig1.add_trace(go.Scatter(x=t, y=filtered, name='Filtered', 
                                line=dict(color='green', dash='dot'), showlegend=is_downstream))
        fig1.add_trace(go.Scatter(x=t, y=peaks, name='Peaks', 
                                line=dict(color='purple', dash='dash'), showlegend=is_downstream))
        fig1.add_trace(go.Scatter(x=t, y=peaking * max_val, name='Peaking', 
                                line=dict(color='orange'), showlegend=is_downstream))
    
    figures.append(fig1)

    # Calculate bit rates (Mb/s)
    tx_bit_rate = 8 * df['tx_bytes'].values / interval / 1e6
    rx_bit_rate = 8 * df['rx_bytes'].values / interval / 1e6
    
    # Mbits/sec figure
    fig2 = go.Figure()
    fig2.add_trace(go.Scatter(x=t, 
                             y=tx_bit_rate, 
                             name='Tx',
                             line=dict(color='blue'),
                             showlegend=is_downstream))
    fig2.add_trace(go.Scatter(x=t, 
                             y=rx_bit_rate, 
                             name='Rx',
                             line=dict(color='red'),
                             showlegend=is_downstream))
    fig2.update_layout(
        title=f'{direction} Throughput (Mb/s)',
        xaxis_title='Time (seconds)',
        yaxis_title=f'{direction} throughput (Mb/s)',
        template='plotly_white',
        height=500,
        xaxis=dict(showgrid=True),
        yaxis=dict(showgrid=True),
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="center",
            x=0.5
        )
    )
    
    if show_peak_detection:
        peaking, peaks, filtered = max_peak_speed_detect(t, tx_bit_rate, [100, window_size])
        max_val = np.max(tx_bit_rate)
        fig2.add_trace(go.Scatter(x=t, y=filtered, name='Filtered', 
                                line=dict(color='green', dash='dot'), showlegend=is_downstream))
        fig2.add_trace(go.Scatter(x=t, y=peaks, name='Peaks', 
                                line=dict(color='purple', dash='dash'), showlegend=is_downstream))
        fig2.add_trace(go.Scatter(x=t, y=peaking * max_val, name='Peaking', 
                                line=dict(color='orange'), showlegend=is_downstream))
    
    figures.append(fig2)

    # Buffer occupancy figure
    fig3 = go.Figure()
    fig3.add_trace(go.Scatter(x=t, 
                             y=df['queue_size'],
                             name='Queue Size',
                             line=dict(color='blue'),
                             showlegend=is_downstream))
    fig3.add_trace(go.Scatter(x=t,
                             y=df['queue_exists'] * df['queue_size'].max(),
                             name='Queue Exists',
                             line=dict(color='red', dash='dash'),
                             showlegend=is_downstream))
    fig3.update_layout(
        title=f'{direction} Buffer Occupancy',
        xaxis_title='Time (seconds)',
        yaxis_title=f'{direction} tx queue buffer occupancy (packets)',
        template='plotly_white',
        height=500,
        xaxis=dict(showgrid=True),
        yaxis=dict(showgrid=True),
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="center",
            x=0.5
        )
    )
    
    figures.append(fig3)
    
    return figures

def parse_log_filename(filename):
    """Parse log filename to extract scenario details"""
    # Remove the stream direction and location suffixes
    base = filename.replace('_upstream.csv', '').replace('_downstream.csv', '')
    base = base.replace('-r1.log', '').replace('-r2.log', '')
    
    info = {
        'full_name': base,
        'type': 'unknown',
        'scenario': '',
        'limited_flows': 0,
        'unlimited_flows': 0,
        'cbr_rate': 0
    }
    
    try:
        # Split into parts
        parts = base.split('_')
        
        # Pattern 1: Xlimited_Yunlimited format
        limited_idx = -1
        unlimited_idx = -1
        for i, part in enumerate(parts):
            if part.endswith('limited') and part != 'limited':
                try:
                    limited_idx = i
                    info['limited_flows'] = int(part[:-7])
                except ValueError:
                    pass
            if part.endswith('unlimited') and part != 'unlimited':
                try:
                    unlimited_idx = i
                    info['unlimited_flows'] = int(part[:-9])
                except ValueError:
                    pass
                    
        # Pattern 2: Xflows format
        flows_idx = -1
        for i, part in enumerate(parts):
            if part.endswith('flows'):
                try:
                    flows_idx = i
                    info['limited_flows'] = int(part[:-5])
                except ValueError:
                    pass
        
        # Check for CBR rate
        for part in parts:
            if part.endswith('mbps'):
                try:
                    info['cbr_rate'] = int(part[:-4])
                except ValueError:
                    pass
        
        # Extract scenario name
        if info['limited_flows'] > 0 and info['unlimited_flows'] > 0:
            # Mixed flows case
            scenario_end = min(i for i in [limited_idx, unlimited_idx] if i >= 0)
            info['type'] = 'mixed'
        elif flows_idx >= 0:
            # Simple flows case
            scenario_end = flows_idx
            info['type'] = 'limited_only'
        elif limited_idx >= 0:
            # Single limited flows case
            scenario_end = limited_idx
            info['type'] = 'limited_only'
        else:
            scenario_end = len(parts) - 1
            
        if scenario_end > 1:
            scenario_parts = []
            for i in range(1, scenario_end):
                if not any(x in parts[i] for x in ['flows', 'limited', 'unlimited', 'mbps']):
                    scenario_parts.append(parts[i])
            info['scenario'] = '_'.join(scenario_parts)
        
        # Add CBR modifier if present
        if info['cbr_rate'] > 0:
            info['type'] += '_cbr'
            
    except Exception as e:
        print(f"Error parsing filename {filename}: {str(e)}")
    
    return info

def main():
    st.set_page_config(page_title="Network Throughput Analysis", layout="wide")
    st.title("Network Throughput Analysis")

    # Find all CSV files in the output folder
    csv_files = [f for f in os.listdir(OUTPUT_FOLDER) if f.endswith('.csv')]
    if not csv_files:
        st.error("No processed CSV files found in the 'extracted_data' directory.")
        return

    # Parse all experiment names and create filters
    experiments = {}
    scenarios = set()
    exp_types = set()
    limited_flows = set()
    unlimited_flows = set()
    cbr_rates = set()
    
    for file in csv_files:
        base_name = file.replace('_downstream.csv', '').replace('_upstream.csv', '')
        if base_name not in experiments:
            info = parse_log_filename(base_name)
            experiments[base_name] = {
                'info': info,
                'downstream': None,
                'upstream': None
            }
            scenarios.add(info['scenario'])
            exp_types.add(info['type'])
            if info['limited_flows'] > 0:
                limited_flows.add(info['limited_flows'])
            if info['unlimited_flows'] > 0:
                unlimited_flows.add(info['unlimited_flows'])
            if info['cbr_rate'] > 0:
                cbr_rates.add(info['cbr_rate'])
        
        if 'downstream' in file:
            experiments[base_name]['downstream'] = file
        elif 'upstream' in file:
            experiments[base_name]['upstream'] = file

    # Create filter controls
    st.sidebar.header("Filters")
    
    # Experiment type filter
    selected_type = st.sidebar.selectbox(
        "Experiment Type",
        ['All'] + sorted(list(exp_types)),
        help="Filter by experiment type"
    )
    
    # Scenario filter
    selected_scenario = st.sidebar.selectbox(
        "Scenario",
        ['All'] + sorted(list(scenarios)),
        help="Filter by scenario name"
    )
    
    # Flow filters
    col1, col2 = st.sidebar.columns(2)
    with col1:
        selected_limited = st.selectbox(
            "Limited Flows",
            ['All'] + sorted(list(limited_flows)),
            help="Number of rate-limited TCP flows"
        )
    
    with col2:
        selected_unlimited = st.selectbox(
            "Unlimited Flows",
            ['All'] + sorted(list(unlimited_flows)),
            help="Number of unlimited TCP flows"
        )
    
    # CBR rate filter
    selected_cbr = st.sidebar.selectbox(
        "CBR Rate (Mbps)",
        ['All'] + sorted(list(cbr_rates)),
        help="CBR traffic rate"
    )

    # Filter experiments based on selections
    filtered_experiments = {}
    for name, exp in experiments.items():
        info = exp['info']
        if (selected_type == 'All' or info['type'] == selected_type) and \
           (selected_scenario == 'All' or info['scenario'] == selected_scenario) and \
           (selected_limited == 'All' or info['limited_flows'] == selected_limited) and \
           (selected_unlimited == 'All' or info['unlimited_flows'] == selected_unlimited) and \
           (selected_cbr == 'All' or info['cbr_rate'] == selected_cbr):
            filtered_experiments[name] = exp

    # Display selected experiment
    if not filtered_experiments:
        st.warning("No experiments match the selected filters.")
        return

    # Create columns for remaining controls
    col1, col2 = st.columns([3, 1])
    
    with col1:
        selected_exp = st.selectbox(
            "Select experiment for analysis:",
            options=list(filtered_experiments.keys()),
            format_func=lambda x: filtered_experiments[x]['info']['full_name']
        )
    
    with col2:
        show_peak_detection = st.checkbox(
            "Show Peak Detection Analysis",
            value=False,
            help="Enable to show peak detection analysis on all plots"
        )

    if show_peak_detection:
        window_size = st.sidebar.slider(
            "Window Size (ms)",
            min_value=100,
            max_value=5000,
            value=1000,
            step=100,
            help="Window size for peak detection analysis"
        )
    else:
        window_size = 1000

    if selected_exp:
        exp_files = filtered_experiments[selected_exp]
        try:
            # Load data
            downstream_df = load_processed_data(os.path.join(OUTPUT_FOLDER, exp_files['downstream']))
            upstream_df = load_processed_data(os.path.join(OUTPUT_FOLDER, exp_files['upstream']))

            # Create throughput figures
            downstream_figs = create_throughput_figures(
                downstream_df, 
                is_downstream=True,
                show_peak_detection=show_peak_detection,
                window_size=window_size
            )
            upstream_figs = create_throughput_figures(
                upstream_df, 
                is_downstream=False,
                show_peak_detection=show_peak_detection,
                window_size=window_size
            )

            # Display throughput figures in grid layout
            for i in range(len(downstream_figs)):
                col1, col2 = st.columns(2)
                with col1:
                    st.plotly_chart(downstream_figs[i], use_container_width=True)
                with col2:
                    st.plotly_chart(upstream_figs[i], use_container_width=True)

            if show_peak_detection:
                st.subheader("Peak Detection Accuracy Analysis")
                
                # Calculate confusion matrices and metrics
                ds_time = downstream_df['relative_time'].values
                us_time = upstream_df['relative_time'].values
                
                # Downstream analysis
                ds_tx_rate = downstream_df['tx_bytes'].values / np.mean(np.diff(ds_time))
                ds_cm, ds_report, ds_peaking, ds_peaks, ds_filtered = calculate_peak_detection_accuracy(
                    ds_time,
                    ds_tx_rate,
                    downstream_df['queue_exists'].values,
                    window_size
                )
                
                # Upstream analysis
                us_tx_rate = upstream_df['tx_bytes'].values / np.mean(np.diff(us_time))
                us_cm, us_report, us_peaking, us_peaks, us_filtered = calculate_peak_detection_accuracy(
                    us_time,
                    us_tx_rate,
                    upstream_df['queue_exists'].values,
                    window_size
                )

                # Display confusion matrices
                col1, col2 = st.columns(2)
                with col1:
                    st.plotly_chart(plot_confusion_matrix(ds_cm, "Downstream Confusion Matrix"), use_container_width=True)
                    st.write("**Downstream Classification Metrics:**")
                    metrics_df = pd.DataFrame({
                        'Metric': ['Accuracy', 'Precision', 'Recall', 'F1-Score'],
                        'Value': [
                            ds_report['accuracy'],
                            ds_report['1']['precision'],
                            ds_report['1']['recall'],
                            ds_report['1']['f1-score']
                        ]
                    })
                    st.dataframe(metrics_df.set_index('Metric').style.format('{:.3f}'), use_container_width=True)
                
                with col2:
                    st.plotly_chart(plot_confusion_matrix(us_cm, "Upstream Confusion Matrix"), use_container_width=True)
                    st.write("**Upstream Classification Metrics:**")
                    metrics_df = pd.DataFrame({
                        'Metric': ['Accuracy', 'Precision', 'Recall', 'F1-Score'],
                        'Value': [
                            us_report['accuracy'],
                            us_report['1']['precision'],
                            us_report['1']['recall'],
                            us_report['1']['f1-score']
                        ]
                    })
                    st.dataframe(metrics_df.set_index('Metric').style.format('{:.3f}'), use_container_width=True)

            # Display experiment info
            st.subheader("Experiment Information")
            info = filtered_experiments[selected_exp]['info']
            
            # Create info table
            info_data = {
                'Parameter': [
                    'Scenario',
                    'Experiment Type',
                    'Limited TCP Flows',
                    'Unlimited TCP Flows',
                    'CBR Rate (Mbps)'
                ],
                'Value': [
                    info['scenario'],
                    info['type'],
                    info['limited_flows'],
                    info['unlimited_flows'],
                    info['cbr_rate']
                ]
            }
            st.table(pd.DataFrame(info_data))

            # Display queue statistics
            st.subheader("Queue Statistics")
            col1, col2 = st.columns(2)
            with col1:
                st.write("**Downstream Queue Statistics**")
                st.write(f"Average queue size: {downstream_df['queue_size'].mean():.2f} packets")
                st.write(f"Maximum queue size: {downstream_df['queue_size'].max():.2f} packets")
                st.write(f"Time with queue: {(downstream_df['queue_exists'].mean() * 100):.2f}%")
                if show_peak_detection:
                    st.write(f"Time with peaks: {(ds_peaking.mean() * 100):.2f}%")
            
            with col2:
                st.write("**Upstream Queue Statistics**")
                st.write(f"Average queue size: {upstream_df['queue_size'].mean():.2f} packets")
                st.write(f"Maximum queue size: {upstream_df['queue_size'].max():.2f} packets")
                st.write(f"Time with queue: {(upstream_df['queue_exists'].mean() * 100):.2f}%")
                if show_peak_detection:
                    st.write(f"Time with peaks: {(us_peaking.mean() * 100):.2f}%")

            if show_peak_detection:
                st.markdown("""
                ### Understanding the Analysis
                - **Confusion Matrix**: Shows the agreement between queue existence and peak detection
                - **Accuracy**: Overall correct predictions (both peaks and non-peaks)
                - **Precision**: Proportion of correctly identified peaks among all predicted peaks
                - **Recall**: Proportion of actual peaks that were correctly identified
                - **F1-Score**: Harmonic mean of precision and recall (balance between precision and recall)
                """)

        except Exception as e:
            st.error(f"Error processing data: {str(e)}")
            st.exception(e)

if __name__ == "__main__":
    main()