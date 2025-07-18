# VRP Streamlit App Testing

## Setup
1. **Install Node.js** (if not installed):
   ```bash
   sudo apt update
   sudo apt install -y nodejs npm
   ```
2. **Install Dependencies**:
   ```bash
   npm install
   ```
3. **Ensure Test Data**: Verify CSV files exist in `tests/test_data/`.

## Running Tests
- Run all tests:
  ```bash
  npm test
  ```
- Results (screenshots) are saved in `tests/results/`.

## Test Scenarios
1. Valid CSV Upload
2. Invalid CSV Upload
3. Single-Row CSV
4. Large CSV File
5. Driver Selection
6. No File Uploaded
