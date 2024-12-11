import numpy as np
from scipy.signal import medfilt

def peak_speed_detect(throughput, time, bin_widths_ms=[100, 1000]):
    """
    Python implementation of MATLAB peak_speed_detect.m
    
    Args:
        throughput: array of throughput values
        time: array of time values
        bin_widths_ms: [short_term, long_term] bin widths in milliseconds
    
    Returns:
        tuple: (score, binned_peaks_lt, filtered_throughput)
        - score: proportion of time throughput is within threshold of peak
        - binned_peaks_lt: long-term peak values
        - filtered_throughput: median-filtered throughput values
    """
    # Calculate mean time difference in milliseconds
    mean_dt = np.mean(np.diff(time)) * 1000
    
    # Convert bin widths to steps
    short_term_step = round(bin_widths_ms[0] / mean_dt)
    long_term_step = round(bin_widths_ms[1] / mean_dt)
    
    # Add padding at the start (like MATLAB implementation)
    padding = np.zeros(long_term_step)
    throughput = np.concatenate([padding, throughput])
    time = np.concatenate([padding, time])
    
    len_data = len(throughput)
    
    # Initialize arrays
    short_term_memfactor = 0.95
    moving_avg = np.zeros(len_data)
    binned_peaks_st = np.zeros(len_data)
    binned_peaks_lt = np.zeros(len_data)
    
    # Calculate moving average
    for idx in range(1, len_data):
        moving_avg[idx] = short_term_memfactor * moving_avg[idx-1] + \
                         (1 - short_term_memfactor) * throughput[idx]
    
    # Short-term peaks
    for idx in range(0, len_data - short_term_step, short_term_step):
        window = throughput[idx:idx + short_term_step]
        binned_peaks_st[idx:idx + short_term_step] = np.max(window)
    
    # Apply median filter (equivalent to MATLAB's medfilt1)
    tpf = medfilt(throughput, 15)
    
    # Long-term peaks with filtered data
    for idx in range(long_term_step, len_data - long_term_step):
        window = tpf[idx - long_term_step:idx + long_term_step]
        binned_peaks_lt[idx] = np.max(window)
    
    # Calculate peaking score (equivalent to MATLAB implementation)
    score = binned_peaks_st > 0.7 * binned_peaks_lt
    
    # Remove the padding we added
    score = score[long_term_step:]
    binned_peaks_lt = binned_peaks_lt[long_term_step:]
    tpf = tpf[long_term_step:]
    
    return score, binned_peaks_lt, tpf

def max_peak_speed_detect(time, throughput, bin_widths_ms=[100, 1000]):
    """
    Wrapper function to handle both packets/s and Mbps cases.
    
    Args:
        time: array of time values
        throughput: array of throughput values
        bin_widths_ms: [short_term, long_term] bin widths in milliseconds
    """
    return peak_speed_detect(throughput, time, bin_widths_ms)

def add_peak_detection_to_figure(fig, time, throughput, window_size=1000, threshold=0.2):
    """
    Add peak detection traces to an existing plotly figure.
    
    Args:
        fig: plotly figure object
        time: array of time values
        throughput: array of throughput values
        window_size: long-term window size in ms
        threshold: threshold for peak detection
    
    Returns:
        Updated plotly figure object
    """
    score, peaks, filtered = max_peak_speed_detect(time, throughput, [100, window_size])
    
    # Add filtered throughput trace
    fig.add_trace(go.Scatter(
        x=time,
        y=filtered,
        name='Filtered Throughput',
        line=dict(color='green', dash='dot'),
        visible=True
    ))
    
    # Add peaks trace
    fig.add_trace(go.Scatter(
        x=time,
        y=peaks,
        name='Peak Throughput',
        line=dict(color='purple', dash='dash'),
        visible=True
    ))
    
    # Get score range
    score_min = np.min(score)
    score_max = np.max(score)
    score_range = score_max - score_min
    # Add small padding to range
    score_min = max(0, score_min - 0.1 * score_range)
    score_max = min(1, score_max + 0.1 * score_range)
    
    # Add score trace
    fig.add_trace(go.Scatter(
        x=time,
        y=score,
        name='Peak Score',
        line=dict(color='orange'),
        yaxis='y2',
        visible=True
    ))
    
    # Update layout to include secondary y-axis
    fig.update_layout(
        yaxis2=dict(
            title='Peak Score',
            titlefont=dict(color='orange'),
            tickfont=dict(color='orange'),
            overlaying='y',
            side='right',
            range=[score_min, score_max]
        )
    )
    
    return fig