import sys
import os
import subprocess

# Set UTF-8 encoding
os.environ['PYTHONIOENCODING'] = 'utf-8'
sys.stdout.reconfigure(encoding='utf-8')
sys.stderr.reconfigure(encoding='utf-8')

# Run modal serve
try:
    result = subprocess.run(
        ['modal', 'deploy', 'main_app.py'],
        capture_output=False,
        text=True,
        encoding='utf-8',
        errors='replace'
    )
    sys.exit(result.returncode)
except Exception as e:
    print(f"Error: {e}")
    sys.exit(1)