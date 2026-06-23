"""
Vercel Serverless Function Entry Point
======================================
This module serves as the entry point for deploying the Streamlit app
on Vercel. It uses subprocess to launch the Streamlit server and 
proxies requests to it.

For Vercel deployment, the recommended approach is to use
Streamlit Community Cloud or a Docker-based deployment on Vercel.
This file provides the HTTP handler that Vercel expects.
"""

import subprocess
import os
import sys

# Set environment variables for Vercel
os.environ["VERCEL"] = "1"

# Add the project root to Python path
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)


def handler(request):
    """
    Vercel serverless function handler.
    
    Note: Streamlit apps are best deployed using:
    1. Streamlit Community Cloud (https://streamlit.io/cloud) — FREE & easiest
    2. Vercel with Docker runtime
    3. Railway, Render, or Heroku
    
    This handler provides a fallback response directing users 
    to the best deployment options.
    """
    return {
        "statusCode": 200,
        "headers": {"Content-Type": "text/html"},
        "body": """
        <!DOCTYPE html>
        <html>
        <head>
            <title>AI App Generator</title>
            <style>
                body { 
                    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
                    max-width: 800px; margin: 100px auto; padding: 20px;
                    background: #0e1117; color: #fafafa;
                }
                h1 { color: #4F46E5; }
                .card {
                    background: #1e1e2e; border-radius: 12px; padding: 24px;
                    margin: 16px 0; border: 1px solid #333;
                }
                a { color: #818cf8; }
                code { background: #2d2d3d; padding: 2px 6px; border-radius: 4px; }
            </style>
        </head>
        <body>
            <h1>🤖 AI App Generator</h1>
            <div class="card">
                <h2>Deployment Options</h2>
                <p>This Streamlit app can be deployed using:</p>
                <ol>
                    <li><strong>Streamlit Community Cloud</strong> (Recommended - Free)<br>
                        <a href="https://streamlit.io/cloud">streamlit.io/cloud</a></li>
                    <li><strong>Docker on Vercel</strong><br>
                        Use the included <code>Dockerfile</code></li>
                    <li><strong>Local Development</strong><br>
                        <code>streamlit run frontend/app.py</code></li>
                </ol>
            </div>
            <div class="card">
                <h2>Quick Start</h2>
                <pre><code>git clone https://github.com/bishtpriyanshu08/Project-Zero.git
cd Project-Zero
pip install -r requirements.txt
streamlit run frontend/app.py</code></pre>
            </div>
        </body>
        </html>
        """,
    }
