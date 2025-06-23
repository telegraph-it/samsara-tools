import requests
import pandas as pd
from datetime import datetime, timezone
import os
from dotenv import load_dotenv
import argparse
from pathlib import Path

# Configuration constants
RESULTS_DIR = Path('data/output')

class SamsaraClient:
    def __init__(self, api_token):
        self.headers = {
            "Authorization": f"Bearer {api_token}",
            "Accept": "application/json"
        }

    def get_all_gateways(self):
        url = "https://api.samsara.com/gateways"
        try:
            response = requests.get(url, headers=self.headers)
            response.raise_for_status()
            return response.json().get('data', [])
        except requests.exceptions.RequestException as e:
            print(f"Error fetching gateways: {e}")
            return []

    def process_gateways(self, gateways):
        gateway_data = []
        current_time = datetime.now(timezone.utc)

        for gateway in gateways:
            connection_status = gateway.get('connectionStatus', {})
            last_connected_str = connection_status.get('lastConnected')
            
            if last_connected_str:
                last_connected = datetime.fromisoformat(last_connected_str.replace('Z', '+00:00'))
                last_connected_formatted = last_connected.strftime('%Y-%m-%d %H:%M:%S UTC')
                days_since_connected = (current_time - last_connected).total_seconds() / (24 * 3600)
            else:
                last_connected_formatted = 'Never'
                days_since_connected = float('inf')

            gateway_info = {
                'serial': gateway.get('serial', ''),
                'model': gateway.get('model', ''),
                'health_status': connection_status.get('healthStatus'),
                'last_connected': last_connected_formatted,
                'days_since_connected': f"{days_since_connected:.1f}" if days_since_connected != float('inf') else 'Never',
                'vin': gateway.get('asset', {}).get('externalIds', {}).get('samsara.vin', ''),
                'asset_id': gateway.get('asset', {}).get('id', '')
            }
            gateway_data.append(gateway_info)

        return pd.DataFrame(gateway_data)

def main():
    load_dotenv()
    
    # Ensure output directory exists
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    
    parser = argparse.ArgumentParser(description='List all Samsara gateways and their connection status')
    parser.add_argument('--token', '-t', help='Samsara API token')
    parser.add_argument('--output', '-o', help='Output filename (will be saved in data/output/)', default='gateway_list')
    args = parser.parse_args()

    api_token = args.token or os.environ.get('SAMSARA_API_TOKEN')
    if not api_token:
        print("Error: Samsara API token not provided. Use --token or set SAMSARA_API_TOKEN environment variable.")
        return

    client = SamsaraClient(api_token)
    print("Fetching gateways...")
    gateways = client.get_all_gateways()
    
    if not gateways:
        print("No gateways found")
        return

    df = client.process_gateways(gateways)
    df = df.sort_values('days_since_connected', ascending=False)
    
    print("\nGateway Summary:")
    print(df.to_string(index=False))

    # Save with timestamp in filename
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    output_path = RESULTS_DIR / f'{args.output}_{timestamp}.csv'
    df.to_csv(output_path, index=False)
    print(f"\nResults saved to: {output_path}")

if __name__ == "__main__":
    main() 