#!/usr/bin/env python3
"""
Seed sample data into NDP-EP API for demo/development purposes.
Creates organizations, datasets, resources, services, and S3 objects.

Usage:
    python seed_sample_data.py
"""

import io
import json
import time
from typing import Any, Dict, List

import requests

# Configuration
BASE_URL = "http://localhost:8002"
TEST_TOKEN = "testing_token"  # From .env
HEADERS = {"Authorization": f"Bearer {TEST_TOKEN}"}


# Color output for terminal
class Colors:
    GREEN = "\033[92m"
    RED = "\033[91m"
    YELLOW = "\033[93m"
    BLUE = "\033[94m"
    CYAN = "\033[96m"
    MAGENTA = "\033[95m"
    RESET = "\033[0m"
    BOLD = "\033[1m"


def log_info(message: str):
    """Log info message."""
    print(f"{Colors.CYAN}ℹ{Colors.RESET} {message}")


def log_success(message: str):
    """Log success message."""
    print(f"{Colors.GREEN}✓{Colors.RESET} {message}")


def log_error(message: str):
    """Log error message."""
    print(f"{Colors.RED}✗{Colors.RESET} {message}")


def log_warning(message: str):
    """Log warning message."""
    print(f"{Colors.YELLOW}⚠{Colors.RESET} {message}")


def log_section(title: str):
    """Print a section header."""
    print(f"\n{Colors.BOLD}{Colors.BLUE}{'='*70}{Colors.RESET}")
    print(f"{Colors.BOLD}{Colors.BLUE}{title}{Colors.RESET}")
    print(f"{Colors.BOLD}{Colors.BLUE}{'='*70}{Colors.RESET}\n")


def make_request(
    method: str, endpoint: str, description: str, silent: bool = False, **kwargs
) -> Any:
    """
    Make an API request and handle response.

    Args:
        method: HTTP method
        endpoint: API endpoint
        description: Human-readable description
        silent: If True, don't log anything
        **kwargs: Additional arguments for requests

    Returns:
        Response JSON or None if failed
    """
    url = f"{BASE_URL}{endpoint}"
    if not silent:
        log_info(f"{description}...")

    try:
        response = requests.request(method=method, url=url, timeout=15, **kwargs)

        if response.status_code in [200, 201]:
            if not silent:
                log_success(f"{description} (Status: {response.status_code})")
            try:
                return response.json()
            except:
                return {"success": True}
        else:
            if not silent:
                error_msg = f"{description} failed (Status: {response.status_code})"
                try:
                    error_detail = response.json()
                    error_msg += f" - {error_detail}"
                except:
                    error_msg += f" - {response.text[:200]}"
                log_error(error_msg)
            return None

    except requests.exceptions.RequestException as e:
        if not silent:
            log_error(f"{description} failed: {str(e)}")
        return None


# ============================================================================
# CLEANUP FUNCTIONS
# ============================================================================


def cleanup_previous_data():
    """Clean up any previously created data to avoid duplicates."""
    log_section("Cleaning Up Previous Data")

    # Organizations to clean
    orgs_to_clean = ["marine-research", "climate-monitoring", "biodiversity-lab"]

    # Datasets to clean (will be deleted with organizations)
    datasets_to_clean = [
        "mediterranean-sea-temperature",
        "marine-species-census",
        "ocean-salinity-profiles",
        "atmospheric-co2-levels",
        "temperature-anomalies",
        "precipitation-patterns",
        "forest-biodiversity-index",
        "endangered-species-tracking",
    ]

    # S3 buckets to clean
    buckets_to_clean = ["marine-data", "climate-datasets", "biodiversity-data"]

    # Clean S3 objects and buckets
    for bucket in buckets_to_clean:
        # Try to list and delete objects first
        objects_result = make_request(
            "GET",
            f"/s3/objects/{bucket}",
            f"Listing objects in bucket '{bucket}'",
            headers=HEADERS,
            silent=True,
        )

        if objects_result and "objects" in objects_result:
            for obj in objects_result["objects"]:
                make_request(
                    "DELETE",
                    f"/s3/objects/{bucket}/{obj['key']}",
                    f"Deleting object '{obj['key']}'",
                    headers=HEADERS,
                    silent=True,
                )

        # Delete bucket
        make_request(
            "DELETE",
            f"/s3/buckets/{bucket}",
            f"Deleting bucket '{bucket}'",
            headers=HEADERS,
            silent=True,
        )

    # Clean datasets
    for dataset in datasets_to_clean:
        make_request(
            "DELETE",
            f"/resource/{dataset}",
            f"Deleting dataset '{dataset}'",
            headers=HEADERS,
            params={"server": "local"},
            silent=True,
        )

    # Clean organizations
    for org in orgs_to_clean:
        make_request(
            "DELETE",
            f"/organization/{org}",
            f"Deleting organization '{org}'",
            headers=HEADERS,
            params={"server": "local"},
            silent=True,
        )

    log_success("Cleanup completed")
    time.sleep(1)  # Give time for cleanup to complete


# ============================================================================
# SAMPLE DATA DEFINITIONS
# ============================================================================

ORGANIZATIONS = [
    {
        "name": "marine-research",
        "title": "Marine Research Institute",
        "description": "Organization focused on oceanographic and marine biology research",
    },
    {
        "name": "climate-monitoring",
        "title": "Climate Monitoring Center",
        "description": "Center dedicated to climate change observation and analysis",
    },
    {
        "name": "biodiversity-lab",
        "title": "Biodiversity Laboratory",
        "description": "Laboratory studying ecosystem biodiversity and conservation",
    },
]

DATASETS = {
    "marine-research": [
        {
            "name": "mediterranean-sea-temperature",
            "title": "Mediterranean Sea Temperature Measurements",
            "notes": "Long-term sea surface temperature measurements from the Mediterranean Sea. Data collected from moored buoys and research vessels between 2020-2023.",
            "tags": ["oceanography", "temperature", "mediterranean", "climate"],
        },
        {
            "name": "marine-species-census",
            "title": "Mediterranean Marine Species Census",
            "notes": "Comprehensive census of marine species in the Mediterranean region, including fish, mollusks, and crustaceans. Updated quarterly with new observations.",
            "tags": ["biodiversity", "marine-biology", "species", "mediterranean"],
        },
        {
            "name": "ocean-salinity-profiles",
            "title": "Ocean Salinity Vertical Profiles",
            "notes": "Vertical salinity profiles collected from CTD casts at various locations across the Mediterranean basin. Includes depth, salinity, temperature, and pressure measurements.",
            "tags": ["oceanography", "salinity", "ctd", "hydrography"],
        },
    ],
    "climate-monitoring": [
        {
            "name": "atmospheric-co2-levels",
            "title": "Atmospheric CO2 Concentration Measurements",
            "notes": "Continuous monitoring of atmospheric CO2 levels from multiple stations across Europe. Hourly measurements since 2010 with quality control flags.",
            "tags": ["climate", "co2", "atmosphere", "greenhouse-gases"],
        },
        {
            "name": "temperature-anomalies",
            "title": "Global Temperature Anomalies Dataset",
            "notes": "Historical temperature anomalies relative to 1951-1980 baseline. Monthly and annual averages from 1880 to present with uncertainty estimates.",
            "tags": ["climate", "temperature", "anomalies", "global-warming"],
        },
        {
            "name": "precipitation-patterns",
            "title": "Regional Precipitation Patterns",
            "notes": "Daily precipitation measurements from weather stations across Southern Europe. Includes intensity, duration, type, and accumulation data.",
            "tags": ["climate", "precipitation", "meteorology", "weather"],
        },
    ],
    "biodiversity-lab": [
        {
            "name": "forest-biodiversity-index",
            "title": "European Forest Biodiversity Index",
            "notes": "Biodiversity indices calculated for various European forest ecosystems. Includes species richness, Shannon diversity, and Simpson index for 500+ forest plots.",
            "tags": ["biodiversity", "forest", "ecology", "species-diversity"],
        },
        {
            "name": "endangered-species-tracking",
            "title": "Endangered Species Monitoring",
            "notes": "Population tracking and habitat monitoring for endangered species across protected areas in Europe. GPS tracking data, population counts, and habitat assessments.",
            "tags": ["conservation", "endangered-species", "monitoring", "wildlife"],
        },
    ],
}

URL_RESOURCES = [
    {
        "org": "marine-research",
        "dataset": "mediterranean-sea-temperature",
        "resource_name": "temperature-data-2023-csv",
        "resource_title": "Temperature Data 2023 (CSV Format)",
        "resource_url": "https://example.com/data/mediterranean/temp_2023.csv",
        "file_type": "CSV",
        "notes": "CSV file containing hourly temperature measurements for 2023",
    },
    {
        "org": "climate-monitoring",
        "dataset": "atmospheric-co2-levels",
        "resource_name": "co2-measurements-api",
        "resource_title": "CO2 Measurements API Endpoint",
        "resource_url": "https://example.com/api/climate/co2/latest",
        "file_type": "JSON",
        "notes": "REST API endpoint providing latest CO2 measurements in JSON format",
    },
]

S3_RESOURCES = [
    {
        "org": "marine-research",
        "dataset": "ocean-salinity-profiles",
        "resource_name": "salinity-profiles-2022",
        "resource_title": "Salinity Profiles 2022 (NetCDF)",
        "resource_s3": "s3://marine-data/salinity/profiles_2022.nc",
        "notes": "NetCDF file with CTD salinity profiles from 2022 research campaign",
    },
    {
        "org": "biodiversity-lab",
        "dataset": "forest-biodiversity-index",
        "resource_name": "biodiversity-calculations",
        "resource_title": "Biodiversity Index Calculations (Parquet)",
        "resource_s3": "s3://biodiversity-data/forest/indices_2020_2023.parquet",
        "notes": "Parquet file containing calculated biodiversity indices for 2020-2023",
    },
]

# REAL PUBLIC APIs
SERVICES = [
    {
        "service_name": "dog-breed-api",
        "service_title": "Dog Breed Information API",
        "service_url": "https://dog.ceo/api/breeds/list/all",
        "service_type": "REST API",
        "notes": "Public API providing information about dog breeds. Returns list of all breeds and sub-breeds.",
        "health_check_url": "https://dog.ceo/api/breeds/list/all",
    },
    {
        "service_name": "cat-facts-api",
        "service_title": "Random Cat Facts API",
        "service_url": "https://catfact.ninja/fact",
        "service_type": "REST API",
        "notes": "Public API that returns random cat facts. Free to use without authentication.",
        "health_check_url": "https://catfact.ninja/fact",
    },
    {
        "service_name": "jsonplaceholder-api",
        "service_title": "JSONPlaceholder Testing API",
        "service_url": "https://jsonplaceholder.typicode.com",
        "service_type": "REST API",
        "notes": "Free fake API for testing and prototyping. Provides posts, comments, users, and more.",
        "health_check_url": "https://jsonplaceholder.typicode.com/posts/1",
    },
    {
        "service_name": "public-holiday-api",
        "service_title": "Public Holidays API",
        "service_url": "https://date.nager.at/api/v3/publicholidays/2024/ES",
        "service_type": "REST API",
        "notes": "Public API for querying public holidays worldwide. No authentication required.",
        "health_check_url": "https://date.nager.at/api/v3/publicholidays/2024/ES",
    },
    {
        "service_name": "open-meteo-weather",
        "service_title": "Open-Meteo Weather Forecast API",
        "service_url": "https://api.open-meteo.com/v1/forecast",
        "service_type": "REST API",
        "notes": "Free weather forecast API. No API key required. Provides temperature, precipitation, wind, and more.",
        "health_check_url": "https://api.open-meteo.com/v1/forecast?latitude=40.4&longitude=-3.7&current=temperature_2m",
    },
]

S3_BUCKETS = [
    {"name": "marine-data", "region": "us-east-1"},
    {"name": "climate-datasets", "region": "us-east-1"},
    {"name": "biodiversity-data", "region": "us-east-1"},
]

# Real data content for S3 objects
S3_OBJECTS = [
    {
        "bucket": "marine-data",
        "filename": "temperature-measurements-sample.csv",
        "content": """timestamp,station_id,latitude,longitude,temperature_c,depth_m,quality_flag
2023-01-15T00:00:00Z,MED-001,40.4168,-3.7038,15.2,5,GOOD
2023-01-15T01:00:00Z,MED-001,40.4168,-3.7038,15.1,5,GOOD
2023-01-15T02:00:00Z,MED-001,40.4168,-3.7038,15.0,5,GOOD
2023-01-15T03:00:00Z,MED-001,40.4168,-3.7038,14.9,5,GOOD
2023-01-15T04:00:00Z,MED-001,40.4168,-3.7038,14.8,5,GOOD
2023-01-15T05:00:00Z,MED-001,40.4168,-3.7038,14.9,5,GOOD
2023-01-15T06:00:00Z,MED-001,40.4168,-3.7038,15.1,5,GOOD
2023-01-15T07:00:00Z,MED-001,40.4168,-3.7038,15.4,5,GOOD
2023-01-15T08:00:00Z,MED-001,40.4168,-3.7038,15.8,5,GOOD
2023-01-15T09:00:00Z,MED-001,40.4168,-3.7038,16.2,5,GOOD
2023-01-15T10:00:00Z,MED-001,40.4168,-3.7038,16.6,5,GOOD
2023-01-15T11:00:00Z,MED-001,40.4168,-3.7038,17.0,5,GOOD
2023-01-15T12:00:00Z,MED-001,40.4168,-3.7038,17.3,5,GOOD
2023-01-15T13:00:00Z,MED-002,38.7223,-9.1393,16.5,10,GOOD
2023-01-15T14:00:00Z,MED-002,38.7223,-9.1393,16.4,10,GOOD
2023-01-15T15:00:00Z,MED-002,38.7223,-9.1393,16.3,10,GOOD
2023-01-15T16:00:00Z,MED-002,38.7223,-9.1393,16.2,10,GOOD
2023-01-15T17:00:00Z,MED-002,38.7223,-9.1393,16.1,10,GOOD
2023-01-15T18:00:00Z,MED-002,38.7223,-9.1393,16.0,10,GOOD
2023-01-15T19:00:00Z,MED-002,38.7223,-9.1393,15.9,10,GOOD
2023-01-15T20:00:00Z,MED-003,41.9028,12.4964,14.2,15,GOOD
2023-01-15T21:00:00Z,MED-003,41.9028,12.4964,14.1,15,GOOD
2023-01-15T22:00:00Z,MED-003,41.9028,12.4964,14.0,15,GOOD
2023-01-15T23:00:00Z,MED-003,41.9028,12.4964,13.9,15,GOOD
""",
        "content_type": "text/csv",
    },
    {
        "bucket": "climate-datasets",
        "filename": "co2-atmospheric-readings.json",
        "content": json.dumps(
            {
                "metadata": {
                    "station_id": "ES-CLM-001",
                    "station_name": "Madrid Climate Station",
                    "location": {
                        "latitude": 40.4168,
                        "longitude": -3.7038,
                        "elevation_m": 667,
                        "country": "Spain",
                        "region": "Madrid",
                    },
                    "instrument": "NDIR CO2 Analyzer",
                    "calibration_date": "2023-01-01",
                    "data_quality": "Level 2 - Quality Controlled",
                },
                "measurements": [
                    {
                        "timestamp": "2023-12-01T00:00:00Z",
                        "co2_ppm": 415.2,
                        "temperature_c": 12.5,
                        "pressure_hpa": 1013.2,
                        "humidity_percent": 65,
                        "quality_flag": "GOOD",
                    },
                    {
                        "timestamp": "2023-12-01T01:00:00Z",
                        "co2_ppm": 415.5,
                        "temperature_c": 12.3,
                        "pressure_hpa": 1013.1,
                        "humidity_percent": 66,
                        "quality_flag": "GOOD",
                    },
                    {
                        "timestamp": "2023-12-01T02:00:00Z",
                        "co2_ppm": 415.3,
                        "temperature_c": 12.1,
                        "pressure_hpa": 1013.0,
                        "humidity_percent": 67,
                        "quality_flag": "GOOD",
                    },
                    {
                        "timestamp": "2023-12-01T03:00:00Z",
                        "co2_ppm": 415.8,
                        "temperature_c": 11.9,
                        "pressure_hpa": 1012.9,
                        "humidity_percent": 68,
                        "quality_flag": "GOOD",
                    },
                    {
                        "timestamp": "2023-12-01T04:00:00Z",
                        "co2_ppm": 416.1,
                        "temperature_c": 11.7,
                        "pressure_hpa": 1012.8,
                        "humidity_percent": 69,
                        "quality_flag": "GOOD",
                    },
                ],
                "statistics": {
                    "mean_co2_ppm": 415.58,
                    "min_co2_ppm": 415.2,
                    "max_co2_ppm": 416.1,
                    "std_dev_co2_ppm": 0.35,
                    "num_measurements": 5,
                },
            },
            indent=2,
        ),
        "content_type": "application/json",
    },
    {
        "bucket": "biodiversity-data",
        "filename": "species-observations.csv",
        "content": """observation_id,date,species_name,scientific_name,location,latitude,longitude,count,observer,habitat_type
OBS-001,2023-06-15,European Robin,Erithacus rubecula,Madrid Forest,40.4168,-3.7038,3,Maria Garcia,Deciduous Forest
OBS-002,2023-06-15,Red Deer,Cervus elaphus,Pyrenees NP,42.6953,0.8701,8,Juan Martinez,Mountain Forest
OBS-003,2023-06-16,Iberian Lynx,Lynx pardinus,Doñana NP,37.0133,-6.4167,2,Carmen Lopez,Mediterranean Scrubland
OBS-004,2023-06-16,European Badger,Meles meles,Basque Forest,43.2627,-2.9253,1,Luis Fernandez,Mixed Forest
OBS-005,2023-06-17,Red Fox,Vulpes vulpes,Sierra Nevada,37.0956,-3.3994,4,Ana Rodriguez,Mountain
OBS-006,2023-06-17,Wild Boar,Sus scrofa,Catalonia,41.5888,1.5564,12,Pedro Sanchez,Oak Forest
OBS-007,2023-06-18,European Otter,Lutra lutra,Galicia River,42.8782,-8.5448,2,Sofia Torres,Riparian
OBS-008,2023-06-18,Spanish Imperial Eagle,Aquila adalberti,Extremadura,39.4691,-6.3724,1,Miguel Alvarez,Open Woodland
OBS-009,2023-06-19,Beech Marten,Martes foina,Cantabrian Mountains,43.0842,-4.7814,3,Laura Gomez,Rocky Forest
OBS-010,2023-06-19,European Hare,Lepus europaeus,Castilla Plain,41.6488,-4.7236,7,Carlos Ruiz,Agricultural
""",
        "content_type": "text/csv",
    },
    {
        "bucket": "biodiversity-data",
        "filename": "README.md",
        "content": """# Biodiversity Data Repository

## Overview
This repository contains biodiversity monitoring data from various ecosystems across Europe.

## Data Contents
- **Species Observations**: CSV files with wildlife sightings and counts
- **Biodiversity Indices**: Calculated metrics (Shannon, Simpson, Species Richness)
- **Habitat Assessments**: Environmental condition reports
- **Population Trends**: Time-series analysis of species populations

## Data Formats
- CSV: Tabular observation data
- JSON: Metadata and structured assessments
- Parquet: Large-scale analysis results

## Update Frequency
- Observations: Daily (during field season)
- Indices: Monthly calculations
- Reports: Quarterly summaries

## Contact Information
- Organization: Biodiversity Laboratory
- Email: data@biodiversity-lab.example.com
- Website: https://biodiversity-lab.example.com

## License
This data is provided under Creative Commons Attribution 4.0 International (CC BY 4.0)

## Citation
Please cite as: Biodiversity Laboratory (2024). European Biodiversity Monitoring Dataset. Version 1.0.
""",
        "content_type": "text/markdown",
    },
]


# ============================================================================
# SEEDING FUNCTIONS
# ============================================================================


def seed_organizations():
    """Create sample organizations."""
    log_section("Creating Organizations")

    created_orgs = {}
    for org in ORGANIZATIONS:
        result = make_request(
            "POST",
            "/organization",
            f"Creating organization '{org['title']}'",
            headers=HEADERS,
            json=org,
            params={"server": "local"},
        )
        if result:
            created_orgs[org["name"]] = result

    return created_orgs


def seed_datasets(organizations):
    """Create sample datasets."""
    log_section("Creating Datasets")

    created_datasets = {}

    for org_name, datasets in DATASETS.items():
        if org_name not in organizations:
            log_error(f"Organization '{org_name}' not created, skipping its datasets")
            continue

        for dataset in datasets:
            dataset_data = {
                **dataset,
                "owner_org": org_name,
                "extras": {"category": "research", "public": True},
            }

            result = make_request(
                "POST",
                "/dataset",
                f"Creating dataset '{dataset['title']}'",
                headers=HEADERS,
                json=dataset_data,
                params={"server": "local"},
            )

            if result:
                created_datasets[dataset["name"]] = result

    return created_datasets


def seed_url_resources(datasets):
    """Create URL-based resources."""
    log_section("Creating URL Resources")

    created_resources = []

    for resource in URL_RESOURCES:
        if resource["dataset"] not in datasets:
            log_error(f"Dataset '{resource['dataset']}' not found, skipping resource")
            continue

        resource_data = {
            "resource_name": resource["resource_name"],
            "resource_title": resource["resource_title"],
            "owner_org": resource["org"],
            "resource_url": resource["resource_url"],
            "file_type": resource["file_type"],
            "notes": resource["notes"],
        }

        result = make_request(
            "POST",
            "/url",
            f"Creating URL resource '{resource['resource_title']}'",
            headers=HEADERS,
            json=resource_data,
            params={"server": "local"},
        )

        if result:
            created_resources.append(result)

    return created_resources


def seed_s3_resources(datasets):
    """Create S3-based resources."""
    log_section("Creating S3 Resources")

    created_resources = []

    for resource in S3_RESOURCES:
        if resource["dataset"] not in datasets:
            log_error(f"Dataset '{resource['dataset']}' not found, skipping resource")
            continue

        resource_data = {
            "resource_name": resource["resource_name"],
            "resource_title": resource["resource_title"],
            "owner_org": resource["org"],
            "resource_s3": resource["resource_s3"],
            "notes": resource["notes"],
        }

        result = make_request(
            "POST",
            "/s3",
            f"Creating S3 resource '{resource['resource_title']}'",
            headers=HEADERS,
            json=resource_data,
            params={"server": "local"},
        )

        if result:
            created_resources.append(result)

    return created_resources


def seed_services():
    """Create sample services with real public APIs."""
    log_section("Creating Services (Real Public APIs)")

    created_services = []

    for service in SERVICES:
        service_data = {
            **service,
            "owner_org": "services",  # Default services organization
        }

        result = make_request(
            "POST",
            "/services",
            f"Creating service '{service['service_title']}'",
            headers=HEADERS,
            json=service_data,
            params={"server": "local"},
        )

        if result:
            created_services.append(result)
            log_info(f"  → API URL: {service['service_url']}")

    return created_services


def seed_s3_buckets():
    """Create S3 buckets."""
    log_section("Creating S3 Buckets")

    created_buckets = []

    for bucket in S3_BUCKETS:
        result = make_request(
            "POST",
            "/s3/buckets/",
            f"Creating S3 bucket '{bucket['name']}'",
            headers=HEADERS,
            json=bucket,
        )

        if result:
            created_buckets.append(bucket["name"])

        # Small delay to ensure bucket is ready
        time.sleep(0.5)

    return created_buckets


def seed_s3_objects(buckets):
    """Upload sample objects to S3 buckets."""
    log_section("Uploading S3 Objects (With Real Content)")

    uploaded_objects = []

    for obj in S3_OBJECTS:
        bucket_name = obj["bucket"]

        if bucket_name not in buckets:
            log_error(f"Bucket '{bucket_name}' not created, skipping object upload")
            continue

        # Prepare file for upload
        files = {
            "file": (
                obj["filename"],
                io.BytesIO(obj["content"].encode("utf-8")),
                obj["content_type"],
            ),
        }

        # Show file size
        file_size_kb = len(obj["content"]) / 1024
        log_info(f"  → File size: {file_size_kb:.2f} KB")

        result = make_request(
            "POST",
            f"/s3/objects/{bucket_name}",
            f"Uploading '{obj['filename']}' to bucket '{bucket_name}'",
            headers=HEADERS,
            files=files,
        )

        if result:
            uploaded_objects.append(
                {
                    "bucket": bucket_name,
                    "key": obj["filename"],
                }
            )

    return uploaded_objects


# ============================================================================
# MAIN
# ============================================================================


def main():
    """Run the seeding process."""
    print(f"\n{Colors.BOLD}{Colors.BLUE}{'='*70}{Colors.RESET}")
    print(
        f"{Colors.BOLD}{Colors.BLUE}NDP-EP API - Sample Data Seeding Script{Colors.RESET}"
    )
    print(f"{Colors.BOLD}{Colors.BLUE}{'='*70}{Colors.RESET}\n")
    print(f"Base URL: {BASE_URL}")
    print(f"This will populate the database with sample data for demo purposes.\n")

    # Clean up any previous data first
    cleanup_previous_data()

    # Seed all data
    try:
        organizations = seed_organizations()
        datasets = seed_datasets(organizations)
        url_resources = seed_url_resources(datasets)
        s3_resources = seed_s3_resources(datasets)
        services = seed_services()
        buckets = seed_s3_buckets()
        objects = seed_s3_objects(buckets)

        # Print summary
        log_section("Summary")
        log_success(f"Organizations created: {len(organizations)}")
        log_success(f"Datasets created: {len(datasets)}")
        log_success(f"URL resources created: {len(url_resources)}")
        log_success(f"S3 resources created: {len(s3_resources)}")
        log_success(f"Services created: {len(services)}")
        log_success(f"S3 buckets created: {len(buckets)}")
        log_success(f"S3 objects uploaded: {len(objects)}")

        print(
            f"\n{Colors.GREEN}{Colors.BOLD}✓ Sample data seeding completed successfully!{Colors.RESET}\n"
        )
        print(f"You can now explore the data through:")
        print(f"  • API: {BASE_URL}")
        print(f"  • Frontend: http://localhost:3000")
        print(f"  • API Docs: {BASE_URL}/docs\n")

        print(f"{Colors.CYAN}Example services to test:{Colors.RESET}")
        for service in SERVICES[:3]:
            print(f"  • {service['service_title']}: {service['service_url']}")

    except Exception as e:
        log_error(f"Error during seeding: {str(e)}")
        log_warning("Attempting to clean up...")
        cleanup_previous_data()
        raise


if __name__ == "__main__":
    main()
