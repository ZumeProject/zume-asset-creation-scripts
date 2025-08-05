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
- Stores configuration in temporary memory for concurrent builds
- Provides options to skip individual steps
- Handles cleanup and error recovery

**Build Steps:**
1. **Project Setup** - Creates folder structure and stores configuration
2. **Video Download** - Downloads all videos from Vimeo folder
3. **Slides Download** - Captures screenshots of training slides
4. **File Rename** - Organizes and renames files according to requirements

**Features:**
- Interactive prompts for all required information
- Concurrent build support (run in separate terminals/directories)
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
- Saves configuration in `.config.json`

### Step 2: Video Download (2-video-download.py)

Downloads all videos from a Vimeo team library folder using the configuration from Step 1.

**Usage:**
```bash
python 2-video-download.py <folder_id> [options]
```

**Arguments:**
- `folder_id`: Vimeo team library folder ID (e.g., 269501)

**Options:**
- `--max-workers`: Maximum number of concurrent downloads (default: 3)
- `--list-only`: Only list videos without downloading

**Examples:**
```bash
# Download all videos from folder 269501
python 2-video-download.py 269501

# List videos without downloading
python 2-video-download.py 269501 --list-only

# Download with more concurrent workers
python 2-video-download.py 269501 --max-workers 5
```

**Features:**
- Uses language and folder structure from setup
- Automatically detects and downloads highest quality version available
- Concurrent downloads for faster processing
- Skips already downloaded videos
- Progress tracking for each download
- Saves download results to JSON file

### Step 3: Slides Download (3-slides-download.py)

Captures screenshots of Zume Training slides using the configuration from Step 1.

**Usage:**
```bash
python 3-slides-download.py [options]
```

**Options:**
- `--width`: Screenshot width (default: 3000)
- `--height`: Screenshot height (default: 1680)
- `--wait`: Wait time in seconds for each page to load (default: 5)
- `--curriculum`: Curriculum to capture (ten_session, twenty_session, intensive_session, or 'all')
- `--resume`: Resume from last processed slide
- `--missing-only`: Only process missing screenshots

**Examples:**
```bash
# Download all slides
python 3-slides-download.py

# Download only 10-session slides
python 3-slides-download.py --curriculum ten_session

# Resume from last processed slide
python 3-slides-download.py --resume

# Only download missing screenshots
python 3-slides-download.py --missing-only
```

**Features:**
- Uses language and folder structure from setup
- Automatically organizes slides by curriculum (10, 20, intensive)
- Progress tracking with resume capability
- Missing slide detection and recovery
- Timestamped filenames to avoid conflicts

### Step 4: File Renaming (4-rename-files.py)

Renames and organizes the downloaded files according to project requirements.

**Usage:**
```bash
python 4-rename-files.py [options]
```

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

The setup script creates a `.config.json` file with:
- `language_code`: The language for your project (e.g., "en", "es", "fr")
- `folder_location`: Base location where files are stored
- `project_path`: Full path to your language folder

## Environment Variables

The `.env` file contains your Vimeo API credentials:
- `VIMEO_CLIENT_ID`: Your Vimeo client ID
- `VIMEO_CLIENT_SECRET`: Your Vimeo client secret
- `VIMEO_ACCESS_TOKEN`: Your Vimeo access token

Get these from: https://developer.vimeo.com/apps

## Troubleshooting

1. **"Configuration file not found"**: Run `1-setup.py` first
2. **"Missing Vimeo credentials"**: Make sure your `.env` file has all required credentials
3. **Chrome driver issues**: The slides script will automatically download ChromeDriver
4. **Resume functionality**: Use `--resume` flag to continue from where you left off
5. **Missing slides**: Use `--missing-only` to only capture slides that weren't downloaded

## Support

For issues or questions, please check the individual script help:
```bash
python 1-setup.py --help
python 2-video-download.py --help
python 3-slides-download.py --help
python 4-rename-files.py --help
``` 