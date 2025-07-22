#!/usr/bin/env python3
"""Main CLI entry point for Samsara Tools."""

import argparse
import os
import sys
from pathlib import Path
from dotenv import load_dotenv

from ..core.geofence_query import SamsaraGeofenceQuery
from ..core.client import SamsaraClient
from ..core.route_service import RouteService
from datetime import datetime, timedelta


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


def cmd_routes_query(args):
    """Query routes within a time range."""
    api_token = setup_environment()
    service = RouteService(api_token)
    
    try:
        # Parse dates
        start_time = datetime.fromisoformat(args.start)
        end_time = datetime.fromisoformat(args.end) if args.end else datetime.now()
        
        print(f"Querying routes from {start_time} to {end_time}")
        if args.vehicle:
            print(f"Filtering by vehicle ID: {args.vehicle}")
        if args.driver:
            print(f"Filtering by driver ID: {args.driver}")
        if args.name_filter:
            print(f"Filtering by name containing: '{args.name_filter}'")
        print("=" * 50)
        
        routes = service.query_routes(
            start_time=start_time,
            end_time=end_time,
            vehicle_id=args.vehicle,
            driver_id=args.driver,
            include_points=args.include_points,
            stops_only=args.stops_only
        )
        
        # Filter by name if specified
        if args.name_filter:
            routes = [r for r in routes if r.name and args.name_filter.lower() in r.name.lower()]
        
        if routes:
            if args.json_output:
                # Generate grouped JSON output
                grouped_data = service.group_routes_by_dairy_and_injection_site(routes)
                output_file = Path(args.output) if args.output else Path(f"grouped_routes_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json")
                service.save_grouped_routes_json(grouped_data, output_file)
                print(f"\nGrouped routes saved to: {output_file}")
            else:
                service.print_route_summary(routes)
                
                if args.output:
                    output_file = Path(args.output)
                    saved_file = service.save_routes(routes, format=args.format, output_file=output_file)
                    print(f"\nRoutes saved to: {saved_file}")
        else:
            print("\nNo routes found in the specified time range")
            
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)


def cmd_routes_get(args):
    """Get details for a specific route."""
    api_token = setup_environment()
    service = RouteService(api_token)
    
    try:
        print(f"Fetching route {args.route_id}...")
        
        route = service.get_route_by_id(args.route_id, include_points=args.include_points, stops_only=args.stops_only)
        
        if route:
            service.print_route_summary([route])
            
            if args.output:
                output_file = Path(args.output)
                saved_file = service.save_routes([route], format=args.format, output_file=output_file)
                print(f"\nRoute saved to: {saved_file}")
        else:
            print(f"\nRoute {args.route_id} not found")
            
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
    
    # Routes subcommand
    routes_parser = subparsers.add_parser('routes', help='Route data operations')
    routes_subparsers = routes_parser.add_subparsers(dest='routes_command', help='Route commands')
    
    # Routes query command
    routes_query = routes_subparsers.add_parser('query', help='Query routes by time range')
    routes_query.add_argument('--start', required=True, 
                            help='Start date/time (ISO format: YYYY-MM-DD or YYYY-MM-DDTHH:MM:SS)')
    routes_query.add_argument('--end', 
                            help='End date/time (ISO format). Defaults to now if not specified')
    routes_query.add_argument('--vehicle', help='Filter by vehicle ID')
    routes_query.add_argument('--driver', help='Filter by driver ID')
    routes_query.add_argument('--name-filter', help='Filter routes by name (case-insensitive substring match)')
    routes_query.add_argument('--include-points', action='store_true', 
                            help='Include GPS track points (increases query time)')
    routes_query.add_argument('--stops-only', action='store_true',
                            help='Only get basic stops data, skip detailed GPS path data (avoids 404 errors)')
    routes_query.add_argument('--format', choices=['json', 'csv', 'gpx'], default='json',
                            help='Output format (default: json)')
    routes_query.add_argument('--output', help='Output file path')
    routes_query.add_argument('--json-output', action='store_true',
                            help='Output grouped JSON format organized by dairy and injection site')
    routes_query.set_defaults(func=cmd_routes_query)
    
    # Routes get command
    routes_get = routes_subparsers.add_parser('get', help='Get a specific route by ID')
    routes_get.add_argument('route_id', help='Route ID to fetch')
    routes_get.add_argument('--include-points', action='store_true', 
                          help='Include GPS track points')
    routes_get.add_argument('--stops-only', action='store_true',
                          help='Only get basic stops data, skip detailed GPS path data')
    routes_get.add_argument('--format', choices=['json', 'csv', 'gpx'], default='json',
                          help='Output format (default: json)')
    routes_get.add_argument('--output', help='Output file path')
    routes_get.set_defaults(func=cmd_routes_get)
    
    # Parse arguments
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        sys.exit(1)
    
    # Handle routes subcommands
    if args.command == 'routes' and not getattr(args, 'routes_command', None):
        routes_parser.print_help()
        sys.exit(1)
    
    # Run the selected command
    if hasattr(args, 'func'):
        args.func(args)
    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main() 