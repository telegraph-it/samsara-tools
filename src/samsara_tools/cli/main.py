#!/usr/bin/env python3
"""Main CLI entry point for Samsara Tools."""

import argparse
import os
import sys
from pathlib import Path
from dotenv import load_dotenv

from ..core.geofence_query import SamsaraGeofenceQuery
from ..core.client import SamsaraClient


def setup_environment():
    """Load environment variables from .env file."""
    load_dotenv()
    
    api_token = os.getenv('SAMSARA_API_TOKEN')
    if not api_token:
        print("Error: SAMSARA_API_TOKEN environment variable not set")
        print("Please create a .env file with your Samsara API token:")
        print("SAMSARA_API_TOKEN=your_token_here")
        sys.exit(1)
    
    return api_token


def cmd_list_tags(args):
    """List all available tags."""
    api_token = setup_environment()
    client = SamsaraClient(api_token)
    
    try:
        print("Fetching all tags...")
        tags = client.get_all_tags()
        
        if not tags:
            print("No tags found")
            return
        
        print(f"\nFound {len(tags)} tags:")
        print("=" * 50)
        
        for i, tag in enumerate(tags, 1):
            name = tag.get('name', 'Unknown')
            tag_id = tag.get('id', 'Unknown')
            created_at = tag.get('createdAtTime', 'Unknown')
            print(f"{i:3d}. {name} (ID: {tag_id})")
            if args.show_details:
                print(f"     Created: {created_at}")
                
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)


def cmd_query_geofences(args):
    """Query geofences by tag name."""
    api_token = setup_environment()
    client = SamsaraGeofenceQuery(api_token)
    
    try:
        print(f"Querying Samsara API for geofences with tag: '{args.tag_name}'")
        print("=" * 50)
        
        geofences = client.query_geofences_by_tag(args.tag_name)
        
        if geofences:
            client.print_geofence_summary(geofences, args.tag_name)
            
            if args.save:
                saved_files = client.save_results(geofences, args.tag_name)
                print(f"\nResults saved:")
                for file_type, path in saved_files.items():
                    print(f"  {file_type.upper()}: {path}")
        else:
            print(f"\nNo geofences found with tag '{args.tag_name}'")
            
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)


def cmd_list_gateways(args):
    """List all gateways and their connection status."""
    api_token = setup_environment()
    client = SamsaraClient(api_token)
    
    try:
        print("Fetching gateways...")
        gateways = client.get_gateways(use_cache=not args.no_cache)
        
        if not gateways:
            print("No gateways found")
            return
        
        print(f"\nFound {len(gateways)} gateways:")
        print("=" * 50)
        
        for i, gateway in enumerate(gateways, 1):
            serial = gateway.get('serial', 'Unknown')
            model = gateway.get('model', 'Unknown')
            status = gateway.get('connectionStatus', {}).get('healthStatus', 'Unknown')
            last_connected = gateway.get('connectionStatus', {}).get('lastConnected', 'Never')
            
            print(f"{i:3d}. {serial} ({model})")
            print(f"     Status: {status}")
            print(f"     Last Connected: {last_connected}")
            
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description='Samsara API Tools - Interact with the Samsara API',
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    
    subparsers = parser.add_subparsers(dest='command', help='Available commands')
    
    # List tags command
    tags_parser = subparsers.add_parser('list-tags', help='List all available tags')
    tags_parser.add_argument('--show-details', action='store_true', 
                           help='Show additional details like creation time')
    tags_parser.set_defaults(func=cmd_list_tags)
    
    # Query geofences command
    geofences_parser = subparsers.add_parser('query-geofences', help='Query geofences by tag')
    geofences_parser.add_argument('tag_name', help='Tag name to search for')
    geofences_parser.add_argument('--save', action='store_true', 
                                help='Save results to CSV and JSON files')
    geofences_parser.set_defaults(func=cmd_query_geofences)
    
    # List gateways command  
    gateways_parser = subparsers.add_parser('list-gateways', help='List all gateways')
    gateways_parser.add_argument('--no-cache', action='store_true',
                               help='Skip cache and fetch fresh data')
    gateways_parser.set_defaults(func=cmd_list_gateways)
    
    # Parse arguments
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        sys.exit(1)
    
    # Run the selected command
    args.func(args)


if __name__ == "__main__":
    main() 