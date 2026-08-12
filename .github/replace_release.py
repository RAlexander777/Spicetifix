import os, requests, sys

GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN") or ""
if not GITHUB_TOKEN:
    print("NO_TOKEN")
    sys.exit(1)

headers = {"Authorization": f"token {GITHUB_TOKEN}", "Accept": "application/vnd.github.v3+json"}
repo = "RAlexander777/Spicetifix"

# Get release v1.0.0
r = requests.get(f"https://api.github.com/repos/{repo}/releases/tags/v1.0.0", headers=headers)
if r.status_code != 200:
    print(f"Error fetching release: {r.status_code} {r.text[:200]}")
    sys.exit(1)

release = r.json()
print(f"Release ID: {release['id']}")
print(f"Assets: {len(release.get('assets', []))}")

# Delete old assets
for asset in release.get("assets", []):
    print(f"  Deleting {asset['name']} (id: {asset['id']})...")
    del_r = requests.delete(asset["url"], headers=headers)
    print(f"    Status: {del_r.status_code}")

# Upload new zip
zip_path = "dist/Spicetifix.zip"
upload_url = release["upload_url"].replace("{?name,label}", "?name=Spicetifix.zip")
print(f"\nUploading {zip_path}...")
with open(zip_path, "rb") as f:
    upload_r = requests.post(
        upload_url,
        headers={**headers, "Content-Type": "application/zip"},
        data=f,
    )
print(f"Upload status: {upload_r.status_code}")
if upload_r.status_code in (200, 201):
    print("Success!")
else:
    print(f"Error: {upload_r.text[:300]}")
