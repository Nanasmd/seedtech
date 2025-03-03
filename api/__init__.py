import sys
import os

print("Python version:", sys.version)
print("Current directory:", os.getcwd())
print("Python path:", sys.path)

try:
    from api import config, cache, parsing, scoring, workable, database, similarity
    print("All modules imported successfully")
except ImportError as e:
    print(f"Import error: {e}")
    print("Problematic module:", e.name)