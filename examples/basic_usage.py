#!/usr/bin/env python3
"""
Basic usage example for Samsara API Tools.

This example shows how to use the Python API to:
1. List all tags
2. Query geofences by tag
3. List gateways
"""

import os
from dotenv import load_dotenv
from samsara_tools import SamsaraClient, SamsaraGeofenceQuery

def main():
    # Load environment variables
    load_dotenv()
    api_token = os.getenv('SAMSARA_API_TOKEN')
    
    if not api_token:
        print("Error: SAMSARA_API_TOKEN not found in environment")
        print("Create a .env file with your API token")
        return
    
    # Initialize client
    print("Initializing Samsara client...")
    client = SamsaraClient(api_token)
    
    # Verify API access
    success, message = client.verify_api_access()
    if not success:
        print(f"API verification failed: {message}")
        return
    print("✓ API access verified")
    
    # Example 1: List all tags
    print("\n1. Listing all tags...")
    tags = client.get_all_tags()
    print(f"Found {len(tags)} tags:")
    for i, tag in enumerate(tags[:5], 1):  # Show first 5
        print(f"  {i}. {tag['name']} (ID: {tag['id']})")
    if len(tags) > 5:
        print(f"  ... and {len(tags) - 5} more")
    
    # Example 2: Query geofences by tag
    if tags:
        print("\n2. Querying geofences...")
        geo_client = SamsaraGeofenceQuery(api_token)
        
        # Use the first tag as an example
        first_tag = tags[0]['name']
        print(f"Searching for geofences with tag: '{first_tag}'")
        geofences = geo_client.query_geofences_by_tag(first_tag)
        
        if geofences:
            print(f"Found {len(geofences)} geofences:")
            for geofence in geofences[:3]:  # Show first 3
                print(f"  - {geofence['name']}")
                print(f"    {geofence['formatted_address']}")
        else:
            print("No geofences found for this tag")
    
    # Example 3: List gateways
    print("\n3. Listing gateways...")
    gateways = client.get_gateways()
    print(f"Found {len(gateways)} gateways:")
    for i, gateway in enumerate(gateways[:5], 1):  # Show first 5
        serial = gateway.get('serial', 'Unknown')
        model = gateway.get('model', 'Unknown')
        status = gateway.get('connectionStatus', {}).get('healthStatus', 'Unknown')
        print(f"  {i}. {serial} ({model}) - {status}")
    if len(gateways) > 5:
        print(f"  ... and {len(gateways) - 5} more")
    
    print("\n✓ Example completed successfully!")
    print("\nNext steps:")
    print("- Try the CLI interface: uv run samsara-tools --help")
    print("- Explore the API documentation in README.md")
    print("- Check out the legacy/ folder for original scripts")

if __name__ == "__main__":
    main() 