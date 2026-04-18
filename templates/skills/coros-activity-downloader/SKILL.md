---
name: "coros-activity-downloader"
description: "Downloads running activity records from COROS Training Hub in FIT format. Invoke when user needs to download COROS activity data for analysis or backup."
---

# COROS Activity Downloader

## Purpose

This skill enables automated downloading of running activity records from the COROS Training Hub platform. It extracts activity data in .fit format (Fitness Information Technology) for further analysis, backup, or import into other fitness platforms like Strava, TrainingPeaks, etc.

## Architecture Overview

```
┌─────────────────────────────────────────────────────────┐
│                   Browser (Chrome DevTools MCP)          │
│  ┌───────────────────────────────────────────────────┐  │
│  │  1. Navigate to https://t.coros.com/admin/views/activities │
│  │  2. Extract activity list (labelId, name, sportType)       │
│  │  3. Return activities as JSON to executor                 │
│  └───────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────┐
│                    Download Executor                      │
│  ┌───────────────────────────────────────────────────┐  │
│  │  Primary: Python script (download_coros.py)        │  │
│  │    - UTF-8 native, handles Chinese filenames       │  │
│  │    - CLI arguments for flexible configuration      │  │
│  │    - Duplicate prevention via labelId matching     │  │
│  │    - File integrity validation                     │  │
│  ├───────────────────────────────────────────────────┤  │
│  │  Backup: PowerShell (for simple system ops only)   │  │
│  │    - Directory creation, file listing              │  │
│  └───────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────┐
│                    Download Output                        │
│  ~/.nanobot-runner/download/                              │
│    {activity_name}_{labelId}.fit                          │
└─────────────────────────────────────────────────────────┘
```

## Prerequisites and Dependencies

### System Requirements
- **Operating System**: Windows 10/11 with PowerShell 7+
- **Python**: Python 3.6+ (uses only standard library modules)
- **Browser**: Chrome browser with Chrome DevTools MCP access
- **Network**: Internet connection with access to:
  - `https://t.coros.com` (COROS Training Hub)
  - `https://teamcnapi.coros.com` (COROS API)
  - `https://oss.coros.com` (COROS file storage)

### Authentication Requirements
- Valid COROS account with logged-in session
- Browser cookies must contain valid access tokens
- Region setting must be configured (China region uses `teamcnapi.coros.com`)

### Required Tools
- Chrome DevTools MCP for browser automation
- Python 3.6+ for download operations
- Write access to target download directory

### Script Location
The download script is bundled with this skill at:
```
.trae/skills/coros-activity-downloader/scripts/download_coros.py
```

## Quick Start (Recommended Workflow)

### Step 1: Navigate to COROS Training Hub

```
mcp_Chrome_DevTools_MCP_navigate_page
  type: "url"
  url: "https://t.coros.com/admin/views/activities"
  timeout: 10000
```

### Step 2: Verify Page Load

```
mcp_Chrome_DevTools_MCP_take_snapshot
  verbose: false
```

Expected elements:
- Activity list table with columns: Date, Name, Distance, Time, Pace, Heart Rate
- Activity count indicator (e.g., "669个活动")

### Step 3: Extract Activity IDs from Browser

```javascript
// Run via mcp_Chrome_DevTools_MCP_evaluate_script
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
  
  return JSON.stringify(activities.slice(0, 15));
}
```

### Step 4: Run Python Download Script

```bash
# Basic usage: download latest 15 activities
python scripts/download_coros.py --count 15 --activities-json '<JSON_FROM_STEP_3>'

# Download specific activities by labelId
python scripts/download_coros.py --label-ids "476855911038615862,476786357002338514"

# Validate existing files without downloading
python scripts/download_coros.py --validate-only

# Output results as JSON (for programmatic use)
python scripts/download_coros.py --count 10 --activities-json '<JSON>' --json-output
```

### Step 5: Verify Results

```bash
# List downloaded files
python -c "import os; dl=os.path.expanduser('~/.nanobot-runner/download'); [print(f'{os.path.getsize(os.path.join(dl,f))/1024:8.2f} KB  {f}') for f in sorted(os.listdir(dl)) if f.endswith('.fit')]"
```

## Download Script Reference

### Location
```
.trae/skills/coros-activity-downloader/scripts/download_coros.py
```

### CLI Arguments

| Argument | Type | Default | Description |
|----------|------|---------|-------------|
| `--count` | int | 10 | Number of activities to download |
| `--sport-type` | int | 100 | Sport type filter (100=running) |
| `--download-dir` | string | `~/.nanobot-runner/download` | Target download directory |
| `--user-id` | string | (auto) | COROS user ID |
| `--label-ids` | string | None | Comma-separated labelIds (bypasses browser) |
| `--activities-json` | string | None | JSON string of activities from browser extraction |
| `--validate-only` | flag | false | Only validate existing files, skip download |
| `--json-output` | flag | false | Output results as JSON |

### Duplicate Prevention Mechanism

The script uses `labelId` as the unique identifier for duplicate detection:

1. **Scan existing files**: Parse all `.fit` files in the download directory
2. **Extract labelId**: Use the pattern `_{digits}$` at the end of filename
   - Works with ANY naming convention (Chinese, English, mixed)
   - Examples:
     - `上海市跑步_476786357002338514.fit` → `476786357002338514`
     - `Shanghai_Run_476786357002338514.fit` → `476786357002338514`
     - `476786357002338514.fit` → `476786357002338514`
3. **Compare and skip**: If labelId exists, skip download

**Key benefits**:
- O(1) lookup per file using hash set
- Independent of filename naming convention
- Handles partial downloads and interrupted sessions
- Prevents wasted bandwidth on duplicate downloads

### File Integrity Validation

After download, each file is validated:
- Minimum file size: > 1KB (1024 bytes)
- Empty file detection
- Files failing validation are flagged but not deleted

### Rate Limiting

Built-in delay of 500ms between downloads to avoid COROS server throttling.

## Error Handling

### Common Issues

#### 1. No Activities Provided
```
ERROR: No activities specified. Use --activities-json, --label-ids, or pipe activities from browser.
```
**Fix**: Extract activities from browser first (Step 3) or use `--label-ids`.

#### 2. HTTP 404 - File Not Found
**Possible causes**:
- Activity was deleted from COROS
- Incorrect userId
- File not yet processed by COROS servers

**Resolution**:
```bash
# Try alternative API endpoint
python -c "
import urllib.request, json
url = 'https://teamcnapi.coros.com/activity/detail/download?labelId=LABEL_ID&sportType=100&fileType=4'
req = urllib.request.Request(url, method='POST')
resp = json.loads(urllib.request.urlopen(req).read())
print(resp['data']['fileUrl'])
"
```

#### 3. HTTP 403 - Access Denied
**Cause**: Activity is private or session expired

**Resolution**: Refresh browser session at `https://t.coros.com/admin/views/activities`

#### 4. Network Timeout
**Resolution**: The script has built-in 30s timeout. Retries are not automatic; simply re-run the script - it will skip already-downloaded files.

#### 5. Corrupted/Small Files
Files < 1KB are flagged during validation. Delete and re-run to retry.

## Input/Output Specifications

### Activities JSON Format (from browser extraction)

```json
[
  {"labelId": "476855911038615862", "name": "恢复跑", "sportType": 100},
  {"labelId": "476786357002338514", "name": "上海市 跑步", "sportType": 100}
]
```

### Success Output (JSON mode)

```json
{
  "success": true,
  "totalCount": 15,
  "downloadedCount": 9,
  "skippedCount": 6,
  "failedCount": 0,
  "downloadDir": "C:\\Users\\yecll\\.nanobot-runner\\download",
  "totalFitFiles": 36,
  "files": [
    {
      "labelId": "476855911038615862",
      "name": "恢复跑",
      "fileName": "恢复跑_476855911038615862.fit",
      "filePath": "C:\\Users\\yecll\\.nanobot-runner\\download\\恢复跑_476855911038615862.fit",
      "fileSize": 98058,
      "fileSizeKB": 95.76,
      "downloadUrl": "https://oss.coros.com/fit/445542372294541312/476855911038615862.fit",
      "status": "success",
      "timestamp": "2026-04-17T14:30:00Z"
    }
  ],
  "skipped": [
    {"labelId": "476136986132906089", "name": "45分钟基础训练", "existingSizeKB": 103.83}
  ],
  "errors": [],
  "timestamp": "2026-04-17T14:30:15Z"
}
```

### Error Output (JSON mode)

```json
{
  "success": false,
  "totalCount": 15,
  "downloadedCount": 8,
  "skippedCount": 6,
  "failedCount": 1,
  "downloadDir": "C:\\Users\\yecll\\.nanobot-runner\\download",
  "totalFitFiles": 35,
  "files": [...],
  "skipped": [...],
  "errors": [
    {
      "labelId": "476999999999999999",
      "name": "Activity_476999999999999999",
      "error": "HTTP 404: Not Found",
      "errorCode": "DOWNLOAD_FAILED",
      "timestamp": "2026-04-17T14:30:05Z"
    }
  ],
  "timestamp": "2026-04-17T14:30:15Z"
}
```

## Success Criteria and Validation

### Primary Success Criteria

1. **File Count**: All requested activities downloaded
   - Expected: `downloadedCount == requestedCount`
   - Acceptable: `downloadedCount >= requestedCount * 0.8` (80% success rate)

2. **File Format**: All files are valid .fit format
   - Extension: `.fit`
   - Minimum size: > 1KB
   - No zero-byte files

3. **File Integrity**: Files are complete and not corrupted
   - File size matches expected range (10KB - 500KB for typical activities)
   - No duplicate downloads

### Quality Metrics

| Metric | Target | Acceptable | Critical |
|--------|--------|------------|----------|
| Success Rate | 100% | ≥ 90% | < 80% |
| Download Speed | ≥ 1 file/sec | ≥ 0.5 file/sec | < 0.2 file/sec |
| File Size Range | 10KB-500KB | 1KB-1MB | < 1KB or > 1MB |
| Corruption Rate | 0% | < 5% | ≥ 5% |

## Usage Examples

### Example 1: Basic Download (Latest 15 Running Activities)

```bash
# 1. Extract activities from browser (JavaScript)
# 2. Run download script
python scripts/download_coros.py --count 15 --activities-json '[{"labelId":"476855911038615862","name":"恢复跑","sportType":100},...]'

# Expected output:
# ==================================================
#   COROS Activity Downloader
#   Download directory: C:\Users\yecll\.nanobot-runner\download
#   Existing files: 27
# ==================================================
#
# Classification:
#   [SKIP] 45分钟基础训练 (exists: 103.83 KB)
#   [TODO] 恢复跑
#   [TODO] 上海市 跑步
#   ...
#
# Summary: 9 to download, 6 skipped, 15 total
#
# [1/9] Downloading: 恢复跑... OK (95.76 KB)
# ...
#
# ==================================================
#   Download Complete!
# ==================================================
#   Total activities:  15
#   Downloaded:        9
#   Skipped (exists):  6
#   Failed:            0
#   Total FIT files:   36
# ==================================================
```

### Example 2: Download Specific Activities

```bash
python scripts/download_coros.py --label-ids "476855911038615862,476786357002338514"
```

### Example 3: Download to Custom Directory

```bash
python scripts/download_coros.py --count 10 --activities-json '<JSON>' --download-dir "D:\COROS_Backup\2026"
```

### Example 4: Validate Without Downloading

```bash
python scripts/download_coros.py --validate-only --json-output
```

### Example 5: Programmatic Integration (JSON output)

```bash
result=$(python scripts/download_coros.py --count 10 --activities-json '<JSON>' --json-output 2>/dev/null)
downloaded=$(echo "$result" | python -c "import sys,json; print(json.load(sys.stdin)['downloadedCount'])")
echo "Downloaded $downloaded files"
```

### Example 6: Re-run After Network Interruption

Simply re-run the same command - the script automatically skips already-downloaded files:

```bash
python scripts/download_coros.py --count 15 --activities-json '<JSON>'
# Will only download the files that were not saved during the interrupted run
```

## Limitations and Edge Cases

### Known Limitations

1. **Authentication Dependency**
   - Requires active browser session with valid cookies
   - Access tokens expire and need refresh
   - Cannot download without prior login

2. **Regional Restrictions**
   - China region: Uses `oss.coros.com` for file downloads
   - Global region: May use different CDN endpoints
   - URLs and user IDs are region-specific

3. **File Access Limitations**
   - Only activities owned by the logged-in user can be downloaded
   - Private activities from other users are inaccessible
   - Deleted activities cannot be recovered

4. **Rate Limiting**
   - COROS API may throttle requests
   - Built-in 500ms delay between downloads
   - Recommended maximum: ~100 activities per minute

5. **Browser Automation Constraints**
   - Chrome DevTools MCP must be available
   - Browser must remain open during activity extraction
   - Multiple tabs may interfere with session

### Edge Cases

#### Case 1: Activity Without GPS Data
Indoor treadmill runs will still produce FIT files containing heart rate, distance (if footpod connected), time, and calories - just no GPS coordinates.

#### Case 2: Duplicate Activity Names
The script appends `labelId` to filenames to ensure uniqueness:
```
45分钟基础训练_476456369027842849.fit
45分钟基础训练_476276321308148214.fit
```

#### Case 3: Very Large Activity Files
Ultra-long activities (100+ km, 10+ hours) may produce files > 500KB. These are valid but flagged for review if > 1MB.

### Performance Considerations

1. **Download Speed**
   - Typical: 0.5-2 files per second
   - Depends on: Network speed, file size, server load

2. **Memory Usage**
   - Each file loaded into memory before saving
   - Memory footprint: ~1-2 MB per active download

3. **Storage Requirements**
   - Average activity: 50-150 KB
   - 10 activities: ~1 MB
   - 100 activities: ~10 MB

### Security Considerations

1. **Credential Protection**
   - Never hardcode access tokens in scripts
   - The download script uses only public CDN URLs (no authentication needed for own files)
   - Browser session is only used for activity list extraction

2. **File Permissions**
   - FIT files contain personal health data
   - Consider encryption for long-term storage

3. **API Usage**
   - Respect COROS terms of service
   - Rate limit requests to avoid server overload

## Script Development Notes

### Why Python Over PowerShell?

During development, PowerShell scripts faced significant issues with:
- **File encoding**: Chinese characters in activity names caused syntax errors when PowerShell parsed `.ps1` files without BOM
- **Command-line escaping**: Complex quote escaping made inline execution unreliable

Python 3.6+ was chosen because:
- Native UTF-8 support (no BOM issues)
- Standard library only (no `pip install` needed)
- Cleaner syntax for HTTP operations and JSON handling
- Cross-platform compatibility

### Script Structure

```
download_coros.py
├── Configuration (defaults)
├── setup_download_dir()     - Create directory
├── scan_existing_files()    - Duplicate detection
├── build_download_url()     - URL construction
├── sanitize_filename()      - Windows-safe filenames
├── download_file()          - HTTP download with error handling
├── validate_fit_file()      - Post-download integrity check
└── main()                   - CLI entry point
```

## Version History

| Version | Date | Changes |
|---------|------|---------|
| 1.0.0 | 2026-04-17 | Initial release |
| 1.0.1 | 2026-04-17 | Added error handling and validation |
| 1.0.2 | 2026-04-17 | Added intelligent duplicate prevention using labelId extraction |
| 2.0.0 | 2026-04-17 | **Major rewrite**: Migrated primary download engine from PowerShell to Python; bundled script with skill; added CLI argument parsing; improved duplicate detection; added JSON output mode |

## Support and Troubleshooting

For issues or questions:
1. Check error messages in Python output
2. Verify browser session is active
3. Ensure network connectivity to COROS servers
4. Review this documentation for edge cases
5. Check COROS service status

## License and Usage Terms

This skill is for personal use only. Users must:
- Have valid COROS account
- Own the activities being downloaded
- Comply with COROS Terms of Service
- Not redistribute downloaded data without permission
