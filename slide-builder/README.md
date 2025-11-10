# Zume Slide Full Builder

NOTE

```This builder has been modified to build the 3circles version of the course. This means the order of the slides is different than the non-3circles version. This will result in a different video insert process.```

A collection of Python scripts for downloading and processing Vimeo videos and slides from the Zume Training platform.

## Prerequisites

- Python 3.6+
- Valid Vimeo API credentials with access to the target folders
- Chrome/Chromium browser (for screenshots)
- Sufficient storage space for video downloads

## Installation

1. Install the required dependencies:
```bash
pip install -r requirements.txt
```

## Quick Start - Automated Build (build.py)

For a complete automated build process, use the `build.py` script which walks through all steps:

**Usage:**
```bash
python build.py
```

**What it does:**
- Collects all necessary information interactively
- Runs all scripts in the correct order automatically
- Uses session-based configuration (no shared config files)
- Supports parallel execution of multiple builds
- Provides options to skip individual steps
- Handles cleanup and error recovery

**Build Steps:**
1. **Project Setup** - Creates folder structure and stores configuration
2. **Video Download** - Downloads all videos from Vimeo folder
3. **Slides Download** - Captures screenshots of training slides
4. **File Rename** - Organizes and renames files according to requirements

**Features:**
- Interactive prompts for all required information
- **Parallel execution support**: Multiple builds can run simultaneously without conflicts
- Session-based configuration (each build gets a unique session ID)
- Step-by-step confirmation with skip options
- Automatic cleanup of temporary configuration
- Comprehensive error handling and recovery

**Example:**
```bash
# Start automated build
python build.py

# Follow the interactive prompts:
# - Enter language code (e.g., 'en', 'es', 'fr')
# - Specify folder destination
# - Provide Vimeo API credentials
# - Enter Vimeo folder ID
# - Confirm each step or skip as needed
```

## Manual Usage - Run Scripts in Order

### Step 1: Setup (1-setup.py)

Set up your project configuration, folder structure, and Vimeo API credentials.

**Usage:**
```bash
# Interactive setup
python 1-setup.py

# Non-interactive setup
python 1-setup.py --language en --folder ./projects

# Show current configuration
python 1-setup.py --show-config
```

**What it does:**
- Creates folder structure for your language (e.g., `en/10/`, `en/20/`, `en/intensive/`, `en/videos/`)
- Stores Vimeo API credentials in `.env` file
- Optionally saves configuration in `.config.json` (use `--save-config` flag)

**New Options:**
- `--session-id`: Session ID for tracking (used by build.py)
- `--save-config`: Save configuration to `.config.json` (for backward compatibility)

### Step 2: Video Download (2-video-download.py)

Downloads all videos from a Vimeo team library folder.

**Usage:**
```bash
# Using CLI arguments (recommended for parallel execution)
python 2-video-download.py --folder-id <folder_id> --project-path <path> --language-code <code>

# Using .config.json (backward compatible)
python 2-video-download.py --folder-id <folder_id>
```

**Arguments:**
- `--folder-id`: Vimeo team library folder ID (e.g., 269501) - **required**
- `--project-path`: Project path (overrides .config.json)
- `--language-code`: Language code (overrides .config.json)

**Options:**
- `--max-workers`: Maximum number of concurrent downloads (default: 3)
- `--list-only`: Only list videos without downloading
- `--list-languages`: List all available languages and exit

**Examples:**
```bash
# Download all videos (with explicit config - recommended for parallel builds)
python 2-video-download.py --folder-id 269501 --project-path ./projects/en --language-code en

# List videos without downloading
python 2-video-download.py --folder-id 269501 --list-only

# Download with more concurrent workers
python 2-video-download.py --folder-id 269501 --project-path ./projects/en --language-code en --max-workers 5

# Using .config.json (backward compatible - single build only)
python 2-video-download.py --folder-id 269501
```

**Features:**
- Uses language and folder structure from CLI args or .config.json
- Automatically detects and downloads highest quality version available
- Concurrent downloads for faster processing
- Skips already downloaded videos
- Progress tracking for each download
- Saves download results to JSON file
- Supports parallel execution via CLI arguments

### Step 3: Slides Download (3-slides-download.py)

Captures screenshots of Zume Training slides using the configuration from Step 1.

**Usage:**
```bash
# Using CLI arguments (recommended for parallel execution)
python 3-slides-download.py --project-path <path> --language-code <code> [options]

# Using .config.json (backward compatible)
python 3-slides-download.py [options]
```

**Required Arguments:**
- `--project-path`: Project path (overrides .config.json)
- `--language-code`: Language code (overrides .config.json)

**Options:**
- `--width`: Screenshot width (default: 3000)
- `--height`: Screenshot height (default: 1680)
- `--wait`: Wait time in seconds for each page to load (default: 5)
- `--curriculum`: Curriculum to capture (ten_session, twenty_session, intensive_session, or 'all')
- `--resume`: Resume from last processed slide
- `--missing-only`: Only process missing screenshots

**Examples:**
```bash
# Download all slides (with explicit config - recommended for parallel builds)
python 3-slides-download.py --project-path ./projects/en --language-code en

# Download only 10-session slides
python 3-slides-download.py --project-path ./projects/en --language-code en --curriculum ten_session

# Resume from last processed slide
python 3-slides-download.py --project-path ./projects/en --language-code en --resume

# Only download missing screenshots
python 3-slides-download.py --project-path ./projects/en --language-code en --missing-only

# Using .config.json (backward compatible - single build only)
python 3-slides-download.py --curriculum ten_session
```

**Features:**
- Uses language and folder structure from CLI args or .config.json
- Automatically organizes slides by curriculum (10, 20, intensive)
- Progress tracking with resume capability
- Missing slide detection and recovery
- Timestamped filenames to avoid conflicts
- Supports parallel execution via CLI arguments

### Step 4: File Renaming (4-rename-files.py)

Renames and organizes the downloaded files according to project requirements.

**Usage:**
```bash
# Using CLI arguments (recommended for parallel execution)
python 4-rename-files.py --project-path <path>

# Using .config.json (backward compatible)
python 4-rename-files.py
```

**Arguments:**
- `--project-path` or `-p`: Project path (overrides .config.json)

## Project Structure

After running the setup script, your project will have this structure:

```
zume-slide-full-builder/
├── 1-setup.py           # Setup script (run first)
├── 2-video-download.py  # Vimeo video downloader
├── 3-slides-download.py # Slide screenshot capture
├── 4-rename-files.py    # File renaming script
├── requirements.txt     # Python dependencies
├── .config.json         # Project configuration (created by setup)
├── .env                 # Vimeo API credentials (created by setup)
└── [language]/          # Language folder (e.g., en/, es/, fr/)
    ├── videos/          # Downloaded videos
    ├── 10/              # 10-session slides
    ├── 20/              # 20-session slides
    └── intensive/       # Intensive session slides
```

## Configuration

### Session-Based Configuration (Recommended)

The `build.py` script uses **session-based configuration** that allows parallel execution:
- Each build process gets a unique session ID
- Configuration is passed via command-line arguments to subprocesses
- No shared `.config.json` file conflicts
- Multiple builds can run simultaneously

### Legacy Configuration (Backward Compatible)

Individual scripts can still use `.config.json` for backward compatibility:
- `language_code`: The language for your project (e.g., "en", "es", "fr")
- `folder_location`: Base location where files are stored
- `project_path`: Full path to your language folder

**Note:** When using `.config.json`, only run one build process at a time to avoid file conflicts.

### Configuration Priority

All scripts follow this priority order:
1. **Command-line arguments** (highest priority)
2. **Environment variables** (`ZUME_PROJECT_PATH`, `ZUME_LANGUAGE_CODE`)
3. **`.config.json` file** (lowest priority, backward compatibility)

## Environment Variables

The `.env` file contains your Vimeo API credentials:
- `VIMEO_CLIENT_ID`: Your Vimeo client ID
- `VIMEO_CLIENT_SECRET`: Your Vimeo client secret
- `VIMEO_ACCESS_TOKEN`: Your Vimeo access token

Get these from: https://developer.vimeo.com/apps

## Parallel Execution

You can now run multiple build processes in parallel without conflicts:

```bash
# Terminal 1: Build English version
python build.py
# Enter: en, ./projects

# Terminal 2: Build Spanish version (simultaneously)
python build.py
# Enter: es, ./projects
```

Both builds will run independently with their own session IDs and won't interfere with each other.

## Troubleshooting

1. **"Configuration file not found"**: 
   - Provide config via CLI arguments: `--project-path` and `--language-code`
   - Or run `1-setup.py --save-config` first to create `.config.json`
2. **"Missing Vimeo credentials"**: Make sure your `.env` file has all required credentials
3. **Chrome driver issues**: The slides script will automatically download ChromeDriver
4. **Resume functionality**: Use `--resume` flag to continue from where you left off
5. **Missing slides**: Use `--missing-only` to only capture slides that weren't downloaded
6. **Parallel build conflicts**: Use CLI arguments instead of `.config.json` for parallel execution

## Support

For issues or questions, please check the individual script help:
```bash
python 1-setup.py --help
python 2-video-download.py --help
python 3-slides-download.py --help
python 4-rename-files.py --help
``` 