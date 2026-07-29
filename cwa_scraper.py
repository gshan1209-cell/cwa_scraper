#!/usr/bin/env python3
"""
CWA Open Data Scraper

Downloads weather forecast files from the Taiwan Central Weather
Administration (CWA) Open Data Platform.

Security policy:
- TLS certificate verification is always enabled.
- SSL verification failures fail closed and are never retried with verify=False.
- CWA_API_KEY from the environment is preferred.
- --api-key remains only for backward compatibility and emits a warning because
  command-line arguments can be exposed through shell history or process lists.
"""

from __future__ import annotations

import argparse
import getpass
import json
import os
import sys
from datetime import datetime

import requests
from dotenv import load_dotenv


EXIT_OK = 0
EXIT_CONFIG = 2
EXIT_TLS = 3
EXIT_NETWORK = 4
EXIT_HTTP = 5
EXIT_PARSE = 6
EXIT_WRITE = 7

DEFAULT_DATASET = "F-A0010-001"
DEFAULT_TIMEOUT_SECONDS = 30
CWA_FILE_API_BASE_URL = "https://opendata.cwa.gov.tw/fileapi/v1/opendataapi"

# Load environment variables from .env when present. Secrets must never be
# written to logs, output files, Agent Context, or Evidence records.
load_dotenv()


def parse_arguments(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Download forecast dataset files from the Taiwan Central Weather "
            "Administration (CWA)."
        )
    )
    parser.add_argument(
        "-k",
        "--api-key",
        type=str,
        default=None,
        help=(
            "Deprecated compatibility option. Prefer the CWA_API_KEY environment "
            "variable because command-line secrets may be exposed."
        ),
    )
    parser.add_argument(
        "-d",
        "--dataset",
        type=str,
        default=DEFAULT_DATASET,
        help=f"Dataset identifier (default: {DEFAULT_DATASET}).",
    )
    parser.add_argument(
        "-f",
        "--format",
        type=str,
        choices=["JSON", "XML"],
        default="JSON",
        help="Output data format (default: JSON).",
    )
    parser.add_argument(
        "-o",
        "--out-dir",
        type=str,
        default="downloads",
        help="Directory to save downloaded files (default: downloads).",
    )
    parser.add_argument(
        "--no-pretty",
        action="store_true",
        help="Disable JSON pretty printing.",
    )
    return parser.parse_args(argv)


def resolve_api_key(args: argparse.Namespace) -> str | None:
    """Resolve the API key without exposing it in output or logs."""
    environment_key = os.getenv("CWA_API_KEY")
    if environment_key:
        return environment_key.strip()

    if args.api_key:
        print(
            "Security warning: --api-key is retained only for backward "
            "compatibility. Prefer CWA_API_KEY because command-line secrets may "
            "appear in shell history or process listings.",
            file=sys.stderr,
        )
        return args.api_key.strip()

    if sys.stdin.isatty():
        try:
            return getpass.getpass("Please enter your CWA API Key: ").strip()
        except (KeyboardInterrupt, EOFError):
            print("\nOperation cancelled.", file=sys.stderr)
            return None

    return None


def preview_json_data(data: object) -> None:
    """Print a small, non-authoritative preview of a retrieved JSON dataset."""
    try:
        if not isinstance(data, dict):
            print("[Preview] Retrieved JSON root is not an object.")
            return

        if "cwaopendata" in data:
            cwa = data["cwaopendata"]
            if not isinstance(cwa, dict):
                print("[Preview] Unexpected cwaopendata structure.")
                return

            title = cwa.get("datasetName", "一週農業氣象預報")
            metadata = cwa.get("resources", {}).get("resource", {}).get("metadata", {})
            issue_time = metadata.get("temporal", {}).get("issueTime", "未知時間")
            print(f"\n[預覽] 資料集名稱: {title}")
            print(f"[預覽] 發布時間: {issue_time}")

            agr = (
                cwa.get("resources", {})
                .get("resource", {})
                .get("data", {})
                .get("agrWeatherForecasts", {})
            )
            profile = agr.get("weatherProfile", "")
            if profile:
                print(f"\n[預覽] 天氣概況:\n{profile}")

            locations = agr.get("weatherForecasts", {}).get("location", [])
            if locations:
                print("\n[預覽] 各地區預報 (前 3 天):")
                for location in locations:
                    location_name = location.get("locationName", "未知區域")
                    print(f"  ● {location_name}:")

                    weather_elements = location.get("weatherElements", {})
                    weather_daily = weather_elements.get("Wx", {}).get("daily", [])
                    minimum_daily = weather_elements.get("MinT", {}).get("daily", [])
                    maximum_daily = weather_elements.get("MaxT", {}).get("daily", [])

                    for index in range(min(3, len(weather_daily))):
                        date = weather_daily[index].get("dataDate", "")
                        description = weather_daily[index].get("weather", "")
                        minimum = (
                            minimum_daily[index].get("temperature", "")
                            if index < len(minimum_daily)
                            else ""
                        )
                        maximum = (
                            maximum_daily[index].get("temperature", "")
                            if index < len(maximum_daily)
                            else ""
                        )
                        temperature = (
                            f" ({minimum}~{maximum}°C)" if minimum or maximum else ""
                        )
                        print(f"    - {date}: {description}{temperature}")
            else:
                print("[預覽] 未找到區域預報資料。")
            return

        if "records" in data:
            records = data["records"]
            if not isinstance(records, dict):
                print("[Preview] Unexpected records structure.")
                return

            dataset_info = records.get("datasetInfo", {})
            title = dataset_info.get("datasetName", "一週農業氣象預報")
            update_time = dataset_info.get("updateDate", "Unknown")
            print(f"\n[Preview] Dataset: {title}")
            print(f"[Preview] Last Update: {update_time}")

            locations = records.get("location", []) or records.get(
                "agriculturalInfo", {}
            ).get("location", [])
            if locations:
                print(f"[Preview] Found forecasts for {len(locations)} locations/regions:")
                for location in locations[:4]:
                    location_name = location.get("locationName", "Unknown Location")
                    values: list[str] = []
                    for element in location.get("weatherElement", [])[:2]:
                        element_name = element.get("elementName", "")
                        time_values = element.get("time", [])
                        if not time_values:
                            continue
                        first_value = time_values[0]
                        value = first_value.get("elementValue", {}).get("value", "")
                        if not value and "parameter" in first_value:
                            value = first_value["parameter"].get("parameterName", "")
                        if value:
                            values.append(f"{element_name}: {value}")
                    suffix = f" ({', '.join(values)})" if values else ""
                    print(f"  - {location_name}{suffix}")
                if len(locations) > 4:
                    print(f"  - ... and {len(locations) - 4} more locations.")
            else:
                print("[Preview] Retrieved JSON records keys:", list(records.keys()))
            return

        print("[Preview] Retrieved JSON format differs from typical CWA responses.")
    except (AttributeError, IndexError, TypeError, ValueError) as error:
        print(f"[Preview Warning] Could not parse forecast preview: {error}")


def request_dataset(
    *, dataset: str, output_format: str, api_key: str
) -> requests.Response:
    """Request a CWA dataset with mandatory TLS verification."""
    url = f"{CWA_FILE_API_BASE_URL}/{dataset}"
    params = {"Authorization": api_key, "format": output_format}

    # Do not add verify=False or an SSL fallback. The default verify=True is a
    # mandatory production invariant approved in Wave 1D Decision D6.
    return requests.get(url, params=params, timeout=DEFAULT_TIMEOUT_SECONDS)


def validate_response(response: requests.Response, dataset: str) -> int:
    if response.status_code == 401:
        print(
            "Error 401: Unauthorized. Check whether CWA_API_KEY is valid.",
            file=sys.stderr,
        )
        return EXIT_HTTP
    if response.status_code == 404:
        print(
            f"Error 404: Dataset '{dataset}' was not found.",
            file=sys.stderr,
        )
        return EXIT_HTTP

    try:
        response.raise_for_status()
    except requests.exceptions.HTTPError as error:
        status = response.status_code
        print(f"HTTP error {status}: {error}", file=sys.stderr)
        return EXIT_HTTP

    return EXIT_OK


def save_response(
    *,
    response: requests.Response,
    output_format: str,
    dataset: str,
    output_directory: str,
    pretty_json: bool,
) -> tuple[int, str | None]:
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    extension = output_format.lower()
    filename = f"{dataset}_{timestamp}.{extension}"
    filepath = os.path.join(output_directory, filename)

    try:
        os.makedirs(output_directory, exist_ok=True)
    except OSError as error:
        print(f"Failed to create output directory: {error}", file=sys.stderr)
        return EXIT_WRITE, None

    if output_format == "JSON":
        try:
            json_data = response.json()
        except ValueError as error:
            print(
                "Invalid JSON response: expected JSON but parsing failed. "
                "No output file was written.",
                file=sys.stderr,
            )
            print(f"Parser detail: {error}", file=sys.stderr)
            return EXIT_PARSE, None

        if isinstance(json_data, dict) and json_data.get("success") in {
            False,
            "false",
            "False",
        }:
            message = json_data.get("message", "Unknown CWA API error")
            print(f"CWA API error: {message}", file=sys.stderr)
            return EXIT_HTTP, None

        try:
            with open(filepath, "w", encoding="utf-8") as output_file:
                json.dump(
                    json_data,
                    output_file,
                    ensure_ascii=False,
                    indent=2 if pretty_json else None,
                )
        except OSError as error:
            print(f"Failed to write output file: {error}", file=sys.stderr)
            return EXIT_WRITE, None

        preview_json_data(json_data)
        return EXIT_OK, filepath

    try:
        with open(filepath, "wb") as output_file:
            output_file.write(response.content)
    except OSError as error:
        print(f"Failed to write output file: {error}", file=sys.stderr)
        return EXIT_WRITE, None

    snippet = response.text[:400]
    print(f"\n[Preview] XML snippet:\n{snippet}...")
    return EXIT_OK, filepath


def main(argv: list[str] | None = None) -> int:
    args = parse_arguments(argv)
    api_key = resolve_api_key(args)
    if not api_key:
        print(
            "Error: CWA API key is required. Set CWA_API_KEY in the environment "
            "or enter it interactively in a secure terminal.",
            file=sys.stderr,
        )
        return EXIT_CONFIG

    output_format = args.format.upper()
    print(
        "Connecting to CWA Open Data Platform "
        f"for dataset {args.dataset} ({output_format}) with TLS verification enabled..."
    )

    try:
        response = request_dataset(
            dataset=args.dataset,
            output_format=output_format,
            api_key=api_key,
        )
    except requests.exceptions.SSLError as error:
        print(
            "TLS verification failed. The request was stopped and will not be "
            "retried with certificate verification disabled.",
            file=sys.stderr,
        )
        print(f"TLS detail: {error}", file=sys.stderr)
        return EXIT_TLS
    except requests.exceptions.Timeout as error:
        print(f"CWA request timed out: {error}", file=sys.stderr)
        return EXIT_NETWORK
    except requests.exceptions.ConnectionError as error:
        print(f"CWA connection failed: {error}", file=sys.stderr)
        return EXIT_NETWORK
    except requests.exceptions.RequestException as error:
        print(f"CWA request failed: {error}", file=sys.stderr)
        return EXIT_NETWORK

    validation_result = validate_response(response, args.dataset)
    if validation_result != EXIT_OK:
        return validation_result

    result, filepath = save_response(
        response=response,
        output_format=output_format,
        dataset=args.dataset,
        output_directory=args.out_dir,
        pretty_json=not args.no_pretty,
    )
    if result != EXIT_OK:
        return result

    assert filepath is not None
    print(f"Saved dataset file to: {os.path.abspath(filepath)}")
    print("\nScraping process finished successfully!")
    return EXIT_OK


if __name__ == "__main__":
    raise SystemExit(main())
