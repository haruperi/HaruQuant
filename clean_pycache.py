import shutil
from pathlib import Path

def clean_pycache(start_path='.'):
    """Recursively finds and deletes all __pycache__ folders."""
    start_dir = Path(start_path).resolve()
    print(f"Scanning for __pycache__ folders in: {start_dir}\n")
    
    count = 0
    # Use rglob to find all directories named __pycache__
    for p in start_dir.rglob('__pycache__'):
        if p.is_dir():
            print(f"Deleting: {p}")
            try:
                shutil.rmtree(p)
                count += 1
            except Exception as e:
                print(f"Error deleting {p}: {e}")
                
    print(f"\nCleanup finished! Successfully removed {count} __pycache__ folders.")

if __name__ == "__main__":
    clean_pycache()
