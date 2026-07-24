from huggingface_hub import snapshot_download
from pathlib import Path

# ----------------------------------------------------
# Government Scheme Dataset Downloader
# ----------------------------------------------------

print("=" * 60)
print("Downloading Government Scheme Dataset...")
print("=" * 60)

# Create dataset directory if it doesn't exist
Path("dataset").mkdir(exist_ok=True)

snapshot_download(
    repo_id="tushkr3/gov_myscheme",
    repo_type="dataset",
    local_dir="dataset/gov_myscheme",
)

print("\n✅ Dataset downloaded successfully!")