#!/usr/bin/env python3
"""
Comprehensive test script for all NDP-EP API endpoints.
Tests all endpoints with proper authentication and parameters.

Usage:
    python test_all_endpoints.py
"""

import io
import json
import sys
import time
from typing import Any, Dict, List, Optional

import requests

# Configuration
BASE_URL = "http://localhost:8000"
TEST_TOKEN = "testing_token"  # From .env
HEADERS = {"Authorization": f"Bearer {TEST_TOKEN}"}

# Generate unique suffix for resource names using timestamp
UNIQUE_SUFFIX = str(int(time.time()))

# Color output for terminal
class Colors:
    GREEN = "\033[92m"
    RED = "\033[91m"
    YELLOW = "\033[93m"
    BLUE = "\033[94m"
    RESET = "\033[0m"
    BOLD = "\033[1m"


class TestResult:
    """Track test results."""

    def __init__(self):
        self.passed = 0
        self.failed = 0
        self.skipped = 0
        self.results: List[Dict[str, Any]] = []

    def add_pass(self, test_name: str, details: str = ""):
        self.passed += 1
        self.results.append({"status": "PASS", "test": test_name, "details": details})
        print(f"{Colors.GREEN}✓ PASS{Colors.RESET} {test_name} {details}")

    def add_fail(self, test_name: str, details: str = ""):
        self.failed += 1
        self.results.append({"status": "FAIL", "test": test_name, "details": details})
        print(f"{Colors.RED}✗ FAIL{Colors.RESET} {test_name} {details}")

    def add_skip(self, test_name: str, reason: str = ""):
        self.skipped += 1
        self.results.append({"status": "SKIP", "test": test_name, "details": reason})
        print(f"{Colors.YELLOW}⊘ SKIP{Colors.RESET} {test_name} {reason}")

    def print_summary(self):
        print(f"\n{Colors.BOLD}{'='*70}{Colors.RESET}")
        print(f"{Colors.BOLD}TEST SUMMARY{Colors.RESET}")
        print(f"{Colors.BOLD}{'='*70}{Colors.RESET}")
        print(f"{Colors.GREEN}Passed: {self.passed}{Colors.RESET}")
        print(f"{Colors.RED}Failed: {self.failed}{Colors.RESET}")
        print(f"{Colors.YELLOW}Skipped: {self.skipped}{Colors.RESET}")
        print(f"Total: {self.passed + self.failed + self.skipped}")
        print(f"{Colors.BOLD}{'='*70}{Colors.RESET}\n")


# Global test result tracker
results = TestResult()

# Store created resources for cleanup and subsequent tests
created_resources: Dict[str, Any] = {}


def test_request(
    method: str,
    endpoint: str,
    test_name: str,
    expected_status: int = 200,
    headers: Optional[Dict] = None,
    json_data: Optional[Dict] = None,
    params: Optional[Dict] = None,
    files: Optional[Dict] = None,
    skip_if_unavailable: bool = False,
) -> Optional[requests.Response]:
    """
    Make a test request and validate response.

    Args:
        method: HTTP method
        endpoint: API endpoint path
        test_name: Name of the test
        expected_status: Expected HTTP status code
        headers: Request headers
        json_data: JSON request body
        params: Query parameters
        files: Files to upload
        skip_if_unavailable: Skip test if service unavailable

    Returns:
        Response object if successful, None if failed
    """
    url = f"{BASE_URL}{endpoint}"
    try:
        response = requests.request(
            method=method,
            url=url,
            headers=headers,
            json=json_data,
            params=params,
            files=files,
            timeout=10,
        )

        if response.status_code == expected_status:
            results.add_pass(test_name, f"({response.status_code})")
            return response
        elif skip_if_unavailable and response.status_code in [503, 500]:
            results.add_skip(test_name, "(Service unavailable)")
            return None
        else:
            details = f"(Expected {expected_status}, got {response.status_code})"
            try:
                error_detail = response.json()
                details += f" - {error_detail}"
            except:
                details += f" - {response.text[:100]}"
            results.add_fail(test_name, details)
            return None

    except requests.exceptions.RequestException as e:
        results.add_fail(test_name, f"(Request failed: {str(e)})")
        return None


def print_section(title: str):
    """Print a section header."""
    print(f"\n{Colors.BOLD}{Colors.BLUE}{'='*70}{Colors.RESET}")
    print(f"{Colors.BOLD}{Colors.BLUE}{title}{Colors.RESET}")
    print(f"{Colors.BOLD}{Colors.BLUE}{'='*70}{Colors.RESET}\n")


# ============================================================================
# TEST FUNCTIONS
# ============================================================================


def test_default_routes():
    """Test default/root endpoints."""
    print_section("DEFAULT ROUTES")

    # Test 1: Root endpoint
    test_request("GET", "/", "GET / - Root endpoint")


def test_status_routes():
    """Test status and health check endpoints."""
    print_section("STATUS ROUTES")

    # Test 2: Status endpoint
    test_request("GET", "/status/", "GET /status/ - System status", skip_if_unavailable=True)

    # Test 3: Metrics endpoint
    test_request("GET", "/status/metrics", "GET /status/metrics - System metrics")

    # Test 4: Kafka details
    test_request(
        "GET",
        "/status/kafka-details",
        "GET /status/kafka-details - Kafka details",
        skip_if_unavailable=True,
    )

    # Test 5: Jupyter details
    test_request(
        "GET",
        "/status/jupyter",
        "GET /status/jupyter - Jupyter details",
        skip_if_unavailable=True,
    )


def test_user_routes():
    """Test user information endpoints."""
    print_section("USER ROUTES")

    # Test 6: Get user info (requires auth)
    response = test_request(
        "GET", "/user/info", "GET /user/info - User information", headers=HEADERS
    )


def test_organization_routes():
    """Test organization CRUD operations."""
    print_section("ORGANIZATION ROUTES")

    # Test 7: List organizations (global)
    test_request(
        "GET",
        "/organization",
        "GET /organization?server=global - List global organizations",
        params={"server": "global"},
        skip_if_unavailable=True,
    )

    # Test 8: List organizations (local)
    response = test_request(
        "GET",
        "/organization",
        "GET /organization?server=local - List local organizations",
        params={"server": "local"},
    )

    # Test 9: Create organization (local) with unique name
    org_data = {
        "name": f"test_org_{UNIQUE_SUFFIX}",
        "title": f"Test Organization {UNIQUE_SUFFIX}",
        "description": "Created by automated test script",
    }
    response = test_request(
        "POST",
        "/organization",
        "POST /organization - Create organization",
        headers=HEADERS,
        json_data=org_data,
        params={"server": "local"},
        expected_status=201,
    )

    if response:
        try:
            created_resources["organization_id"] = response.json()["id"]
            created_resources["organization_name"] = org_data["name"]
        except:
            pass


def test_dataset_routes():
    """Test dataset CRUD operations."""
    print_section("DATASET ROUTES")

    # Ensure we have an organization
    if "organization_name" not in created_resources:
        results.add_skip("Dataset tests", "(No organization created)")
        return

    # Test 10: Create general dataset
    dataset_data = {
        "name": f"test_dataset_{UNIQUE_SUFFIX}",
        "title": f"Test Dataset {UNIQUE_SUFFIX}",
        "owner_org": created_resources["organization_name"],
        "notes": "Test dataset created by automated script",
        "extras": {"test_key": "test_value"},  # Fixed: extras should be dict, not list
    }
    response = test_request(
        "POST",
        "/dataset",
        "POST /dataset - Create general dataset",
        headers=HEADERS,
        json_data=dataset_data,
        params={"server": "local"},
        expected_status=201,
    )

    if response:
        try:
            created_resources["dataset_id"] = response.json()["id"]
            created_resources["dataset_name"] = dataset_data["name"]
        except:
            pass

    # Test 11: Search datasets
    test_request(
        "GET",
        "/search",
        "GET /search?terms=test - Search datasets by terms",
        params={"terms": ["test"], "server": "local"},
    )

    # Test 12: POST search
    search_data = {
        "search_term": "test",
        "server": "local",
    }
    test_request(
        "POST",
        "/search",
        "POST /search - Search datasets (POST)",
        json_data=search_data,
    )

    # Test 13: Update dataset (PATCH)
    if "dataset_id" in created_resources:
        update_data = {
            "notes": "Updated by automated test script",
        }
        test_request(
            "PATCH",
            f"/dataset/{created_resources['dataset_id']}",
            "PATCH /dataset/{id} - Partial update dataset",
            headers=HEADERS,
            json_data=update_data,
            params={"server": "local"},
        )

    # Test 14: Update dataset (PUT)
    if "dataset_id" in created_resources:
        update_data = {
            "name": created_resources["dataset_name"],
            "title": "Updated Test Dataset",
            "owner_org": created_resources["organization_name"],
            "notes": "Fully updated by automated test script",
        }
        test_request(
            "PUT",
            f"/dataset/{created_resources['dataset_id']}",
            "PUT /dataset/{id} - Full update dataset",
            headers=HEADERS,
            json_data=update_data,
            params={"server": "local"},
        )


def test_url_resource_routes():
    """Test URL resource CRUD operations."""
    print_section("URL RESOURCE ROUTES")

    if "organization_name" not in created_resources:
        results.add_skip("URL resource tests", "(No organization created)")
        return

    # Test 15: Create URL resource
    url_data = {
        "resource_name": f"test_url_resource_{UNIQUE_SUFFIX}",
        "resource_title": f"Test URL Resource {UNIQUE_SUFFIX}",
        "owner_org": created_resources["organization_name"],
        "resource_url": "https://example.com/data.csv",
        "file_type": "CSV",
        "notes": "Test URL resource",
    }
    response = test_request(
        "POST",
        "/url",
        "POST /url - Create URL resource",
        headers=HEADERS,
        json_data=url_data,
        params={"server": "local"},
        expected_status=201,
    )

    if response:
        try:
            created_resources["url_resource_id"] = response.json()["resource_id"]
        except:
            pass

    # Test 16: Update URL resource (PATCH)
    if "url_resource_id" in created_resources:
        update_data = {
            "resource_title": "Updated URL Resource",
        }
        test_request(
            "PATCH",
            f"/url/{created_resources['url_resource_id']}",
            "PATCH /url/{id} - Partial update URL resource",
            headers=HEADERS,
            json_data=update_data,
            params={"server": "local"},
        )


def test_s3_resource_routes():
    """Test S3 resource CRUD operations."""
    print_section("S3 RESOURCE ROUTES")

    if "organization_name" not in created_resources:
        results.add_skip("S3 resource tests", "(No organization created)")
        return

    # Test 17: Create S3 resource
    s3_data = {
        "resource_name": f"test_s3_resource_{UNIQUE_SUFFIX}",
        "resource_title": f"Test S3 Resource {UNIQUE_SUFFIX}",
        "owner_org": created_resources["organization_name"],
        "resource_s3": "s3://test-bucket/test-object.csv",
        "notes": "Test S3 resource",
    }
    response = test_request(
        "POST",
        "/s3",
        "POST /s3 - Create S3 resource",
        headers=HEADERS,
        json_data=s3_data,
        params={"server": "local"},
        expected_status=201,
    )

    if response:
        try:
            created_resources["s3_resource_id"] = response.json()["resource_id"]
        except:
            pass

    # Test 18: Update S3 resource (PATCH)
    if "s3_resource_id" in created_resources:
        update_data = {
            "resource_title": "Updated S3 Resource",
        }
        test_request(
            "PATCH",
            f"/s3/{created_resources['s3_resource_id']}",
            "PATCH /s3/{id} - Partial update S3 resource",
            headers=HEADERS,
            json_data=update_data,
            params={"server": "local"},
        )


def test_service_routes():
    """Test service CRUD operations."""
    print_section("SERVICE ROUTES")

    # Test 19: Create service
    service_data = {
        "service_name": f"test_service_{UNIQUE_SUFFIX}",
        "service_title": f"Test Service {UNIQUE_SUFFIX}",
        "owner_org": "services",  # Default services organization
        "service_url": f"https://example.com/api/{UNIQUE_SUFFIX}",
        "service_type": "REST API",
        "notes": "Test service",
        "health_check_url": f"https://example.com/health/{UNIQUE_SUFFIX}",
    }
    response = test_request(
        "POST",
        "/services",
        "POST /services - Create service",
        headers=HEADERS,
        json_data=service_data,
        params={"server": "local"},
        expected_status=201,
    )

    if response:
        try:
            created_resources["service_id"] = response.json()["resource_id"]
        except:
            pass

    # Test 20: Update service (PATCH)
    if "service_id" in created_resources:
        update_data = {
            "service_title": "Updated Test Service",
        }
        test_request(
            "PATCH",
            f"/services/{created_resources['service_id']}",
            "PATCH /services/{id} - Partial update service",
            headers=HEADERS,
            json_data=update_data,
            params={"server": "local"},
        )


def test_kafka_routes():
    """Test Kafka resource CRUD operations."""
    print_section("KAFKA RESOURCE ROUTES")

    if "organization_name" not in created_resources:
        results.add_skip("Kafka resource tests", "(No organization created)")
        return

    # Test 21: Create Kafka resource (may fail if Kafka not configured)
    kafka_data = {
        "dataset_name": f"test_kafka_dataset_{UNIQUE_SUFFIX}",
        "dataset_title": f"Test Kafka Dataset {UNIQUE_SUFFIX}",
        "owner_org": created_resources["organization_name"],
        "kafka_topic": f"test-topic-{UNIQUE_SUFFIX}",
        "kafka_host": "localhost",
        "kafka_port": "9092",
        "dataset_description": "Test Kafka dataset",
    }
    response = test_request(
        "POST",
        "/kafka",
        "POST /kafka - Create Kafka resource",
        headers=HEADERS,
        json_data=kafka_data,
        params={"server": "local"},
        expected_status=201,
        skip_if_unavailable=True,
    )

    if response:
        try:
            created_resources["kafka_dataset_id"] = response.json()["id"]
        except:
            pass


def test_minio_bucket_routes():
    """Test MinIO bucket operations."""
    print_section("MINIO BUCKET ROUTES")

    # Test 22: List buckets
    test_request(
        "GET",
        "/s3/buckets/",
        "GET /s3/buckets/ - List S3 buckets",
        headers=HEADERS,
        skip_if_unavailable=True,
    )

    # Test 23: Create bucket
    bucket_data = {
        "name": f"test-bucket-{UNIQUE_SUFFIX}",
        "region": "us-east-1",
    }
    response = test_request(
        "POST",
        "/s3/buckets/",
        "POST /s3/buckets/ - Create S3 bucket",
        headers=HEADERS,
        json_data=bucket_data,
        expected_status=201,
        skip_if_unavailable=True,
    )

    if response:
        created_resources["bucket_name"] = bucket_data["name"]

    # Test 24: Get bucket info
    if "bucket_name" in created_resources:
        test_request(
            "GET",
            f"/s3/buckets/{created_resources['bucket_name']}",
            "GET /s3/buckets/{name} - Get bucket info",
            headers=HEADERS,
            skip_if_unavailable=True,
        )


def test_minio_object_routes():
    """Test MinIO object operations."""
    print_section("MINIO OBJECT ROUTES")

    if "bucket_name" not in created_resources:
        results.add_skip("MinIO object tests", "(No bucket created)")
        return

    bucket_name = created_resources["bucket_name"]

    # Test 25: Upload object
    test_file_content = b"This is test file content for API testing."
    files = {
        "file": ("test-file.txt", io.BytesIO(test_file_content), "text/plain"),
    }
    response = test_request(
        "POST",
        f"/s3/objects/{bucket_name}",
        "POST /s3/objects/{bucket} - Upload object",
        headers=HEADERS,
        files=files,
        skip_if_unavailable=True,
    )

    if response:
        try:
            created_resources["object_key"] = response.json()["object_key"]
        except:
            created_resources["object_key"] = "test-file.txt"

    # Test 26: List objects
    test_request(
        "GET",
        f"/s3/objects/{bucket_name}",
        "GET /s3/objects/{bucket} - List objects",
        headers=HEADERS,
        skip_if_unavailable=True,
    )

    # Test 27: Get object metadata
    if "object_key" in created_resources:
        test_request(
            "GET",
            f"/s3/objects/{bucket_name}/{created_resources['object_key']}/metadata",
            "GET /s3/objects/{bucket}/{key}/metadata - Get object metadata",
            headers=HEADERS,
            skip_if_unavailable=True,
        )

    # Test 28: Generate presigned upload URL
    if "object_key" in created_resources:
        presigned_data = {"expires_in": 3600}
        test_request(
            "POST",
            f"/s3/objects/{bucket_name}/presigned-upload-test.txt/presigned-upload",
            "POST /s3/objects/{bucket}/{key}/presigned-upload - Generate presigned upload URL",
            headers=HEADERS,
            json_data=presigned_data,
            skip_if_unavailable=True,
        )

    # Test 29: Generate presigned download URL
    if "object_key" in created_resources:
        presigned_data = {"expires_in": 3600}
        test_request(
            "POST",
            f"/s3/objects/{bucket_name}/{created_resources['object_key']}/presigned-download",
            "POST /s3/objects/{bucket}/{key}/presigned-download - Generate presigned download URL",
            headers=HEADERS,
            json_data=presigned_data,
            skip_if_unavailable=True,
        )

    # Test 30: Download object
    if "object_key" in created_resources:
        test_request(
            "GET",
            f"/s3/objects/{bucket_name}/{created_resources['object_key']}",
            "GET /s3/objects/{bucket}/{key} - Download object",
            headers=HEADERS,
            skip_if_unavailable=True,
        )


def test_cleanup():
    """Clean up created resources."""
    print_section("CLEANUP - Delete Created Resources")

    # Delete MinIO object
    if "bucket_name" in created_resources and "object_key" in created_resources:
        test_request(
            "DELETE",
            f"/s3/objects/{created_resources['bucket_name']}/{created_resources['object_key']}",
            "DELETE /s3/objects/{bucket}/{key} - Delete object",
            headers=HEADERS,
            expected_status=200,
            skip_if_unavailable=True,
        )

    # Delete MinIO bucket
    if "bucket_name" in created_resources:
        test_request(
            "DELETE",
            f"/s3/buckets/{created_resources['bucket_name']}",
            "DELETE /s3/buckets/{name} - Delete bucket",
            headers=HEADERS,
            expected_status=200,
            skip_if_unavailable=True,
        )

    # Delete URL resource
    if "url_resource_id" in created_resources:
        test_request(
            "DELETE",
            "/resource",
            "DELETE /resource?resource_id={id} - Delete URL resource",
            headers=HEADERS,
            params={
                "resource_id": created_resources["url_resource_id"],
                "server": "local",
            },
            expected_status=200,
        )

    # Delete S3 resource
    if "s3_resource_id" in created_resources:
        test_request(
            "DELETE",
            "/resource",
            "DELETE /resource?resource_id={id} - Delete S3 resource",
            headers=HEADERS,
            params={"resource_id": created_resources["s3_resource_id"], "server": "local"},
            expected_status=200,
        )

    # Delete service
    if "service_id" in created_resources:
        test_request(
            "DELETE",
            "/resource",
            "DELETE /resource?resource_id={id} - Delete service",
            headers=HEADERS,
            params={"resource_id": created_resources["service_id"], "server": "local"},
            expected_status=200,
        )

    # Delete dataset
    if "dataset_id" in created_resources:
        test_request(
            "DELETE",
            f"/resource/{created_resources['dataset_name']}",
            "DELETE /resource/{name} - Delete dataset",
            headers=HEADERS,
            params={"server": "local"},
            expected_status=200,
        )

    # Delete organization
    if "organization_name" in created_resources:
        test_request(
            "DELETE",
            f"/organization/{created_resources['organization_name']}",
            "DELETE /organization/{name} - Delete organization",
            headers=HEADERS,
            params={"server": "local"},
            expected_status=200,
        )


def main():
    """Run all tests."""
    print(f"\n{Colors.BOLD}{Colors.BLUE}{'='*70}{Colors.RESET}")
    print(
        f"{Colors.BOLD}{Colors.BLUE}NDP-EP API - Comprehensive Endpoint Test Suite{Colors.RESET}"
    )
    print(f"{Colors.BOLD}{Colors.BLUE}{'='*70}{Colors.RESET}\n")
    print(f"Base URL: {BASE_URL}")
    print(f"Auth Token: {TEST_TOKEN[:20]}..." if len(TEST_TOKEN) > 20 else f"Auth Token: {TEST_TOKEN}")
    print(f"\nStarting tests...\n")

    # Run all test suites
    test_default_routes()
    test_status_routes()
    test_user_routes()
    test_organization_routes()
    test_dataset_routes()
    test_url_resource_routes()
    test_s3_resource_routes()
    test_service_routes()
    test_kafka_routes()
    test_minio_bucket_routes()
    test_minio_object_routes()
    test_cleanup()

    # Print summary
    results.print_summary()

    # Exit with appropriate code
    sys.exit(0 if results.failed == 0 else 1)


if __name__ == "__main__":
    main()
