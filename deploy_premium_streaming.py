#!/usr/bin/env python3
"""
Deploy PLAYALTER Premium Live Streaming Platform
GPU-optimized deployment with A10G and batch processing
"""

import sys
import os
import subprocess

# Set UTF-8 encoding
os.environ['PYTHONIOENCODING'] = 'utf-8'
sys.stdout.reconfigure(encoding='utf-8')
sys.stderr.reconfigure(encoding='utf-8')

print("Deploying PLAYALTER Premium Live Streaming Platform...")
print("Features: GPU-accelerated, batch processing, premium tiers, API access")

# Run modal deploy for premium streaming app
try:
    result = subprocess.run(
        ['modal', 'deploy', 'main_app_premium_streaming.py'],
        capture_output=False,
        text=True,
        encoding='utf-8',
        errors='replace'
    )
    sys.exit(result.returncode)
except Exception as e:
    print(f"Error: {e}")
    sys.exit(1)