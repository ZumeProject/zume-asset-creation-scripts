# Plan: Remove `.config.json` Dependency and Implement Session Logic

## Problem Statement

Currently, the build process uses a shared `.config.json` file for persistence. When running multiple build processes in parallel, they overwrite each other's configuration file, causing conflicts and data loss.

## Current Architecture

### Files That Write to `.config.json`:
1. **`build.py`** (line 58): Writes config during `save_temp_config()`
2. **`parts/1-setup.py`** (line 143): Writes config during setup

### Files That Read from `.config.json`:
1. **`build.py`** (line 355): Verifies setup completion
2. **`parts/1-setup.py`** (line 150): Loads existing config
3. **`parts/2-video-download.py`** (line 23): Loads `project_path` and `language_code`
4. **`parts/3-slides-download.py`** (line 16): Loads `project_path` and `language_code`
5. **`parts/4-rename-files.py`** (line 29): Loads `project_path`

## Solution: Session-Based Configuration

### Approach
1. **Generate unique session IDs** for each build process
2. **Pass configuration via command-line arguments** to subprocesses
3. **Update all scripts** to accept config via CLI args (with backward compatibility)
4. **Remove shared file writes** from parallel execution paths

## Implementation Plan

### Phase 1: Session ID Generation and Management

#### 1.1 Update `build.py`
- Add session ID generation using `uuid` or timestamp-based unique ID
- Store session ID in `BuildRunner` instance
- Remove `.config.json` write operations from `save_temp_config()`
- Keep config in memory only

**Changes:**
```python
import uuid

class BuildRunner:
    def __init__(self):
        self.config = {}
        self.session_id = str(uuid.uuid4())[:8]  # Short unique ID
        # ... existing code ...
    
    def save_temp_config(self):
        # Remove .config.json write
        # Only save to temp_dir for tracking/debugging
        temp_config_path = os.path.join(self.temp_dir, 'build_config.json')
        with open(temp_config_path, 'w') as f:
            json.dump(self.config, f, indent=2)
```

#### 1.2 Remove Config File Verification
- Remove `.config.json` existence check from `verify_setup()` in `build.py`
- Verify setup by checking directory structure instead

### Phase 2: Update Subprocess Invocations

#### 2.1 Update `run_setup()` in `build.py`
**Current:**
```python
args = [
    sys.executable, 'parts/1-setup.py',
    '--language', self.config['language_code'],
    '--folder', self.config['folder_location']
]
```

**New:**
```python
args = [
    sys.executable, 'parts/1-setup.py',
    '--language', self.config['language_code'],
    '--folder', self.config['folder_location'],
    '--session-id', self.session_id
]
```

#### 2.2 Update `run_video_download()` in `build.py`
**Current:**
```python
result = subprocess.run(
    [sys.executable, 'parts/2-video-download.py', 
     '--folder-id', self.config['vimeo_folder_id']],
    ...
)
```

**New:**
```python
result = subprocess.run(
    [sys.executable, 'parts/2-video-download.py', 
     '--folder-id', self.config['vimeo_folder_id'],
     '--project-path', self.config['project_path'],
     '--language-code', self.config['language_code']],
    ...
)
```

#### 2.3 Update `run_slides_download()` in `build.py`
**Current:**
```python
result = subprocess.run(
    [sys.executable, 'parts/3-slides-download.py', 
     '--curriculum', 'all',
     '--missing-only',
     '--width', '3000',
     '--height', '1680',
     '--wait', '5'],
    ...
)
```

**New:**
```python
result = subprocess.run(
    [sys.executable, 'parts/3-slides-download.py', 
     '--curriculum', 'all',
     '--missing-only',
     '--width', '3000',
     '--height', '1680',
     '--wait', '5',
     '--project-path', self.config['project_path'],
     '--language-code', self.config['language_code']],
    ...
)
```

#### 2.4 Update `run_rename_files()` in `build.py`
**Current:**
```python
return self.run_script('parts/4-rename-files.py', 'File Rename and Organization')
```

**New:**
```python
result = subprocess.run(
    [sys.executable, 'parts/4-rename-files.py',
     '--project-path', self.config['project_path']],
    ...
)
```

### Phase 3: Update Individual Scripts

#### 3.1 Update `parts/1-setup.py`
- Add `--session-id` argument (optional, for tracking)
- Keep `--language` and `--folder` arguments
- Make `.config.json` write optional (only if `--save-config` flag is provided)
- For backward compatibility, still read from `.config.json` if it exists and no CLI args provided

**Changes:**
```python
parser.add_argument(
    '--session-id',
    help='Session ID for tracking (optional)'
)

parser.add_argument(
    '--save-config',
    action='store_true',
    help='Save configuration to .config.json (optional, for backward compatibility)'
)

# In save_config():
if args.save_config:
    with open('../.config.json', 'w') as f:
        json.dump(config, f, indent=2)
```

#### 3.2 Update `parts/2-video-download.py`
- Add `--project-path` and `--language-code` arguments
- Update `load_config()` to accept config from CLI args or environment variables
- Fall back to `.config.json` only if args not provided (backward compatibility)

**Changes:**
```python
parser.add_argument(
    '--project-path',
    help='Project path (overrides .config.json)'
)

parser.add_argument(
    '--language-code',
    help='Language code (overrides .config.json)'
)

def load_config(args=None):
    """Load configuration from CLI args, env vars, or .config.json"""
    config = {}
    
    # Priority 1: Command-line arguments
    if args and args.project_path:
        config['project_path'] = args.project_path
    if args and args.language_code:
        config['language_code'] = args.language_code
    
    # Priority 2: Environment variables
    if not config.get('project_path'):
        config['project_path'] = os.environ.get('ZUME_PROJECT_PATH')
    if not config.get('language_code'):
        config['language_code'] = os.environ.get('ZUME_LANGUAGE_CODE')
    
    # Priority 3: .config.json file (backward compatibility)
    if not config.get('project_path') or not config.get('language_code'):
        config_file = Path('../.config.json')
        if config_file.exists():
            with open(config_file, 'r') as f:
                file_config = json.load(f)
                config.update(file_config)
    
    # Validate required fields
    if 'project_path' not in config or 'language_code' not in config:
        print("? Missing required configuration")
        print("Provide via --project-path and --language-code, or use .config.json")
        sys.exit(1)
    
    return config
```

#### 3.3 Update `parts/3-slides-download.py`
- Add `--project-path` and `--language-code` arguments
- Update `load_config()` similar to `2-video-download.py`

**Changes:**
Same pattern as `2-video-download.py`

#### 3.4 Update `parts/4-rename-files.py`
- Already has `--project-path` argument support (line 441)
- Enhance to prioritize CLI args over `.config.json`
- Update `load_config()` to match pattern

**Changes:**
```python
def load_config(args=None) -> dict:
    """Load configuration from CLI args, env vars, or .config.json"""
    config = {}
    
    # Priority 1: Command-line arguments
    if args and args.project_path:
        config['project_path'] = args.project_path
    
    # Priority 2: Environment variables
    if not config.get('project_path'):
        config['project_path'] = os.environ.get('ZUME_PROJECT_PATH')
    
    # Priority 3: .config.json file (backward compatibility)
    if not config.get('project_path'):
        config_file = Path('../.config.json')
        if config_file.exists():
            with open(config_file, 'r') as f:
                file_config = json.load(f)
                config.update(file_config)
    
    return config
```

### Phase 4: Cleanup and Testing

#### 4.1 Remove Temporary Config File Logic
- Remove `setup_temp_config()` and `cleanup_temp_config()` methods that manipulate `.config.json`
- Keep temp directory for session tracking/debugging only

#### 4.2 Update Documentation
- Update `README.md` to reflect new session-based approach
- Document CLI argument usage for each script
- Note backward compatibility with `.config.json`

#### 4.3 Testing Checklist
- [ ] Test single build process
- [ ] Test two parallel build processes (different languages)
- [ ] Test backward compatibility (scripts still work with `.config.json`)
- [ ] Test CLI argument override functionality
- [ ] Test environment variable fallback
- [ ] Verify no file conflicts between parallel processes

## Migration Strategy

### Backward Compatibility
- All scripts will continue to support reading from `.config.json` as a fallback
- This ensures existing workflows continue to work
- Only `build.py` will stop writing to `.config.json` during execution

### Gradual Migration
1. **Phase 1-2**: Implement session logic and update `build.py` (no breaking changes)
2. **Phase 3**: Update all scripts to accept CLI args (backward compatible)
3. **Phase 4**: Test thoroughly, then remove `.config.json` writes from `build.py`

## Benefits

1. **Parallel Execution**: Multiple builds can run simultaneously without conflicts
2. **Isolation**: Each build process has its own session context
3. **Flexibility**: Scripts can be called independently with CLI args
4. **Backward Compatibility**: Existing `.config.json` workflows still work
5. **Debugging**: Session IDs help track and debug parallel builds

## Files to Modify

1. `build.py` - Main orchestrator
2. `parts/1-setup.py` - Setup script
3. `parts/2-video-download.py` - Video downloader
4. `parts/3-slides-download.py` - Slides downloader
5. `parts/4-rename-files.py` - File renamer
6. `README.md` - Documentation

## Risk Assessment

**Low Risk:**
- Changes are backward compatible
- Existing workflows continue to work
- Gradual migration path

**Mitigation:**
- Test thoroughly before deployment
- Keep `.config.json` support as fallback
- Document changes clearly
