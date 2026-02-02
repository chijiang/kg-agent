import sys
import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables from backend/.env
backend_dir = Path(__file__).parent.parent / "backend"
env_file = backend_dir / ".env"
if env_file.exists():
    load_dotenv(env_file)

# Add backend directory to Python path for imports
sys.path.insert(0, str(backend_dir))
