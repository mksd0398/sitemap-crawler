# Sitemap Crawler and Analysis Tool

A comprehensive Python tool for crawling and analyzing website sitemaps, with special support for Shopify stores that require crawler authentication.

## Features

- **Sitemap Discovery**: Automatically finds sitemap files in common locations
- **URL Categorization**: Intelligently categorizes URLs into products, collections, blogs, pages, etc.
- **Shopify Support**: Handles Shopify stores with crawler authentication
- **Comprehensive Analysis**: Provides detailed insights and statistics
- **Multiple Export Formats**: JSON, CSV, and detailed log files
- **Duplicate Detection**: Identifies duplicate product URLs
- **Pattern Analysis**: Analyzes URL naming patterns and structures

## Installation

1. Clone or download the tool
2. Install required dependencies:
```bash
pip install requests
```

## Configuration

### Step 1: Create Configuration File

Copy the example configuration file:
```bash
cp config.example.json config.json
```

### Step 2: Configure Your Store

Edit `config.json` with your store details:

```json
{
  "base_url": "https://your-store.myshopify.com",
  "credentials": {
    "signature": "sig1=:your-signature-here:",
    "signature_input": "sig1=(\"@authority\" \"signature-agent\");keyid=\"your-key-id\";nonce=\"your-nonce\";tag=\"web-bot-auth\";created=timestamp;expires=timestamp",
    "signature_agent": "https://shopify.com"
  },
  "log_file": "sitemap_tool_log.txt"
}
```

### Step 3: Get Shopify Crawler Credentials

For Shopify stores, you need to obtain crawler authentication credentials:

1. **Go to your Shopify Admin**
2. **Navigate to**: `Online Store` → `Preferences`
3. **Look for**: "Crawler access" or "Bot access" section
4. **Copy the credentials** from the crawler access settings

The credentials will look like this:
- **Signature**: A long base64-encoded string
- **Signature-Input**: Contains keyid, nonce, created, and expires values
- **Signature-Agent**: Usually "https://shopify.com"

## Usage

### Basic Usage

Run the tool with your configuration file:

```bash
python sitemap_tool.py config.json
```

### What the Tool Does

The tool performs a complete analysis workflow:

1. **Discovers sitemap** in common locations (`/sitemap.xml`, `/sitemap_index.xml`, etc.)
2. **Fetches all URLs** from the sitemap(s)
3. **Categorizes URLs** into logical groups (products, collections, blogs, pages, etc.)
4. **Analyzes patterns** in product naming and URL structure
5. **Exports data** in multiple formats
6. **Generates comprehensive reports**

### Output Files

The tool generates several output files:

- **JSON Data File**: `sitemap_urls_[domain]_[timestamp].json` - Complete categorized URL data
- **Comprehensive Log**: `sitemap_comprehensive_[timestamp].txt` - All URLs listed by category
- **Analysis Log**: `sitemap_analysis_[timestamp].txt` - Detailed insights and statistics
- **Product Handles CSV**: `sitemap_product_handles_[domain]_[timestamp].csv` - Product handles for analysis
- **Tool Log**: `sitemap_tool_log.txt` - Execution log with timestamps

## Configuration Options

### Required Fields

- **`base_url`**: Your store's base URL (e.g., "https://your-store.myshopify.com")

### Optional Fields

- **`credentials`**: Shopify crawler authentication (required for protected stores)
  - `signature`: The signature string from Shopify admin
  - `signature_input`: The signature input string from Shopify admin
  - `signature_agent`: Usually "https://shopify.com"
- **`log_file`**: Path to log file (default: "sitemap_tool_log.txt")

## URL Categories

The tool automatically categorizes URLs into:

- **`all_urls`**: Complete list of all URLs from sitemap
- **`products`**: Product pages (`/products/`, `/product/`, etc.)
- **`collections`**: Collection/category pages (`/collections/`, `/categories/`, etc.)
- **`blogs`**: Blog posts (`/blogs/`, `/blog/`, etc.)
- **`pages`**: Static pages (`/pages/`, `/about`, `/contact`, etc.)
- **`cart_checkout`**: Cart and checkout pages
- **`search`**: Search pages
- **`home`**: Homepage URLs
- **`others`**: URLs that don't match any pattern

## Analysis Features

### Product Analysis
- Total product count
- Product naming patterns (with/without numbers, special codes)
- Duplicate detection
- Domain distribution

### Collection Analysis
- Collection count and patterns
- Naming convention analysis

### URL Structure Analysis
- Domain distribution
- Path pattern analysis
- Duplicate URL detection

## Troubleshooting

### Common Issues

1. **"No sitemap found"**
   - Check if your store has a sitemap at `/sitemap.xml`
   - Verify the base URL is correct
   - Some stores may have sitemaps at different locations

2. **"Authentication failed"**
   - Verify your Shopify credentials are correct
   - Check if credentials have expired
   - Ensure you're using the correct signature format

3. **"No URLs found"**
   - Check if the sitemap is accessible
   - Verify the sitemap contains URLs
   - Some stores may have empty or restricted sitemaps

### Getting Help

If you encounter issues:

1. Check the log file (`sitemap_tool_log.txt`) for detailed error messages
2. Verify your configuration file format
3. Ensure your store's sitemap is accessible
4. For Shopify stores, verify your crawler credentials are current

## Example Output

```
[14:30:15] Starting sitemap crawl for: https://your-store.myshopify.com
[14:30:15] ------------------------------------------------------------
[14:30:15] Searching for sitemap...
[14:30:15] Trying sitemap: https://your-store.myshopify.com/sitemap.xml
[14:30:15] Response status: 200
[14:30:15] Found sitemap: https://your-store.myshopify.com/sitemap.xml
[14:30:15] Fetching URLs from: https://your-store.myshopify.com/sitemap.xml
[14:30:16] Found 1,250 URLs in sitemap
[14:30:16] Processing and categorizing URLs...
[14:30:16] 
============================================================
URL SUMMARY
============================================================
Total URLs found: 1,250
----------------------------------------
ALL URLS           :    1,250 URLs (100.0%)
  ^ Complete list of all URLs from sitemap

CATEGORIZED BREAKDOWN (for analysis):
----------------------------------------
PRODUCTS           :      850 URLs ( 68.0%)
COLLECTIONS        :       45 URLs (  3.6%)
BLOGS              :       12 URLs (  1.0%)
PAGES              :       25 URLs (  2.0%)
CART_CHECKOUT      :        8 URLs (  0.6%)
SEARCH             :        3 URLs (  0.2%)
HOME               :        2 URLs (  0.2%)
OTHERS             :      305 URLs ( 24.4%)
```

## License

This tool is provided as-is for educational and analysis purposes.
