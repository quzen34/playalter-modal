#!/usr/bin/env python3
"""
Deploy PLAYALTER Live Streaming Platform
Complete deployment script for the live streaming version
"""

import sys
import os
import subprocess

# Set UTF-8 encoding
os.environ['PYTHONIOENCODING'] = 'utf-8'
sys.stdout.reconfigure(encoding='utf-8')
sys.stderr.reconfigure(encoding='utf-8')

# Run modal deploy for live streaming app
try:
    result = subprocess.run(
        ['modal', 'deploy', 'main_app_live_streaming.py'],
        capture_output=False,
        text=True,
        encoding='utf-8',
        errors='replace'
    )
    sys.exit(result.returncode)
except Exception as e:
    print(f"Error: {e}")
    sys.exit(1)