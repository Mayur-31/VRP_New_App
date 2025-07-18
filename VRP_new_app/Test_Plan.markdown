# Comprehensive Test Plan for Smart Vehicle Routing Optimizer

## 1. Test Environment Setup
- **Operating System**: WSL Ubuntu (on Windows 10/11)
- **Browsers**: Chrome (via Playwright, latest version)
- **Network**: Normal (local network) and throttled (3G simulation via Playwright)
- **Test URL**: `http://157.180.87.7:8501/`
- **Tools**: Playwright v1.39.0, Node.js v18.19.1
- **Test Data**:
  - `valid.csv`: Complete dataset with routes (e.g., CF31 3BG → DE74 2TZ, expected ~340.1 mi)
  - `invalid.csv`: Malformed CSV with incorrect headers (`WRONG_COLUMN1,WRONG_COLUMN2`)
  - `single_row.csv`: Single route for minimal data testing
  - `large_file.csv`: 201 rows for performance testing
- **Prerequisites**: Node.js, Playwright, and test data in `tests/test_data/`

## 2. Functional Test Cases
| **Test Case ID** | **Description** | **Steps** | **Expected Result** |
|------------------|-----------------|-----------|---------------------|
| **TC-01** | CSV File Upload (Valid) | 1. Navigate to `http://157.180.87.7:8501/` <br> 2. Click "Upload CSV File" <br> 3. Select `valid.csv` <br> 4. Submit | Success message ("Data loaded and cached") appears, metrics displayed (e.g., Total Loaded with mileage) |
| **TC-02** | Metrics Validation | 1. After uploading `valid.csv` <br> 2. Check "Summary Metrics" section | Total Loaded, Total Empty, and Grand Total metrics display correct values (e.g., ~340.1 mi for Total Loaded) |
| **TC-03** | Processed CSV Download | 1. Upload `valid.csv` <br> 2. Click "Download Processed CSV" | CSV file downloads with correct route data (e.g., optimized routes, distances) |
| **TC-04** | Empty Miles Display | 1. Upload `valid.csv` <br> 2. Toggle "Show empty miles by driver" | Table shows/hides driver-specific empty miles correctly |
| **TC-05** | Driver Selection | 1. Upload `valid.csv` <br> 2. Select a driver from dropdown (e.g., "ZULFIQAR ALI DAD") | Driver details and empty miles map update to reflect selected driver |
| **TC-06** | Map Display | 1. Upload `valid.csv` <br> 2. Toggle "Show empty-mile segments" | Interactive map renders with correct route paths (e.g., CF31 3BG → DE74 2TZ) |
| **TC-07** | Route Details | 1. Upload `valid.csv` <br> 2. Select a driver <br> 3. View route details | Correct route (e.g., CF31 3BG → DE74 2TZ) and distance (e.g., ~326.13 mi) displayed |
| **TC-08** | Invalid CSV Handling | 1. Upload `invalid.csv` (wrong headers) <br> 2. Submit | Error message (e.g., containing "invalid", "error", or "missing") or no metrics displayed |
| **TC-09** | Single-Row CSV | 1. Upload `single_row.csv` <br> 2. Submit | Metrics and map display correctly for single route |
| **TC-10** | Large CSV File | 1. Upload `large_file.csv` (201 rows) <br> 2. Submit | Data processes within 2 minutes, metrics and map displayed |

## 3. Non-Functional Test Cases
- **Performance**:
  - Page load time: < 3 seconds (measured manually or via browser dev tools)
  - Map rendering: < 5 seconds after CSV upload
  - Large file processing: < 2 minutes for 201 rows
- **Responsiveness**:
  - Test on mobile (360px), tablet (768px), and desktop (1200px) viewports using Playwright’s viewport settings
  - Ensure UI elements (file uploader, dropdowns, maps) are accessible and functional
- **Error Handling**:
  - Test invalid file formats (e.g., `.txt` instead of `.csv`)
  - Test empty CSV uploads
  - Test corrupted CSVs (e.g., malformed rows, non-UTF-8 encoding)
- **Security**:
  - Verify HTTPS is enabled (manual check)
  - Test for XSS by uploading a CSV with script tags in fields (e.g., `<script>alert('xss')</script>`)
  - Confirm input sanitization for file uploads (no execution of malicious content)

## 4. Test Execution
- **Automated Tests**: Run `npm test` with `tests/test_app.js` to execute TC-01, TC-08, TC-09, and TC-10
- **Manual Tests**: Perform TC-02 to TC-07, responsiveness, and security tests manually
- **Outputs**:
  - Screenshots: Saved in `tests/results/` (e.g., `after_upload_valid.csv.png`, `test2_invalid_upload.png`)
  - Console logs: Captured from `npm test`
  - Network logs: Captured via Playwright’s request/response logging
  - Manual test results: Documented in a report

## 5. Deliverables
- Test plan document (`Test_Plan.md`)
- Playwright test script (`test_app.js`)
- Test data files (`tests/test_data/*.csv`)
- Test execution report (`report.txt` with results, logs, and screenshots)
- Manual test results for TC-02 to TC-07, responsiveness, and security