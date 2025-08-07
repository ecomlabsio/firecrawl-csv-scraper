#!/usr/bin/env python3
"""
Firecrawl CSV Scraper Web Application

A Flask web interface for the Firecrawl CSV URL scraper.
Features file upload, real-time progress tracking, and results download.
"""

import os
import json
import csv
import uuid
import time
from datetime import datetime
from pathlib import Path
from threading import Thread
from flask import Flask, render_template, request, jsonify, send_file, redirect, url_for, flash
from werkzeug.utils import secure_filename
from werkzeug.exceptions import RequestEntityTooLarge
import pandas as pd
from dotenv import load_dotenv

# Import our scraper classes
from firecrawl_csv_scraper import FirecrawlCSVScraper, ScrapeResult

# Load environment variables
load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv('SECRET_KEY', 'dev-secret-key-change-in-production')
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file size

# Configuration
UPLOAD_FOLDER = 'uploads'
RESULTS_FOLDER = 'results'
ALLOWED_EXTENSIONS = {'csv', 'txt'}

# Create folders if they don't exist
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(RESULTS_FOLDER, exist_ok=True)

# Global storage for job status (in production, use Redis or database)
job_status = {}

def allowed_file(filename):
    """Check if file extension is allowed"""
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def run_scraping_job(job_id, csv_file, url_column, formats, delay, max_retries, api_key, json_prompt=""):
    """Background task to run the scraping job"""
    try:
        # Update job status
        job_status[job_id]['status'] = 'running'
        job_status[job_id]['message'] = 'Initializing scraper...'
        
        # Initialize scraper
        scraper = FirecrawlCSVScraper(api_key=api_key, delay=delay)
        
        # Read URLs from CSV
        job_status[job_id]['message'] = 'Reading URLs from CSV...'
        urls = scraper.read_urls_from_csv(csv_file, url_column)
        job_status[job_id]['total_urls'] = len(urls)
        
        if not urls:
            job_status[job_id]['status'] = 'error'
            job_status[job_id]['message'] = 'No URLs found in CSV file'
            return
        
        job_status[job_id]['message'] = f'Starting to scrape {len(urls)} URLs...'
        job_status[job_id]['start_time'] = time.time()
        
        # Custom scraping with progress updates
        results = []
        total_scrape_time = 0
        
        for i, url in enumerate(urls, 1):
            # Check if job was cancelled
            if job_status[job_id].get('status') == 'cancelled':
                print(f"🛑 Job {job_id} was cancelled by user")
                job_status[job_id]['message'] = f'Job cancelled after processing {i-1}/{len(urls)} URLs'
                return
            
            job_status[job_id]['processed'] = i
            
            # Calculate ETA
            if i > 1:
                elapsed = time.time() - job_status[job_id]['start_time']
                avg_time_per_url = elapsed / (i - 1)
                remaining_urls = len(urls) - i + 1
                eta_seconds = remaining_urls * avg_time_per_url
                eta_minutes = int(eta_seconds / 60)
                job_status[job_id]['message'] = f'Scraping {i}/{len(urls)}: {url[:50]}... (ETA: {eta_minutes}m)'
            else:
                job_status[job_id]['message'] = f'Scraping {i}/{len(urls)}: {url[:50]}...'
            
            # Scrape URL with retries
            url_start_time = time.time()
            for attempt in range(max_retries + 1):
                try:
                    # Prepare scraping parameters
                    scrape_params = {'formats': formats}
                    
                    # Add JSON extraction if requested
                    if 'json' in formats and json_prompt:
                        scrape_params['json_options'] = {'prompt': json_prompt}
                    
                    result = scraper.scrape_url_advanced(url, scrape_params)
                    results.append(result)
                    
                    # Track timing
                    url_time = time.time() - url_start_time
                    total_scrape_time += url_time
                    
                    # Show results in console
                    if result.success:
                        print(f"✅ SUCCESS ({url_time:.1f}s): {url}")
                        if result.title:
                            print(f"   📄 Title: {result.title}")
                        
                        # Show extracted JSON data if available
                        if 'json' in formats and result.content and "---\nExtracted Data:" in result.content:
                            try:
                                json_part = result.content.split("---\nExtracted Data:\n")[1]
                                extracted_data = json.loads(json_part)
                                print(f"   🤖 Extracted: {json.dumps(extracted_data, indent=4)[:200]}...")
                            except:
                                print(f"   🤖 JSON extraction completed")
                        
                        # Show content preview for other formats
                        elif result.content and len(result.content.strip()) > 0:
                            preview = result.content.strip()[:150].replace('\n', ' ')
                            print(f"   📝 Content: {preview}...")
                        
                        print()  # Empty line for readability
                    else:
                        print(f"❌ FAILED ({url_time:.1f}s): {url}")
                        print(f"   ⚠️  Error: {result.error}")
                        print()
                    
                    # Log slow URLs
                    if url_time > 30:  # More than 30 seconds
                        print(f"🐌 SLOW URL ({url_time:.1f}s): {url}")
                    
                    break
                except Exception as e:
                    if attempt < max_retries:
                        time.sleep((attempt + 1) * 2)
                    else:
                        result = ScrapeResult(
                            url=url,
                            success=False,
                            error=f"Failed after {max_retries} retries: {str(e)}",
                            scraped_at=datetime.now().isoformat()
                        )
                        results.append(result)
            
            # Rate limiting delay
            if i < len(urls):
                time.sleep(delay)
        
        # Check if job was cancelled before finishing
        if job_status[job_id].get('status') == 'cancelled':
            return
            
        # Save results
        scraper.results = results
        output_file = os.path.join(RESULTS_FOLDER, f'{job_id}_results.json')
        scraper.export_to_json(output_file, include_html=True)
        
        # Update final status
        successful = sum(1 for r in results if r.success)
        total_time = time.time() - job_status[job_id]['start_time']
        avg_time_per_url = total_time / len(results) if results else 0
        
        job_status[job_id]['status'] = 'completed'
        job_status[job_id]['message'] = f'Completed! {successful}/{len(results)} URLs scraped successfully (avg: {avg_time_per_url:.1f}s per URL)'
        job_status[job_id]['results_file'] = output_file
        job_status[job_id]['successful'] = successful
        job_status[job_id]['failed'] = len(results) - successful
        job_status[job_id]['total_time'] = total_time
        job_status[job_id]['avg_time_per_url'] = avg_time_per_url
        
    except Exception as e:
        job_status[job_id]['status'] = 'error'
        job_status[job_id]['message'] = f'Error: {str(e)}'

@app.route('/')
def index():
    """Main page with upload form"""
    return render_template('index.html')

@app.route('/health')
def health_check():
    """Health check endpoint for Railway"""
    return jsonify({
        'status': 'healthy',
        'message': 'Firecrawl CSV Scraper is running',
        'port': os.getenv('PORT', 5000)
    })

@app.route('/upload', methods=['POST'])
def upload_file():
    """Handle file upload and start scraping job"""
    try:
        # Check if API key is provided
        api_key = request.form.get('api_key') or os.getenv('FIRECRAWL_API_KEY')
        if not api_key:
            flash('Firecrawl API key is required', 'error')
            return redirect(url_for('index'))
        
        # Check if file was uploaded
        if 'file' not in request.files:
            flash('No file selected', 'error')
            return redirect(url_for('index'))
        
        file = request.files['file']
        if file.filename == '':
            flash('No file selected', 'error')
            return redirect(url_for('index'))
        
        if not allowed_file(file.filename):
            flash('File type not allowed. Please upload a CSV file.', 'error')
            return redirect(url_for('index'))
        
        # Save uploaded file
        filename = secure_filename(file.filename)
        job_id = str(uuid.uuid4())
        file_path = os.path.join(UPLOAD_FOLDER, f'{job_id}_{filename}')
        file.save(file_path)
        
        # Get form parameters
        url_column = request.form.get('url_column', 'url')
        formats = request.form.getlist('formats') or ['markdown']
        delay = float(request.form.get('delay', 1.0))
        max_retries = int(request.form.get('max_retries', 3))
        json_prompt = request.form.get('json_prompt', '')
        
        # Validate CSV and column
        try:
            df = pd.read_csv(file_path)
            if url_column not in df.columns:
                flash(f'Column "{url_column}" not found. Available columns: {", ".join(df.columns)}', 'error')
                return redirect(url_for('index'))
        except Exception as e:
            flash(f'Error reading CSV file: {str(e)}', 'error')
            return redirect(url_for('index'))
        
        # Initialize job status
        job_status[job_id] = {
            'status': 'queued',
            'message': 'Job queued for processing',
            'total_urls': 0,
            'processed': 0,
            'filename': filename,
            'created_at': datetime.now().isoformat()
        }
        
        # Start background scraping job
        thread = Thread(
            target=run_scraping_job,
            args=(job_id, file_path, url_column, formats, delay, max_retries, api_key, json_prompt)
        )
        thread.start()
        
        return redirect(url_for('job_status_page', job_id=job_id))
        
    except RequestEntityTooLarge:
        flash('File too large. Maximum size is 16MB.', 'error')
        return redirect(url_for('index'))
    except Exception as e:
        flash(f'Error processing request: {str(e)}', 'error')
        return redirect(url_for('index'))

@app.route('/job/')
@app.route('/job')
def job_redirect():
    """Redirect to jobs list if no job_id provided"""
    return redirect(url_for('jobs_list'))

@app.route('/job/<job_id>')
def job_status_page(job_id):
    """Job status page with real-time updates"""
    if not job_id or job_id not in job_status:
        flash('Job not found', 'error')
        return redirect(url_for('index'))
    
    return render_template('job_status.html', job_id=job_id)

@app.route('/api/job/<job_id>/status')
def job_status_api(job_id):
    """API endpoint for job status updates"""
    if not job_id or job_id not in job_status:
        return jsonify({'error': 'Job not found'}), 404
    
    status = job_status[job_id].copy()
    
    # Calculate progress percentage
    if status.get('total_urls', 0) > 0:
        status['progress'] = int((status.get('processed', 0) / status['total_urls']) * 100)
    else:
        status['progress'] = 0
    
    return jsonify(status)

@app.route('/cancel/<job_id>', methods=['POST'])
def cancel_job(job_id):
    """Cancel a running job"""
    if not job_id or job_id not in job_status:
        return jsonify({'error': 'Job not found'}), 404
    
    job = job_status[job_id]
    if job['status'] in ['completed', 'error', 'cancelled']:
        return jsonify({'error': 'Job cannot be cancelled'}), 400
    
    # Mark job as cancelled
    job_status[job_id]['status'] = 'cancelled'
    job_status[job_id]['message'] = 'Job cancelled by user'
    
    print(f"🛑 User cancelled job {job_id}")
    
    return jsonify({'success': True, 'message': 'Job cancelled successfully'})

@app.route('/download/<job_id>')
def download_results(job_id):
    """Download results file"""
    if not job_id or job_id not in job_status:
        flash('Job not found', 'error')
        return redirect(url_for('index'))
    
    job = job_status[job_id]
    if job['status'] not in ['completed', 'cancelled'] or 'results_file' not in job:
        flash('Results not available', 'error')
        return redirect(url_for('job_status_page', job_id=job_id))
    
    return send_file(
        job['results_file'],
        as_attachment=True,
        download_name=f"firecrawl_results_{job_id}.json"
    )

@app.route('/api/jobs')
def list_jobs():
    """API endpoint to list all jobs"""
    jobs = []
    for job_id, status in job_status.items():
        jobs.append({
            'job_id': job_id,
            'status': status['status'],
            'filename': status.get('filename', ''),
            'created_at': status.get('created_at', ''),
            'total_urls': status.get('total_urls', 0),
            'processed': status.get('processed', 0)
        })
    
    # Sort by creation time (newest first)
    jobs.sort(key=lambda x: x['created_at'], reverse=True)
    return jsonify(jobs)

@app.route('/jobs')
def jobs_list():
    """Jobs list page"""
    return render_template('jobs.html')

@app.errorhandler(413)
def too_large(e):
    flash('File too large. Maximum size is 16MB.', 'error')
    return redirect(url_for('index'))

@app.errorhandler(404)
def not_found(e):
    return render_template('404.html'), 404

@app.errorhandler(500)
def server_error(e):
    return render_template('500.html'), 500

if __name__ == '__main__':
    port = int(os.getenv('PORT', 5000))
    debug = os.getenv('FLASK_ENV') == 'development'
    app.run(host='0.0.0.0', port=port, debug=debug)
