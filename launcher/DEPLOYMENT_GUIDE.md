# Deployment Guide - Meeting Whisperer Windows Application

Complete guide for distributing your Meeting Whisperer application to end users.

## Distribution Options

### Option 1: Windows Installer (Recommended)

Best for end users - professional installation experience.

**File**: `launcher/output/MeetingWhisperer-Setup-1.0.0.exe`

**Advantages**:
- Professional installer wizard
- Auto-creates Start Menu shortcuts
- Easy uninstall through Control Panel
- Users keep their data on update
- Can set to run at startup

**Distribution**:
```bash
# Upload to:
- Your website download page
- GitHub Releases
- Cloud storage (OneDrive, Google Drive, etc.)

# Share link with users
# Users download and run installer
```

### Option 2: Portable Executable (Lightweight)

Archive the standalone executable for portability.

**File**: `launcher/dist/MeetingWhisperer/MeetingWhisperer.exe` (and all files)

**Advantages**:
- No installation required
- Can run from USB drive
- Works on systems without admin rights
- Minimal setup

**Distribution**:
```bash
# Create zip archive
cd launcher\dist
powershell Compress-Archive -Path MeetingWhisperer -DestinationPath MeetingWhisperer-Portable.zip -Force

# Upload MeetingWhisperer-Portable.zip
# Users extract and run MeetingWhisperer.exe
```

### Option 3: Cloud Deployment (Advanced)

Host on cloud platforms for automatic updates.

**Platforms**:
- Microsoft Store (requires app submission)
- Scoop (package manager)
- Winget (Windows Package Manager)

## Pre-Deployment Checklist

### Testing Checklist

- [ ] Executable runs on fresh Windows 10/11 system
- [ ] Frontend loads correctly
- [ ] Backend starts and responds
- [ ] Audio recording works
- [ ] Transcription works
- [ ] File operations (save, load) work
- [ ] Database persists between restarts
- [ ] Uninstall is clean (no leftover files)
- [ ] Installer creates proper shortcuts
- [ ] Works on system without development tools installed

### Version Control

Ensure before deployment:
- [ ] Version updated in `app_launcher.py` (APP_NAME or version var)
- [ ] Version updated in `installer.iss` (#define MyAppVersion)
- [ ] CHANGELOG updated with new features
- [ ] README updated if needed
- [ ] Dependencies updated to latest stable
- [ ] All tests pass

### Security

- [ ] No hardcoded passwords or tokens
- [ ] API keys use environment variables only
- [ ] Database connection secured
- [ ] No debug information in production build
- [ ] Code reviewed for security issues

## Building Release Version

### Clean Build

```bash
# Clean previous builds
cd launcher
rmdir /s /q build dist output
rmdir /s /q ..\frontend\node_modules ..\frontend\dist

# Fresh install and build
quickbuild.bat
```

### Build with Specific Version

```batch
@echo off
REM Update version before building
set VERSION=1.2.0

REM Update app_launcher.py
REM Update installer.iss

REM Then build
pyinstaller --clean app_launcher.spec
```

### Code Signing (Optional but Recommended)

```bash
# Sign the executable
signtool sign /f certificate.pfx /p password /tr http://timestamp.example.com /td sha256 ^
    launcher/dist/MeetingWhisperer/MeetingWhisperer.exe

# Sign the installer
signtool sign /f certificate.pfx /p password /tr http://timestamp.example.com /td sha256 ^
    launcher/output/MeetingWhisperer-Setup-1.0.0.exe
```

### Create Checksum

```bash
# Create SHA256 hash for integrity verification
certutil -hashfile launcher/output/MeetingWhisperer-Setup-1.0.0.exe SHA256 > MeetingWhisperer-Setup-1.0.0.exe.sha256

# Users can verify:
certutil -hashfile downloaded-installer.exe SHA256
# Compare with .sha256 file
```

## Installer Distribution

### Website

1. Create download page with:
   - App description
   - Installation instructions
   - System requirements
   - Screenshots
   - Version history
   - Checksum for verification

2. Add download links:
```html
<a href="https://your-site.com/downloads/MeetingWhisperer-Setup-1.0.0.exe">
  Download Meeting Whisperer (v1.0.0)
</a>

Checksum (SHA256):
<code>abc123...</code>
```

### GitHub Releases

```bash
# Create release on GitHub
git tag v1.0.0
git push origin v1.0.0

# Then upload to GitHub Releases:
# 1. Go to Releases page
# 2. Create new release
# 3. Upload files:
#    - MeetingWhisperer-Setup-1.0.0.exe
#    - MeetingWhisperer-Setup-1.0.0.exe.sha256
#    - MeetingWhisperer-Portable.zip (optional)
# 4. Add release notes
```

### Package Managers

#### Windows Package Manager (Winget)

```yaml
# Create manifests/MeetingWhisperer.yaml
PackageIdentifier: YourOrg.MeetingWhisperer
PackageVersion: 1.0.0
PackageName: Meeting Whisperer
Publisher: Your Organization
License: Your License
Homepage: https://github.com/yourusername/meeting-whisperer
Installers:
- Architecture: x64
  InstallerType: inno
  InstallerUrl: https://your-site.com/MeetingWhisperer-Setup-1.0.0.exe
  InstallerSha256: abc123...
```

Submit to: https://github.com/microsoft/winget-pkgs

#### Scoop

```json
{
  "version": "1.0.0",
  "description": "AI-powered meeting transcription with speaker diarization",
  "homepage": "https://github.com/yourusername/meeting-whisperer",
  "license": "MIT",
  "url": "https://your-site.com/MeetingWhisperer-Setup-1.0.0.exe",
  "hash": "sha256:abc123...",
  "installer": {
    "script": [
      "$installPath = \"$env:PROGRAMFILES\\Meeting Whisperer\"",
      "Start-Process $file -ArgumentList @(\"/S\", \"/D=$installPath\") -Wait"
    ]
  }
}
```

Create a fork at: https://github.com/ScoopInstaller/Extras

## Updates and Versioning

### Semantic Versioning

Use format: `MAJOR.MINOR.PATCH` (e.g., 1.2.3)

- **MAJOR**: Major features or breaking changes
- **MINOR**: New features (backwards compatible)
- **PATCH**: Bug fixes

Example:
- 1.0.0 - Initial release
- 1.0.1 - Bug fix
- 1.1.0 - New feature (audio import)
- 2.0.0 - Major rewrite (major feature changes)

### Update Process for Users

Users with installer:
1. Run new installer
2. Choose "Upgrade" option
3. Data preserved in AppData
4. New version ready to use

Users with portable version:
1. Download new version
2. Replace executable
3. Run new version
4. Data automatically found in AppData

## Support and Feedback

### Provide Support Channels

```markdown
## Support

- **GitHub Issues**: Report bugs and request features
- **Email**: support@your-org.com
- **Discord**: Join our community server
- **Documentation**: Full user guide at [docs]
```

### Collect Usage Analytics (Optional)

```python
# In app_launcher.py, optionally add:
def send_usage_analytics(event_name, data=None):
    """Send anonymized usage data to analytics service"""
    # POST to analytics endpoint
    # Include: version, OS, event_name
    # DO NOT include: personal data, audio content
    pass
```

### Feedback Form

Add to application UI:
```tsx
<button onClick={() => window.open('https://forms.your-site.com/feedback')}>
  Send Feedback
</button>
```

## Troubleshooting for Users

Provide users with:

1. **Installation Guide**: [INSTALLATION_GUIDE.md](INSTALLATION_GUIDE.md)
2. **Troubleshooting**: [TROUBLESHOOTING.md](TROUBLESHOOTING.md)
3. **FAQ**: Common questions answered
4. **Video Tutorials**: Screen recordings of common tasks

### Create FAQ

```markdown
## Frequently Asked Questions

**Q: Where is my data stored?**
A: In `%APPDATA%\MeetingWhisperer\Meeting Whisperer\data\`

**Q: Can I use GPU?**
A: Yes, set WHISPER_DEVICE=cuda if NVIDIA GPU available

**Q: How do I uninstall?**
A: Settings > Apps > Meeting Whisperer > Uninstall
```

## Monitoring Deployments

### Check Download Statistics

If hosting on GitHub:
- View release download counts
- Monitor which versions are used most

### Version Adoption Rate

```python
# Optional telemetry (with user permission)
def report_version_usage():
    """Report which version user is running"""
    # POST to telemetry server
    version = "1.0.0"
    os_version = platform.platform()
    # Analytics dashboard shows adoption
```

### User Feedback

- Monitor issue reports
- Track feature requests
- Identify common errors
- Fix and release patch versions

## Continuous Deployment (Advanced)

### Automated Release Process

```bash
#!/bin/bash
# Deploy on each GitHub release

VERSION=$1  # e.g., 1.0.0

# Build
cd launcher
quickbuild.bat

# Sign
signtool sign ...

# Upload to GitHub
gh release create v$VERSION \
  launcher/output/MeetingWhisperer-Setup-$VERSION.exe \
  --title "Release v$VERSION"

# Update website
# Update package managers
```

### Rollback Plan

If issues discovered:

```bash
# Re-release previous version
gh release create v1.0.0-rollback \
  launcher/output/MeetingWhisperer-Setup-1.0.0.exe \
  --title "ROLLBACK: v1.0.0"

# Announce issue and fixes
# Release patched version
```

## Metrics and Success

Track:
- Download counts
- Installation success rate
- User retention (app usage over time)
- Bug reports and issue resolution time
- User satisfaction (if applicable)

## Post-Release Checklist

- [ ] Release tagged in Git
- [ ] Installer downloaded and tested by team
- [ ] Users notified of new version
- [ ] Documentation updated
- [ ] Support channels monitored
- [ ] Bug reports tracked

## Long-term Maintenance

- Keep dependencies updated
- Monitor security advisories
- Collect user feedback
- Plan next feature release
- Monitor usage metrics
- Maintain documentation

## Support Resources

- Installation: [INSTALLATION_GUIDE.md](INSTALLATION_GUIDE.md)
- Troubleshooting: [TROUBLESHOOTING.md](TROUBLESHOOTING.md)
- Building: [README.md](README.md)
- Backend: [backend/README.md](../backend/README.md)
- Frontend: [frontend/README.md](../frontend/README.md)

---

Last updated: 2024
Estimated deployment time: 1-2 hours (including testing)
