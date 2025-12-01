import os
import subprocess
import sys

port = os.environ.get("PORT", "8080")

cmd = [
    "streamlit", 
    "run", 
    "dashboard/app.py", 
    f"--server.port={port}", 
    "--server.address=0.0.0.0"
]

print(f"Launching Streamlit on port {port}...")


try:
    subprocess.run(cmd, check=True)
except KeyboardInterrupt:
    sys.exit(0)
except Exception as e:
    print(f"Error launching app: {e}")
    sys.exit(1)