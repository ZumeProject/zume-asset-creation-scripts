#!/usr/bin/env python3
"""
Vimeo Team Library Downloader

This script lists all videos in a Vimeo team library folder and downloads
each of them in high definition format.
"""

import os
import sys
import argparse
import requests
import vimeo
import time
import json
from dotenv import load_dotenv
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed


def load_config():
    """Load configuration from .config.json file"""
    config_file = Path('../.config.json')
    if not config_file.exists():
        print("❌ Configuration file .config.json not found!")
        print("Please run 1-setup.py first to create the configuration.")
        sys.exit(1)
    
    try:
        with open(config_file, 'r') as f:
            config = json.load(f)
        
        # Validate required fields
        if 'project_path' not in config:
            print("❌ Invalid configuration: missing 'project_path' field")
            sys.exit(1)
        
        if 'language_code' not in config:
            print("❌ Invalid configuration: missing 'language_code' field")
            sys.exit(1)
        
        return config
    except json.JSONDecodeError as e:
        print(f"❌ Error reading configuration file: {e}")
        sys.exit(1)


def load_vimeo_folders():
    """Load vimeo-folders.json file"""
    folders_file = Path('../vimeo-folders.json')
    if not folders_file.exists():
        print("❌ vimeo-folders.json file not found!")
        print("This file should contain the mapping between language codes and Vimeo folder IDs.")
        sys.exit(1)
    
    try:
        with open(folders_file, 'r') as f:
            data = json.load(f)
        
        if 'languages' not in data:
            print("❌ Invalid vimeo-folders.json: missing 'languages' field")
            sys.exit(1)
        
        return data['languages']
    except json.JSONDecodeError as e:
        print(f"❌ Error reading vimeo-folders.json: {e}")
        sys.exit(1)


def get_folder_id_for_language(language_code, vimeo_folders):
    """Get the Vimeo folder ID for a given language code"""
    language_code = language_code.lower()
    
    for language in vimeo_folders:
        if language['language_code'].lower() == language_code:
            return language['folder_id'], language['name']
    
    # If exact match not found, try partial matches
    for language in vimeo_folders:
        if language['language_code'].lower().startswith(language_code) or language_code.startswith(language['language_code'].lower()):
            return language['folder_id'], language['name']
    
    return None, None


def list_available_languages(vimeo_folders):
    """List all available languages and their codes"""
    print("\nAvailable languages:")
    print("-" * 50)
    for language in vimeo_folders:
        print(f"{language['language_code']:8} - {language['name']}")
    print("-" * 50)


def get_videos_output_dir(config):
    """Get the videos output directory from configuration"""
    project_path = config['project_path']
    videos_dir = os.path.join(project_path, 'videos')
    
    # Create the videos directory if it doesn't exist
    os.makedirs(videos_dir, exist_ok=True)
    
    return videos_dir


def create_env_file():
    """Create a .env file if it doesn't exist"""
    env_path = Path('../.env')
    
    if env_path.exists():
        return
    
    print("No .env file found. Creating one now...")
    print("Please enter your Vimeo API credentials:")
    
    client_id = input("Vimeo Client ID: ")
    client_secret = input("Vimeo Client Secret: ")
    access_token = input("Vimeo Access Token: ")
    
    with open('../.env', 'w') as f:
        f.write(f"VIMEO_CLIENT_ID={client_id}\n")
        f.write(f"VIMEO_CLIENT_SECRET={client_secret}\n")
        f.write(f"VIMEO_ACCESS_TOKEN={access_token}\n")
    
    print(".env file created successfully!")


def load_env_variables():
    """Load environment variables from .env file"""
    # Check if .env file exists, create it if it doesn't
    create_env_file()
    
    # Load environment variables from the parent directory
    load_dotenv('../.env')
    client_id = os.getenv("VIMEO_CLIENT_ID")
    client_secret = os.getenv("VIMEO_CLIENT_SECRET")
    access_token = os.getenv("VIMEO_ACCESS_TOKEN")
    
    if not all([client_id, client_secret, access_token]):
        print("Error: Missing Vimeo API credentials in .env file")
        print("Please update your .env file with VIMEO_CLIENT_ID, VIMEO_CLIENT_SECRET, and VIMEO_ACCESS_TOKEN")
        sys.exit(1)
    
    return client_id, client_secret, access_token


def get_vimeo_client():
    """Initialize and return a Vimeo client"""
    client_id, client_secret, access_token = load_env_variables()
    
    try:
        client = vimeo.VimeoClient(
            token=access_token,
            key=client_id,
            secret=client_secret
        )
        return client
    except Exception as e:
        print(f"Error initializing Vimeo client: {e}")
        sys.exit(1)


def get_team_library_videos(client, folder_id):
    """Get all videos in a team library folder"""
    videos = []
    page = 1
    per_page = 25  # Reduced from 100 to avoid "not enough content" errors
    has_more = True
    
    print(f"Fetching videos from team library folder ID: {folder_id}")
    
    while has_more:
        try:
            # Try different API endpoints to handle various folder types
            endpoints = [
                f'/me/folders/{folder_id}/videos',  # Personal folders
                f'/me/projects/{folder_id}/videos', # Projects
                f'/users/me/folders/{folder_id}/videos', # Alternative format
                f'/users/me/projects/{folder_id}/videos' # Alternative format for projects
            ]
            
            response = None
            success = False
            
            # Try each endpoint until one works
            for endpoint in endpoints:
                try:
                    print(f"Trying endpoint: {endpoint}")
                    response = client.get(endpoint, params={
                        'page': page,
                        'per_page': per_page,
                        'fields': 'uri,name,description,duration,created_time,link'
                    })
                    
                    if response.status_code == 200:
                        success = True
                        break
                except Exception as e:
                    print(f"Endpoint {endpoint} failed: {e}")
                    continue
            
            if not success or response is None:
                print("All endpoints failed. Please check the folder ID and your permissions.")
                if response:
                    print(f"Last error: Status code: {response.status_code}")
                    print(f"Response: {response.text}")
                sys.exit(1)
            
            data = response.json()
            
            # Add videos to the list
            for video in data['data']:
                # Extract video ID from URI (format: /videos/123456789)
                video_id = video['uri'].split('/')[-1]
                video['id'] = video_id
                videos.append(video)
            
            # Check if there are more pages
            if 'paging' in data and 'next' in data['paging'] and data['paging']['next'] is not None:
                page += 1
                print(f"Moving to page {page}...")
            else:
                has_more = False
                
            print(f"Found {len(videos)} videos so far...")
            
            # Add a small delay between requests to avoid rate limiting
            time.sleep(0.5)
            
        except Exception as e:
            print(f"Error getting videos from folder: {e}")
            sys.exit(1)
    
    print(f"Total videos found: {len(videos)}")
    return videos


def get_video_info(client, video_id):
    """Get detailed video information from Vimeo API"""
    try:
        response = client.get(f'/videos/{video_id}')
        
        if response.status_code != 200:
            print(f"Error: Failed to get video info. Status code: {response.status_code}")
            print(f"Response: {response.text}")
            return None
        
        return response.json()
    except Exception as e:
        print(f"Error getting video info: {e}")
        return None


def get_highest_quality_download_link(video_info):
    """Extract the highest quality download link from video info"""
    try:
        # Check if download links are available
        if 'download' not in video_info:
            print(f"Error: Download links not available for video '{video_info.get('name')}'")
            return None, None
        
        # Sort download links by quality (highest first)
        download_links = sorted(
            video_info['download'],
            key=lambda x: int(x.get('width', 0) * x.get('height', 0)),
            reverse=True
        )
        
        if not download_links:
            print(f"Error: No download links found for video '{video_info.get('name')}'")
            return None, None
        
        # Get the highest quality link
        highest_quality = download_links[0]
        
        return highest_quality['link'], highest_quality['quality']
    except Exception as e:
        print(f"Error extracting download link: {e}")
        return None, None


def download_video(url, output_path, video_title):
    """Download the video from the given URL"""
    try:
        print(f"Downloading video: {video_title}")
        print(f"Output path: {output_path}")
        
        # Make a streaming request
        with requests.get(url, stream=True) as r:
            r.raise_for_status()
            total_size = int(r.headers.get('content-length', 0))
            
            # Create directory if it doesn't exist
            output_dir = os.path.dirname(os.path.abspath(output_path))
            os.makedirs(output_dir, exist_ok=True)
            
            # Download with progress bar
            with open(output_path, 'wb') as f:
                downloaded = 0
                start_time = time.time()
                for chunk in r.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
                        downloaded += len(chunk)
                        
                        # Calculate progress and speed
                        percent = int(100 * downloaded / total_size) if total_size > 0 else 0
                        elapsed = time.time() - start_time
                        speed = downloaded / (1024 * 1024 * elapsed) if elapsed > 0 else 0
                        
                        # Print progress
                        sys.stdout.write(f"\rProgress: {percent}% | {downloaded/(1024*1024):.1f} MB / {total_size/(1024*1024):.1f} MB | {speed:.1f} MB/s")
                        sys.stdout.flush()
            
            print("\nDownload complete!")
            return True
    except Exception as e:
        print(f"\nError downloading video: {e}")
        # Remove partial file if download failed
        if os.path.exists(output_path):
            os.remove(output_path)
        return False


def sanitize_filename(filename):
    """Sanitize filename to remove invalid characters"""
    invalid_chars = '<>:"/\\|?*'
    for char in invalid_chars:
        filename = filename.replace(char, '_')
    return filename


def process_video(client, video, output_dir, max_retries=3):
    """Process a single video: get info, download link, and download"""
    video_id = video['id']
    video_title = video['name']
    safe_title = sanitize_filename(video_title)
    output_path = os.path.join(output_dir, f"{safe_title}.mp4")
    
    # Skip if file already exists
    if os.path.exists(output_path):
        print(f"Video already exists, skipping: {video_title}")
        return {
            'id': video_id,
            'title': video_title,
            'status': 'skipped',
            'path': output_path
        }
    
    # Get detailed video info
    print(f"Getting information for video: {video_title} (ID: {video_id})")
    
    retries = 0
    while retries < max_retries:
        try:
            video_info = get_video_info(client, video_id)
            if not video_info:
                print(f"Could not get info for video {video_id}, retrying...")
                retries += 1
                time.sleep(2)
                continue
            
            # Get download link
            download_url, quality = get_highest_quality_download_link(video_info)
            if not download_url:
                print(f"Could not get download link for video {video_id}, retrying...")
                retries += 1
                time.sleep(2)
                continue
            
            print(f"Found highest quality: {quality} for video: {video_title}")
            
            # Download the video
            success = download_video(download_url, output_path, video_title)
            
            if success:
                return {
                    'id': video_id,
                    'title': video_title,
                    'status': 'success',
                    'quality': quality,
                    'path': output_path
                }
            else:
                retries += 1
                time.sleep(2)
        except Exception as e:
            print(f"Error processing video {video_id}: {e}")
            retries += 1
            time.sleep(2)
    
    return {
        'id': video_id,
        'title': video_title,
        'status': 'failed',
        'error': f"Failed after {max_retries} attempts"
    }


def main():
    """Main function"""
    parser = argparse.ArgumentParser(description='Download all videos from a Vimeo team library folder based on language configuration')
    parser.add_argument('--max-workers', type=int, default=3, help='Maximum number of concurrent downloads (default: 3)')
    parser.add_argument('--list-only', action='store_true', help='Only list videos without downloading')
    parser.add_argument('--folder-id', help='Override: Use specific Vimeo folder ID instead of language lookup')
    parser.add_argument('--list-languages', action='store_true', help='List all available languages and exit')
    
    args = parser.parse_args()
    
    # Handle list-languages option
    if args.list_languages:
        try:
            vimeo_folders = load_vimeo_folders()
            list_available_languages(vimeo_folders)
            sys.exit(0)
        except Exception as e:
            print(f"Error loading languages: {e}")
            sys.exit(1)
    
    # Load configuration
    config = load_config()
    
    # Determine folder ID - either from override argument or language lookup
    if args.folder_id:
        folder_id = args.folder_id
        folder_name = f"Override: {folder_id}"
        print(f"Using override folder ID: {folder_id}")
    else:
        # Load vimeo-folders.json to get folder ID based on language
        vimeo_folders = load_vimeo_folders()
        folder_id, folder_name = get_folder_id_for_language(config['language_code'], vimeo_folders)
        
        if not folder_id:
            print(f"Error: No folder found for language code '{config['language_code']}' in vimeo-folders.json")
            list_available_languages(vimeo_folders)
            sys.exit(1)
        
        print(f"Using folder ID: {folder_id} (Name: {folder_name})")
    
    # Get videos output directory
    output_dir = get_videos_output_dir(config)
    
    # Initialize Vimeo client
    client = get_vimeo_client()
    
    # Get videos from the team library folder
    videos = get_team_library_videos(client, folder_id)
    
    if not videos:
        print("No videos found in the specified folder.")
        sys.exit(0)
    
    # Print video list
    print("\nVideos in folder:")
    for i, video in enumerate(videos, 1):
        print(f"{i}. {video['name']} (ID: {video['id']})")
    
    # Exit if list-only mode
    if args.list_only:
        print("\nList-only mode, exiting without downloading.")
        sys.exit(0)
    
    # Print output directory information
    print(f"\nDownloading videos to: {output_dir}")
    print(f"Project path: {config['project_path']}")
    print(f"Language: {config.get('language_code', 'unknown')}")
    print(f"Vimeo folder: {folder_name} (ID: {folder_id})")
    
    # Download videos
    results = []
    
    # Use ThreadPoolExecutor for concurrent downloads
    with ThreadPoolExecutor(max_workers=args.max_workers) as executor:
        # Submit all download tasks
        future_to_video = {
            executor.submit(process_video, client, video, output_dir): video
            for video in videos
        }
        
        # Process results as they complete
        for future in as_completed(future_to_video):
            video = future_to_video[future]
            try:
                result = future.result()
                results.append(result)
                print(f"Completed processing video: {video['name']} - Status: {result['status']}")
            except Exception as e:
                print(f"Error processing video {video['name']}: {e}")
                results.append({
                    'id': video['id'],
                    'title': video['name'],
                    'status': 'error',
                    'error': str(e)
                })
    
    # Save results to a JSON file
    results_file = os.path.join(output_dir, "download_results.json")
    with open(results_file, 'w') as f:
        json.dump(results, f, indent=2)
    
    # Print summary
    success_count = sum(1 for r in results if r['status'] == 'success')
    skipped_count = sum(1 for r in results if r['status'] == 'skipped')
    failed_count = sum(1 for r in results if r['status'] in ['failed', 'error'])
    
    print("\nDownload Summary:")
    print(f"Total videos: {len(videos)}")
    print(f"Successfully downloaded: {success_count}")
    print(f"Skipped (already exists): {skipped_count}")
    print(f"Failed: {failed_count}")
    print(f"Results saved to: {results_file}")


if __name__ == "__main__":
    main() 