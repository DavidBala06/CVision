"""Shared test fixtures."""
import sys
from pathlib import Path

# Make `backend/` importable so `from ai.guardrails import ...` works
# whether pytest is invoked from the repo root or from backend/.
BACKEND_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND_DIR))
