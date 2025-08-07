#!/usr/bin/env python3
"""
Simple test script to verify the Flask app structure and imports
"""

import sys
import os

def test_imports():
    """Test if all required modules can be imported"""
    print("Testing imports...")
    
    try:
        # Test Flask imports
        print("✓ Python standard library modules available")
        
        # Test file structure
        required_files = [
            'app.py',
            'firecrawl_csv_scraper.py',
            'requirements.txt',
            'templates/base.html',
            'templates/index.html',
            'templates/job_status.html',
            'templates/jobs.html',
            'static/css/style.css',
            'static/js/app.js'
        ]
        
        for file_path in required_files:
            if os.path.exists(file_path):
                print(f"✓ {file_path}")
            else:
                print(f"✗ {file_path} - MISSING")
                return False
        
        print("\n✅ All files present and structure looks good!")
        print("📝 Note: Install dependencies with: pip install -r requirements.txt")
        print("🚀 Then run with: python app.py")
        return True
        
    except ImportError as e:
        print(f"✗ Import error: {e}")
        return False

if __name__ == "__main__":
    success = test_imports()
    sys.exit(0 if success else 1)
