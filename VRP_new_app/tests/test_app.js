const { chromium } = require('playwright');

(async () => {
  const browser = await chromium.launch({ headless: false });
  const page = await browser.newPage();
  const APP_URL = 'http://157.180.87.7:8501/';

  // Log network requests for debugging
  page.on('request', request => console.log('>>', request.method(), request.url()));
  page.on('response', response => console.log('<<', response.status(), response.url()));

  async function uploadFile(filePath, timeout = 60000) {
    await page.goto(APP_URL);
    await page.waitForSelector('.stFileUploader input[type="file"]', { timeout: 10000 });
    const fileInput = await page.$('.stFileUploader input[type="file"]');
    if (!fileInput) throw new Error('File input element not found');
    await fileInput.setInputFiles(filePath);
    try {
      await page.waitForSelector('text=Data loaded and cached', { timeout });
    } catch (error) {
      console.log(`Timeout waiting for "Data loaded and cached" with ${filePath}`);
      console.log(await page.content());
      await page.screenshot({ path: `tests/results/failed_${filePath.split('/').pop()}.png` });
      throw error;
    }
    await page.screenshot({ path: `tests/results/after_upload_${filePath.split('/').pop()}.png` });
  }

  // Test 1: Valid CSV Upload
  console.log('Running Test 1: Valid CSV Upload');
  try {
    await uploadFile('tests/test_data/valid.csv');
    const totalLoaded = await page.textContent('text=Total Loaded');
    console.log('Total Loaded text:', totalLoaded); // Debug output
    if (totalLoaded && totalLoaded.includes('340.1 mi')) {
      console.log('Test 1 Passed');
    } else {
      console.log('Test 1 Failed: Expected "340.1 mi" in Total Loaded');
      await page.screenshot({ path: 'tests/results/test1_failed.png' });
      console.log('Page content:', await page.content());
    }
  } catch (error) {
    console.log('Test 1 Failed with error:', error);
    await page.screenshot({ path: 'tests/results/test1_error.png' });
  }

  // Test 2: Invalid CSV Upload
  console.log('Running Test 2: Invalid CSV Upload');
  try {
    await page.goto(APP_URL);
    await page.waitForSelector('.stFileUploader input[type="file"]', { timeout: 10000 });
    const fileInput = await page.$('.stFileUploader input[type="file"]');
    await fileInput.setInputFiles('tests/test_data/invalid.csv');
    const errorMessage = await page.locator(':text-matches("invalid|error|missing", "i")').textContent({ timeout: 10000 }).catch(() => null);
    await page.screenshot({ path: 'tests/results/test2_invalid_upload.png' });
    const totalLoaded = await page.$('text=Total Loaded');
    if (errorMessage || !totalLoaded) {
      console.log('Test 2 Passed: Error detected or no metrics displayed');
    } else {
      console.log('Test 2 Failed: Expected error or no metrics');
      console.log('Page content:', await page.content());
    }
  } catch (error) {
    console.log('Test 2 Failed with error:', error);
    await page.screenshot({ path: 'tests/results/test2_error.png' });
  }

  // Test 3: Single-Row CSV
  console.log('Running Test 3: Single-Row CSV');
  try {
    await uploadFile('tests/test_data/single_row.csv');
    const metricsSingle = await page.textContent('text=Total Loaded');
    if (metricsSingle) {
      console.log('Test 3 Passed');
    } else {
      console.log('Test 3 Failed: No metrics found');
      await page.screenshot({ path: 'tests/results/test3_failed.png' });
    }
  } catch (error) {
    console.log('Test 3 Failed with error:', error);
    await page.screenshot({ path: 'tests/results/test3_error.png' });
  }

  // Test 4: Large CSV File
  console.log('Running Test 4: Large CSV File');
  try {
    await uploadFile('tests/test_data/large_file.csv', 120000);
    const metricsLarge = await page.textContent('text=Total Loaded');
    if (metricsLarge) {
      console.log('Test 4 Passed');
    } else {
      console.log('Test 4 Failed: No metrics found');
      await page.screenshot({ path: 'tests/results/test4_failed.png' });
    }
  } catch (error) {
    console.log('Test 4 Failed with error:', error);
    await page.screenshot({ path: 'tests/results/test4_error.png' });
  }

  await browser.close();
})();
