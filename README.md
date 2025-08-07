# Firecrawl CSV URL Scraper

A production-grade web application for scraping websites from URLs listed in a CSV file using the Firecrawl.dev API. Features both a web interface and command-line tool.

## Features

### 🌐 Web Interface
- **Easy File Upload**: Drag-and-drop CSV file upload with validation
- **Real-time Progress**: Live progress tracking with detailed statistics
- **Job Management**: View all jobs and their status in a dashboard
- **Results Download**: Download scraped data in JSON format
- **Mobile Responsive**: Works perfectly on desktop and mobile devices

### 🛠️ Core Functionality  
- **CSV Input**: Read URLs from any CSV file with flexible column naming
- **Firecrawl Integration**: Uses Firecrawl.dev for robust web scraping that bypasses blockers
- **Multiple Output Formats**: Export results to JSON or CSV
- **Error Handling**: Comprehensive retry logic with exponential backoff
- **Rate Limiting**: Configurable delays between requests
- **Progress Tracking**: Real-time progress updates and detailed summaries
- **Resume Capability**: Designed for processing large datasets reliably

## Installation

1. Clone or download this repository
2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

3. Set up your Firecrawl API key:
   - Copy `.env.example` to `.env`
   - Get your API key from [firecrawl.dev](https://firecrawl.dev)
   - Update the `.env` file with your key

## Usage

### 🌐 Web Interface (Recommended)

1. **Start the web application**:
   ```bash
   python app.py
   ```

2. **Open your browser** to `http://localhost:5000`

3. **Upload a CSV file** with URLs and configure scraping options

4. **Monitor progress** in real-time and download results when complete

### 📟 Command Line Interface

```bash
python firecrawl_csv_scraper.py --input urls.csv --output results.json
```

### Advanced Usage

```bash
# Custom CSV column name and output format
python firecrawl_csv_scraper.py \
  --input sites.csv \
  --url-column website \
  --output data.json \
  --formats markdown html

# Slower scraping with more retries
python firecrawl_csv_scraper.py \
  --input urls.csv \
  --output results.csv \
  --delay 2.0 \
  --max-retries 5

# Include HTML in JSON output
python firecrawl_csv_scraper.py \
  --input urls.csv \
  --output results.json \
  --include-html
```

## Command Line Options

| Option | Description | Default |
|--------|-------------|---------|
| `--input, -i` | Input CSV file containing URLs | Required |
| `--output, -o` | Output file (.json or .csv) | Required |
| `--api-key` | Firecrawl API key | From FIRECRAWL_API_KEY env var |
| `--url-column` | CSV column name containing URLs | `url` |
| `--formats` | Output formats from Firecrawl | `markdown html` |
| `--delay` | Delay between requests (seconds) | `1.0` |
| `--max-retries` | Maximum retries per URL | `3` |
| `--include-html` | Include HTML in JSON output | `False` |

## CSV Input Format

Your CSV file should have at least one column containing URLs. Example:

```csv
url,description
https://example.com,Example domain
https://github.com,Code repository
https://stackoverflow.com,Q&A site
```

You can use any column name for URLs - just specify it with `--url-column`.

## Output Formats

### JSON Output
- Contains full scraping results including content, metadata, and errors
- Optionally includes HTML content with `--include-html`
- Structured data perfect for further processing

### CSV Output
- Summary view with URL, success status, title, and errors
- Lighter format for quick analysis
- Easy to import into spreadsheet applications

## Error Handling

The scraper includes robust error handling:

- **Retry Logic**: Failed requests are retried with exponential backoff
- **Rate Limiting**: Configurable delays prevent overwhelming target servers
- **Graceful Failures**: Individual URL failures don't stop the entire batch
- **Detailed Logging**: Clear feedback on progress and errors

## API Key Setup

1. Visit [firecrawl.dev](https://firecrawl.dev) and sign up
2. Get your API key from the dashboard
3. Set it as an environment variable:
   ```bash
   export FIRECRAWL_API_KEY=fc-your-api-key-here
   ```
   Or use the `--api-key` command line option

## Examples

### Example 1: Basic Website Scraping
```bash
# Create a CSV with URLs
echo "url
https://example.com
https://httpbin.org" > test_urls.csv

# Scrape and export to JSON
python firecrawl_csv_scraper.py --input test_urls.csv --output results.json
```

### Example 2: E-commerce Product Pages
```bash
# Scrape product pages with specific formats
python firecrawl_csv_scraper.py \
  --input product_urls.csv \
  --output products.json \
  --formats markdown links \
  --delay 1.5
```

### Example 3: Large Dataset Processing
```bash
# Process large dataset with conservative settings
python firecrawl_csv_scraper.py \
  --input large_url_list.csv \
  --output results.csv \
  --delay 2.0 \
  --max-retries 5 \
  --formats markdown
```

## Troubleshooting

### Common Issues

1. **API Key Error**: Make sure your Firecrawl API key is set correctly
2. **CSV Column Not Found**: Check that your CSV has the expected column name
3. **Rate Limiting**: Increase the `--delay` value if you're hitting rate limits
4. **Memory Issues**: Use CSV output for large datasets instead of JSON

### Performance Tips

- Use only the formats you need (`--formats markdown` is often sufficient)
- Increase delays (`--delay 2.0`) for better reliability
- Don't include HTML in JSON output unless necessary
- Process large datasets in smaller batches

## Related Files

- `crawl_hardrace.py`: Original website crawler for reference
- `example_urls.csv`: Sample CSV file for testing
- `.env.example`: Environment variable template

## License

This project is open source and available under the MIT License.
