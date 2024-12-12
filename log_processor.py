import numpy as np
import pandas as pd
import os
import glob

# Define folder paths
LOG_FOLDER = 'raw_data'
OUTPUT_FOLDER = 'extracted_data'

def ensure_folder_exists(folder_path):
    """Create folder if it doesn't exist"""
    if not os.path.exists(folder_path):
        os.makedirs(folder_path)

def find_log_pairs(base_folder=LOG_FOLDER):
    """
    Find pairs of log files ending with -r1.log and -r2.log in all subfolders.
    Returns a dictionary of pairs with their subfolder and base names as keys.
    """
    pairs = {}
    
    # Walk through all subfolders
    for root, _, _ in os.walk(base_folder):
        r1_files = glob.glob(os.path.join(root, '*-r1.log'))
        r2_files = glob.glob(os.path.join(root, '*-r2.log'))
        
        for r1_file in r1_files:
            base_name = r1_file[:-7]
            r2_file = f"{base_name}-r2.log"
            if r2_file in r2_files:
                # Get relative path from raw_data folder
                rel_path = os.path.relpath(root, base_folder)
                if rel_path == '.':
                    rel_path = ''
                    
                # Create key that includes subfolder path
                key = os.path.join(rel_path, os.path.basename(base_name))
                pairs[key] = (r1_file, r2_file)
    
    return pairs

def process_log_to_df(input_log, time_threshold=100):
    """
    Process log file to DataFrame with specified column names.
    Only includes data for first time_threshold seconds.
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
    
    # Calculate relative time starting from second row
    relative_time = df['time'].iloc[1:].values - df['time'].iloc[1]
    
    # Create mask for time threshold
    time_mask = relative_time <= time_threshold
    
    # Create processed DataFrame starting from second row and applying time threshold
    processed_df = pd.DataFrame({
        'time': df['time'].iloc[1:].values[time_mask],
        'relative_time': relative_time[time_mask],
        'rx_packets': df['rx_packets'].iloc[1:].values[time_mask],
        'rx_bytes': df['rx_bytes'].iloc[1:].values[time_mask],
        'tx_packets': df['tx_packets'].iloc[1:].values[time_mask],
        'tx_bytes': df['tx_bytes'].iloc[1:].values[time_mask],
        'bytes': df['bytes'].iloc[1:].values[time_mask],
        'packets': df['packets'].iloc[1:].values[time_mask],
        'drops': df['drops'].iloc[1:].values[time_mask],
        'overlimits': df['overlimits'].iloc[1:].values[time_mask],
        'BACKLOG': df['BACKLOG'].iloc[1:].values[time_mask]
    })
    
    # Calculate buffer metrics
    processed_df['queue_size'] = processed_df['BACKLOG'].diff()
    processed_df['queue_exists'] = (processed_df['queue_size'] > 10).astype(int)
    
    return processed_df

def process_all_logs(queue_threshold=10, time_threshold=100):
    """
    Process all log files from all subfolders and save results to corresponding
    subfolders in extracted_data.
    Only includes data for first time_threshold seconds.
    """
    ensure_folder_exists(OUTPUT_FOLDER)
    log_pairs = find_log_pairs()
    
    processed_files = []
    for base_name, (downstream_log, upstream_log) in log_pairs.items():
        try:
            # Create output subfolder if needed
            output_subfolder = os.path.join(OUTPUT_FOLDER, os.path.dirname(base_name))
            ensure_folder_exists(output_subfolder)
            
            # Process logs to DataFrames
            ds_df = process_log_to_df(downstream_log, time_threshold)
            us_df = process_log_to_df(upstream_log, time_threshold)
            
            # Save processed data maintaining subfolder structure
            ds_output = os.path.join(OUTPUT_FOLDER, f'{base_name}_downstream.csv')
            us_output = os.path.join(OUTPUT_FOLDER, f'{base_name}_upstream.csv')
            
            ds_df.to_csv(ds_output, index=False)
            us_df.to_csv(us_output, index=False)
            
            processed_files.extend([ds_output, us_output])
            print(f"Processed {base_name} - Files saved: {ds_output}, {us_output}")
            print(f"  Downstream: {len(ds_df)} samples up to {ds_df['relative_time'].max():.1f}s")
            print(f"  Upstream: {len(us_df)} samples up to {us_df['relative_time'].max():.1f}s")
            
        except Exception as e:
            print(f"Error processing {base_name}: {str(e)}")
    
    return processed_files

if __name__ == "__main__":
    processed_files = process_all_logs()
    print(f"\nProcessing complete. {len(processed_files)} files generated in {OUTPUT_FOLDER}/")