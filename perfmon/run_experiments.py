import os
import subprocess
import time
from glob import glob

def run_experiments(test_configs_dir="test_configs", stats_config="stats_collection.json"):
    """
    Run experiments for each test configuration file in the test_configs directory.
    
    Args:
        test_configs_dir (str): Directory containing the test JSON files
        stats_config (str): Statistics configuration file name
    """
    # Get all JSON files in the test_configs directory
    test_files = glob(os.path.join(test_configs_dir, "*.json"))
    
    for test_file in test_files:
        # Extract the base name without extension to use as test name
        test_name = os.path.splitext(os.path.basename(test_file))[0]
        
        # Construct the commands
        stats_cmd = f"./run_stats_all_interfaces.py -i 50 -d 100 -n {test_name} -c {stats_config}"
        trafgen_cmd = f"./trafgen.py -c {test_file}"
        
        print(f"\nRunning experiment for {test_name}")
        print(f"Commands:\n{stats_cmd} & {trafgen_cmd}")
        
        try:
            # Start the stats collection and traffic generator processes
            stats_process = subprocess.Popen(stats_cmd.split())
            trafgen_process = subprocess.Popen(trafgen_cmd.split())
            
            # Wait for traffic generator to complete
            trafgen_process.wait()
            
            # Terminate the stats collection
            stats_process.terminate()
            stats_process.wait()
            
            print(f"Completed experiment: {test_name}")
            
            # Delay between experiments (30 seconds)
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