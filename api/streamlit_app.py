"""
Vercel Serverless Function Entry Point
======================================
Vercel's @vercel/python runtime expects a BaseHTTPRequestHandler class
named 'handler' (lowercase) at the module level.
"""

from http.server import BaseHTTPRequestHandler


class handler(BaseHTTPRequestHandler):
    """Vercel serverless function handler."""

    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.end_headers()
        self.wfile.write(PAGE_HTML.encode("utf-8"))

    def do_POST(self):
        self.do_GET()

    def do_HEAD(self):
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.end_headers()


PAGE_HTML = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>AI App Generator — Project Zero</title>
    <meta name="description" content="Convert natural language app requirements into structured, validated application schemas using AI.">
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&display=swap" rel="stylesheet">
    <style>
        *, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }

        body {
            font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
            background: #0a0a0f;
            color: #e4e4e7;
            min-height: 100vh;
            overflow-x: hidden;
        }

        /* Animated gradient background */
        .bg-glow {
            position: fixed; top: -50%; left: -50%;
            width: 200%; height: 200%;
            background: radial-gradient(circle at 30% 40%, rgba(79,70,229,0.12) 0%, transparent 50%),
                        radial-gradient(circle at 70% 60%, rgba(139,92,246,0.08) 0%, transparent 50%),
                        radial-gradient(circle at 50% 80%, rgba(59,130,246,0.06) 0%, transparent 40%);
            animation: bgRotate 20s linear infinite;
            z-index: 0;
        }
        @keyframes bgRotate { to { transform: rotate(360deg); } }

        .container {
            position: relative; z-index: 1;
            max-width: 860px; margin: 0 auto;
            padding: 60px 24px 80px;
        }

        /* Hero */
        .hero { text-align: center; margin-bottom: 56px; }
        .hero-icon {
            font-size: 4rem; margin-bottom: 16px;
            filter: drop-shadow(0 0 32px rgba(79,70,229,0.4));
            animation: float 3s ease-in-out infinite;
        }
        @keyframes float {
            0%,100% { transform: translateY(0); }
            50% { transform: translateY(-10px); }
        }
        .hero h1 {
            font-size: clamp(2rem, 5vw, 3rem);
            font-weight: 800;
            background: linear-gradient(135deg, #818cf8, #a78bfa, #c084fc);
            -webkit-background-clip: text; -webkit-text-fill-color: transparent;
            background-clip: text;
            line-height: 1.15; margin-bottom: 12px;
        }
        .hero p {
            font-size: 1.1rem; color: #a1a1aa;
            max-width: 540px; margin: 0 auto; line-height: 1.6;
        }

        /* Pipeline graphic */
        .pipeline {
            display: flex; align-items: center; justify-content: center;
            flex-wrap: wrap; gap: 8px;
            margin: 40px 0; padding: 24px;
            background: rgba(255,255,255,0.03);
            border: 1px solid rgba(255,255,255,0.06);
            border-radius: 16px;
        }
        .stage {
            padding: 6px 14px; border-radius: 8px;
            font-size: 0.78rem; font-weight: 600;
            background: rgba(79,70,229,0.15); color: #a5b4fc;
            border: 1px solid rgba(79,70,229,0.25);
            white-space: nowrap;
        }
        .arrow { color: #4f46e5; font-size: 1.1rem; }

        /* Cards */
        .cards { display: grid; grid-template-columns: repeat(auto-fit, minmax(260px, 1fr)); gap: 20px; margin-bottom: 48px; }
        .card {
            background: rgba(255,255,255,0.04);
            border: 1px solid rgba(255,255,255,0.07);
            border-radius: 16px; padding: 28px;
            transition: all 0.3s ease;
        }
        .card:hover {
            border-color: rgba(79,70,229,0.4);
            box-shadow: 0 8px 40px rgba(79,70,229,0.1);
            transform: translateY(-3px);
        }
        .card-icon { font-size: 1.8rem; margin-bottom: 12px; }
        .card h3 { font-size: 1.05rem; font-weight: 700; margin-bottom: 8px; color: #f4f4f5; }
        .card p { font-size: 0.88rem; color: #a1a1aa; line-height: 1.55; }
        .card code {
            display: inline-block; margin-top: 10px;
            background: rgba(0,0,0,0.4); color: #c084fc;
            padding: 6px 12px; border-radius: 6px;
            font-size: 0.82rem; font-family: 'JetBrains Mono', monospace;
        }
        .card a {
            display: inline-block; margin-top: 12px;
            color: #818cf8; font-weight: 600;
            text-decoration: none; font-size: 0.9rem;
            transition: color 0.2s;
        }
        .card a:hover { color: #a5b4fc; }

        /* CTA */
        .cta-section { text-align: center; }
        .cta-btn {
            display: inline-flex; align-items: center; gap: 8px;
            background: linear-gradient(135deg, #4f46e5, #7c3aed);
            color: #fff; font-weight: 700; font-size: 1rem;
            padding: 14px 32px; border-radius: 12px;
            text-decoration: none; border: none;
            box-shadow: 0 4px 24px rgba(79,70,229,0.35);
            transition: all 0.3s ease;
        }
        .cta-btn:hover {
            transform: translateY(-2px);
            box-shadow: 0 8px 32px rgba(79,70,229,0.5);
        }

        /* Footer */
        .footer {
            margin-top: 64px; text-align: center;
            color: #52525b; font-size: 0.8rem;
            border-top: 1px solid rgba(255,255,255,0.05);
            padding-top: 24px;
        }
        .footer a { color: #818cf8; text-decoration: none; }
    </style>
</head>
<body>
    <div class="bg-glow"></div>

    <div class="container">
        <div class="hero">
            <div class="hero-icon">🤖</div>
            <h1>AI App Generator</h1>
            <p>Convert natural language application requirements into structured, validated, executable application schemas.</p>
        </div>

        <div class="pipeline">
            <span class="stage">1 &middot; Intent Extraction</span>
            <span class="arrow">&rarr;</span>
            <span class="stage">2 &middot; System Design</span>
            <span class="arrow">&rarr;</span>
            <span class="stage">3 &middot; Schema Gen</span>
            <span class="arrow">&rarr;</span>
            <span class="stage">4 &middot; Validation</span>
            <span class="arrow">&rarr;</span>
            <span class="stage">5 &middot; Repair</span>
            <span class="arrow">&rarr;</span>
            <span class="stage">6 &middot; Simulation</span>
        </div>

        <div class="cards">
            <div class="card">
                <div class="card-icon">☁️</div>
                <h3>Streamlit Cloud (Free)</h3>
                <p>The fastest way to try the live app. Hosted on Streamlit Community Cloud with zero setup.</p>
                <a href="https://streamlit.io/cloud" target="_blank">Deploy on Streamlit &rarr;</a>
            </div>

            <div class="card">
                <div class="card-icon">🐳</div>
                <h3>Docker</h3>
                <p>Run the full app locally or deploy anywhere with Docker.</p>
                <code>docker build -t ai-app-gen .</code>
            </div>

            <div class="card">
                <div class="card-icon">💻</div>
                <h3>Local Development</h3>
                <p>Clone the repo, install deps, and run the Streamlit app locally.</p>
                <code>streamlit run frontend/app.py</code>
            </div>
        </div>

        <div class="cta-section">
            <a class="cta-btn" href="https://github.com/bishtpriyanshu08/Project-Zero" target="_blank">
                ⭐ View on GitHub
            </a>
        </div>

        <div class="footer">
            <p>Built with Python &middot; Streamlit &middot; Pydantic &middot; Gemini / OpenAI</p>
            <p style="margin-top:6px;">
                <a href="https://github.com/bishtpriyanshu08/Project-Zero">github.com/bishtpriyanshu08/Project-Zero</a>
            </p>
        </div>
    </div>
</body>
</html>"""
