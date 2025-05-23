import pytest
import subprocess
import time
import requests
from playwright.sync_api import sync_playwright, expect
import os
import re
import pandas as pd  # for reading the CSV

# Path to the test CSV
test_dir = os.path.dirname(__file__)
TEST_CSV_PATH = os.path.join(test_dir, "data", "test_postcodes.csv")

@pytest.fixture(scope="session", autouse=True)
def manage_containers():
    # 1) Tear down any existing containers/volumes
    subprocess.run(["docker-compose", "down", "-v"], check=True)
    # 2) Bring up all services in detached mode
    subprocess.run(["docker-compose", "up", "-d"], check=True)

    # Wait (up to 5 minutes) for Postcodes.io and Streamlit to become healthy
    start_time = time.time()
    timeout = 300  # 5 minutes

    # 3) Health-check Postcodes.io on port 8000
    while time.time() - start_time < timeout:
        try:
            r = requests.get("http://localhost:8000/postcodes/EC1A1BB", timeout=10)
            if r.status_code == 200 and "result" in r.json():
                break
        except:
            time.sleep(5)
    else:
        subprocess.run(["docker-compose", "logs"])
        subprocess.run(["docker-compose", "down", "-v"])
        pytest.fail("Postcodes.io service did not become healthy within 5 minutes")

    # 4) Health-check Streamlit on port 8501
    while time.time() - start_time < timeout:
        try:
            r = requests.get("http://localhost:8501", timeout=10)
            if r.status_code == 200:
                break
        except:
            time.sleep(5)
    else:
        subprocess.run(["docker-compose", "logs"])
        subprocess.run(["docker-compose", "down", "-v"])
        pytest.fail("Streamlit app did not become healthy within 5 minutes")

    yield  # run tests here

    # Teardown: shut down containers/volumes
    subprocess.run(["docker-compose", "down", "-v"], check=True)


def extract_miles(metric_text):
    """
    Given a metric label text like:
      "Total Loaded\n48.3 mi"
    extract the numeric value (48.3) as float.
    """
    m = re.search(r"([0-9]+(?:\.[0-9]+)?)\s*mi", metric_text)
    if not m:
        pytest.fail(f"Could not parse miles from metric text: {metric_text}")
    return float(m.group(1))


def test_full_vrp_setup():
    # Read driver names from the CSV
    df_test = pd.read_csv(TEST_CSV_PATH)
    drivers_in_csv = df_test["DRIVER NAME"].unique().tolist()
    first_driver = drivers_in_csv[0]

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()

        # Navigate to the Streamlit app
        page.goto("http://localhost:8501")
        expect(page).to_have_title("🚚 Smart Vehicle Routing Optimizer")

        # Upload CSV
        page.wait_for_selector("input[type='file']", timeout=30000)
        page.set_input_files("input[type='file']", TEST_CSV_PATH)

        # Wait for summary metrics
        page.wait_for_selector(".stMetric", timeout=300000)  # 5 minutes
        metrics = page.query_selector_all(".stMetric")
        assert len(metrics) >= 3, "Expected at least 3 metrics (Total Loaded, Total Empty, Grand Total)"

        total_loaded_text = metrics[0].inner_text()
        total_empty_text = metrics[1].inner_text()
        assert "mi" in total_loaded_text and "mi" in total_empty_text, "Metrics should contain 'mi' unit"

        total_loaded_value = extract_miles(total_loaded_text)
        total_empty_value = extract_miles(total_empty_text)
        assert total_loaded_value > 0, "Total loaded miles should be positive"
        assert total_empty_value >= 0, "Total empty miles should be non-negative"

        # Show empty miles table by driver
        page.check("text=Show empty miles by driver")
        page.wait_for_selector(".stDataFrame", timeout=60000)

        # Wait for at least one row to appear in the grid
        page.wait_for_function(
            "document.querySelector('.stDataFrame table tbody tr')", timeout=60000
        )

        # Scroll through the table to verify all drivers
        scroller = page.query_selector(".stDataFrameGlideDataEditor .dvn-scroller")
        assert scroller, "Could not find the data-grid's scrollable container"

        for driver in drivers_in_csv:
            found = False
            scroll_amount = 0
            max_scroll = 10000
            while scroll_amount < max_scroll:
                if page.locator(f"text={driver}").count() > 0:
                    found = True
                    break
                scroller.evaluate("el => el.scrollBy(0, 200)")
                scroll_amount += 200
                time.sleep(0.1)
            assert found, f"Driver {driver} not found after scrolling"

        # Wait for the first dropdown to be present
        page.wait_for_selector(".stSelectbox", timeout=120000)

        # Interact with the first dropdown to select the first driver
        page.click(".stSelectbox")  # Open the dropdown
        dropdown = page.locator('[data-testid="stSelectboxVirtualDropdown"]')
        dropdown.wait_for(state="visible", timeout=120000)
        option_locator = dropdown.locator(f"text={first_driver}")
        option_locator.wait_for(state="visible", timeout=120000)
        option_locator.click()

        # Check the map checkbox and verify the map loads
        page.check("text=Show empty-mile segments on map for selected driver")
        page.wait_for_selector("iframe", timeout=60000)
        assert page.query_selector("iframe"), "Map iframe not found"

        # Wait for the second dropdown to be present
        page.wait_for_selector(".stSelectbox >> nth=1", timeout=60000)

        # Interact with the second dropdown to select the first driver
        page.click(".stSelectbox >> nth=1")  # Open the second dropdown
        dropdown = page.locator('[data-testid="stSelectboxVirtualDropdown"]')
        dropdown.wait_for(state="visible", timeout=60000)
        option_locator = dropdown.locator(f"text={first_driver}")
        option_locator.wait_for(state="visible", timeout=60000)
        option_locator.click()

        # Debug: Save screenshot and HTML after dropdown selection
        page.screenshot(path="debug_route_summary.png")
        with open("debug_route_summary.html", "w", encoding="utf-8") as f:
            f.write(page.content())

        # Debug: Log the number of iframes
        iframes = page.query_selector_all("iframe")
        print(f"Number of iframes found: {len(iframes)}")
        for i, iframe in enumerate(iframes):
            print(f"iframe {i}: {iframe.get_attribute('src')}")

        # Verify route summary and map
        page.wait_for_selector(".stMarkdown >> text=→", timeout=60000)
        route_summary = page.locator(".stMarkdown >> text=→").inner_text()
        assert "→" in route_summary, "Route summary should contain '→' arrows"

        # Check for route map (assuming single iframe is reused)
        page.wait_for_selector("iframe", timeout=60000)
        assert page.query_selector("iframe"), "Route map iframe not found"
        browser.close()