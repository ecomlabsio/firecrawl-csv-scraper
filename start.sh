#!/bin/bash
echo "Starting Firecrawl CSV Scraper..."
echo "Port: $PORT"
echo "Python version: $(python --version)"
echo "Working directory: $(pwd)"
echo "Files: $(ls -la)"

# Start the Flask application
exec python app.py
