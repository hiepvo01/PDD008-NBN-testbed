import os
import subprocess
import time
import shutil
from glob import glob

def run_experiments(test_configs_dir="test_configs", stats_config="stats_collection.json", completed_dir="completed_experiments"):
    """
    Run experiments for each test configuration file using simultaneous_capture_trafgen.py
    and move completed test files to a separate directory.
    
    Args:
        test_configs_dir (str): Directory containing the test JSON files
        stats_config (str): Statistics configuration file name
        completed_dir (str): Directory to move completed test files to
    """
    # Create completed experiments directory if it doesn't exist
    os.makedirs(completed_dir, exist_ok=True)
    
    # Get all JSON files in the test_configs directory
    test_files = glob(os.path.join(test_configs_dir, "*.json"))
    
    for test_file in test_files:
        # Extract the base name without extension to use as test name
        test_name = os.path.splitext(os.path.basename(test_file))[0]
        
        # Construct the command
        cmd = f"./simultaneous_capture_trafgen.py -d 100 -i 20 -t {test_file} -c {stats_config} -n {test_name}"
        
        print(f"\nRunning experiment for {test_name}")
        print(f"Command: {cmd}")
        
        try:
            # Run the experiment and wait for completion
            process = subprocess.Popen(cmd.split())
            process.wait()
            
            print(f"Completed experiment: {test_name}")
            
            # Move the completed test file to the completed directory
            completed_file_path = os.path.join(completed_dir, os.path.basename(test_file))
            shutil.move(test_file, completed_file_path)
            print(f"Moved {test_file} to {completed_file_path}")
            
            # Delay between experiments (20 seconds)
            print("Waiting 20 seconds before next experiment...")
            time.sleep(20)
            
        except subprocess.CalledProcessError as e:
            print(f"Error running experiment {test_name}: {e}")
        except Exception as e:
            print(f"Unexpected error during experiment {test_name}: {e}")
            
        print(f"Finished experiment: {test_name}\n")
        print("-" * 80)

if __name__ == "__main__":
    run_experiments()