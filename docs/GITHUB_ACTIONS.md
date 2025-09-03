# GitHub Actions Workflows Documentation

Comprehensive documentation for the automated CI/CD workflows in the WSL-Tmux-Nvim-Setup project.

## Table of Contents

- [Overview](#overview)
- [Workflow Files](#workflow-files)
- [Continuous Integration](#continuous-integration)
- [Release Automation](#release-automation)
- [Asset Preparation](#asset-preparation)
- [Workflow Configuration](#workflow-configuration)
- [Secrets and Variables](#secrets-and-variables)
- [Troubleshooting](#troubleshooting)
- [Contributing](#contributing)

## Overview

The project uses GitHub Actions for automated testing, building, and releasing. The workflow system ensures code quality, automates repetitive tasks, and provides consistent release processes.

### Key Features

- **Automated Testing**: Multi-platform CI testing
- **Release Automation**: Automated version releases with changelog generation
- **Asset Building**: Automated binary and package creation
- **Security Scanning**: Automated security and dependency checks
- **Documentation**: Automated documentation updates

## Workflow Files

All workflows are located in `.github/workflows/`:

| Workflow | File | Purpose | Triggers |
|----------|------|---------|----------|
| **CI** | `ci.yml` | Continuous integration testing | Push, PR |
| **Release** | `release.yml` | Automated releases | Release creation |
| **Assets** | `prepare-assets.yml` | Build release assets | Release, workflow dispatch |

## Continuous Integration

**File:** `.github/workflows/ci.yml`

The CI workflow runs comprehensive tests across multiple platforms and configurations.

### Trigger Events

```yaml
on:
  push:
    branches: [ main, develop ]
  pull_request:
    branches: [ main, develop ]
  workflow_dispatch:
```

### Jobs Overview

#### 1. Lint and Validate (`lint-and-validate`)

**Platform:** `ubuntu-latest`

**Purpose:** Code quality and validation

**Steps:**
- Checkout repository
- Set up Python 3.9
- Install linting tools (ShellCheck, flake8, black, yamllint)
- Lint shell scripts with ShellCheck
- Lint Python code with flake8 and black
- Validate JSON and YAML configuration files

**Tools Used:**
- **ShellCheck**: Shell script analysis
- **flake8**: Python linting
- **black**: Python code formatting
- **yamllint**: YAML validation

```bash
# Example ShellCheck usage
find . -name "*.sh" -type f | while read -r file; do
  echo "Checking: $file"
  shellcheck -x "$file"
done
```

#### 2. Installation Matrix (`test-installation-matrix`)

**Platform:** `ubuntu-latest` with container matrix

**Purpose:** Multi-platform installation testing

**Matrix Configuration:**
```yaml
strategy:
  fail-fast: false
  matrix:
    ubuntu_version: ["20.04", "22.04", "24.04"]
    shell: ["bash", "zsh"]
```

**Test Coverage:**
- **Ubuntu 20.04, 22.04, 24.04** compatibility
- **Bash and Zsh** shell compatibility
- **Core installation scripts** validation
- **Component installation** testing

**Key Tests:**
- Dependency installation (`install_dependencies.sh --dry-run`)
- Individual component scripts (`install_git.sh --dry-run`)
- Shell configuration compatibility

#### 3. Update Scripts (`test-update-scripts`)

**Platform:** `ubuntu-latest`

**Purpose:** Update mechanism validation

**Test Coverage:**
- Update check script syntax validation
- Update script syntax validation
- Release-based update script validation
- Python dependency compatibility

**Dependencies Tested:**
- requests
- pyyaml
- Core Python modules

#### 4. Security Scan (`security-scan`)

**Platform:** `ubuntu-latest`

**Purpose:** Security and vulnerability analysis

**Security Tools:**
- **Bandit**: Python security analysis
- **Safety**: Known vulnerability checking
- **Secret scanning**: Hardcoded secret detection
- **Permission validation**: Script permission verification

**Scans Performed:**
```bash
# Bandit security scan
find . -name "*.py" -type f | xargs bandit -r

# Vulnerability check
safety check -r requirements.txt

# Secret detection
grep -r -i -E "(password|secret|key|token)" --include="*.sh" --include="*.py" .
```

#### 5. Documentation Test (`test-documentation`)

**Platform:** `ubuntu-latest`

**Purpose:** Documentation validation

**Validation Checks:**
- Markdown syntax validation
- Configuration file structure
- Example configuration validation
- Documentation completeness

### Environment Variables

```yaml
env:
  PYTHONUNBUFFERED: 1
  PYTHON_VERSION: "3.9"
```

### Example CI Run

```bash
# Trigger CI manually
gh workflow run ci.yml

# Monitor CI status
gh run list --workflow=ci.yml

# View specific run
gh run view <run-id>
```

## Release Automation

**File:** `.github/workflows/release.yml`

Automates the release process when a new release is created.

### Release Process

1. **Trigger**: GitHub release creation
2. **Build**: Create release artifacts
3. **Test**: Validate release package
4. **Upload**: Attach artifacts to release
5. **Notify**: Update changelog and notifications

### Release Components

#### Version Management
- Automatic version extraction from release tag
- Version validation and consistency checking
- Changelog generation from commits

#### Asset Creation
- Source code archives (tar.gz, zip)
- Binary packages for different platforms
- Documentation packages
- Checksum files for verification

#### Quality Assurance
- Release package testing
- Installation verification
- Smoke tests on target platforms

### Example Release Workflow

```bash
# Create new release
gh release create v1.2.0 \
  --title "Release v1.2.0" \
  --notes "Release notes here" \
  --prerelease

# Monitor release workflow
gh run list --workflow=release.yml

# Download release assets
gh release download v1.2.0
```

## Asset Preparation

**File:** `.github/workflows/prepare-assets.yml`

Builds and prepares release assets.

### Asset Types

#### 1. Source Archives
- Complete source code
- Documentation included
- Configuration templates
- Installation scripts

#### 2. Binary Packages
- Platform-specific binaries
- Dependency bundling
- Installation packages
- Portable executables

#### 3. Documentation
- User guides (PDF, HTML)
- API documentation
- Installation instructions
- Configuration examples

#### 4. Verification Files
- SHA256 checksums
- GPG signatures (if configured)
- Vulnerability reports
- Dependency manifests

### Build Matrix

```yaml
strategy:
  matrix:
    os: [ubuntu-latest, windows-latest, macos-latest]
    python-version: [3.7, 3.8, 3.9, 3.10, 3.11]
```

### Asset Naming Convention

```
wsl-tmux-nvim-setup-v1.2.0-linux-x64.tar.gz
wsl-tmux-nvim-setup-v1.2.0-windows-x64.zip
wsl-tmux-nvim-setup-v1.2.0-macos-x64.tar.gz
wsl-tmux-nvim-setup-v1.2.0-checksums.txt
```

## Workflow Configuration

### Common Configurations

#### Timeout Settings
```yaml
timeout-minutes: 30  # Default timeout
```

#### Retry Configuration
```yaml
uses: nick-invision/retry@v2
with:
  timeout_minutes: 10
  max_attempts: 3
  command: npm test
```

#### Caching
```yaml
- name: Cache Python dependencies
  uses: actions/cache@v4
  with:
    path: ~/.cache/pip
    key: ${{ runner.os }}-pip-${{ hashFiles('requirements.txt') }}
```

### Performance Optimization

#### Parallel Execution
Most jobs run in parallel to minimize CI time:

```yaml
jobs:
  lint:
    # Runs independently
  test-matrix:
    # Runs independently
  security:
    # Runs independently
```

#### Selective Triggers
```yaml
on:
  push:
    paths:
      - 'cli/**'
      - 'tests/**'
      - 'requirements.txt'
```

#### Artifact Optimization
```yaml
- name: Upload artifacts
  uses: actions/upload-artifact@v4
  with:
    name: test-results
    path: test-results/
    retention-days: 30
    if-no-files-found: warn
```

## Secrets and Variables

### Required Secrets

| Secret | Purpose | Scope |
|--------|---------|-------|
| `GITHUB_TOKEN` | API access | Automatic |
| `GPG_PRIVATE_KEY` | Release signing | Repository |
| `GPG_PASSPHRASE` | Key passphrase | Repository |

### Repository Variables

| Variable | Purpose | Example |
|----------|---------|---------|
| `PYTHON_VERSION` | Default Python version | `3.9` |
| `NODE_VERSION` | Node.js version | `18` |

### Environment-Specific Variables

#### Development
```yaml
environment: development
env:
  API_URL: https://api-dev.example.com
  DEBUG: true
```

#### Production
```yaml
environment: production  
env:
  API_URL: https://api.example.com
  DEBUG: false
```

### Security Best Practices

#### Secret Handling
- Never log secret values
- Use masked outputs for sensitive data
- Rotate secrets regularly
- Use least-privilege access

#### Example Secret Usage
```yaml
- name: Configure Git
  env:
    GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}
  run: |
    git config --global user.email "bot@example.com"
    git config --global user.name "Release Bot"
```

## Troubleshooting

### Common Issues

#### 1. Test Failures

**Symptom:** Tests fail in CI but pass locally

**Solutions:**
- Check environment differences
- Verify dependencies are installed
- Check file permissions
- Review timeout settings

```bash
# Debug locally with same environment
docker run -it ubuntu:22.04 bash
apt update && apt install -y git python3 python3-pip
# Reproduce CI steps
```

#### 2. Permission Errors

**Symptom:** Scripts fail with permission denied

**Solutions:**
- Ensure scripts are executable: `chmod +x script.sh`
- Check file permissions in repository
- Verify container user permissions

```yaml
- name: Fix permissions
  run: |
    chmod +x scripts/*.sh
    chmod +x bin/*.sh
```

#### 3. Dependency Issues

**Symptom:** Package installation failures

**Solutions:**
- Pin dependency versions
- Use lock files (requirements.txt)
- Cache dependencies
- Check for platform-specific dependencies

```yaml
- name: Install dependencies with retry
  uses: nick-invision/retry@v2
  with:
    timeout_minutes: 5
    max_attempts: 3
    command: pip install -r requirements.txt
```

#### 4. Network Timeouts

**Symptom:** Downloads or API calls timeout

**Solutions:**
- Increase timeout values
- Use retry mechanisms
- Implement fallback mirrors
- Check network connectivity

```yaml
- name: Download with timeout
  run: |
    timeout 300 wget https://example.com/file.tar.gz
    # Or with curl
    curl -L --max-time 300 https://example.com/file.tar.gz -o file.tar.gz
```

### Debugging Workflows

#### 1. Enable Debug Logging
```yaml
env:
  ACTIONS_STEP_DEBUG: true
  ACTIONS_RUNNER_DEBUG: true
```

#### 2. Add Debug Steps
```yaml
- name: Debug environment
  run: |
    echo "OS: $(uname -a)"
    echo "Python: $(python3 --version)"
    echo "Working directory: $(pwd)"
    echo "Files: $(ls -la)"
    env | sort
```

#### 3. Use tmate for SSH Access
```yaml
- name: Setup tmate session
  if: failure()
  uses: mxschmitt/action-tmate@v3
  timeout-minutes: 15
```

### Performance Monitoring

#### Workflow Duration Tracking
```bash
# Get workflow run times
gh run list --workflow=ci.yml --json status,conclusion,createdAt,updatedAt

# Analyze job performance
gh run view <run-id> --json jobs
```

#### Resource Usage
- Monitor memory usage in build jobs
- Track artifact sizes
- Measure test execution times
- Monitor API rate limits

## Contributing

### Adding New Workflows

1. **Create workflow file** in `.github/workflows/`
2. **Define clear triggers** and job dependencies
3. **Add comprehensive testing**
4. **Update documentation**
5. **Test with workflow dispatch**

### Modifying Existing Workflows

1. **Create feature branch**
2. **Test changes with draft PR**
3. **Verify all job combinations**
4. **Update related documentation**
5. **Monitor first few runs after merge**

### Best Practices

#### Workflow Design
- **Keep jobs focused** and single-purpose
- **Use matrix builds** for multi-platform testing
- **Implement proper error handling**
- **Add meaningful job names and descriptions**

#### Security
- **Never commit secrets** to repository
- **Use least-privilege permissions**
- **Validate external inputs**
- **Pin action versions** for security

#### Performance
- **Cache dependencies** where possible
- **Use parallel execution**
- **Optimize Docker images**
- **Clean up artifacts** regularly

#### Maintenance
- **Keep actions updated**
- **Monitor for deprecated features**
- **Review workflow performance**
- **Update documentation regularly**

### Testing Workflows

#### Local Testing
```bash
# Use act to run GitHub Actions locally
act -j test-installation-matrix

# Test specific workflow
act -W .github/workflows/ci.yml
```

#### Draft PR Testing
- Create draft PR to test workflow changes
- Use workflow_dispatch for manual testing
- Monitor resource usage and timing

---

*For more information about GitHub Actions, see the [official documentation](https://docs.github.com/en/actions).*