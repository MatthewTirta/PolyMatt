"""
conftest.py - pytest configuration for PolyMatt tests.
Ensures the polymatt package is on the Python path.
"""
import sys
from pathlib import Path

# Add the project root to sys.path so that 'polymatt' can be imported
project_root = Path(__file__).parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))
