import numpy as np
from scipy.signal import medfilt
import plotly.graph_objects as go

def calculate_mean_dt(time):
    """Calculate mean time difference between samples"""
    return np.mean(np.diff(time))

def max_peak_speed_detect(time, throughput, long_window, threshold=0.2):
    """
    Detect peak speeds and calculate score based on throughput data.
    
    Args:
        time: array of sample times in seconds since start
        throughput: array of bytes transferred during previous sample interval
        long_window: period (in ms) over which fraction of time that throughput is 
                    within threshold of peak is assessed
        threshold: threshold for considering throughput as peak (default: 0.2)
    
    Returns:
        tuple: (score, binned_peaks_lt, filtered_throughput)
        - score: proportion of time throughput is within threshold of peak
        - binned_peaks_lt: long-term peak values
        - filtered_throughput: median-filtered throughput values
    """
    # Input validation
    if len(time) != len(throughput):
        raise ValueError("Time and throughput arrays must have the same length")
    
    # Calculate mean time difference
    mean_dt = calculate_mean_dt(time)
    
    # Convert throughput to Mb/s
    throughput_mbps = throughput * 8 / 1000000 / mean_dt
    
    # Convert mean_dt to milliseconds
    mean_dt_ms = mean_dt * 1000
    
    # Calculate steps based on window size
    long_term_step = round(long_window / mean_dt_ms)
    
    # Initialize arrays
    len_data = len(throughput)
    binned_peaks_lt = np.zeros(len_data)
    score = np.zeros(len_data)
    
    # Apply median filter (equivalent to MATLAB's medfilt1)
    filtered_throughput = medfilt(throughput_mbps, 15)
    
    # Calculate peaks and scores
    for idx in range(0, len_data - long_term_step, long_term_step):
        end_idx = idx + long_term_step
        window_data = filtered_throughput[idx:end_idx]
        
        # Calculate peak for window
        peak = np.max(window_data)
        binned_peaks_lt[idx:end_idx] = peak
        
        # Calculate score (proportion of time within threshold of peak)
        above_threshold = np.sum(window_data > (1 - threshold) * peak)
        score[idx:end_idx] = above_threshold / long_term_step
    
    return score, binned_peaks_lt, filtered_throughput

def add_peak_detection_to_figure(fig, time, throughput, long_window=1000, threshold=0.2):
    """
    Add peak detection traces to an existing Plotly figure.
    
    Args:
        fig: Plotly figure object
        time: array of time values
        throughput: array of throughput values
        long_window: window size in ms
        threshold: threshold for peak detection
    
    Returns:
        Updated Plotly figure object
    """
    score, peaks, filtered = max_peak_speed_detect(time, throughput, long_window, threshold)
    
    # Add filtered throughput trace
    fig.add_trace(
        go.Scatter(
            x=time,
            y=filtered,
            name='Filtered Throughput',
            line=dict(color='green', dash='dot'),
            visible=True
        )
    )
    
    # Add peaks trace
    fig.add_trace(
        go.Scatter(
            x=time,
            y=peaks,
            name='Peak Throughput',
            line=dict(color='purple', dash='dash'),
            visible=True
        )
    )
    
    # Add score trace using secondary y-axis
    fig.add_trace(
        go.Scatter(
            x=time,
            y=score,
            name='Peak Speed Score',
            line=dict(color='orange'),
            yaxis='y2',
            visible=True
        )
    )
    
    # Update layout to include secondary y-axis
    fig.update_layout(
        yaxis2=dict(
            title='Peak Speed Score (0-1)',
            overlaying='y',
            side='right',
            range=[0, 1]
        )
    )
    
    return fig