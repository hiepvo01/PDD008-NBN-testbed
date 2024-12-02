import pandas as pd
import json
import os
from typing import List, Dict, Any, Union, Tuple

def parse_traffic_config(value: str) -> Tuple[List[Union[int, float]], str, float]:
    """Parse traffic configuration strings into flow counts and rates."""
    if pd.isna(value) or value == '-':
        return [], '', 0.0
    
    if '@' in value:  # TCP flows with rate limit: "1, 2, 4, 8 @20 Mb/s/flow"
        flows_str, rate_str = value.split('@')
        flows = [int(x.strip()) for x in flows_str.split(',')]
        rate = float(rate_str.split()[0])
        return flows, 'tcp', rate
    elif 'CBR UDP' in value:  # CBR traffic: "10, 20, 40 Mb/s CBR UDP"
        rates_str = value.split('Mb/s')[0]
        rates = [float(x.strip()) for x in rates_str.split(',')]
        return rates, 'cbr', 0.0
    elif 'TCP flows' in value:  # Unlimited TCP flows: "1, 2, 4, 8 TCP flows"
        flows_str = value.split('TCP')[0]
        flows = [int(x.strip()) for x in flows_str.split(',')]
        return flows, 'tcp_unlimited', float('inf')
    
    return [], '', 0.0

def create_tcp_config(index: int, rate: float, start_time: int) -> Dict[str, Any]:
    """Create a TCP test configuration."""
    cmd = f"iperf3 -c server{index} -C reno -R -t 60"
    if rate != float('inf'):
        cmd = f"iperf3 -c server{index} -C reno -R -b {rate}M -t 60"
        
    return {
        "testname": f"iperf TCP-reno {'rate-limited' if rate != float('inf') else 'unlimited'} download #{index}",
        "host1": {
            "name": f"client{index}-mgmt",
            "cmd": cmd,
            "persist": False,
            "start_time": start_time
        },
    }

def create_udp_config(index: int, rate: float, start_time: int) -> Dict[str, Any]:
    """Create a UDP test configuration."""
    return {
        "testname": f"iperf UDP download #{index}",
        "host1": {
            "name": f"client{index}-mgmt",
            "cmd": f"iperf3 -c server{index} -R -u -b {rate}M -t 60",
            "persist": False,
            "start_time": start_time
        },
    }

def generate_test_files(csv_file: str, output_dir: str = "test_configs"):
    """Generate test.json files combining rate-limited and unlimited TCP flows with CBR traffic."""
    df = pd.read_csv(csv_file)
    # Filter for scenarios containing "no background", including those with "+ CBR UDP"
    df = df[df['Scenario'].str.contains(r'no background(?:\s+\+\s+CBR UDP)?', case=False)]
    os.makedirs(output_dir, exist_ok=True)
    
    for idx, row in df.iterrows():
        scenario = row['Scenario']
        
        # Create base scenario name
        base_scenario = scenario.split('+')[0].strip()
        base_scenario_name = base_scenario.replace(" ", "_").replace(",", "").lower()
        
        # Check if scenario includes CBR UDP
        has_cbr = 'CBR UDP' in scenario
        if has_cbr:
            scenario_name = f"{base_scenario_name}_cbr_udp"
        else:
            scenario_name = base_scenario_name
        
        # Parse configurations
        limited_flows, limited_type, limited_rate = parse_traffic_config(row['TCP flows (rate limited)'])
        unlimited_flows, unlimited_type, _ = parse_traffic_config(row['TCP flows (unlimited)'])
        cbr_rates, cbr_type, _ = parse_traffic_config(row['CBR traffic'])
        
        # Skip if no TCP flows configured
        if not limited_flows and not unlimited_flows:
            continue
            
        # Handle all combinations
        if unlimited_flows:
            # Handle combinations of rate-limited, unlimited, and CBR
            for unl_flow_count in unlimited_flows:
                # Start with base configuration (TCP flows)
                base_tests = []
                client_index = 1
                start_time = 0
                
                # Add rate-limited flows first (if any)
                if limited_flows:
                    limited_flow_count = limited_flows[0]  # Use the specified number of rate-limited flows
                    for i in range(limited_flow_count):
                        base_tests.append(create_tcp_config(
                            client_index,
                            limited_rate,
                            start_time
                        ))
                        client_index += 1
                        start_time += 1
                
                # Add unlimited flows
                for i in range(unl_flow_count):
                    base_tests.append(create_tcp_config(
                        client_index,
                        float('inf'),
                        start_time
                    ))
                    client_index += 1
                    start_time += 1
                
                # If there are CBR rates, create a file for each combination
                if cbr_rates:
                    for cbr_rate in cbr_rates:
                        tests = base_tests.copy()
                        tests.append(create_udp_config(
                            client_index,
                            cbr_rate,
                            start_time
                        ))
                        
                        filename = os.path.join(output_dir, 
                            f"test_{scenario_name}_{limited_flows[0] if limited_flows else 0}limited_{unl_flow_count}unlimited_{int(cbr_rate)}mbps_cbr.json")
                        with open(filename, 'w') as f:
                            json.dump(tests, f, indent=2)
                else:
                    # Save just the TCP flows configuration
                    filename = os.path.join(output_dir, 
                        f"test_{scenario_name}_{limited_flows[0] if limited_flows else 0}limited_{unl_flow_count}unlimited.json")
                    with open(filename, 'w') as f:
                        json.dump(base_tests, f, indent=2)
        
        # Handle scenarios with only rate-limited flows
        elif limited_flows:
            for flow_count in limited_flows:
                if cbr_rates:
                    for cbr_rate in cbr_rates:
                        tests = []
                        client_index = 1
                        start_time = 0
                        
                        # Add TCP flows
                        for i in range(flow_count):
                            tests.append(create_tcp_config(
                                client_index,
                                limited_rate,
                                start_time
                            ))
                            client_index += 1
                            start_time += 1
                        
                        # Add CBR traffic
                        tests.append(create_udp_config(
                            client_index,
                            cbr_rate,
                            start_time
                        ))
                        
                        filename = os.path.join(output_dir, 
                            f"test_{scenario_name}_{flow_count}flows_{int(cbr_rate)}mbps_cbr.json")
                        with open(filename, 'w') as f:
                            json.dump(tests, f, indent=2)
                else:
                    tests = []
                    client_index = 1
                    start_time = 0
                    
                    for i in range(flow_count):
                        tests.append(create_tcp_config(
                            client_index,
                            limited_rate,
                            start_time
                        ))
                        client_index += 1
                        start_time += 1
                    
                    filename = os.path.join(output_dir, 
                        f"test_{scenario_name}_{flow_count}flows.json")
                    with open(filename, 'w') as f:
                            json.dump(tests, f, indent=2)

if __name__ == "__main__":
    generate_test_files("Experiments.csv")