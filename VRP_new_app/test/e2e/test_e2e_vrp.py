import pytest
import subprocess
import time
import requests
from playwright.sync_api import sync_playwright, expect
import os
import re
import pandas as pd
import logging
import json

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler("e2e_test.log")
    ]
)
logger = logging.getLogger(__name__)

# Define the path to the test CSV file
test_dir = os.path.dirname(__file__)
TEST_CSV_PATH = os.path.join(test_dir, "data", "test_postcodes.csv")

# Fixture to manage Docker containers for the test environment
@pytest.fixture(scope="session", autouse=True)
def manage_containers():
    # Use docker compose (v2) command
    compose_cmd = ["docker", "compose"]
    
    # Tear down any existing containers/volumes
    logger.info("Tearing down existing containers...")
    subprocess.run(compose_cmd + ["down", "-v", "--remove-orphans"], 
                  check=False, 
                  stdout=subprocess.DEVNULL,
                  stderr=subprocess.DEVNULL)
    
    # Build images
    logger.info("Building Docker images...")
    subprocess.run(compose_cmd + ["build"], check=True)
    
    # Bring up all services in detached mode
    logger.info("Starting services...")
    subprocess.run(compose_cmd + ["up", "-d"], check=True)
    
    # Health-check with exponential backoff
    services = {
        "postcodes-db": {
            "type": "postgres",
            "cmd": ["pg_isready", "-U", "postcodesio", "-d", "postcodesio"],
            "timeout": 600  # 10 minutes
        },
        "postcodes-app": {
            "url": "http://localhost:8000/postcodes/EC1A1BB",
            "timeout": 600  # 10 minutes
        },
        "osrm": {
            "url": "http://localhost:5000/route/v1/driving/-0.141,51.523;-0.142,51.524",
            "timeout": 600  # 10 minutes
        },
        "app": {
            "url": "http://localhost:8501",
            "timeout": 300  # 5 minutes
        }
    }
    
    # Check database initialization first
    logger.info("Checking postcodes-db health...")
    start_time = time.time()
    attempt = 1
    while time.time() - start_time < services["postcodes-db"]["timeout"]:
        try:
            result = subprocess.run(
                ["docker", "exec", "vrp_new_app-postcodes-db-1"] + services["postcodes-db"]["cmd"],
                capture_output=True,
                text=True
            )
            if "accepting connections" in result.stdout:
                logger.info("Postcodes DB is ready!")
                break
        except Exception as e:
            logger.warning(f"DB check attempt {attempt} failed: {str(e)}")
        
        sleep_time = min(2 ** attempt, 30)
        logger.info(f"DB not ready, waiting {sleep_time} seconds...")
        time.sleep(sleep_time)
        attempt += 1
    else:
        logger.error("Postcodes DB did not become healthy within timeout")
        logs = subprocess.run(
            compose_cmd + ["logs", "--no-color", "--tail=100", "postcodes-db"],
            capture_output=True, text=True
        )
        logger.error(f"Postcodes DB logs:\n{logs.stdout}")
        pytest.fail("Postcodes DB service did not become healthy")
    
    # Check other services
    for service, config in services.items():
        if service == "postcodes-db":
            continue  # Already checked
            
        logger.info(f"Checking health of {service} service...")
        start_time = time.time()
        attempt = 1
        
        while time.time() - start_time < config["timeout"]:
            try:
                if service == "postcodes-app":
                    # Special check for postcodes-app
                    response = requests.get(config["url"], timeout=10)
                    if response.status_code == 200:
                        data = response.json()
                        if data.get("status") == 200 and "result" in data:
                            logger.info(f"{service} is healthy!")
                            break
                else:
                    # Standard health check
                    response = requests.get(config["url"], timeout=10)
                    if response.status_code == 200:
                        logger.info(f"{service} is healthy!")
                        break
            except (requests.ConnectionError, requests.Timeout) as e:
                logger.warning(f"Attempt {attempt}: {service} not ready - {str(e)}")
            except Exception as e:
                logger.error(f"Unexpected error checking {service}: {str(e)}")
            
            sleep_time = min(2 ** attempt, 30)
            logger.info(f"Waiting {sleep_time} seconds for {service}...")
            time.sleep(sleep_time)
            attempt += 1
        else:
            logger.error(f"{service} service did not become healthy within timeout")
            logs = subprocess.run(
                compose_cmd + ["logs", "--no-color", "--tail=100", service],
                capture_output=True, text=True
            )
            logger.error(f"Container logs for {service}:\n{logs.stdout}")
            pytest.fail(f"{service} service did not become healthy within {config['timeout']} seconds")

    logger.info("All services are healthy. Starting tests...")
    yield  # Run tests here

    # Teardown: shut down containers/volumes
    logger.info("Tearing down containers...")
    subprocess.run(compose_cmd + ["down", "-v", "--remove-orphans"], check=True)
    logger.info("Containers successfully shut down")

# Helper function to extract miles from metric text
def extract_miles(metric_text):
    m = re.search(r"([0-9]+(?:\.[0-9]+)?)\s*mi", metric_text)
    if not m:
        pytest.fail(f"Could not parse miles from metric text: {metric_text}")
    return float(m.group(1))

# Test function for the full VRP setup
def test_full_vrp_setup():
    # Read the test CSV file
    df_test = pd.read_csv(TEST_CSV_PATH)
    drivers_in_csv = df_test["DRIVER NAME"].unique().tolist()
    first_driver = drivers_in_csv[0]

    # Start Playwright
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context()
        page = context.new_page()
        
        logger.info("Navigating to Streamlit app...")
        page.goto("http://localhost:8501", timeout=120000)
        
        # Wait for the page to fully load
        logger.info("Waiting for page to load...")
        page.wait_for_selector("text=Smart Vehicle Routing Optimizer", timeout=60000)

        # Upload the CSV file
        logger.info("Uploading CSV file...")
        with page.expect_file_chooser() as fc_info:
            page.click("text=Upload CSV File")
        file_chooser = fc_info.value
        file_chooser.set_files(TEST_CSV_PATH)

        # Wait for data processing to complete
        logger.info("Waiting for data processing...")
        page.wait_for_selector("text=Data loaded and cached", timeout=300000)  # 5 minutes

        # Verify summary metrics
        metrics = page.query_selector_all(".stMetric")
        assert len(metrics) >= 3, "Expected at least 3 metrics"
        logger.info(f"Found {len(metrics)} metrics")

        # Extract and verify metric values
        total_loaded_text = metrics[0].inner_text()
        total_empty_text = metrics[1].inner_text()
        total_loaded_value = extract_miles(total_loaded_text)
        total_empty_value = extract_miles(total_empty_text)
        logger.info(f"Total loaded miles: {total_loaded_value}")
        logger.info(f"Total empty miles: {total_empty_value}")

        # Show empty miles table by driver
        logger.info("Enabling empty miles table...")
        page.check("text=Show empty miles by driver")
        page.wait_for_selector(".stDataFrame", timeout=120000)

        # Select driver for empty miles map
        logger.info(f"Selecting driver: {first_driver}")
        page.click(".stSelectbox", timeout=60000)
        dropdown = page.locator('[data-testid="stSelectboxVirtualDropdown"]')
        dropdown.wait_for(state="visible", timeout=60000)
        page.locator(f"text={first_driver}").click(timeout=60000)
        
        # Enable map display
        logger.info("Enabling map display...")
        page.check("text=Show empty-mile segments on map for selected driver")
        page.wait_for_selector("iframe", timeout=120000)

        # Select driver for route optimization
        logger.info(f"Selecting driver for optimization: {first_driver}")
        page.click(".stSelectbox >> nth=1", timeout=60000)
        dropdown = page.locator('[data-testid="stSelectboxVirtualDropdown"]')
        dropdown.wait_for(state="visible", timeout=60000)
        page.locator(f"text={first_driver}").click(timeout=60000)

        # Wait for optimization to start
        logger.info("Waiting for optimization to start...")
        page.wait_for_selector("text=Solving VRP for", timeout=120000)
        
        # Wait for optimization to complete
        logger.info("Waiting for optimization to complete...")
        try:
            page.wait_for_selector("text=Solving VRP for", state="hidden", timeout=300000)  # 5 minutes
        except:
            logger.warning("Optimization status didn't disappear, continuing anyway")
        
        # Verify route summary
        logger.info("Verifying route summary...")
        page.wait_for_selector("text=Route:", timeout=120000)
        route_summary = page.locator(".stMarkdown").filter(has_text="Route:").inner_text(timeout=60000)
        assert "→" in route_summary, "Route summary missing arrows"
        logger.info(f"Route summary: {route_summary[:50]}...")

        # Verify route map
        logger.info("Verifying route map...")
        page.wait_for_selector("iframe >> nth=1", timeout=120000)
        
        # Save screenshot for debugging
        logger.info("Saving screenshot...")
        page.screenshot(path="test_completion_screenshot.png")
        
        # Close browser
        logger.info("Closing browser...")
        context.close()
        browser.close()

    logger.info("End-to-end test completed successfully")
