#!/usr/bin/env python3
"""List all available tags in Samsara."""

import os
import sys
from datetime import datetime
from dotenv import load_dotenv
from query_geofences import SamsaraGeofenceQuery

def format_timestamp(timestamp):
    """Format timestamp for display."""
    if not timestamp:
        return "N/A"
    try:
        # Handle both string and numeric timestamps
        if isinstance(timestamp, str):
            dt = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
        else:
            dt = datetime.fromtimestamp(timestamp)
        return dt.strftime("%Y-%m-%d %H:%M:%S")
    except:
        return str(timestamp)

def main():
    load_dotenv()
    
    api_token = os.getenv('SAMSARA_API_TOKEN')
    if not api_token:
        print("Error: SAMSARA_API_TOKEN environment variable not set")
        sys.exit(1)
    
    client = SamsaraGeofenceQuery(api_token)
    
    try:
        # Clear cache to get fresh data
        print("Clearing cache to get fresh data...")
        client.clear_cache()
        
        print("Fetching all tags...")
        tags = client.get_all_tags()
        
        print(f"\nFound {len(tags)} tags:")
        print("=" * 80)
        
        # Sort by creation time if available, otherwise by name
        def sort_key(tag):
            created_at = tag.get('createdAtTime') or tag.get('created_at') or tag.get('createdAt')
            if created_at:
                try:
                    if isinstance(created_at, str):
                        return datetime.fromisoformat(created_at.replace('Z', '+00:00'))
                    else:
                        return datetime.fromtimestamp(created_at)
                except:
                    pass
            return datetime.min
        
        sorted_tags = sorted(tags, key=sort_key, reverse=True)
        
        for i, tag in enumerate(sorted_tags, 1):
            name = tag.get('name', 'Unknown')
            tag_id = tag.get('id', 'Unknown')
            
            # Try different possible timestamp field names
            created_at = (tag.get('createdAtTime') or 
                         tag.get('created_at') or 
                         tag.get('createdAt') or 
                         tag.get('dateCreated'))
            
            created_str = format_timestamp(created_at)
            
            print(f"{i:3d}. {name:<30} (ID: {tag_id:<10}) Created: {created_str}")
            
            # Debug: show all available fields for first few tags
            if i <= 3:
                print(f"     Available fields: {list(tag.keys())}")
            
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    finally:
        client.close()

if __name__ == "__main__":
    main() 