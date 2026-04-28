#!/usr/bin/env python3
"""
COROS Activity Downloader

Downloads running activity records from COROS Training Hub in FIT format.
Supports duplicate prevention, file integrity validation, and configurable parameters.

Usage:
    python download_coros.py --count 15 --sport-type 100
    python download_coros.py --label-ids 476855911038615862,476786357002338514
    python download_coros.py --validate-only
"""

import argparse
import json
import os
import sys
import time
from datetime import datetime
from urllib.request import Request, urlopen
from urllib.error import URLError, HTTPError


# ============================================================
# Configuration (can be overridden by CLI arguments)
# ============================================================
DEFAULT_USER_ID = "445542372294541312"
DEFAULT_DOWNLOAD_DIR = os.path.expanduser("D:/yecll/Downloads/coros/test-fit-files")
DEFAULT_SPORT_TYPE = 100  # 100 = Running
DEFAULT_COUNT = 10
DOWNLOAD_DELAY_MS = 500
MIN_FILE_SIZE = 1024  # 1KB
USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"


def setup_download_dir(path):
    """Create download directory if it doesn't exist."""
    os.makedirs(path, exist_ok=True)
    return path


def scan_existing_files(download_dir):
    """
    Scan existing FIT files and extract their labelIds.
    
    Uses regex-like logic to extract labelId from filenames.
    Handles ANY naming convention: Chinese, English, mixed.
    
    Examples:
        "上海市跑步_476786357002338514.fit" -> "476786357002338514"
        "Shanghai_Run_476786357002338514.fit" -> "476786357002338514"
        "476786357002338514.fit" -> "476786357002338514"
    
    Returns:
        dict: {labelId: {"filename": ..., "size": ..., "size_kb": ...}}
    """
    existing = {}
    try:
        files = [f for f in os.listdir(download_dir) if f.endswith('.fit')]
    except FileNotFoundError:
        return existing
    
    for f in files:
        base = f.replace('.fit', '')
        if '_' in base:
            # Extract last segment after underscore (the labelId)
            lid = base.rsplit('_', 1)[-1]
            if lid.isdigit():
                fpath = os.path.join(download_dir, f)
                size = os.path.getsize(fpath)
                existing[lid] = {
                    "filename": f,
                    "size": size,
                    "size_kb": round(size / 1024, 2)
                }
        elif base.isdigit():
            # File is just labelId.fit
            fpath = os.path.join(download_dir, f)
            size = os.path.getsize(fpath)
            existing[base] = {
                "filename": f,
                "size": size,
                "size_kb": round(size / 1024, 2)
            }
    
    return existing


def build_download_url(user_id, label_id):
    """Build the download URL for a FIT file."""
    return f"https://oss.coros.com/fit/{user_id}/{label_id}.fit"


def sanitize_filename(name):
    """Remove or replace characters invalid in Windows filenames."""
    for ch in r'\/:*?"<>|':
        name = name.replace(ch, '_')
    return name


def download_file(url, filepath):
    """
    Download a file from URL to filepath.
    
    Returns:
        tuple: (success: bool, size_bytes: int, error_msg: str)
    """
    try:
        req = Request(url, headers={'User-Agent': USER_AGENT})
        with urlopen(req, timeout=30) as response, open(filepath, 'wb') as out_file:
            data = response.read()
            out_file.write(data)
        return True, os.path.getsize(filepath), ""
    except HTTPError as e:
        return False, 0, f"HTTP {e.code}: {e.reason}"
    except URLError as e:
        return False, 0, f"URL Error: {e.reason}"
    except Exception as e:
        return False, 0, str(e)


def validate_fit_file(filepath):
    """
    Basic FIT file integrity check.
    
    Checks:
        - File size >= MIN_FILE_SIZE
        - File is not empty
    
    Returns:
        tuple: (valid: bool, issues: list[str])
    """
    issues = []
    size = os.path.getsize(filepath)
    
    if size == 0:
        issues.append("File is empty")
    elif size < MIN_FILE_SIZE:
        issues.append(f"File too small ({size} bytes, minimum {MIN_FILE_SIZE})")
    
    return len(issues) == 0, issues


def get_activities_from_browser(count=10):
    """
    Placeholder: In actual usage, extract activity list from browser
    using Chrome DevTools MCP evaluate_script.
    
    This function documents the JavaScript extraction pattern.
    
    JavaScript to run in browser:
    ```javascript
    () => {
      const activities = [];
      const links = document.querySelectorAll('a[href*="activity-detail?labelId="]');
      
      links.forEach(link => {
        const url = new URL(link.href);
        const labelId = url.searchParams.get('labelId');
        const sportType = url.searchParams.get('sportType');
        
        if (sportType === '100' && labelId) {
          const nameLink = link.closest('tr')?.querySelector('a[href*="activity-detail"]');
          const name = nameLink ? nameLink.innerText.trim() : 'Running';
          
          if (!activities.find(a => a.labelId === labelId)) {
            activities.push({ labelId, name: name || 'Running', sportType: 100 });
          }
        }
      });
      
      return activities.slice(0, 15);
    }
    ```
    
    Returns the activities JSON that would be returned by the browser.
    """
    # This is a documentation placeholder. Actual data comes from browser extraction.
    return []


def main():
    parser = argparse.ArgumentParser(description='COROS Activity Downloader')
    parser.add_argument('--count', type=int, default=DEFAULT_COUNT,
                        help=f'Number of activities to download (default: {DEFAULT_COUNT})')
    parser.add_argument('--sport-type', type=int, default=DEFAULT_SPORT_TYPE,
                        help=f'Sport type filter (100=running, default: {DEFAULT_SPORT_TYPE})')
    parser.add_argument('--download-dir', type=str, default=DEFAULT_DOWNLOAD_DIR,
                        help=f'Download directory (default: {DEFAULT_DOWNLOAD_DIR})')
    parser.add_argument('--user-id', type=str, default=DEFAULT_USER_ID,
                        help='COROS user ID')
    parser.add_argument('--label-ids', type=str, default=None,
                        help='Comma-separated list of labelIds to download (bypasses browser extraction)')
    parser.add_argument('--activities-json', type=str, default=None,
                        help='JSON string of activities array (from browser extraction)')
    parser.add_argument('--validate-only', action='store_true',
                        help='Only validate existing files, do not download')
    parser.add_argument('--json-output', action='store_true',
                        help='Output results as JSON')
    
    args = parser.parse_args()
    
    download_dir = setup_download_dir(args.download_dir)
    
    # Step 1: Scan existing files
    existing = scan_existing_files(download_dir)
    
    if args.json_output:
        print(f"Scanned {len(existing)} existing FIT files", file=sys.stderr)
    else:
        print(f"\n{'='*50}")
        print(f"  COROS Activity Downloader")
        print(f"  Download directory: {download_dir}")
        print(f"  Existing files: {len(existing)}")
        print(f"{'='*50}\n")
    
    # Step 2: Determine activities to download
    activities = []
    
    if args.activities_json:
        # Use activities provided as JSON (from browser extraction)
        activities = json.loads(args.activities_json)
    elif args.label_ids:
        # Use explicit labelId list
        for lid in args.label_ids.split(','):
            lid = lid.strip()
            if lid:
                activities.append({"labelId": lid, "name": f"Activity_{lid}", "sportType": args.sport_type})
    else:
        print("ERROR: No activities specified. Use --activities-json, --label-ids, or pipe activities from browser.",
              file=sys.stderr)
        sys.exit(1)
    
    # Step 3: Classify - to download vs already exists
    to_download = []
    skipped = []
    
    for act in activities:
        lid = act["labelId"]
        if lid in existing:
            skipped.append({**act, "existing_size_kb": existing[lid]["size_kb"]})
        else:
            to_download.append(act)
    
    if not args.json_output:
        print(f"Classification:")
        for s in skipped:
            print(f"  [SKIP] {s['name']} (exists: {s.get('existing_size_kb', '?')} KB)")
        for t in to_download:
            print(f"  [TODO] {t['name']}")
        print(f"\nSummary: {len(to_download)} to download, {len(skipped)} skipped, {len(activities)} total\n")
    
    # Step 4: Validate-only mode
    if args.validate_only:
        if args.json_output:
            result = {
                "success": True,
                "mode": "validate_only",
                "existingCount": len(existing),
                "files": [
                    {"labelId": lid, **info}
                    for lid, info in existing.items()
                ]
            }
            print(json.dumps(result, indent=2, ensure_ascii=False))
        return
    
    # Step 5: Download files
    downloaded = []
    failed = []
    
    for i, act in enumerate(to_download):
        lid = act["labelId"]
        name = act.get("name", f"Activity_{lid}") or f"Activity_{lid}"
        url = build_download_url(args.user_id, lid)
        filename = sanitize_filename(f"{name}_{lid}.fit")
        filepath = os.path.join(download_dir, filename)
        
        if not args.json_output:
            print(f"[{i+1}/{len(to_download)}] Downloading: {name}...", end=" ")
        
        success, size, error = download_file(url, filepath)
        
        if success:
            is_valid, issues = validate_fit_file(filepath)
            if is_valid:
                downloaded.append({
                    "labelId": lid,
                    "name": name,
                    "fileName": filename,
                    "filePath": filepath,
                    "fileSize": size,
                    "fileSizeKB": round(size / 1024, 2),
                    "downloadUrl": url,
                    "status": "success",
                    "timestamp": datetime.utcnow().isoformat() + "Z"
                })
                if not args.json_output:
                    print(f"OK ({size/1024:.2f} KB)")
            else:
                failed.append({
                    "labelId": lid,
                    "name": name,
                    "error": f"Validation failed: {'; '.join(issues)}",
                    "errorCode": "VALIDATION_FAILED",
                    "timestamp": datetime.utcnow().isoformat() + "Z"
                })
                if not args.json_output:
                    print(f"WARNING: {'; '.join(issues)}")
        else:
            failed.append({
                "labelId": lid,
                "name": name,
                "error": error,
                "errorCode": "DOWNLOAD_FAILED",
                "timestamp": datetime.utcnow().isoformat() + "Z"
            })
            if not args.json_output:
                print(f"FAILED: {error}")
        
        # Delay to avoid rate limiting
        time.sleep(DOWNLOAD_DELAY_MS / 1000)
    
    # Step 6: Final summary
    total_fit = len([f for f in os.listdir(download_dir) if f.endswith('.fit')])
    
    if args.json_output:
        result = {
            "success": len(failed) == 0,
            "totalCount": len(activities),
            "downloadedCount": len(downloaded),
            "skippedCount": len(skipped),
            "failedCount": len(failed),
            "downloadDir": download_dir,
            "totalFitFiles": total_fit,
            "files": downloaded,
            "skipped": [
                {"labelId": s["labelId"], "name": s["name"], "existingSizeKB": s.get("existing_size_kb")}
                for s in skipped
            ],
            "errors": failed,
            "timestamp": datetime.utcnow().isoformat() + "Z"
        }
        print(json.dumps(result, indent=2, ensure_ascii=False))
    else:
        print(f"\n{'='*50}")
        print(f"  Download Complete!")
        print(f"{'='*50}")
        print(f"  Total activities:  {len(activities)}")
        print(f"  Downloaded:        {len(downloaded)}")
        print(f"  Skipped (exists):  {len(skipped)}")
        print(f"  Failed:            {len(failed)}")
        print(f"  Total FIT files:   {total_fit}")
        print(f"{'='*50}")
        
        if failed:
            print(f"\nFailed downloads:")
            for f_item in failed:
                print(f"  - {f_item['name']} ({f_item['labelId']}): {f_item['error']}")


if __name__ == '__main__':
    main()
