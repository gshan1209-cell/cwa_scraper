#!/usr/bin/env python3
"""
CWA Open Data Scraper
Author: Antigravity

This script downloads the weather forecast files (specifically F-A0010-001,
"一週農業氣象預報") from the Taiwan Central Weather Administration (CWA)
Open Data Platform.
"""

import os
import sys
import json
import argparse
from datetime import datetime
import requests
from dotenv import load_dotenv

# Load environment variables from .env file if it exists
load_dotenv()

def parse_arguments():
    parser = argparse.ArgumentParser(
        description="Download forecast dataset files from the Taiwan Central Weather Administration (CWA)."
    )
    parser.add_argument(
        "-k", "--api-key",
        type=str,
        default=os.getenv("CWA_API_KEY"),
        help="CWA API Authorization Code. Can also be set in .env as CWA_API_KEY."
    )
    parser.add_argument(
        "-d", "--dataset",
        type=str,
        default="F-A0010-001",
        help="Dataset identifier (default: F-A0010-001)."
    )
    parser.add_argument(
        "-f", "--format",
        type=str,
        choices=["JSON", "XML"],
        default="JSON",
        help="Output data format (default: JSON)."
    )
    parser.add_argument(
        "-o", "--out-dir",
        type=str,
        default="downloads",
        help="Directory to save downloaded files (default: downloads)."
    )
    parser.add_argument(
        "--no-pretty",
        action="store_true",
        help="Disable JSON pretty printing."
    )
    return parser.parse_args()

def preview_json_data(data):
    """
    Prints a simple overview of the retrieved forecast dataset.
    """
    try:
        # CWA response structure usually has success and records
        if "records" in data:
            records = data["records"]
            
            # Print dataset info
            dataset_info = records.get("datasetInfo", {})
            title = dataset_info.get("datasetName", "一週農業氣象預報")
            update_time = dataset_info.get("updateDate", "Unknown")
            print(f"\n[Preview] Dataset: {title}")
            print(f"[Preview] Last Update: {update_time}")
            
            # Print some content summary if available
            # Agriculture forecast structure typically has locations/regions under records
            # Let's inspect location or agriculturalInfo
            locations = records.get("location", []) or records.get("agriculturalInfo", {}).get("location", [])
            
            if locations:
                print(f"[Preview] Found forecasts for {len(locations)} locations/regions:")
                for loc in locations[:4]: # Limit to first 4 for preview
                    loc_name = loc.get("locationName", "Unknown Location")
                    # Weather elements
                    we_str = []
                    weather_elements = loc.get("weatherElement", [])
                    for elem in weather_elements[:2]:
                        elem_name = elem.get("elementName", "")
                        # Try to get value or time values
                        time_vals = elem.get("time", [])
                        if time_vals:
                            val = time_vals[0].get("elementValue", {}).get("value", "")
                            if not val and "parameter" in time_vals[0]:
                                val = time_vals[0]["parameter"].get("parameterName", "")
                            if val:
                                we_str.append(f"{elem_name}: {val}")
                    
                    if we_str:
                        print(f"  - {loc_name} ({', '.join(we_str)})")
                    else:
                        print(f"  - {loc_name}")
                if len(locations) > 4:
                    print(f"  - ... and {len(locations) - 4} more locations.")
            else:
                # Fallback to general structures
                print("[Preview] Retreived JSON records keys:", list(records.keys()))
        else:
            print("[Preview] Retrieved JSON format differs from typical CWA API responses.")
    except Exception as e:
        print(f"[Preview Warning] Could not parse forecast preview: {e}")

def main():
    args = parse_arguments()
    api_key = args.api_key
    
    # If API key is not provided, prompt the user if it's an interactive shell, or error
    if not api_key:
        if sys.stdin.isatty():
            print("CWA API Authorization Code (API Key) not found in environment or arguments.")
            try:
                api_key = input("Please enter your CWA API Key: ").strip()
            except KeyboardInterrupt:
                print("\nOperation cancelled.")
                sys.exit(1)
        
        if not api_key:
            print("Error: CWA API key is required. Get yours at https://opendata.cwa.gov.tw/", file=sys.stderr)
            print("Set it in a .env file (CWA_API_KEY=xxx) or pass it via --api-key / -k.", file=sys.stderr)
            sys.exit(1)

    # Clean the format variable (CWA api accepts uppercase/lowercase sometimes, but let's standardize)
    fmt = args.format.upper()
    
    # Construct the download URL for File API (v1)
    # URL pattern: https://opendata.cwa.gov.tw/fileapi/v1/opendataapi/{dataset}?Authorization={api_key}&format={format}
    url = f"https://opendata.cwa.gov.tw/fileapi/v1/opendataapi/{args.dataset}"
    
    params = {
        "Authorization": api_key,
        "format": fmt
    }
    
    print(f"Connecting to CWA Open Data Platform to fetch dataset: {args.dataset} ({fmt})...")
    
    # Suppress SSL certificate verification warning if verification is bypassed
    import urllib3
    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
    
    try:
        try:
            response = requests.get(url, params=params, timeout=30)
        except requests.exceptions.SSLError as ssl_err:
            print(f"Warning: SSL certificate verification failed ({ssl_err}).")
            print("Retrying with SSL verification disabled...")
            response = requests.get(url, params=params, timeout=30, verify=False)
        
        # Check HTTP status code
        if response.status_code == 401:
            print("Error 401: Unauthorized. Please check if your CWA API Key is valid.", file=sys.stderr)
            sys.exit(1)
        elif response.status_code == 404:
            print(f"Error 404: Dataset '{args.dataset}' not found. Make sure the ID is correct.", file=sys.stderr)
            sys.exit(1)
        
        response.raise_for_status()
        
    except requests.exceptions.RequestException as e:
        print(f"HTTP Request failed: {e}", file=sys.stderr)
        sys.exit(1)

    # Ensure output directory exists
    os.makedirs(args.out_dir, exist_ok=True)
    
    # Generate output file name with timestamp
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    extension = fmt.lower()
    filename = f"{args.dataset}_{timestamp}.{extension}"
    filepath = os.path.join(args.out_dir, filename)
    
    print(f"Download complete. Processing content...")
    
    # Save the content
    try:
        if fmt == "JSON":
            try:
                json_data = response.json()
                
                # Check for API error response disguised as a 200 OK JSON
                # e.g., {"success": "false", "message": "..."} or similar
                if isinstance(json_data, dict) and json_data.get("success") == "false":
                    message = json_data.get("message", "Unknown API error")
                    print(f"API Error: {message}", file=sys.stderr)
                    sys.exit(1)
                
                with open(filepath, "w", encoding="utf-8") as f:
                    if not args.no_pretty:
                        json.dump(json_data, f, ensure_ascii=False, indent=2)
                    else:
                        json.dump(json_data, f, ensure_ascii=False)
                
                print(f"Saved dataset file to: {os.path.abspath(filepath)}")
                
                # Provide a quick terminal preview
                preview_json_data(json_data)
                
            except json.JSONDecodeError:
                # In case response is not valid JSON
                print("Warning: Response was expected to be JSON but could not be parsed. Saving raw content.", file=sys.stderr)
                with open(filepath, "wb") as f:
                    f.write(response.content)
                print(f"Saved raw content to: {os.path.abspath(filepath)}")
        else:
            # XML or other formats, save raw content
            with open(filepath, "wb") as f:
                f.write(response.content)
            print(f"Saved dataset file to: {os.path.abspath(filepath)}")
            
            # Simple preview for XML
            if fmt == "XML":
                snippet = response.text[:400]
                print(f"\n[Preview] XML snippet:\n{snippet}...")
                
    except IOError as e:
        print(f"Failed to write file to disk: {e}", file=sys.stderr)
        sys.exit(1)
        
    print("\nScraping process finished successfully!")

if __name__ == "__main__":
    main()
