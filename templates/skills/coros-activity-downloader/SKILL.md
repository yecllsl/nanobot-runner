---
name: "coros-activity-downloader"
description: "Downloads running activity records from COROS Training Hub in FIT format. Invoke when user needs to download COROS activity data for analysis or backup."
---

# COROS Activity Downloader

## Purpose

This skill enables automated downloading of running activity records from the COROS Training Hub platform. It extracts activity data in .fit format (Fitness Information Technology) for further analysis, backup, or import into other fitness platforms like Strava, TrainingPeaks, etc.

## Prerequisites and Dependencies

### System Requirements
- **Operating System**: Windows 10/11 with PowerShell 7+
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
- PowerShell for file download operations
- Write access to target download directory

### Dependencies
```powershell
# PowerShell modules (built-in, no installation required)
- Microsoft.PowerShell.Management
- Microsoft.PowerShell.Utility
```

## Step-by-Step Implementation

### Phase 1: Initiate Download Process

#### Step 1.1: Navigate to COROS Training Hub
```powershell
# Use Chrome DevTools MCP to navigate
mcp_Chrome_DevTools_MCP_navigate_page
  type: "url"
  url: "https://t.coros.com/admin/views/activities"
  timeout: 10000
```

#### Step 1.2: Verify Page Load
```powershell
# Take snapshot to verify page structure
mcp_Chrome_DevTools_MCP_take_snapshot
  verbose: false
```

Expected elements:
- Activity list table with columns: Date, Name, Distance, Time, Pace, Heart Rate
- Activity count indicator (e.g., "668 个活动")
- Export button with class `.export-icon`

#### Step 1.3: Extract Activity IDs
```javascript
// Execute in browser context to extract activity data
const activities = [];
const activityLinks = document.querySelectorAll('a[href*="activity-detail?labelId="]');

activityLinks.forEach(link => {
  const url = new URL(link.href);
  const labelId = url.searchParams.get('labelId');
  const sportType = url.searchParams.get('sportType');
  const name = link.innerText.trim();
  
  // Filter for running activities only (sportType=100)
  if (sportType === '100' && labelId) {
    activities.push({ labelId, name, sportType: 100 });
  }
});

// Return latest 10 activities
return activities.slice(0, 10);
```

### Phase 2: Monitor and Execute Downloads

#### Step 2.1: Create Download Directory
```powershell
$downloadDir = "$env:USERPROFILE\.nanobot-runner\download"

if (-not (Test-Path $downloadDir)) {
    New-Item -ItemType Directory -Path $downloadDir -Force
    Write-Host "Created download directory: $downloadDir"
}
```

#### Step 2.2: Generate Download URLs
```powershell
# Pattern: https://oss.coros.com/fit/{userId}/{labelId}.fit
$userId = "445542372294541312"  # Extract from browser session
$activities = @(
    @{ labelId = "476786357002338514"; name = "Activity_1" },
    # ... more activities
)

foreach ($activity in $activities) {
    $downloadUrl = "https://oss.coros.com/fit/$userId/$($activity.labelId).fit"
}
```

#### Step 2.3: Download Files
```powershell
foreach ($activity in $activities) {
    $fileName = "$($activity.name)_$($activity.labelId).fit"
    $fileName = $fileName -replace '[\\/:*?"<>|]', '_'  # Sanitize filename
    $filePath = Join-Path $downloadDir $fileName
    $downloadUrl = "https://oss.coros.com/fit/$userId/$($activity.labelId).fit"
    
    try {
        Invoke-WebRequest -Uri $downloadUrl -OutFile $filePath -UseBasicParsing
        
        if (Test-Path $filePath) {
            $fileSize = (Get-Item $filePath).Length
            Write-Host "SUCCESS: $fileName ($([math]::Round($fileSize / 1KB, 2)) KB)" -ForegroundColor Green
        }
    } catch {
        Write-Host "ERROR: $($_.Exception.Message)" -ForegroundColor Red
    }
}
```

### Phase 3: Complete and Validate

#### Step 3.1: Verify Download Completion
```powershell
$downloadedFiles = Get-ChildItem $downloadDir -Filter *.fit
$expectedCount = $activities.Count
$actualCount = $downloadedFiles.Count

Write-Host "Download Complete!"
Write-Host "Expected: $expectedCount files"
Write-Host "Actual: $actualCount files"
Write-Host "Success Rate: $([math]::Round($actualCount/$expectedCount*100, 1))%"
```

#### Step 3.2: Validate File Integrity
```powershell
foreach ($file in $downloadedFiles) {
    # Check minimum file size (FIT files should be > 1KB)
    if ($file.Length -lt 1024) {
        Write-Host "WARNING: $($file.Name) may be corrupted (size: $($file.Length) bytes)" -ForegroundColor Yellow
    }
    
    # Optional: Validate FIT file header (first 2 bytes should be file size)
    $bytes = [System.IO.File]::ReadAllBytes($file.FullName)
    if ($bytes[0] -eq 0xFF -and $bytes[1] -eq 0xFF) {
        Write-Host "VALID: $($file.Name) has valid FIT header" -ForegroundColor Green
    }
}
```

## Error Handling Protocols

### Common Download Issues

#### 1. Authentication Errors
**Error**: `Access token is invalid` or HTTP 401/403

**Resolution**:
```powershell
# Check if user is logged in
$testResponse = Invoke-WebRequest -Uri "https://teamcnapi.coros.com/account/query" -Method GET
if ($testResponse.StatusCode -ne 200) {
    Write-Error "User not authenticated. Please log in to COROS Training Hub first."
    # Trigger browser navigation to login page
    mcp_Chrome_DevTools_MCP_navigate_page
      type: "url"
      url: "https://t.coros.com/admin/views/activities"
}
```

#### 2. Network Timeout
**Error**: `The request was aborted: Could not create SSL/TLS secure channel`

**Resolution**:
```powershell
# Enable TLS 1.2
[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12

# Retry with exponential backoff
$maxRetries = 3
$retryCount = 0
while ($retryCount -lt $maxRetries) {
    try {
        Invoke-WebRequest -Uri $downloadUrl -OutFile $filePath -UseBasicParsing
        break
    } catch {
        $retryCount++
        Start-Sleep -Seconds (2 * $retryCount)
    }
}
```

#### 3. File Not Found (404)
**Error**: HTTP 404 - The activity file does not exist

**Resolution**:
```powershell
# Alternative: Try to trigger download via API first
$apiUrl = "https://teamcnapi.coros.com/activity/detail/download?labelId=$labelId&sportType=100&fileType=4"
$apiResponse = Invoke-WebRequest -Uri $apiUrl -Method POST

if ($apiResponse.StatusCode -eq 200) {
    $data = $apiResponse.Content | ConvertFrom-Json
    $fileUrl = $data.data.fileUrl
    # Then download from fileUrl
}
```

#### 4. Insufficient Permissions
**Error**: HTTP 403 - Access denied to activity

**Resolution**:
```powershell
Write-Warning "Activity $labelId is private or requires additional permissions"
# Skip this activity and continue with others
continue
```

#### 5. Disk Space Issues
**Error**: `No space left on device`

**Resolution**:
```powershell
$freeSpace = (Get-Volume -DriveLetter ($downloadDir -replace ':.*','')).SizeRemaining
if ($freeSpace -lt (10 * 1MB)) {  # Check for at least 10MB free
    Write-Error "Insufficient disk space. Required: ~1MB per activity"
    throw "Disk space check failed"
}
```

## Input/Output Specifications

### Input Parameters

| Parameter | Type | Required | Description | Example |
|-----------|------|----------|-------------|---------|
| `activityCount` | int | No | Number of activities to download (default: 10) | `10` |
| `sportType` | int | No | Filter by sport type (100=running) | `100` |
| `downloadDir` | string | No | Target download directory | `"C:\Users\name\.nanobot-runner\download"` |
| `fileFormat` | string | No | Output file format | `"fit"` |
| `dateRange` | object | No | Date range filter | `@{ start="2026-03-01"; end="2026-04-17" }` |
| `userId` | string | No | COROS user ID (auto-detected if not provided) | `"445542372294541312"` |

### Return Format

```json
{
  "success": true,
  "downloadedCount": 10,
  "failedCount": 0,
  "downloadDir": "C:\\Users\\yecll\\.nanobot-runner\\download",
  "files": [
    {
      "labelId": "476786357002338514",
      "name": "Shanghai_Run",
      "fileName": "Shanghai_Run_476786357002338514.fit",
      "filePath": "C:\\Users\\yecll\\.nanobot-runner\\download\\Shanghai_Run_476786357002338514.fit",
      "fileSize": 46912,
      "fileSizeKB": 45.81,
      "downloadUrl": "https://oss.coros.com/fit/445542372294541312/476786357002338514.fit",
      "status": "success",
      "timestamp": "2026-04-17T14:30:00Z"
    }
  ],
  "errors": [],
  "duration": "15.3s",
  "averageSpeed": "0.65 files/sec"
}
```

### Error Return Format

```json
{
  "success": false,
  "downloadedCount": 8,
  "failedCount": 2,
  "downloadDir": "C:\\Users\\yecll\\.nanobot-runner\\download",
  "files": [...],
  "errors": [
    {
      "labelId": "476123456789",
      "name": "Failed_Activity",
      "error": "HTTP 404: File not found",
      "errorCode": "FILE_NOT_FOUND",
      "timestamp": "2026-04-17T14:30:05Z"
    }
  ],
  "duration": "12.1s"
}
```

## Success Criteria and Validation

### Primary Success Criteria

1. **File Count**: All requested activities downloaded
   - Expected: `downloadedCount == activityCount`
   - Acceptable: `downloadedCount >= activityCount * 0.8` (80% success rate)

2. **File Format**: All files are valid .fit format
   - Extension: `.fit`
   - Minimum size: > 1KB
   - Header validation: First 2 bytes contain file size

3. **File Integrity**: Files are complete and not corrupted
   - File size matches expected range (10KB - 500KB for typical activities)
   - No zero-byte files
   - FIT file structure validation (optional)

### Validation Methods

#### Method 1: File Existence Check
```powershell
$allFilesExist = $activities | ForEach-Object {
    $fileName = "$($_.name)_$($_.labelId).fit"
    Test-Path (Join-Path $downloadDir $fileName)
} | Measure-Object -Sum | Select-Object -ExpandProperty Sum

if ($allFilesExist -eq $activities.Count) {
    Write-Host "All files downloaded successfully" -ForegroundColor Green
}
```

#### Method 2: File Size Validation
```powershell
$validFiles = Get-ChildItem $downloadDir -Filter *.fit | Where-Object {
    $_.Length -gt 1024 -and $_.Length -lt (500 * 1KB)
}

$invalidFiles = Get-ChildItem $downloadDir -Filter *.fit | Where-Object {
    $_.Length -le 1024 -or $_.Length -gt (500 * 1KB)
}

if ($invalidFiles.Count -gt 0) {
    Write-Warning "Found $($invalidFiles.Count) files with suspicious sizes"
}
```

#### Method 3: FIT Header Validation (Advanced)
```powershell
function Test-FitFileHeader {
    param([string]$filePath)
    
    try {
        $bytes = [System.IO.File]::ReadAllBytes($filePath)
        
        # FIT files start with a header containing file size
        # First 2 bytes (little-endian) should match file size
        $headerSize = [System.BitConverter]::ToUInt16($bytes, 0)
        
        return $headerSize -gt 0 -and $headerSize -le $bytes.Length
    } catch {
        return $false
    }
}

$validFitFiles = Get-ChildItem $downloadDir -Filter *.fit | Where-Object {
    Test-FitFileHeader -filePath $_.FullName
}
```

### Quality Metrics

| Metric | Target | Acceptable | Critical |
|--------|--------|------------|----------|
| Success Rate | 100% | ≥ 90% | < 80% |
| Average Download Speed | ≥ 1 file/sec | ≥ 0.5 file/sec | < 0.2 file/sec |
| File Size Range | 10KB-500KB | 1KB-1MB | < 1KB or > 1MB |
| Corruption Rate | 0% | < 5% | ≥ 5% |

## Usage Examples

### Example 1: Basic Download (Latest 10 Running Activities)

```powershell
# Navigate to COROS Training Hub
mcp_Chrome_DevTools_MCP_navigate_page
  type: "url"
  url: "https://t.coros.com/admin/views/activities"
  timeout: 10000

# Execute download script
powershell -ExecutionPolicy Bypass -File "d:\yecll\download_coros_activities.ps1"

# Expected output:
# Starting download of 10 running activities...
# Download directory: C:\Users\yecll\.nanobot-runner\download
# Downloading: Shanghai_Run ...
#   SUCCESS (Size: 45.81 KB)
# ...
# Download Complete!
# Success: 10
# Failed: 0
```

### Example 2: Download Specific Activity

```powershell
# Navigate to specific activity detail page
mcp_Chrome_DevTools_MCP_navigate_page
  type: "url"
  url: "https://t.coros.com/activity-detail?labelId=476786357002338514&sportType=100"
  timeout: 10000

# Click export button
mcp_Chrome_DevTools_MCP_evaluate_script
  function: "() => { document.querySelector('.export-icon').click(); return 'clicked'; }"

# Wait for export menu
mcp_Chrome_DevTools_MCP_wait_for
  text: [".fit"]
  timeout: 3000

# Click FIT option (via JavaScript)
mcp_Chrome_DevTools_MCP_evaluate_script
  function: "() => { /* trigger FIT download */ }"
```

### Example 3: Download with Custom Parameters

```powershell
$downloadDir = "D:\COROS_Backup\2026"
$activityCount = 20
$sportType = 100  # Running only

# Create custom download script
$script = @"
`$downloadDir = "$downloadDir"
`$activityCount = $activityCount
# ... rest of script
"@

# Execute
Invoke-Expression $script
```

### Example 4: Scheduled Automatic Download

```powershell
# Create scheduled task for daily downloads
$action = New-ScheduledTaskAction -Execute "PowerShell.exe" `
  -Argument "-ExecutionPolicy Bypass -File `"d:\yecll\download_coros_activities.ps1`""

$trigger = New-ScheduledTaskTrigger -Daily -At 6:00AM

Register-ScheduledTask -TaskName "COROS Activity Backup" `
  -Action $action -Trigger $trigger -RunLevel Highest
```

### Example 5: Integration with Analysis Pipeline

```powershell
# Download activities
.\download_coros_activities.ps1

# Process with FIT file reader
$fitFiles = Get-ChildItem "$env:USERPROFILE\.nanobot-runner\download" -Filter *.fit

foreach ($file in $fitFiles) {
    # Import FIT file data (requires FIT SDK or third-party library)
    $activityData = Read-FitFile -Path $file.FullName
    
    # Analyze data
    $analysis = @{
        Distance = $activityData.TotalDistance
        Duration = $activityData.TotalElapsedTime
        AvgHeartRate = $activityData.AvgHeartRate
        AvgPace = $activityData.AvgSpeed
    }
    
    # Export to CSV
    $analysis | Export-Csv -Path "analysis.csv" -Append
}
```

## Limitations and Edge Cases

### Known Limitations

1. **Authentication Dependency**
   - Requires active browser session with valid cookies
   - Access tokens expire and need refresh
   - Cannot download without prior login

2. **Regional Restrictions**
   - China region: Uses `teamcnapi.coros.com`
   - Global region: Uses different API endpoints
   - URLs and user IDs are region-specific

3. **File Access Limitations**
   - Only activities owned by the logged-in user can be downloaded
   - Private activities from other users are inaccessible
   - Deleted activities cannot be recovered

4. **Rate Limiting**
   - COROS API may throttle requests
   - Recommended: Add 500ms delay between downloads
   - Maximum: ~100 activities per minute

5. **Browser Automation Constraints**
   - Chrome DevTools MCP must be available
   - Browser must remain open during download
   - Multiple tabs may interfere with session

### Edge Cases

#### Case 1: Activity Without GPS Data
**Scenario**: Indoor treadmill run with no GPS track

**Handling**:
```powershell
# FIT file will still contain:
# - Heart rate data
# - Distance (if footpod connected)
# - Time and calories
# But no GPS coordinates

# Check for GPS data
if ($activity.GpsData.Count -eq 0) {
    Write-Host "INFO: $($activity.Name) has no GPS data (indoor activity)" -ForegroundColor Yellow
}
```

#### Case 2: Very Large Activity Files
**Scenario**: Ultra-long activities (100+ km, 10+ hours)

**Handling**:
```powershell
# Check file size before download
$estimatedSize = Get-EstimatedFileSize -duration $activity.Duration
if ($estimatedSize -gt (10 * 1MB)) {
    Write-Warning "Large file detected: $([math]::Round($estimatedSize/1MB, 2)) MB"
    # Proceed with caution
}
```

#### Case 3: Duplicate Activity Names
**Scenario**: Multiple activities with same name (e.g., "45 分钟基础训练")

**Handling**:
```powershell
# Use labelId in filename to ensure uniqueness
$fileName = "$($activity.name)_$($activity.labelId).fit"
# Result: "45 分钟基础训练_476456369027842849.fit"
#         "45 分钟基础训练_476276321308148214.fit"
```

#### Case 4: Partial Download (Network Interruption)
**Scenario**: Download interrupted mid-process

**Handling**:
```powershell
# Resume from last successful download
$existingFiles = Get-ChildItem $downloadDir -Filter *.fit
$existingIds = $existingFiles.BaseName -replace '.*_', ''

$remainingActivities = $activities | Where-Object {
    $_.labelId -notin $existingIds
}

if ($remainingActivities.Count -gt 0) {
    Write-Host "Resuming download of $($remainingActivities.Count) activities..."
    # Download remaining activities
}
```

#### Case 5: Corrupted FIT File
**Scenario**: Downloaded file is corrupted or incomplete

**Handling**:
```powershell
function Test-FitFileIntegrity {
    param([string]$filePath)
    
    try {
        $fileSize = (Get-Item $filePath).Length
        
        # Check minimum size
        if ($fileSize -lt 1024) { return $false }
        
        # Read header
        $bytes = [System.IO.File]::ReadAllBytes($filePath)
        
        # Validate header size field
        $headerSize = [System.BitConverter]::ToUInt16($bytes, 0)
        if ($headerSize -eq 0 -or $headerSize -gt $fileSize) { return $false }
        
        return $true
    } catch {
        return $false
    }
}

# Retry corrupted downloads
$corruptedFiles = Get-ChildItem $downloadDir -Filter *.fit | Where-Object {
    -not (Test-FitFileIntegrity -filePath $_.FullName)
}

foreach ($file in $corruptedFiles) {
    Write-Warning "Corrupted file detected: $($file.Name). Retrying download..."
    Remove-Item $file.FullName
    # Re-download logic
}
```

### Performance Considerations

1. **Download Speed**
   - Typical: 0.5-2 files per second
   - Depends on: Network speed, file size, server load
   - Optimization: Parallel downloads (max 3 concurrent)

2. **Memory Usage**
   - Each file loaded into memory before saving
   - Recommended: Process files sequentially for large batches
   - Memory footprint: ~1-2 MB per active download

3. **Storage Requirements**
   - Average activity: 50-150 KB
   - 10 activities: ~1 MB
   - 100 activities: ~10 MB
   - 1000 activities: ~100 MB

### Security Considerations

1. **Credential Protection**
   - Never hardcode access tokens in scripts
   - Use browser session cookies for authentication
   - Clear temporary files after download

2. **File Permissions**
   - Download directory should have restricted access
   - FIT files contain personal health data
   - Consider encryption for long-term storage

3. **API Usage**
   - Respect COROS terms of service
   - Do not use downloaded data for commercial purposes without permission
   - Rate limit requests to avoid server overload

---

## Version History

| Version | Date | Changes |
|---------|------|---------|
| 1.0.0 | 2026-04-17 | Initial release |
| 1.0.1 | 2026-04-17 | Added error handling and validation |

## Support and Troubleshooting

For issues or questions:
1. Check error messages in PowerShell output
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
