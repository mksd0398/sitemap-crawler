#!/usr/bin/env python3
"""
Unified Sitemap Crawler and Analysis Tool
Fetches all URLs from a website's sitemap, categorizes them, and provides comprehensive analysis.
Supports Shopify stores with crawler authentication.
"""

import requests
import xml.etree.ElementTree as ET
import csv
import json
import re
from urllib.parse import urljoin, urlparse
from typing import Dict, List, Set, Optional
import time
import argparse
from datetime import datetime
import sys
import os
from collections import defaultdict


class SitemapTool:
    def __init__(self, config: Dict):
        """
        Initialize the sitemap tool with configuration.
        
        Args:
            config: Configuration dictionary containing base_url, credentials, and settings
        """
        self.config = config
        self.base_url = config['base_url'].rstrip('/')
        self.session = requests.Session()
        
        # Set up logging to file
        self.log_file = config.get('log_file')
        if self.log_file:
            # Create log directory if it doesn't exist
            log_dir = os.path.dirname(self.log_file)
            if log_dir and not os.path.exists(log_dir):
                os.makedirs(log_dir)
            
            # Open log file for writing
            self.log_fd = open(self.log_file, 'w', encoding='utf-8')
            self.log(f"Sitemap Tool started at {datetime.now().isoformat()}")
            self.log(f"Target URL: {self.base_url}")
        else:
            self.log_fd = None
        
        # Set up Shopify crawler authentication if provided
        credentials = config.get('credentials', {})
        if credentials.get('signature') and credentials.get('signature_input') and credentials.get('signature_agent'):
            self.session.headers.update({
                'Signature': credentials['signature'],
                'Signature-Input': credentials['signature_input'],
                'Signature-Agent': credentials['signature_agent']
            })
            self.log("Shopify crawler authentication configured")
        
        # Common sitemap locations
        self.sitemap_urls = [
            f"{self.base_url}/sitemap.xml",
            f"{self.base_url}/sitemap_index.xml",
            f"{self.base_url}/sitemaps/sitemap.xml",
            f"{self.base_url}/sitemaps/sitemap_index.xml"
        ]
        
        # URL categorization patterns (optional - for common e-commerce patterns)
        self.url_patterns = {
            'products': [
                r'/products/',
                r'/product/',
                r'/p/',
                r'/item/',
                r'/shop/.*?/products/',
                r'/collections/.*?/products/'
            ],
            'collections': [
                r'/collections/',
                r'/collection/',
                r'/categories/',
                r'/category/',
                r'/shop/',
                r'/browse/'
            ],
            'blogs': [
                r'/blogs/',
                r'/blog/',
                r'/news/',
                r'/articles/',
                r'/journal/'
            ],
            'pages': [
                r'/pages/',
                r'/page/',
                r'/about',
                r'/contact',
                r'/privacy',
                r'/terms',
                r'/shipping',
                r'/returns',
                r'/faq',
                r'/help',
                r'/support'
            ],
            'cart_checkout': [
                r'/cart',
                r'/checkout',
                r'/checkouts/',
                r'/orders/',
                r'/account'
            ],
            'search': [
                r'/search',
                r'/search\?',
                r'/find'
            ],
            'home': [
                r'^' + re.escape(self.base_url) + r'/?$',
                r'^' + re.escape(self.base_url) + r'/index'
            ]
        }
        
        # Initialize with dynamic categories
        self.categorized_urls = {
            'all_urls': set(),  # All URLs regardless of category
            'others': set()     # URLs that don't match any pattern
        }
        
        # Add pattern-based categories dynamically
        for category in self.url_patterns.keys():
            self.categorized_urls[category] = set()
    
    def log(self, message: str):
        """Log message to both console and file."""
        timestamp = datetime.now().strftime("%H:%M:%S")
        formatted_message = f"[{timestamp}] {message}"
        
        # Print to console
        print(formatted_message)
        
        # Write to log file if available
        if self.log_fd:
            self.log_fd.write(formatted_message + '\n')
            self.log_fd.flush()
    
    def close_log(self):
        """Close the log file."""
        if self.log_fd:
            self.log(f"Sitemap Tool finished at {datetime.now().isoformat()}")
            self.log_fd.close()
            self.log_fd = None
    
    def find_sitemap(self) -> Optional[str]:
        """Find the main sitemap URL."""
        self.log("Searching for sitemap...")
        
        for sitemap_url in self.sitemap_urls:
            try:
                self.log(f"Trying sitemap: {sitemap_url}")
                response = self.session.head(sitemap_url, timeout=10)
                self.log(f"Response status: {response.status_code}")
                
                if response.status_code == 200:
                    self.log(f"Found sitemap: {sitemap_url}")
                    return sitemap_url
                    
            except requests.RequestException as e:
                self.log(f"Error accessing {sitemap_url}: {e}")
                continue
        
        self.log("No sitemap found in common locations")
        return None
    
    def fetch_sitemap_urls(self, sitemap_url: str) -> List[str]:
        """Fetch all URLs from sitemap(s)."""
        self.log(f"Fetching URLs from: {sitemap_url}")
        
        try:
            response = self.session.get(sitemap_url, timeout=30)
            response.raise_for_status()
            
            # Parse XML
            root = ET.fromstring(response.content)
            
            # Handle sitemap index
            if root.tag.endswith('sitemapindex'):
                self.log("Found sitemap index, processing individual sitemaps...")
                urls = []
                for sitemap in root.findall('.//{http://www.sitemaps.org/schemas/sitemap/0.9}sitemap'):
                    loc = sitemap.find('{http://www.sitemaps.org/schemas/sitemap/0.9}loc')
                    if loc is not None:
                        sub_urls = self.fetch_sitemap_urls(loc.text)
                        urls.extend(sub_urls)
                        time.sleep(0.5)  # Be respectful
                return urls
            
            # Handle regular sitemap
            elif root.tag.endswith('urlset'):
                urls = []
                for url_elem in root.findall('.//{http://www.sitemaps.org/schemas/sitemap/0.9}url'):
                    loc = url_elem.find('{http://www.sitemaps.org/schemas/sitemap/0.9}loc')
                    if loc is not None:
                        urls.append(loc.text)
                
                self.log(f"Found {len(urls)} URLs in sitemap")
                return urls
            
            else:
                self.log(f"Unknown XML structure: {root.tag}")
                return []
                
        except requests.RequestException as e:
            self.log(f"Error fetching sitemap: {e}")
            return []
        except ET.ParseError as e:
            self.log(f"Error parsing XML: {e}")
            return []
    
    def categorize_urls(self, urls: List[str]) -> Dict[str, List[str]]:
        """Categorize URLs based on patterns while preserving all URLs."""
        self.log("Processing and categorizing URLs...")
        
        # Reset categorized URLs
        for category in self.categorized_urls:
            self.categorized_urls[category].clear()
        
        # Add ALL URLs to the 'all_urls' category (this is the complete list)
        self.categorized_urls['all_urls'].update(urls)
        
        # Additionally, try to categorize URLs based on patterns for analysis
        for url in urls:
            categorized = False
            
            for category, patterns in self.url_patterns.items():
                for pattern in patterns:
                    if re.search(pattern, url, re.IGNORECASE):
                        self.categorized_urls[category].add(url)
                        categorized = True
                        break
                if categorized:
                    break
            
            if not categorized:
                self.categorized_urls['others'].add(url)
        
        # Convert sets to sorted lists
        result = {}
        for category, url_set in self.categorized_urls.items():
            result[category] = sorted(list(url_set))
        
        return result
    
    def print_summary(self, categorized_urls: Dict[str, List[str]]):
        """Print summary of categorized URLs."""
        self.log("\n" + "="*60)
        self.log("URL SUMMARY")
        self.log("="*60)
        
        # Show total URLs first
        total_urls = len(categorized_urls.get('all_urls', []))
        self.log(f"Total URLs found: {total_urls:,}")
        self.log("-" * 40)
        
        # Show all URLs category first
        if 'all_urls' in categorized_urls:
            self.log(f"{'ALL URLS':<15}: {len(categorized_urls['all_urls']):>8,} URLs (100.0%)")
            self.log("  ^ Complete list of all URLs from sitemap")
        
        # Show categorized breakdown
        self.log("\nCATEGORIZED BREAKDOWN (for analysis):")
        self.log("-" * 40)
        for category, urls in categorized_urls.items():
            if category != 'all_urls':  # Skip all_urls as it's shown above
                count = len(urls)
                percentage = (count / total_urls * 100) if total_urls > 0 else 0
                self.log(f"{category.upper():<15}: {count:>8,} URLs ({percentage:>5.1f}%)")
    
    def export_to_json(self, categorized_urls: Dict[str, List[str]], filename: str = None):
        """Export categorized URLs to JSON file."""
        if not filename:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            domain_name = self.base_url.replace('https://', '').replace('http://', '').replace('www.', '').replace('.', '_')
            filename = f"sitemap_urls_{domain_name}_{timestamp}.json"
        
        export_data = {
            'metadata': {
                'base_url': self.base_url,
                'crawl_date': datetime.now().isoformat(),
                'total_urls': sum(len(urls) for urls in categorized_urls.values())
            },
            'categorized_urls': categorized_urls
        }
        
        with open(filename, 'w', encoding='utf-8') as jsonfile:
            json.dump(export_data, jsonfile, indent=2, ensure_ascii=False)
        
        self.log(f"Exported to {filename}")
        return filename
    
    def crawl(self) -> Dict[str, List[str]]:
        """Main crawling method."""
        self.log(f"Starting sitemap crawl for: {self.base_url}")
        self.log("-" * 60)
        
        # Find sitemap
        sitemap_url = self.find_sitemap()
        if not sitemap_url:
            self.log("Could not find sitemap. Exiting.")
            return {}
        
        # Fetch URLs
        urls = self.fetch_sitemap_urls(sitemap_url)
        if not urls:
            self.log("No URLs found in sitemap. Exiting.")
            return {}
        
        # Categorize URLs
        categorized_urls = self.categorize_urls(urls)
        
        # Print summary
        self.print_summary(categorized_urls)
        
        return categorized_urls
    
    # Analysis methods (from sitemap_analysis.py)
    def analyze_sitemap_data(self, json_file: str):
        """Analyze the sitemap JSON data for insights."""
        self.log("Analyzing sitemap data...")
        
        with open(json_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        categorized_urls = data['categorized_urls']
        metadata = data['metadata']
        
        self.log(f"\nSUMMARY:")
        self.log(f"Base URL: {metadata['base_url']}")
        self.log(f"Crawl Date: {metadata['crawl_date']}")
        self.log(f"Total URLs: {metadata['total_urls']}")
        
        self.log(f"\nCATEGORIZATION BREAKDOWN:")
        for category, urls in categorized_urls.items():
            self.log(f"{category.upper():<15}: {len(urls):>6} URLs")
        
        # Analyze product URLs
        products = categorized_urls['products']
        self.log(f"\nPRODUCT ANALYSIS:")
        self.log(f"Total Products: {len(products)}")
        
        # Extract product IDs from URLs
        product_ids = []
        product_patterns = defaultdict(int)
        
        for url in products:
            # Extract product handle from URL
            path = urlparse(url).path
            if '/products/' in path:
                product_handle = path.split('/products/')[-1]
                product_ids.append(product_handle)
                
                # Analyze product naming patterns
                if re.search(r'es\d+', product_handle):
                    product_patterns['with_es_code'] += 1
                elif re.search(r'ah\d+', product_handle):
                    product_patterns['with_ah_code'] += 1
                elif re.search(r'\d+', product_handle):
                    product_patterns['with_numbers'] += 1
                else:
                    product_patterns['no_numbers'] += 1
        
        self.log(f"\nPRODUCT NAMING PATTERNS:")
        for pattern, count in product_patterns.items():
            self.log(f"{pattern.replace('_', ' ').title():<20}: {count:>6} products")
        
        # Check for duplicates
        unique_products = set(product_ids)
        if len(unique_products) != len(product_ids):
            self.log(f"\nDUPLICATE DETECTION:")
            self.log(f"Total product URLs: {len(product_ids)}")
            self.log(f"Unique product handles: {len(unique_products)}")
            self.log(f"Duplicates found: {len(product_ids) - len(unique_products)}")
        
        # Analyze URL structure
        self.log(f"\nURL STRUCTURE ANALYSIS:")
        domain_counts = defaultdict(int)
        for url in products:
            domain = urlparse(url).netloc
            domain_counts[domain] += 1
        
        for domain, count in domain_counts.items():
            self.log(f"{domain}: {count} products")
        
        return {
            'total_products': len(products),
            'unique_products': len(unique_products),
            'product_patterns': dict(product_patterns),
            'duplicates': len(product_ids) - len(unique_products)
        }
    
    def analyze_product_count(self, actual_count: int):
        """Analyze product count and provide insights."""
        self.log(f"\nPRODUCT COUNT ANALYSIS:")
        self.log(f"Total Products Found: {actual_count:,}")
        
        if actual_count == 0:
            self.log("\nNo products found in sitemap. Possible reasons:")
            self.log("1. Products might be in draft status (not published)")
            self.log("2. Products might be archived or hidden")
            self.log("3. Sitemap generation might exclude certain product types")
            self.log("4. Products might have specific visibility settings")
        elif actual_count < 100:
            self.log(f"\nLow product count ({actual_count:,}). Consider checking:")
            self.log("1. Sitemap generation settings")
            self.log("2. Product publication status")
            self.log("3. Store configuration")
        else:
            self.log(f"\nGood product count found ({actual_count:,} products)")
            self.log("Consider monitoring for changes over time")
    
    def export_product_handles(self, json_file: str, output_file: str):
        """Export all product handles to a CSV file for further analysis."""
        self.log(f"\nExporting product handles to {output_file}...")
        
        with open(json_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        products = data['categorized_urls']['products']
        
        with open(output_file, 'w', newline='', encoding='utf-8') as csvfile:
            writer = csv.writer(csvfile)
            writer.writerow(['Index', 'Product_URL', 'Product_Handle'])
            
            for i, url in enumerate(products, 1):
                path = urlparse(url).path
                if '/products/' in path:
                    product_handle = path.split('/products/')[-1]
                    writer.writerow([i, url, product_handle])
        
        self.log(f"Exported {len(products)} product handles to {output_file}")
    
    def list_all_urls(self, json_file: str):
        """List all URLs from the sitemap data organized by category."""
        self.log("\nListing all URLs from sitemap...")
        
        with open(json_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        categorized_urls = data['categorized_urls']
        metadata = data['metadata']
        
        all_urls = []
        category_stats = {}
        
        # First, show ALL URLs (complete list from sitemap)
        if 'all_urls' in categorized_urls:
            urls = categorized_urls['all_urls']
            category_stats['all_urls'] = len(urls)
            self.log(f"\nALL URLS FROM SITEMAP ({len(urls)} URLs):")
            self.log("=" * 60)
            self.log("This is the complete list of all URLs found in the sitemap")
            self.log("-" * 60)
            
            for i, url in enumerate(urls, 1):
                all_urls.append({
                    'category': 'all_urls',
                    'index': i,
                    'url': url,
                    'domain': urlparse(url).netloc,
                    'path': urlparse(url).path
                })
                self.log(f"{i:>6}: {url}")
        
        # Then show categorized URLs (for additional analysis)
        self.log(f"\n" + "=" * 60)
        self.log("CATEGORIZED URLS (for analysis purposes)")
        self.log("=" * 60)
        self.log("These are the same URLs organized by patterns for analysis")
        self.log("-" * 60)
        
        for category, urls in categorized_urls.items():
            if category != 'all_urls':  # Skip all_urls as it's shown above
                category_stats[category] = len(urls)
                self.log(f"\n{category.upper()} ({len(urls)} URLs):")
                self.log("-" * 50)
                
                for i, url in enumerate(urls, 1):
                    all_urls.append({
                        'category': category,
                        'index': i,
                        'url': url,
                        'domain': urlparse(url).netloc,
                        'path': urlparse(url).path
                    })
                    self.log(f"{i:>6}: {url}")
        
        return all_urls, category_stats
    
    def generate_comprehensive_log(self, json_file: str, log_prefix: str = "sitemap_comprehensive"):
        """Generate a comprehensive log file with all URLs and analysis."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        log_file = f"{log_prefix}_{timestamp}.txt"
        
        self.log(f"\nGenerating comprehensive log: {log_file}")
        
        with open(json_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        categorized_urls = data['categorized_urls']
        metadata = data['metadata']
        
        with open(log_file, 'w', encoding='utf-8') as f:
            f.write("=" * 80 + "\n")
            f.write("SITEMAP COMPREHENSIVE ANALYSIS LOG\n")
            f.write("=" * 80 + "\n")
            f.write(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"Source File: {json_file}\n")
            f.write(f"Base URL: {metadata['base_url']}\n")
            f.write(f"Crawl Date: {metadata['crawl_date']}\n")
            f.write(f"Total URLs: {metadata['total_urls']:,}\n")
            f.write("=" * 80 + "\n\n")
            
            # Summary statistics
            f.write("CATEGORY SUMMARY:\n")
            f.write("-" * 40 + "\n")
            for category, urls in categorized_urls.items():
                f.write(f"{category.upper():<15}: {len(urls):>8,} URLs\n")
            f.write("\n")
            
            # First show ALL URLs (complete list from sitemap)
            if 'all_urls' in categorized_urls:
                urls = categorized_urls['all_urls']
                f.write(f"\nALL URLS FROM SITEMAP ({len(urls)} total):\n")
                f.write("=" * 60 + "\n")
                f.write("This is the complete list of all URLs found in the sitemap\n")
                f.write("-" * 60 + "\n")
                
                for i, url in enumerate(urls, 1):
                    f.write(f"{i:>6}: {url}\n")
                
                f.write(f"\nEnd of ALL URLS FROM SITEMAP\n")
                f.write("-" * 60 + "\n")
            
            # Then show categorized URLs (for analysis)
            f.write(f"\nCATEGORIZED URLS (for analysis purposes):\n")
            f.write("=" * 60 + "\n")
            f.write("These are the same URLs organized by patterns for analysis\n")
            f.write("-" * 60 + "\n")
            
            for category, urls in categorized_urls.items():
                if category != 'all_urls':  # Skip all_urls as it's shown above
                    f.write(f"\n{category.upper()} URLs ({len(urls)} total):\n")
                    f.write("=" * 60 + "\n")
                    
                    for i, url in enumerate(urls, 1):
                        f.write(f"{i:>6}: {url}\n")
                    
                    f.write(f"\nEnd of {category.upper()} URLs\n")
                    f.write("-" * 60 + "\n")
        
        self.log(f"Comprehensive log generated: {log_file}")
        return log_file
    
    def generate_url_analysis_log(self, json_file: str, log_prefix: str = "sitemap_analysis"):
        """Generate a detailed analysis log with insights and statistics."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        log_file = f"{log_prefix}_{timestamp}.txt"
        
        self.log(f"\nGenerating analysis log: {log_file}")
        
        with open(json_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        categorized_urls = data['categorized_urls']
        metadata = data['metadata']
        
        with open(log_file, 'w', encoding='utf-8') as f:
            f.write("=" * 80 + "\n")
            f.write("SITEMAP ANALYSIS AND INSIGHTS LOG\n")
            f.write("=" * 80 + "\n")
            f.write(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"Source File: {json_file}\n")
            f.write("=" * 80 + "\n\n")
            
            # Basic metadata
            f.write("BASIC INFORMATION:\n")
            f.write("-" * 40 + "\n")
            f.write(f"Base URL: {metadata['base_url']}\n")
            f.write(f"Crawl Date: {metadata['crawl_date']}\n")
            f.write(f"Total URLs: {metadata['total_urls']:,}\n\n")
            
            # Category breakdown
            f.write("CATEGORY BREAKDOWN:\n")
            f.write("-" * 40 + "\n")
            total_urls = 0
            for category, urls in categorized_urls.items():
                count = len(urls)
                total_urls += count
                percentage = (count / metadata['total_urls'] * 100) if metadata['total_urls'] > 0 else 0
                f.write(f"{category.upper():<15}: {count:>8,} URLs ({percentage:>5.1f}%)\n")
            f.write(f"{'TOTAL':<15}: {total_urls:>8,} URLs\n\n")
            
            # Product analysis
            if 'products' in categorized_urls:
                products = categorized_urls['products']
                f.write("PRODUCT ANALYSIS:\n")
                f.write("-" * 40 + "\n")
                f.write(f"Total Products: {len(products):,}\n")
                
                # Product naming patterns
                product_patterns = defaultdict(int)
                domain_counts = defaultdict(int)
                
                for url in products:
                    domain = urlparse(url).netloc
                    domain_counts[domain] += 1
                    
                    path = urlparse(url).path
                    if '/products/' in path:
                        product_handle = path.split('/products/')[-1]
                        
                        if re.search(r'es\d+', product_handle):
                            product_patterns['with_es_code'] += 1
                        elif re.search(r'ah\d+', product_handle):
                            product_patterns['with_ah_code'] += 1
                        elif re.search(r'\d+', product_handle):
                            product_patterns['with_numbers'] += 1
                        else:
                            product_patterns['no_numbers'] += 1
                
                f.write("\nProduct Naming Patterns:\n")
                for pattern, count in product_patterns.items():
                    percentage = (count / len(products) * 100) if products else 0
                    f.write(f"  {pattern.replace('_', ' ').title():<20}: {count:>6,} ({percentage:>5.1f}%)\n")
                
                f.write("\nDomain Distribution:\n")
                for domain, count in domain_counts.items():
                    percentage = (count / len(products) * 100) if products else 0
                    f.write(f"  {domain:<30}: {count:>6,} ({percentage:>5.1f}%)\n")
                
                # Check for duplicates
                product_handles = []
                for url in products:
                    path = urlparse(url).path
                    if '/products/' in path:
                        product_handle = path.split('/products/')[-1]
                        product_handles.append(product_handle)
                
                unique_handles = set(product_handles)
                if len(unique_handles) != len(product_handles):
                    f.write(f"\nDuplicate Detection:\n")
                    f.write(f"  Total product URLs: {len(product_handles):,}\n")
                    f.write(f"  Unique product handles: {len(unique_handles):,}\n")
                    f.write(f"  Duplicates found: {len(product_handles) - len(unique_handles):,}\n")
            
            # Collection analysis
            if 'collections' in categorized_urls:
                collections = categorized_urls['collections']
                f.write(f"\nCOLLECTION ANALYSIS:\n")
                f.write("-" * 40 + "\n")
                f.write(f"Total Collections: {len(collections):,}\n")
                
                # Collection patterns
                collection_patterns = defaultdict(int)
                for url in collections:
                    path = urlparse(url).path
                    if '/collections/' in path:
                        collection_handle = path.split('/collections/')[-1]
                        if re.search(r'\d+', collection_handle):
                            collection_patterns['with_numbers'] += 1
                        else:
                            collection_patterns['no_numbers'] += 1
                
                f.write("\nCollection Naming Patterns:\n")
                for pattern, count in collection_patterns.items():
                    percentage = (count / len(collections) * 100) if collections else 0
                    f.write(f"  {pattern.replace('_', ' ').title():<20}: {count:>6,} ({percentage:>5.1f}%)\n")
            
            # Blog analysis
            if 'blogs' in categorized_urls:
                blogs = categorized_urls['blogs']
                f.write(f"\nBLOG ANALYSIS:\n")
                f.write("-" * 40 + "\n")
                f.write(f"Total Blog Posts: {len(blogs):,}\n")
            
            # Page analysis
            if 'pages' in categorized_urls:
                pages = categorized_urls['pages']
                f.write(f"\nPAGE ANALYSIS:\n")
                f.write("-" * 40 + "\n")
                f.write(f"Total Pages: {len(pages):,}\n")
            
            # Recommendations
            f.write(f"\nRECOMMENDATIONS:\n")
            f.write("-" * 40 + "\n")
            f.write("1. Monitor sitemap generation frequency and timing\n")
            f.write("2. Check for products in draft/archived status\n")
            f.write("3. Verify sitemap generation settings in Shopify\n")
            f.write("4. Compare with direct product database queries\n")
            f.write("5. Check product visibility and publication settings\n")
            f.write("6. Monitor for URL structure changes\n")
            f.write("7. Validate all URLs for accessibility\n")
        
        self.log(f"Analysis log generated: {log_file}")
        return log_file
    
    def run_full_analysis(self):
        """Run the complete crawl and analysis workflow."""
        self.log("=" * 80)
        self.log("UNIFIED SITEMAP CRAWLER AND ANALYSIS TOOL")
        self.log("=" * 80)
        
        # Step 1: Crawl sitemap
        self.log("\nSTEP 1: CRAWLING SITEMAP")
        self.log("=" * 40)
        categorized_urls = self.crawl()
        
        if not categorized_urls:
            self.log("Crawling failed. Exiting.")
            return
        
        # Step 2: Export to JSON
        self.log("\nSTEP 2: EXPORTING DATA")
        self.log("=" * 40)
        json_file = self.export_to_json(categorized_urls)
        
        # Step 3: Analyze data
        self.log("\nSTEP 3: ANALYZING DATA")
        self.log("=" * 40)
        analysis = self.analyze_sitemap_data(json_file)
        
        # Step 4: Analyze product count
        self.log("\nSTEP 4: PRODUCT COUNT ANALYSIS")
        self.log("=" * 40)
        self.analyze_product_count(analysis['total_products'])
        
        # Step 5: List all URLs
        self.log("\nSTEP 5: LISTING ALL URLS")
        self.log("=" * 40)
        all_urls, category_stats = self.list_all_urls(json_file)
        
        # Step 6: Generate comprehensive logs
        self.log("\nSTEP 6: GENERATING LOG FILES")
        self.log("=" * 40)
        comprehensive_log = self.generate_comprehensive_log(json_file)
        analysis_log = self.generate_url_analysis_log(json_file)
        
        # Step 7: Export product handles
        self.log("\nSTEP 7: EXPORTING PRODUCT HANDLES")
        self.log("=" * 40)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        domain_name = self.base_url.replace('https://', '').replace('http://', '').replace('www.', '').replace('.', '_')
        csv_file = f"sitemap_product_handles_{domain_name}_{timestamp}.csv"
        self.export_product_handles(json_file, csv_file)
        
        # Final summary
        self.log(f"\n" + "=" * 80)
        self.log("ANALYSIS COMPLETE")
        self.log("=" * 80)
        self.log(f"Generated Files:")
        self.log(f"  1. JSON Data: {json_file}")
        self.log(f"  2. Comprehensive Log: {comprehensive_log}")
        self.log(f"  3. Analysis Log: {analysis_log}")
        self.log(f"  4. Product Handles CSV: {csv_file}")
        self.log(f"\nTotal URLs Processed: {len(all_urls):,}")
        self.log(f"Categories Found: {len(category_stats)}")
        
        self.log(f"\nRECOMMENDATIONS:")
        self.log("1. Check your admin panel for draft/archived products")
        self.log("2. Verify sitemap generation settings")
        self.log("3. Compare with your product database directly")
        self.log("4. Check if any products have specific visibility rules")
        self.log("5. Consider the timing of sitemap generation")
        self.log("6. Review the generated log files for detailed insights")
        
        return {
            'json_file': json_file,
            'comprehensive_log': comprehensive_log,
            'analysis_log': analysis_log,
            'csv_file': csv_file,
            'total_urls': len(all_urls),
            'categories': len(category_stats)
        }


def load_config(config_file: str) -> Dict:
    """Load configuration from JSON file."""
    try:
        with open(config_file, 'r', encoding='utf-8') as f:
            config = json.load(f)
        return config
    except FileNotFoundError:
        print(f"Error: Configuration file '{config_file}' not found.")
        sys.exit(1)
    except json.JSONDecodeError as e:
        print(f"Error: Invalid JSON in configuration file: {e}")
        sys.exit(1)


def main():
    parser = argparse.ArgumentParser(description='Unified Sitemap Crawler and Analysis Tool')
    parser.add_argument('config_file', help='Path to configuration JSON file')
    
    args = parser.parse_args()
    
    # Load configuration
    config = load_config(args.config_file)
    
    # Initialize tool
    tool = SitemapTool(config)
    
    try:
        # Run full analysis
        results = tool.run_full_analysis()
        
        if results:
            tool.log(f"\nDetailed log saved to: {tool.log_file}")
        
    except Exception as e:
        tool.log(f"Unexpected error: {e}")
        tool.log(f"Error type: {type(e).__name__}")
        raise
    finally:
        # Always close the log file
        tool.close_log()


if __name__ == "__main__":
    main()
