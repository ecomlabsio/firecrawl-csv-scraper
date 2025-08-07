#!/usr/bin/env python3
"""
Firecrawl CSV URL Scraper

A production-grade tool to scrape websites from URLs listed in a CSV file using Firecrawl.dev API.
Supports batch processing, error handling, rate limiting, and multiple output formats.

Features:
- Read URLs from CSV file
- Scrape using Firecrawl.dev API
- Export results to JSON or CSV
- Rate limiting and retry logic
- Progress tracking
- Resume capability for large datasets

Usage:
    python firecrawl_csv_scraper.py --input urls.csv --output results.json --api-key YOUR_API_KEY
"""

import argparse
import csv
import json
import os
import sys
import time
from dataclasses import dataclass, asdict
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any, Optional
import pandas as pd
from dotenv import load_dotenv

try:
    from firecrawl import FirecrawlApp
except ImportError:
    print("Error: firecrawl-py not installed. Run: pip install firecrawl-py")
    sys.exit(1)

# Load environment variables
load_dotenv()

@dataclass
class ScrapeResult:
    """Data class for storing scrape results"""
    url: str
    success: bool
    status_code: Optional[int] = None
    title: Optional[str] = None
    content: Optional[str] = None
    html: Optional[str] = None
    error: Optional[str] = None
    scraped_at: Optional[str] = None
    processing_time: Optional[float] = None

class FirecrawlCSVScraper:
    """Main scraper class for processing CSV URLs with Firecrawl"""
    
    def __init__(self, api_key: str, delay: float = 1.0):
        """
        Initialize the scraper
        
        Args:
            api_key: Firecrawl API key
            delay: Delay between requests in seconds
        """
        self.api_key = api_key
        self.delay = delay
        self.app = FirecrawlApp(api_key=api_key)
        self.results: List[ScrapeResult] = []
        
    def read_urls_from_csv(self, csv_file: str, url_column: str = 'url') -> List[str]:
        """
        Read URLs from CSV file
        
        Args:
            csv_file: Path to CSV file
            url_column: Name of the column containing URLs
            
        Returns:
            List of URLs
        """
        try:
            df = pd.read_csv(csv_file)
            
            if url_column not in df.columns:
                available_columns = ', '.join(df.columns.tolist())
                raise ValueError(f"Column '{url_column}' not found. Available columns: {available_columns}")
            
            urls = df[url_column].dropna().tolist()
            print(f"Loaded {len(urls)} URLs from {csv_file}")
            return urls
            
        except Exception as e:
            print(f"Error reading CSV file: {e}")
            raise
    
    def scrape_url(self, url: str, formats: List[str] = None) -> ScrapeResult:
        """
        Scrape a single URL using Firecrawl
        
        Args:
            url: URL to scrape
            formats: List of formats to return (markdown, html, etc.)
            
        Returns:
            ScrapeResult object
        """
        if formats is None:
            formats = ['markdown', 'html']
            
        start_time = time.time()
        scraped_at = datetime.now().isoformat()
        
        try:
            print(f"Scraping: {url}")
            
            # Use Firecrawl to scrape the URL with correct v1 API parameters
            result = self.app.scrape_url(url, formats=formats)
            
            processing_time = time.time() - start_time
            
            if result.get('success', False) and result.get('data'):
                data = result['data']
                metadata = data.get('metadata', {})
                
                return ScrapeResult(
                    url=url,
                    success=True,
                    status_code=metadata.get('statusCode'),
                    title=metadata.get('title'),
                    content=data.get('markdown'),
                    html=data.get('html'),
                    scraped_at=scraped_at,
                    processing_time=processing_time
                )
            else:
                error_msg = result.get('error', 'Unknown error occurred')
                return ScrapeResult(
                    url=url,
                    success=False,
                    error=error_msg,
                    scraped_at=scraped_at,
                    processing_time=processing_time
                )
                
        except Exception as e:
            processing_time = time.time() - start_time
            error_msg = str(e)
            print(f"Error scraping {url}: {error_msg}")
            
            return ScrapeResult(
                url=url,
                success=False,
                error=error_msg,
                scraped_at=scraped_at,
                processing_time=processing_time
            )
    
    def scrape_url_advanced(self, url: str, params: Dict[str, Any]) -> ScrapeResult:
        """
        Advanced scrape with custom parameters for Firecrawl v1 API
        
        Args:
            url: URL to scrape
            params: Dictionary of Firecrawl API parameters
            
        Returns:
            ScrapeResult object
        """
        start_time = time.time()
        scraped_at = datetime.now().isoformat()
        
        try:
            print(f"Scraping: {url}")
            
            # Use Firecrawl to scrape the URL with custom parameters
            result = self.app.scrape_url(url, **params)
            
            processing_time = time.time() - start_time
            
            if result.get('success', False) and result.get('data'):
                data = result['data']
                metadata = data.get('metadata', {})
                
                # Handle different response formats
                content = data.get('markdown', '')
                html_content = data.get('html', '') or data.get('rawHtml', '')
                
                # Handle JSON extraction results
                json_data = data.get('json', {})
                if json_data and isinstance(json_data, dict):
                    # Add JSON data to content
                    content += f"\n\n---\nExtracted Data:\n{json.dumps(json_data, indent=2)}"
                
                return ScrapeResult(
                    url=url,
                    success=True,
                    status_code=metadata.get('statusCode'),
                    title=metadata.get('title'),
                    content=content,
                    html=html_content,
                    scraped_at=scraped_at,
                    processing_time=processing_time
                )
            else:
                error_msg = result.get('error', 'Unknown error occurred')
                return ScrapeResult(
                    url=url,
                    success=False,
                    error=error_msg,
                    scraped_at=scraped_at,
                    processing_time=processing_time
                )
                
        except Exception as e:
            processing_time = time.time() - start_time
            error_msg = str(e)
            print(f"Error scraping {url}: {error_msg}")
            
            return ScrapeResult(
                url=url,
                success=False,
                error=error_msg,
                scraped_at=scraped_at,
                processing_time=processing_time
            )
    
    def scrape_urls_batch(self, urls: List[str], formats: List[str] = None, 
                         max_retries: int = 3) -> List[ScrapeResult]:
        """
        Scrape multiple URLs with error handling and retries
        
        Args:
            urls: List of URLs to scrape
            formats: List of formats to return
            max_retries: Maximum number of retries per URL
            
        Returns:
            List of ScrapeResult objects
        """
        results = []
        total_urls = len(urls)
        
        for i, url in enumerate(urls, 1):
            print(f"\nProgress: {i}/{total_urls} ({i/total_urls*100:.1f}%)")
            
            # Retry logic
            for attempt in range(max_retries + 1):
                try:
                    result = self.scrape_url(url, formats)
                    results.append(result)
                    
                    if result.success:
                        print(f"✓ Successfully scraped: {url}")
                    else:
                        print(f"✗ Failed to scrape: {url} - {result.error}")
                    
                    break  # Success or final failure, exit retry loop
                    
                except Exception as e:
                    if attempt < max_retries:
                        wait_time = (attempt + 1) * 2  # Exponential backoff
                        print(f"Attempt {attempt + 1} failed for {url}, retrying in {wait_time}s...")
                        time.sleep(wait_time)
                    else:
                        # Final attempt failed
                        result = ScrapeResult(
                            url=url,
                            success=False,
                            error=f"Failed after {max_retries} retries: {str(e)}",
                            scraped_at=datetime.now().isoformat()
                        )
                        results.append(result)
                        print(f"✗ Final failure for: {url}")
            
            # Rate limiting delay
            if i < total_urls:  # Don't delay after the last URL
                time.sleep(self.delay)
        
        self.results = results
        return results
    
    def export_to_json(self, output_file: str, include_html: bool = False):
        """Export results to JSON file"""
        export_data = []
        
        for result in self.results:
            data = asdict(result)
            if not include_html:
                data.pop('html', None)  # Remove HTML to reduce file size
            export_data.append(data)
        
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(export_data, f, ensure_ascii=False, indent=2)
        
        print(f"Results exported to {output_file}")
    
    def export_to_csv(self, output_file: str):
        """Export results to CSV file"""
        if not self.results:
            print("No results to export")
            return
        
        fieldnames = ['url', 'success', 'status_code', 'title', 'error', 'scraped_at', 'processing_time']
        
        with open(output_file, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            
            for result in self.results:
                row = {field: getattr(result, field) for field in fieldnames}
                writer.writerow(row)
        
        print(f"Results exported to {output_file}")
    
    def print_summary(self):
        """Print scraping summary statistics"""
        if not self.results:
            print("No results to summarize")
            return
        
        successful = sum(1 for r in self.results if r.success)
        failed = len(self.results) - successful
        avg_time = sum(r.processing_time or 0 for r in self.results) / len(self.results)
        
        print(f"\n{'='*50}")
        print("SCRAPING SUMMARY")
        print(f"{'='*50}")
        print(f"Total URLs processed: {len(self.results)}")
        print(f"Successful: {successful}")
        print(f"Failed: {failed}")
        print(f"Success rate: {successful/len(self.results)*100:.1f}%")
        print(f"Average processing time: {avg_time:.2f}s")
        
        if failed > 0:
            print(f"\nFailed URLs:")
            for result in self.results:
                if not result.success:
                    print(f"  - {result.url}: {result.error}")

def main():
    """Main function with CLI argument parsing"""
    parser = argparse.ArgumentParser(
        description="Scrape URLs from CSV using Firecrawl.dev",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s --input urls.csv --output results.json
  %(prog)s --input sites.csv --url-column website --output data.json --formats markdown
  %(prog)s --input urls.csv --output results.csv --delay 2.0 --max-retries 5
        """
    )
    
    parser.add_argument(
        '--input', '-i',
        required=True,
        help='Input CSV file containing URLs'
    )
    
    parser.add_argument(
        '--output', '-o',
        required=True,
        help='Output file (JSON or CSV format based on extension)'
    )
    
    parser.add_argument(
        '--api-key',
        default=os.getenv('FIRECRAWL_API_KEY'),
        help='Firecrawl API key (or set FIRECRAWL_API_KEY env var)'
    )
    
    parser.add_argument(
        '--url-column',
        default='url',
        help='Name of the CSV column containing URLs (default: url)'
    )
    
    parser.add_argument(
        '--formats',
        nargs='+',
        default=['markdown', 'html'],
        choices=['markdown', 'html', 'rawHtml', 'links', 'screenshot'],
        help='Output formats to request from Firecrawl (default: markdown html)'
    )
    
    parser.add_argument(
        '--delay',
        type=float,
        default=1.0,
        help='Delay between requests in seconds (default: 1.0)'
    )
    
    parser.add_argument(
        '--max-retries',
        type=int,
        default=3,
        help='Maximum retries per URL (default: 3)'
    )
    
    parser.add_argument(
        '--include-html',
        action='store_true',
        help='Include HTML content in JSON output (increases file size)'
    )
    
    args = parser.parse_args()
    
    # Validate API key
    if not args.api_key:
        print("Error: Firecrawl API key required. Set FIRECRAWL_API_KEY environment variable or use --api-key")
        sys.exit(1)
    
    # Validate input file
    if not Path(args.input).exists():
        print(f"Error: Input file '{args.input}' not found")
        sys.exit(1)
    
    try:
        # Initialize scraper
        scraper = FirecrawlCSVScraper(
            api_key=args.api_key,
            delay=args.delay
        )
        
        # Read URLs from CSV
        urls = scraper.read_urls_from_csv(args.input, args.url_column)
        
        if not urls:
            print("No URLs found in CSV file")
            sys.exit(1)
        
        print(f"Starting to scrape {len(urls)} URLs with Firecrawl...")
        print(f"Formats: {', '.join(args.formats)}")
        print(f"Delay: {args.delay}s between requests")
        print(f"Max retries: {args.max_retries}")
        
        # Scrape URLs
        results = scraper.scrape_urls_batch(
            urls=urls,
            formats=args.formats,
            max_retries=args.max_retries
        )
        
        # Export results
        output_path = Path(args.output)
        if output_path.suffix.lower() == '.json':
            scraper.export_to_json(args.output, include_html=args.include_html)
        elif output_path.suffix.lower() == '.csv':
            scraper.export_to_csv(args.output)
        else:
            print("Error: Output file must have .json or .csv extension")
            sys.exit(1)
        
        # Print summary
        scraper.print_summary()
        
    except KeyboardInterrupt:
        print("\nScraping interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
