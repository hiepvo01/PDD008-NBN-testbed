import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st
import os
import glob
from scipy.signal import medfilt
from peak_speed_detect import max_peak_speed_detect, add_peak_detection_to_figure

# Define folder paths
LOG_FOLDER = 'perfmon'
OUTPUT_FOLDER = 'extracted_data'

def ensure_folder_exists(folder_path):
    """Create folder if it doesn't exist"""
    if not os.path.exists(folder_path):
        os.makedirs(folder_path)

def find_log_pairs(folder_path=LOG_FOLDER):
    """
    Find pairs of log files ending with -r1.log and -r2.log in the specified folder.
    Returns a dictionary of pairs with their base names as keys.
    """
    # Find all r1 and r2 log files
    r1_files = glob.glob(os.path.join(folder_path, '*-r1.log'))
    r2_files = glob.glob(os.path.join(folder_path, '*-r2.log'))
    
    # Create pairs dictionary
    pairs = {}
    for r1_file in r1_files:
        # Get base name by removing -r1.log
        base_name = r1_file[:-7]
        # Check if corresponding r2 file exists
        r2_file = f"{base_name}-r2.log"
        if r2_file in r2_files:
            # Use just the basename without path as the key
            key = os.path.basename(base_name)
            pairs[key] = (r1_file, r2_file)
    
    return pairs

def process_log_to_csv(input_log, output_csv):
    """
    Process log file to CSV with specified column names.
    """
    # Read the data, skipping the first line (comments)
    df = pd.read_csv(input_log, delimiter=' ', skiprows=1, header=None)
    
    # Define the column names
    columns = [
        'time',
        'rx_packets',
        'rx_bytes',
        'tx_packets',
        'tx_bytes',
        'qdisc',
        'bytes',
        'packets',
        'drops',
        'overlimits',
        'BACKLOG'
    ]
    
    # Assign column names to the DataFrame
    df.columns = columns
    
    # Ensure output folder exists
    ensure_folder_exists(OUTPUT_FOLDER)
    
    # Save to CSV in the output folder
    output_path = os.path.join(OUTPUT_FOLDER, output_csv)
    df.to_csv(output_path, index=False)
    return df

def plot_net_throughput(downstream_log, upstream_log, show_peak_detection=False):
    """
    Process the log files and create plots.
    """
    # Convert logs to CSV and load data
    ds = process_log_to_csv(downstream_log, 'downstream.csv')
    us = process_log_to_csv(upstream_log, 'upstream.csv')

    # Calculate relative time
    t_ds = ds['time'].iloc[1:].values - ds['time'].iloc[1]
    t_us = us['time'].iloc[1:].values - us['time'].iloc[1]

    # Calculate intervals
    ds_interval = np.mean(np.diff(t_ds))
    us_interval = np.mean(np.diff(t_us))

    # Create figures
    figures = []
    
    # Figure 1: Downstream packets/sec
    fig1 = go.Figure()
    fig1.add_trace(go.Scatter(x=t_ds, 
                             y=ds['tx_packets'].iloc[1:] / ds_interval, 
                             name='Tx',
                             line=dict(color='blue')))
    fig1.add_trace(go.Scatter(x=t_ds, 
                             y=ds['rx_packets'].iloc[1:] / ds_interval, 
                             name='Rx',
                             line=dict(color='red')))
    fig1.update_layout(
        title='Downstream Throughput (packets/s)',
        xaxis_title='Time (seconds)',
        yaxis_title='Downstream throughput (packets/s)',
        showlegend=True,
        template='plotly_white',
        height=500,
        xaxis=dict(showgrid=True),
        yaxis=dict(showgrid=True)
    )
    figures.append(fig1)

    # Figure 2: Downstream Mbits/sec
    fig2 = go.Figure()
    fig2.add_trace(go.Scatter(x=t_ds, 
                             y=8 * ds['tx_bytes'].iloc[1:] / ds_interval / 1e6, 
                             name='Tx',
                             line=dict(color='blue')))
    fig2.add_trace(go.Scatter(x=t_ds, 
                             y=8 * ds['rx_bytes'].iloc[1:] / ds_interval / 1e6, 
                             name='Rx',
                             line=dict(color='red')))
    fig2.update_layout(
        title='Downstream Throughput (Mb/s)',
        xaxis_title='Time (seconds)',
        yaxis_title='Downstream throughput (Mb/s)',
        showlegend=True,
        template='plotly_white',
        height=500,
        xaxis=dict(showgrid=True),
        yaxis=dict(showgrid=True)
    )
    
    # Add peak detection if enabled
    if show_peak_detection:
        tx_throughput = ds['tx_bytes'].iloc[1:].values
        rx_throughput = ds['rx_bytes'].iloc[1:].values
        fig2 = add_peak_detection_to_figure(fig2, t_ds, tx_throughput)
    
    figures.append(fig2)

    # Figure 3: Upstream packets/sec
    fig3 = go.Figure()
    fig3.add_trace(go.Scatter(x=t_us, 
                             y=us['tx_packets'].iloc[1:] / us_interval, 
                             name='Tx',
                             line=dict(color='blue')))
    fig3.add_trace(go.Scatter(x=t_us, 
                             y=us['rx_packets'].iloc[1:] / us_interval, 
                             name='Rx',
                             line=dict(color='red')))
    fig3.update_layout(
        title='Upstream Throughput (packets/s)',
        xaxis_title='Time (seconds)',
        yaxis_title='Upstream throughput (packets/s)',
        showlegend=True,
        template='plotly_white',
        height=500,
        xaxis=dict(showgrid=True),
        yaxis=dict(showgrid=True)
    )
    figures.append(fig3)

    # Figure 4: Upstream Mbits/sec
    fig4 = go.Figure()
    fig4.add_trace(go.Scatter(x=t_us, 
                             y=8 * us['tx_bytes'].iloc[1:] / us_interval / 1e6, 
                             name='Tx',
                             line=dict(color='blue')))
    fig4.add_trace(go.Scatter(x=t_us, 
                             y=8 * us['rx_bytes'].iloc[1:] / us_interval / 1e6, 
                             name='Rx',
                             line=dict(color='red')))
    fig4.update_layout(
        title='Upstream Throughput (Mb/s)',
        xaxis_title='Time (seconds)',
        yaxis_title='Upstream throughput (Mb/s)',
        showlegend=True,
        template='plotly_white',
        height=500,
        xaxis=dict(showgrid=True),
        yaxis=dict(showgrid=True)
    )
    
    # Add peak detection if enabled
    if show_peak_detection:
        tx_throughput = us['tx_bytes'].iloc[1:].values
        rx_throughput = us['rx_bytes'].iloc[1:].values
        fig4 = add_peak_detection_to_figure(fig4, t_us, tx_throughput)
    
    figures.append(fig4)

    # Figure 5: Downstream buffer occupancy
    fig5 = go.Figure()
    fig5.add_trace(go.Scatter(x=t_ds, 
                             y=ds['BACKLOG'].iloc[1:].values - ds['BACKLOG'].iloc[:-1].values,
                             line=dict(color='blue')))
    fig5.update_layout(
        title='Downstream Buffer Occupancy',
        xaxis_title='Time (seconds)',
        yaxis_title='Downstream tx queue buffer occupancy (packets)',
        showlegend=False,
        template='plotly_white',
        height=500,
        xaxis=dict(showgrid=True),
        yaxis=dict(showgrid=True)
    )
    figures.append(fig5)

    # Figure 6: Upstream buffer occupancy
    fig6 = go.Figure()
    fig6.add_trace(go.Scatter(x=t_us,
                             y=us['BACKLOG'].iloc[1:].values - us['BACKLOG'].iloc[:-1].values,
                             line=dict(color='blue')))
    fig6.update_layout(
        title='Upstream Buffer Occupancy',
        xaxis_title='Time (seconds)',
        yaxis_title='Upstream tx queue buffer occupancy (packets)',
        showlegend=False,
        template='plotly_white',
        height=500,
        xaxis=dict(showgrid=True),
        yaxis=dict(showgrid=True)
    )
    figures.append(fig6)

    # Create summary DataFrames with relative time
    downstream_summary = pd.DataFrame({
        'time': t_ds,
        'rx_packets': ds['rx_packets'].iloc[1:].values,
        'rx_bytes': ds['rx_bytes'].iloc[1:].values,
        'tx_packets': ds['tx_packets'].iloc[1:].values,
        'tx_bytes': ds['tx_bytes'].iloc[1:].values,
        'bytes': ds['bytes'].iloc[1:].values,
        'packets': ds['packets'].iloc[1:].values,
        'drops': ds['drops'].iloc[1:].values,
        'overlimits': ds['overlimits'].iloc[1:].values,
        'BACKLOG': ds['BACKLOG'].iloc[1:].values
    })
    
    upstream_summary = pd.DataFrame({
        'time': t_us,
        'rx_packets': us['rx_packets'].iloc[1:].values,
        'rx_bytes': us['rx_bytes'].iloc[1:].values,
        'tx_packets': us['tx_packets'].iloc[1:].values,
        'tx_bytes': us['tx_bytes'].iloc[1:].values,
        'bytes': us['bytes'].iloc[1:].values,
        'packets': us['packets'].iloc[1:].values,
        'drops': us['drops'].iloc[1:].values,
        'overlimits': us['overlimits'].iloc[1:].values,
        'BACKLOG': us['BACKLOG'].iloc[1:].values
    })
    
    # Save summary DataFrames to CSV with pair name prefix in the output folder
    base_name = os.path.basename(downstream_log).replace('-r1.log', '')
    downstream_summary.to_csv(os.path.join(OUTPUT_FOLDER, f'{base_name}_downstream_summary.csv'), index=False)
    upstream_summary.to_csv(os.path.join(OUTPUT_FOLDER, f'{base_name}_upstream_summary.csv'), index=False)
    
    return figures, downstream_summary, upstream_summary

def main():
    st.set_page_config(page_title="Network Throughput Analysis", layout="wide")
    st.title("Network Throughput Analysis")

    # Ensure both folders exist
    ensure_folder_exists(LOG_FOLDER)
    ensure_folder_exists(OUTPUT_FOLDER)

    # Find log file pairs
    log_pairs = find_log_pairs()
    
    if not log_pairs:
        st.error(f"No log file pairs found in the {LOG_FOLDER} directory. Please ensure log files are present and follow the naming pattern *-r1.log and *-r2.log")
        return

    # Create dropdown for selecting log pair
    selected_pair = st.selectbox(
        "Select log file pair for analysis:",
        options=list(log_pairs.keys()),
        format_func=lambda x: f"Pair: {x}"
    )

    # Add checkbox for peak detection
    show_peak_detection = st.checkbox("Show Peak Speed Detection", value=False)

    if selected_pair:
        downstream_log, upstream_log = log_pairs[selected_pair]
        try:
            figures, downstream_summary, upstream_summary = plot_net_throughput(
                downstream_log, 
                upstream_log,
                show_peak_detection=show_peak_detection
            )
            
            # Display all figures in a grid layout
            for i in range(0, len(figures), 2):
                col1, col2 = st.columns(2)
                with col1:
                    st.plotly_chart(figures[i], use_container_width=True)
                with col2:
                    if i + 1 < len(figures):
                        st.plotly_chart(figures[i + 1], use_container_width=True)

            st.success(f"CSV files have been generated for pair {selected_pair} in the '{OUTPUT_FOLDER}' folder:")
            
            st.markdown("### Raw Data Files")
            st.write("These files contain the original data with unix timestamps:")
            col1, col2 = st.columns(2)
            with col1:
                st.write("**downstream.csv**")
                down_path = os.path.join(OUTPUT_FOLDER, 'downstream.csv')
                if os.path.exists(down_path):
                    df_down = pd.read_csv(down_path)
                    st.dataframe(df_down.head(3))
            with col2:
                st.write("**upstream.csv**")
                up_path = os.path.join(OUTPUT_FOLDER, 'upstream.csv')
                if os.path.exists(up_path):
                    df_up = pd.read_csv(up_path)
                    st.dataframe(df_up.head(3))

            st.markdown("### Processed Summary Files")
            st.write("These files contain the processed data with relative timestamps (starting from 0):")
            col1, col2 = st.columns(2)
            with col1:
                st.write(f"**{selected_pair}_downstream_summary.csv**")
                st.dataframe(downstream_summary.head(3))
            with col2:
                st.write(f"**{selected_pair}_upstream_summary.csv**")
                st.dataframe(upstream_summary.head(3))

            st.markdown("### Generated Files Location")
            st.info(f"""
            All CSV files are saved in the '{OUTPUT_FOLDER}' folder:
            1. downstream.csv
            2. upstream.csv
            3. {selected_pair}_downstream_summary.csv
            4. {selected_pair}_upstream_summary.csv
            """)

            st.markdown("### Column Descriptions")
            st.markdown("""
            - **time**: Unix timestamp (raw) or relative seconds (summary)
            - **rx_packets**: Number of received packets
            - **rx_bytes**: Number of received bytes
            - **tx_packets**: Number of transmitted packets
            - **tx_bytes**: Number of transmitted bytes
            - **bytes**: Queue bytes
            - **packets**: Queue packets
            - **drops**: Number of dropped packets
            - **overlimits**: Number of times the queue limit was exceeded
            - **BACKLOG**: Current queue depth in packets
            """)

            if show_peak_detection:
                st.markdown("### Peak Speed Detection")
                st.markdown("""
                The peak speed detection analysis shows:
                - **Filtered Throughput** (green dotted line): Median-filtered version of the throughput
                - **Peak Throughput** (purple dashed line): Maximum throughput in each time window
                - **Peak Speed Score** (orange line, right axis): Proportion of time the throughput stays within 20% of peak value
                """)

        except Exception as e:
            st.error(f"Error processing log files: {str(e)}")

if __name__ == "__main__":
    main()