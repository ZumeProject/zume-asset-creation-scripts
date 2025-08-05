#!/usr/bin/env python3
"""
Script to copy and rename video files and PNG files from source directories to output directory,
then delete specific PNG files and copy videos to create mixed sequences.

Part 1: Copies .mp4 files from {project_path}/videos to {project_path}/output/videos and renames them to 1.mp4, 2.mp4, etc. based on their numeric order
Part 2: Copies .png files from {project_path}/10, {project_path}/20, and {project_path}/intensive to {project_path}/output/10, {project_path}/output/20, and {project_path}/output/intensive 
        and renames them to 1.png, 2.png, etc. based on timestamp order
        Each folder gets its own numbering sequence starting from 1.
Part 3: Deletes specific PNG files from the output folders based on the values in 10.json, 20.json, and intensive.json
Part 4: Copies MP4 files from {project_path}/output/videos to the PNG folders and renames them based on JSON configuration
        (e.g., 1.mp4 becomes 6.mp4 in {project_path}/output/10 if JSON has "1": "6")

The result is mixed sequences of PNG and MP4 files in numerical order within each folder.
The output directory is cleared before processing to ensure a fresh start.
"""

import os
import re
import shutil
import json
from pathlib import Path
import datetime
import sys
import argparse

def load_config() -> dict:
    """Load configuration from .config.json file"""
    config_file = Path('../.config.json')
    if config_file.exists():
        with open(config_file, 'r') as f:
            return json.load(f)
    return {}

def get_project_path(provided_path: str = None) -> Path:
    """Get the project path from command line argument, environment variable, or configuration"""
    # Check command line argument first
    if provided_path:
        project_path = Path(provided_path)
        if not project_path.exists():
            print(f"❌ Provided project path {project_path} does not exist.")
            sys.exit(1)
        return project_path
    
    # Check environment variable
    env_path = os.environ.get('ZUME_PROJECT_PATH')
    if env_path:
        project_path = Path(env_path)
        if not project_path.exists():
            print(f"❌ Environment project path {project_path} does not exist.")
            sys.exit(1)
        return project_path
    
    # Fall back to configuration file
    config = load_config()
    if not config:
        print("❌ No configuration found and no path provided. Please run 1-setup.py first or provide a path.")
        sys.exit(1)
    
    project_path = config.get('project_path')
    if not project_path:
        print("❌ No project path found in configuration. Please run 1-setup.py first or provide a path.")
        sys.exit(1)
    
    project_path = Path(project_path)
    if not project_path.exists():
        print(f"❌ Project path {project_path} does not exist. Please run 1-setup.py first.")
        sys.exit(1)
    
    return project_path

def setup_output_directory(project_path: Path):
    """
    Set up the output directory. If it exists, empty it. If not, create it.
    """
    output_path = project_path / "output"
    
    if output_path.exists():
        print("=== Clearing existing output directory ===")
        # Remove all contents of the output directory
        for item in output_path.iterdir():
            if item.is_file():
                item.unlink()
                print(f"  Removed file: {item.name}")
            elif item.is_dir():
                shutil.rmtree(item)
                print(f"  Removed directory: {item.name}")
    else:
        print("=== Creating output directory ===")
        output_path.mkdir(exist_ok=True)
        print(f"  Created output directory: {output_path}")

def rename_video_files(project_path: Path):
    """
    Copy .mp4 files from {project_path}/videos to {project_path}/output/videos and rename them to 1.mp4, 2.mp4, etc.
    based on the numeric order in their filenames.
    """
    source_dir = project_path / "videos"
    output_dir = project_path / "output" / "videos"
    
    print(f"=== Copying and renaming video files from {source_dir} to {output_dir} ===")
    
    # Get the path to the source videos directory
    videos_path = Path(source_dir)
    output_path = Path(output_dir)
    
    if not videos_path.exists():
        print(f"Error: Directory {source_dir} does not exist!")
        return
    
    # Create output directory if it doesn't exist
    output_path.mkdir(parents=True, exist_ok=True)
    
    # Find all .mp4 files
    mp4_files = []
    for file in videos_path.glob("*.mp4"):
        if file.is_file():
            mp4_files.append(file)
    
    if not mp4_files:
        print("No .mp4 files found in the videos directory.")
        return
    
    # Extract numbers from filenames and sort
    files_with_numbers = []
    for file in mp4_files:
        # Try multiple regex patterns to extract numbers from different filename formats
        number = None
        
        # Pattern 1: Numbers in parentheses at the beginning: (01), (02), etc.
        match = re.match(r'^\((\d+)\)', file.name)
        if match:
            number = int(match.group(1))
        else:
            # Pattern 2: Numbers at the beginning: 01_file, 02_file, etc.
            match = re.match(r'^(\d+)', file.name)
            if match:
                number = int(match.group(1))
            else:
                # Pattern 3: First occurrence of numbers anywhere in filename
                match = re.search(r'(\d+)', file.name)
                if match:
                    number = int(match.group(1))
        
        if number is not None:
            files_with_numbers.append((number, file))
            print(f"  Found number {number} in: {file.name}")
        else:
            print(f"Warning: Could not extract number from {file.name}")
    
    # Sort by the extracted number
    files_with_numbers.sort(key=lambda x: x[0])
    
    print(f"Found {len(files_with_numbers)} .mp4 files to copy and rename:")
    
    # Copy and rename files
    for i, (original_num, file) in enumerate(files_with_numbers, 1):
        new_name = f"{i}.mp4"
        new_path = output_path / new_name
        
        print(f"  {file.name} -> {new_name}")
        
        try:
            shutil.copy2(file, new_path)
            print(f"    ✓ Copied and renamed successfully")
        except Exception as e:
            print(f"    ✗ Error copying file: {e}")


def rename_png_files(project_path: Path, folder_name: str):
    """
    Copy .png files from {project_path}/{folder_name} to {project_path}/output/{folder_name} and rename them to 1.png, 2.png, etc.
    based on the timestamp order in their filenames.
    """
    source_dir = project_path / folder_name
    output_dir = project_path / "output" / folder_name
    
    print(f"\n=== Copying and renaming PNG files from {source_dir} to {output_dir} ===")
    
    # Get the path to the source directory
    png_path = Path(source_dir)
    output_path = Path(output_dir)
    
    if not png_path.exists():
        print(f"Error: Directory {source_dir} does not exist!")
        return
    
    # Create output directory if it doesn't exist
    output_path.mkdir(parents=True, exist_ok=True)
    
    # Find all .png files
    png_files = []
    for file in png_path.glob("*.png"):
        if file.is_file():
            png_files.append(file)
    
    if not png_files:
        print("No .png files found in the directory.")
        return
    
    # Extract timestamps from filenames and sort
    files_with_timestamps = []
    for file in png_files:
        # Look for timestamp pattern at the beginning: YYYYMMDD_HHMMSS
        match = re.match(r'^(\d{8}_\d{6})', file.name)
        if match:
            timestamp_str = match.group(1)
            try:
                # Parse the timestamp
                timestamp = datetime.datetime.strptime(timestamp_str, "%Y%m%d_%H%M%S")
                files_with_timestamps.append((timestamp, file))
            except ValueError:
                print(f"Warning: Could not parse timestamp from {file.name}")
        else:
            print(f"Warning: Could not extract timestamp from {file.name}")
    
    # Sort by timestamp
    files_with_timestamps.sort(key=lambda x: x[0])
    
    print(f"Found {len(files_with_timestamps)} .png files to copy and rename:")
    
    # Copy and rename files
    for i, (timestamp, file) in enumerate(files_with_timestamps, 1):
        new_name = f"{i}.png"
        new_path = output_path / new_name
        
        print(f"  {file.name} -> {new_name}")
        
        try:
            shutil.copy2(file, new_path)
            print(f"    ✓ Copied and renamed successfully")
        except Exception as e:
            print(f"    ✗ Error copying file: {e}")


def delete_png_files_from_json(project_path: Path, json_file: str, folder_name: str):
    """
    Delete PNG files from the output folder based on the values in the JSON file.
    
    Args:
        project_path: Path to the project directory
        json_file: Path to the JSON file (e.g., "10.json")
        folder_name: Name of the folder (e.g., "10")
    """
    json_path = Path(json_file)
    output_folder = project_path / "output" / folder_name
    
    print(f"\n=== Deleting PNG files from {output_folder} based on {json_file} ===")
    
    # Check if JSON file exists
    if not json_path.exists():
        print(f"Warning: JSON file {json_file} does not exist, skipping deletion...")
        return
    
    # Check if output folder exists
    if not output_folder.exists():
        print(f"Warning: Output folder {output_folder} does not exist, skipping deletion...")
        return
    
    try:
        # Read the JSON file
        with open(json_path, 'r') as f:
            deletion_data = json.load(f)
        
        # Extract the values (PNG file numbers to delete)
        files_to_delete = list(deletion_data.values())
        
        print(f"Found {len(files_to_delete)} PNG files to delete: {files_to_delete}")
        
        deleted_count = 0
        not_found_count = 0
        
        # Delete each PNG file specified in the JSON
        for file_num in files_to_delete:
            png_file = output_folder / f"{file_num}.png"
            
            if png_file.exists():
                try:
                    png_file.unlink()
                    print(f"  ✓ Deleted {file_num}.png")
                    deleted_count += 1
                except Exception as e:
                    print(f"  ✗ Error deleting {file_num}.png: {e}")
            else:
                print(f"  - File {file_num}.png not found (may have been out of range)")
                not_found_count += 1
        
        print(f"  Summary: {deleted_count} files deleted, {not_found_count} files not found")
        
    except json.JSONDecodeError as e:
        print(f"Error: Could not parse JSON file {json_file}: {e}")
    except Exception as e:
        print(f"Error: Could not process JSON file {json_file}: {e}")


def copy_videos_from_json(project_path: Path, json_file: str, folder_name: str):
    """
    Copy and rename MP4 files from {project_path}/output/videos to the specified folder based on JSON configuration.
    
    Args:
        project_path: Path to the project directory
        json_file: Path to the JSON file (e.g., "10.json")
        folder_name: Name of the folder (e.g., "10")
    """
    json_path = Path(json_file)
    output_folder = project_path / "output" / folder_name
    videos_path = project_path / "output" / "videos"
    
    print(f"\n=== Copying MP4 files to {output_folder} based on {json_file} ===")
    
    # Check if JSON file exists
    if not json_path.exists():
        print(f"Warning: JSON file {json_file} does not exist, skipping video copying...")
        return
    
    # Check if output folder exists
    if not output_folder.exists():
        print(f"Warning: Output folder {output_folder} does not exist, skipping video copying...")
        return
    
    # Check if videos folder exists
    if not videos_path.exists():
        print(f"Warning: Videos folder {videos_path} does not exist, skipping video copying...")
        return
    
    try:
        # Read the JSON file
        with open(json_path, 'r') as f:
            video_mapping = json.load(f)
        
        print(f"Found {len(video_mapping)} MP4 files to copy and rename")
        
        copied_count = 0
        not_found_count = 0
        
        # Copy and rename each MP4 file specified in the JSON
        for source_num, target_num in video_mapping.items():
            source_video = videos_path / f"{source_num}.mp4"
            target_video = output_folder / f"{target_num}.mp4"
            
            if source_video.exists():
                try:
                    shutil.copy2(source_video, target_video)
                    print(f"  ✓ Copied {source_num}.mp4 -> {target_num}.mp4")
                    copied_count += 1
                except Exception as e:
                    print(f"  ✗ Error copying {source_num}.mp4: {e}")
            else:
                print(f"  - Video {source_num}.mp4 not found in videos folder")
                not_found_count += 1
        
        print(f"  Summary: {copied_count} videos copied, {not_found_count} videos not found")
        
    except json.JSONDecodeError as e:
        print(f"Error: Could not parse JSON file {json_file}: {e}")
    except Exception as e:
        print(f"Error: Could not process JSON file {json_file}: {e}")


def display_final_contents(project_path: Path):
    """
    Display the final contents of each output folder to show the mixed sequence.
    """
    print("\n" + "=" * 50)
    print("Final Contents of Output Folders:")
    print("=" * 50)
    
    folders = [
        project_path / "output" / "videos",
        project_path / "output" / "10",
        project_path / "output" / "20",
        project_path / "output" / "intensive"
    ]
    
    for folder in folders:
        if folder.exists():
            print(f"\n{folder}:")
            # Get all files and sort them numerically
            files = []
            for file in folder.iterdir():
                if file.is_file():
                    # Extract number from filename for sorting
                    match = re.match(r'^(\d+)\.(png|mp4)$', file.name)
                    if match:
                        number = int(match.group(1))
                        extension = match.group(2)
                        files.append((number, file.name, extension))
            
            # Sort by number
            files.sort(key=lambda x: x[0])
            
            if files:
                for number, filename, extension in files:
                    print(f"  {filename} ({extension.upper()})")
                print(f"  Total: {len(files)} files")
            else:
                print("  No files found")
        else:
            print(f"\n{folder}: Directory does not exist")


def main():
    """Main function to run both copying and renaming operations."""
    # Add argument parsing
    parser = argparse.ArgumentParser(description='Copy and rename video and PNG files')
    parser.add_argument('--project-path', '-p', type=str, 
                       help='Path to the project directory (overrides config file)')
    args = parser.parse_args()
    
    print("File Copying and Renaming Script")
    print("=" * 50)
    
    # Change to the script directory to ensure relative paths work
    script_dir = Path(__file__).parent
    os.chdir(script_dir)
    
    # Load configuration and get project path
    project_path = get_project_path(args.project_path)
    print(f"📍 Project path: {project_path}")
    
    # Step 0: Set up output directory (clear if exists, create if not)
    setup_output_directory(project_path)
    
    # Part 1: Copy and rename video files
    rename_video_files(project_path)
    
    # Part 2: Copy and rename PNG files in multiple folders
    png_folders = ["10", "20", "intensive"]
    
    for folder in png_folders:
        folder_path = project_path / folder
        if folder_path.exists():
            rename_png_files(project_path, folder)
        else:
            print(f"\nWarning: Directory {folder_path} does not exist, skipping...")
    
    # Part 3: Delete PNG files based on JSON configuration
    print("\n" + "=" * 50)
    print("Starting PNG file deletion based on JSON configuration...")
    
    json_configs = [
        ("../10.json", "10"),
        ("../20.json", "20"),
        ("../intensive.json", "intensive")
    ]
    
    for json_file, folder_name in json_configs:
        delete_png_files_from_json(project_path, json_file, folder_name)
    
    # Part 4: Copy MP4 files to PNG folders and rename based on JSON configuration
    print("\n" + "=" * 50)
    print("Starting MP4 file copying to PNG folders based on JSON configuration...")
    
    for json_file, folder_name in json_configs:
        copy_videos_from_json(project_path, json_file, folder_name)
    
    print("\n" + "=" * 50)
    print("File copying, renaming, and deletion completed!")
    print(f"All processed files are now in the '{project_path}/output' directory.")
    print("PNG files specified in JSON files have been deleted.")
    print("MP4 files have been copied to PNG folders and renamed based on JSON configuration.")
    print("Each folder now contains a mixed sequence of PNG and MP4 files in numerical order.")
    
    # Display final contents
    display_final_contents(project_path)


if __name__ == "__main__":
    main() 