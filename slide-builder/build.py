#!/usr/bin/env python3
"""
ZUME Slide Full Builder - Comprehensive Build Script
This script walks through all the build steps, collecting information
from the command line and storing variables in temporary memory.
"""

import os
import sys
import json
import subprocess
import tempfile
from pathlib import Path
from typing import Dict, Any


class BuildRunner:
    """Manages the entire build process with temporary configuration storage"""
    
    def __init__(self):
        self.config = {}
        self.temp_dir = None
        self.original_config_file = None
        self.backup_created = False
    
    def setup_temp_config(self):
        """Create a temporary directory for storing configuration during build"""
        self.temp_dir = tempfile.mkdtemp(prefix="zume_build_")
        print(f"📁 Created temporary config directory: {self.temp_dir}")
        
        # Check if existing config file exists and back it up
        if os.path.exists('.config.json'):
            self.original_config_file = Path('.config.json').read_text()
            self.backup_created = True
            print("💾 Backed up existing .config.json")
    
    def cleanup_temp_config(self):
        """Clean up temporary configuration and restore original if needed"""
        if self.backup_created and self.original_config_file:
            # Restore original config
            with open('.config.json', 'w') as f:
                f.write(self.original_config_file)
            print("🔄 Restored original .config.json")
        elif not self.backup_created and os.path.exists('.config.json'):
            # Remove the config file we created
            os.remove('.config.json')
            print("🧹 Removed temporary .config.json")
        
        # Clean up temporary directory
        if self.temp_dir and os.path.exists(self.temp_dir):
            import shutil
            shutil.rmtree(self.temp_dir)
            print("🧹 Cleaned up temporary directory")
    
    def save_temp_config(self):
        """Save current configuration to temporary file and main config"""
        # Save to main config file for scripts to use
        with open('.config.json', 'w') as f:
            json.dump(self.config, f, indent=2)
        
        # Also save to temp directory for tracking
        temp_config_path = os.path.join(self.temp_dir, 'build_config.json')
        with open(temp_config_path, 'w') as f:
            json.dump(self.config, f, indent=2)
    
    def collect_basic_info(self):
        """Collect basic build information"""
        print("🚀 ZUME Slide Full Builder")
        print("=" * 50)
        print("This script will walk you through building a complete language package.")
        print("All information will be stored in temporary memory for this build session.\n")
        
        # Get language code
        while True:
            language = input("What is the language code? (e.g., 'en', 'es', 'fr', 'de'): ").strip().lower()
            if language and len(language) >= 2:
                self.config['language_code'] = language
                break
            print("❌ Please enter a valid language code (2+ characters)")
        
        # Get folder destination
        while True:
            folder = input("What is the folder destination? (default: current directory): ").strip()
            if not folder:
                folder = "."
            
            folder_path = Path(folder).resolve()
            if not folder_path.exists():
                create = input(f"Directory {folder_path} doesn't exist. Create it? (y/n): ").lower()
                if create in ['y', 'yes']:
                    folder_path.mkdir(parents=True, exist_ok=True)
                    break
                else:
                    continue
            else:
                break
        
        self.config['folder_location'] = str(folder_path)
        self.config['project_path'] = str(folder_path / language)
        
        print(f"\n📋 Configuration Summary:")
        print(f"   Language: {self.config['language_code']}")
        print(f"   Destination: {self.config['folder_location']}")
        print(f"   Project Path: {self.config['project_path']}")
    
    def collect_vimeo_info(self):
        """Collect Vimeo API credentials"""
        print("\n🔑 Vimeo API Configuration")
        
        # Check if .env file exists and load existing variables
        env_vars = {}
        if os.path.exists('.env'):
            with open('.env', 'r') as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith('#') and '=' in line:
                        key, value = line.split('=', 1)
                        env_vars[key.strip()] = value.strip().strip('"\'')
        
        # Check if all required credentials are present and not empty
        required_credentials = ['VIMEO_CLIENT_ID', 'VIMEO_CLIENT_SECRET', 'VIMEO_ACCESS_TOKEN']
        all_present = True
        
        for cred in required_credentials:
            value = env_vars.get(cred, '').strip()
            if not value:
                all_present = False
                break
        
        if all_present:
            # All credentials are present, just show confirmation
            print("✅ Vimeo credentials found in .env file:")
            for cred in required_credentials:
                masked_value = env_vars[cred][:8] + "..." if len(env_vars[cred]) > 8 else env_vars[cred]
                print(f"   ✅ {cred}: {masked_value}")
            print("✅ All Vimeo credentials are configured!")
            return
        
        # Some credentials are missing, collect them interactively
        print("You can get these from: https://developer.vimeo.com/apps")
        print("Missing or empty Vimeo credentials detected. Please provide them:")
        
        for cred in required_credentials:
            current_value = env_vars.get(cred, '').strip()
            if current_value:
                print(f"Current {cred}: {current_value[:10]}...")
                use_current = input(f"Use current {cred}? (y/n): ").lower().strip()
                if use_current in ['y', 'yes', '']:
                    continue
            
            while True:
                value = input(f"Enter {cred}: ").strip()
                if value:
                    env_vars[cred] = value
                    break
                print("❌ This value is required.")
        
        # Save to .env file
        with open('.env', 'w') as f:
            f.write("# ZUME Slide Full Builder Environment Variables\n")
            f.write("# Generated by build script\n\n")
            for key, value in env_vars.items():
                f.write(f'{key}="{value}"\n')
        
        print("✅ Vimeo credentials saved to .env file")
    
    def collect_vimeo_folder_id(self):
        """Get Vimeo folder ID from vimeo-folders.json based on language code"""
        print("\n📹 Video Download Configuration")
        
        # Check if vimeo-folders.json exists
        if not os.path.exists('vimeo-folders.json'):
            print("❌ vimeo-folders.json not found. Please ensure this file exists.")
            while True:
                folder_id = input("Please enter the Vimeo folder ID manually: ").strip()
                if folder_id:
                    self.config['vimeo_folder_id'] = folder_id
                    break
                print("❌ Please enter a valid Vimeo folder ID")
            return
        
        try:
            # Load the vimeo-folders.json file
            with open('vimeo-folders.json', 'r', encoding='utf-8') as f:
                folders_data = json.load(f)
            
            # Find the language entry
            language_code = self.config['language_code']
            folder_id = None
            language_name = None
            
            for language in folders_data.get('languages', []):
                if language.get('language_code') == language_code:
                    folder_id = language.get('folder_id')
                    language_name = language.get('name')
                    break
            
            if folder_id:
                self.config['vimeo_folder_id'] = folder_id
                print(f"✅ Found Vimeo folder ID for {language_name} ({language_code}): {folder_id}")
            else:
                print(f"❌ Language code '{language_code}' not found in vimeo-folders.json")
                print("Available languages:")
                for lang in folders_data.get('languages', []):
                    print(f"  - {lang.get('name')} ({lang.get('language_code')}): {lang.get('folder_id')}")
                
                while True:
                    folder_id = input("Please enter the Vimeo folder ID manually: ").strip()
                    if folder_id:
                        self.config['vimeo_folder_id'] = folder_id
                        break
                    print("❌ Please enter a valid Vimeo folder ID")
                    
        except (json.JSONDecodeError, KeyError) as e:
            print(f"❌ Error reading vimeo-folders.json: {e}")
            while True:
                folder_id = input("Please enter the Vimeo folder ID manually: ").strip()
                if folder_id:
                    self.config['vimeo_folder_id'] = folder_id
                    break
                print("❌ Please enter a valid Vimeo folder ID")
    
    def confirm_continue(self, step_name: str) -> str:
        """Ask user to confirm continuing to next step"""
        print(f"\n⏸️  Ready to proceed with: {step_name}")
        while True:
            response = input("Review and continue? (Y/n/s=skip/q=quit): ").strip().lower()
            if response in ['', 'y', 'yes']:
                return 'continue'
            elif response in ['n', 'no', 's', 'skip']:
                return 'skip'
            elif response in ['q', 'quit', 'c', 'cancel']:
                return 'cancel'
            else:
                print("❌ Please enter 'y' to continue, 'n' to skip, 's' to skip, or 'q' to quit.")
    
    def run_script(self, script_name: str, description: str):
        """Run a Python script with error handling"""
        print(f"\n🔄 Running {script_name} - {description}")
        print("-" * 50)
        
        try:
            # Run the script
            result = subprocess.run(
                [sys.executable, script_name],
                capture_output=False,
                text=True,
                cwd=os.getcwd()
            )
            
            if result.returncode == 0:
                print(f"✅ {script_name} completed successfully")
                return True
            else:
                print(f"❌ {script_name} failed with return code {result.returncode}")
                return False
                
        except Exception as e:
            print(f"❌ Error running {script_name}: {e}")
            return False
    
    def run_setup(self):
        """Run the setup script"""
        # Save current config
        self.save_temp_config()
        
        # Check if Vimeo credentials are already present
        credentials_exist = self.check_vimeo_credentials()
        
        # Prepare arguments for setup script
        args = [
            sys.executable, '1-setup.py',
            '--language', self.config['language_code'],
            '--folder', self.config['folder_location']
        ]
        
        # Only force interactive mode if credentials don't exist
        if not credentials_exist:
            args.append('--force-interactive')
        
        print(f"\n🔄 Running 1-setup.py - Project Setup")
        print("-" * 50)
        
        try:
            result = subprocess.run(args, capture_output=False, text=True)
            if result.returncode == 0:
                print("✅ Setup completed successfully")
                return True
            else:
                print(f"❌ Setup failed with return code {result.returncode}")
                return False
        except Exception as e:
            print(f"❌ Error running setup: {e}")
            return False
    
    def check_vimeo_credentials(self):
        """Check if Vimeo credentials are present and not empty"""
        if not os.path.exists('.env'):
            return False
        
        env_vars = {}
        with open('.env', 'r') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    key, value = line.split('=', 1)
                    env_vars[key.strip()] = value.strip().strip('"\'')
        
        required_credentials = ['VIMEO_CLIENT_ID', 'VIMEO_CLIENT_SECRET', 'VIMEO_ACCESS_TOKEN']
        for cred in required_credentials:
            if not env_vars.get(cred, '').strip():
                return False
        
        return True
    
    def verify_setup(self):
        """Verify that setup completed properly"""
        print("\n🔍 Verifying setup...")
        
        # Check if project directory was created
        project_path = Path(self.config['project_path'])
        if not project_path.exists():
            print(f"❌ Project directory not found: {project_path}")
            return False
        
        # Check if required subdirectories exist
        required_dirs = ['10', '20', 'intensive', 'videos']
        for dir_name in required_dirs:
            dir_path = project_path / dir_name
            if not dir_path.exists():
                print(f"❌ Required directory not found: {dir_path}")
                return False
        
        # Check if .env file exists and has required variables
        if not os.path.exists('.env'):
            print("❌ .env file not found")
            return False
        
        # Verify Vimeo credentials in .env file
        env_vars = {}
        with open('.env', 'r') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    key, value = line.split('=', 1)
                    env_vars[key.strip()] = value.strip().strip('"\'')
        
        required_credentials = ['VIMEO_CLIENT_ID', 'VIMEO_CLIENT_SECRET', 'VIMEO_ACCESS_TOKEN']
        for cred in required_credentials:
            if not env_vars.get(cred, '').strip():
                print(f"❌ Missing or empty {cred} in .env file")
                return False
        
        # Check if config file was created
        if not os.path.exists('.config.json'):
            print("❌ .config.json file not found")
            return False
        
        print("✅ Setup verification passed")
        return True
    
    def run_video_download(self):
        """Run the video download script"""
        # Update config with Vimeo folder ID
        self.save_temp_config()
        
        # Video download script requires folder_id as --folder-id argument
        print(f"\n🔄 Running 2-video-download.py - Video Download")
        print("-" * 50)
        
        try:
            # Run the script with folder_id as named argument
            result = subprocess.run(
                [sys.executable, '2-video-download.py', '--folder-id', self.config['vimeo_folder_id']],
                capture_output=False,
                text=True,
                cwd=os.getcwd()
            )
            
            if result.returncode == 0:
                print(f"✅ 2-video-download.py completed successfully")
                return True
            else:
                print(f"❌ 2-video-download.py failed with return code {result.returncode}")
                return False
                
        except Exception as e:
            print(f"❌ Error running 2-video-download.py: {e}")
            return False
    
    def run_slides_download(self):
        """Run the slides download script"""
        # Slides download script accepts command-line arguments
        print(f"\n🔄 Running 3-slides-download.py - Slides Download")
        print("-" * 50)
        
        try:
            # Run the script with optimal arguments
            result = subprocess.run(
                [sys.executable, '3-slides-download.py', 
                 '--curriculum', 'all',  # Process all curricula
                 '--missing-only',       # Only process missing screenshots
                 '--width', '3000',      # High-resolution screenshots
                 '--height', '1680',
                 '--wait', '5'],         # Wait 5 seconds for page load
                capture_output=False,
                text=True,
                cwd=os.getcwd()
            )
            
            if result.returncode == 0:
                print(f"✅ 3-slides-download.py completed successfully")
                return True
            else:
                print(f"❌ 3-slides-download.py failed with return code {result.returncode}")
                return False
                
        except Exception as e:
            print(f"❌ Error running 3-slides-download.py: {e}")
            return False
    
    def run_rename_files(self):
        """Run the file rename script"""
        # Check if required JSON files exist
        json_files = ['10.json', '20.json', 'intensive.json']
        missing_files = []
        
        for json_file in json_files:
            if not os.path.exists(json_file):
                missing_files.append(json_file)
        
        if missing_files:
            print(f"\n⚠️  Warning: Missing JSON configuration files: {', '.join(missing_files)}")
            print("The rename script may not work properly without these files.")
            response = input("Continue anyway? (y/n): ").lower().strip()
            if response not in ['y', 'yes']:
                print("Rename step cancelled by user.")
                return False
        
        # Rename files script uses the config file automatically
        return self.run_script('4-rename-files.py', 'File Rename and Organization')
    
    def display_build_summary(self):
        """Display a summary of the build process"""
        print("\n" + "=" * 50)
        print("🎉 BUILD PROCESS SUMMARY")
        print("=" * 50)
        print(f"Language: {self.config['language_code']}")
        print(f"Project Path: {self.config['project_path']}")
        print(f"Vimeo Folder ID: {self.config.get('vimeo_folder_id', 'N/A')}")
        
        # Check if output directory exists
        output_dir = Path(self.config['project_path']) / 'output'
        if output_dir.exists():
            print(f"\n📁 Output Directory: {output_dir}")
            
            # Count files in each subdirectory
            subdirs = ['videos', '10', '20', 'intensive']
            for subdir in subdirs:
                subdir_path = output_dir / subdir
                if subdir_path.exists():
                    file_count = len(list(subdir_path.glob('*')))
                    print(f"   {subdir}/: {file_count} files")
        
        print("\n✅ Build process completed!")
        print("You can now use the files in the output directory.")
    
    def run_build(self):
        """Run the complete build process"""
        try:
            # Setup temporary configuration
            self.setup_temp_config()
            
            # Step 1: Collect basic information
            self.collect_basic_info()
            
            # Step 2: Collect Vimeo credentials (if not already present)
            self.collect_vimeo_info()
            
            # Step 3: Run setup script
            setup_action = self.confirm_continue("Project Setup (1-setup.py)")
            if setup_action == 'cancel':
                print("Build cancelled by user.")
                return
            elif setup_action == 'skip':
                print("⏭️  Skipping Project Setup step.")
            else:  # continue
                if not self.run_setup():
                    print("❌ Setup failed. Build process stopped.")
                    return
                
                # Verify setup completed properly
                if not self.verify_setup():
                    print("❌ Setup verification failed. Build process stopped.")
                    return
            
            # Step 4: Collect Vimeo folder ID and run video download
            video_action = self.confirm_continue("Video Download (2-video-download.py)")
            if video_action == 'cancel':
                print("Build cancelled by user.")
                return
            elif video_action == 'skip':
                print("⏭️  Skipping Video Download step.")
            else:  # continue
                self.collect_vimeo_folder_id()
                
                if not self.run_video_download():
                    print("❌ Video download failed. Build process stopped.")
                    return
            
            # Step 5: Run slides download
            slides_action = self.confirm_continue("Slides Download (3-slides-download.py)")
            if slides_action == 'cancel':
                print("Build cancelled by user.")
                return
            elif slides_action == 'skip':
                print("⏭️  Skipping Slides Download step.")
            else:  # continue
                if not self.run_slides_download():
                    print("❌ Slides download failed. Build process stopped.")
                    return
            
            # Step 6: Run file rename and organization
            rename_action = self.confirm_continue("File Rename and Organization (4-rename-files.py)")
            if rename_action == 'cancel':
                print("Build cancelled by user.")
                return
            elif rename_action == 'skip':
                print("⏭️  Skipping File Rename and Organization step.")
            else:  # continue
                if not self.run_rename_files():
                    print("❌ File rename failed. Build process stopped.")
                    return
            
            # Step 7: Display build summary
            self.display_build_summary()
            
        except KeyboardInterrupt:
            print("\n\n⛔ Build process interrupted by user.")
        except Exception as e:
            print(f"\n❌ Unexpected error during build: {e}")
        finally:
            # Clean up temporary configuration
            self.cleanup_temp_config()


def main():
    """Main function to run the build process"""
    print("🚀 ZUME Slide Full Builder - Complete Build Script")
    print("=" * 60)
    print("This script automates the complete build process for ZUME language packages.")
    print("It walks through all steps and stores configuration in temporary memory")
    print("to allow concurrent builds of multiple languages.")
    print()
    print("Build steps:")
    print("  1. Project Setup (1-setup.py)")
    print("  2. Video Download (2-video-download.py)")
    print("  3. Slides Download (3-slides-download.py)")
    print("  4. File Rename and Organization (4-rename-files.py)")
    print()
    print("For concurrent builds, run this script in separate terminals/directories.")
    print("=" * 60)
    print()
    
    # Check if all required scripts exist
    required_scripts = ['1-setup.py', '2-video-download.py', '3-slides-download.py', '4-rename-files.py']
    missing_scripts = []
    
    for script in required_scripts:
        if not os.path.exists(script):
            missing_scripts.append(script)
    
    if missing_scripts:
        print(f"❌ Missing required scripts: {', '.join(missing_scripts)}")
        print("Please make sure all scripts are in the current directory.")
        sys.exit(1)
    
    # Check if required JSON files exist
    json_files = ['10.json', '20.json', 'intensive.json']
    missing_json = []
    
    for json_file in json_files:
        if not os.path.exists(json_file):
            missing_json.append(json_file)
    
    if missing_json:
        print(f"⚠️  Warning: Missing JSON configuration files: {', '.join(missing_json)}")
        print("The build process will work but file renaming may not be optimal.")
        print()
    
    # Check if vimeo-folders.json exists
    if not os.path.exists('vimeo-folders.json'):
        print("⚠️  Warning: vimeo-folders.json not found.")
        print("The build process will prompt for Vimeo folder ID manually.")
        print()
    
    # Run the build process
    runner = BuildRunner()
    runner.run_build()


if __name__ == "__main__":
    main()
