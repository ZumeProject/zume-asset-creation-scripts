import os
import sys
import time
import argparse
import json
import datetime
from pathlib import Path
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager


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
        if 'project_path' not in config or 'language_code' not in config:
            print("❌ Invalid configuration: missing required fields")
            sys.exit(1)
        
        return config
    except json.JSONDecodeError as e:
        print(f"❌ Error reading configuration file: {e}")
        sys.exit(1)


def get_slides_output_dir(config, curriculum_folder):
    """Get the slides output directory for a specific curriculum"""
    project_path = config['project_path']
    slides_dir = os.path.join(project_path, curriculum_folder)
    
    # Create the slides directory if it doesn't exist
    os.makedirs(slides_dir, exist_ok=True)
    
    return slides_dir


def take_screenshot(url, output_path, width=3000, height=1680, wait_time=3):
    """
    Visit a URL and take a screenshot at specified dimensions.
    
    Args:
        url (str): The URL to visit
        output_path (str): Path where screenshot will be saved
        width (int): Screenshot width in pixels
        height (int): Screenshot height in pixels
        wait_time (int): Time to wait for page to load in seconds
    """
    print(f"Taking {width}x{height} screenshot of {url}")
    
    # Set up Chrome options
    chrome_options = Options()
    chrome_options.add_argument("--headless")  # Run in headless mode (no UI)
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument(f"--window-size={width},{height}")
    
    # Initialize the Chrome driver
    driver = webdriver.Chrome(
        service=Service(ChromeDriverManager().install()),
        options=chrome_options
    )
    
    try:
        # Set window size
        driver.set_window_size(width, height)
        
        # Navigate to the URL
        driver.get(url)
        
        # Wait for the page to load
        time.sleep(wait_time)
        
        # Take screenshot
        driver.save_screenshot(output_path)
        print(f"Screenshot saved to {output_path}")
        return True
    
    except Exception as e:
        print(f"Error taking screenshot: {e}")
        return False
    
    finally:
        # Close the driver
        driver.quit()

def get_progress_file_path(config, curriculum):
    """Get the path to the progress tracking file for a specific curriculum."""
    # Use folder mapping for correct directory name
    curriculum_folder_mapping = {
        "ten_session": "10",
        "twenty_session": "20",
        "intensive_session": "intensive"
    }
    folder_name = curriculum_folder_mapping.get(curriculum, curriculum)
    slides_dir = get_slides_output_dir(config, folder_name)
    return os.path.join(slides_dir, f"{folder_name}_progress.json")

def save_progress(config, curriculum, session_num, current_index):
    """Save the current progress to a JSON file."""
    progress_file = get_progress_file_path(config, curriculum)
    os.makedirs(os.path.dirname(progress_file), exist_ok=True)
    
    with open(progress_file, 'w') as f:
        json.dump({
            "session": session_num,
            "index": current_index
        }, f)
    
    print(f"Progress saved: {curriculum}/{config['language_code']} - Session {session_num}, processed up to index {current_index}")

def load_progress(config, curriculum):
    """Load the current progress from the JSON file if it exists."""
    progress_file = get_progress_file_path(config, curriculum)
    
    if os.path.exists(progress_file):
        try:
            with open(progress_file, 'r') as f:
                data = json.load(f)
                session = data.get("session")
                index = data.get("index", -1)
                print(f"Resuming {curriculum}/{config['language_code']} from Session {session}, index {index + 1}")
                return session, index + 1
        except Exception as e:
            print(f"Error loading progress file: {e}")
    
    # Start from the beginning if no valid progress file
    first_session = next(iter(curricula[curriculum].keys()))
    return first_session, 0

def find_missing_screenshots(config, curriculum, sessions_dict):
    """Find which screenshots are missing by checking the output directory."""
    missing = []
    
    # Use folder mapping for correct directory name
    curriculum_folder_mapping = {
        "ten_session": "10",
        "twenty_session": "20",
        "intensive_session": "intensive"
    }
    folder_name = curriculum_folder_mapping.get(curriculum, curriculum)
    
    for session_num, slides in sessions_dict.items():
        for i, slide_id in enumerate(slides):
            slide_id = slide_id.strip("'\"")  # Remove any quotes
            
            # Check if any file exists with the pattern *_session_{session_num}_{slide_id}.png
            # instead of looking for the exact filename
            curriculum_dir = get_slides_output_dir(config, folder_name)
            
            # If the directory doesn't exist yet, all slides are missing
            if not os.path.exists(curriculum_dir):
                missing.append((session_num, i, slide_id))
                continue
                
            pattern = f"*_session_{session_num}_{slide_id}.png"
            matching_files = [f for f in os.listdir(curriculum_dir) if os.path.isfile(os.path.join(curriculum_dir, f)) and f.endswith(f"_session_{session_num}_{slide_id}.png")]
            
            if not matching_files:
                missing.append((session_num, i, slide_id))
    
    return missing

def process_curriculum(curriculum_name, sessions_dict, config, width, height, wait_time, starting_session=None, starting_index=0):
    """Process a specific curriculum's slides."""
    # Create curriculum directory using folder mapping
    curriculum_folder_mapping = {
        "ten_session": "10",
        "twenty_session": "20",
        "intensive_session": "intensive"
    }
    folder_name = curriculum_folder_mapping.get(curriculum_name, curriculum_name)
    curriculum_dir = get_slides_output_dir(config, folder_name)
    language = config['language_code']
    
    # Determine where to start
    sessions = list(sessions_dict.keys())
    start_from = sessions.index(starting_session) if starting_session in sessions else 0
    
    # Loop through sessions
    for i in range(start_from, len(sessions)):
        session_num = sessions[i]
        slides = sessions_dict[session_num]
        
        print(f"\nProcessing {curriculum_name} in {language} - Session {session_num} ({len(slides)} slides)")
        
        # Determine starting index within the session
        idx_start = starting_index if i == start_from else 0
        
        # Loop through slides in the session
        for j in range(idx_start, len(slides)):
            slide_id = slides[j].strip("'\"")  # Remove any quotes that might be in the string
            
            # Determine the type parameter based on curriculum name
            type_param = ""
            if curriculum_name == "ten_session":
                type_param = "10"
            elif curriculum_name == "twenty_session":
                type_param = "20"
            elif curriculum_name == "intensive_session":
                type_param = "intensive"
            
            # Construct URL with the language code, session number, type, and slide parameter
            url = f"https://zume.training/{language}/presenter?session={session_num}&type={type_param}&view=slideshow&screenshot=&slide={slide_id}"
            
            # Get current timestamp
            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            
            # Construct output path - include timestamp at the beginning of the filename
            output_path = os.path.join(curriculum_dir, f"{timestamp}_session_{session_num}_{slide_id}.png")
            
            # Take the screenshot
            success = take_screenshot(
                url,
                output_path,
                width,
                height,
                wait_time
            )
            
            # If screenshot failed, try one more time
            if not success:
                print(f"Retrying screenshot for slide {slide_id}...")
                time.sleep(2)  # Wait a bit before retrying
                # Update timestamp for retry
                timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
                output_path = os.path.join(curriculum_dir, f"{timestamp}_session_{session_num}_{slide_id}.png")
                success = take_screenshot(
                    url,
                    output_path,
                    width,
                    height,
                    wait_time
                )
            
            # Save progress after each screenshot
            save_progress(config, curriculum_name, session_num, j)

def main():
    # Define curriculum dictionaries
    global curricula
    
    ten_session = {
        "1": ["s1_1_1", "s1_1_2", "s1_1_3", "s1_1_4", "t1_a", "t1_b", "t1_c", "t2_a", "t2_b", "t2_c", "t3_a", "t3_b", "t3_c", "t4_a", "t4_b", "t4_c", "t5_a", "t5_b", "t5_c", "s1_1_20", "s1_1_21", "final"],  # session 1
        "2": ["s1_2_1", "s1_2_2", "s1_2_3", "s1_2_4", "s1_2_5", "t6_a", "t6_b", "t6_c", "t7_a", "t7_b", "t7_c", "t7_d", "t8_a", "t8_b", "t8_c", "s1_2_6", "s1_2_7", "final"],  # session 2
        "3": ["s1_3_1", "s1_3_2", "s1_3_3", "s1_3_4", "s1_3_5", "t9_a", "t9_b", "t9_c", "t10_a", "t10_b", "t10_c", "t10_d", "t10_e", "s1_3_8", "t11_a", "t11_b", "t11_c", "t11_d", "s1_3_10", "s1_3_11", "s1_3_12", "final"],  # session 3
        "4": ["s1_4_1", "s1_4_2", "s1_4_3", "s1_4_4", "s1_4_5", "t12_a", "t12_b", "t12_c", "t13_a", "t13_b", "t13_c", "t14_a", "t14_b", "t14_c", "t15_a", "t15_b", "t15_c", "t16_a", "t16_b", "t16_c", "s1_4_6", "s1_4_7", "final"],  # session 4
        "5": ["s1_5_1", "s1_5_2", "s1_5_3", "s1_5_4", "s1_5_5", "t17_a", "t17_b", "t18_a", "t18_b", "t18_c", "t19_a", "t17_d", "t17_e", "final"],  # session 5
        "6": ["s1_6_1", "s1_6_2", "s1_6_3", "s1_6_4", "s1_6_5", "t20_a", "t20_b", "t20_c", "t21_a", "t21_b", "t21_c", "s1_6_6", "s1_6_7", "final"],  # session 6
        "7": ["s1_7_1", "s1_7_2", "s1_7_3", "s1_7_4", "s1_7_5", "t22_a", "t22_b", "t22_c", "s1_7_6", "s1_7_7", "s1_7_8", "s1_7_9", "final"],  # session 7
        "8": ["s1_8_1", "s1_8_2", "s1_8_3", "s1_8_4", "s1_8_5", "t23_a", "t23_b", "t23_c", "s1_8_6", "s1_8_7", "s1_8_8", "final"],  # session 8
        "9": ["s1_9_1", "s1_9_2", "s1_9_3", "s1_9_4", "s1_9_5", "t24_a", "t24_b", "t24_c", "t25_a", "t25_b", "t25_c", "t26_a", "t26_b", "t26_c", "t28_a", "t28_b", "t28_c", "t28_d", "t28_e", "t31_a", "t31_b", "t31_c", "t31_d", "t31_e", "t32_a", "t32_b", "t32_c", "s1_9_9", "s1_9_10", "final"],  # session 9
        "10": ["s1_10_1", "s1_10_2", "s1_10_3", "s1_10_4", "s1_10_5", "s1_10_6", "t29_a", "t29_b", "t29_c", "t30_a", "t30_b", "t30_c", "t27_a", "t27_b", "t27_c", "s1_10_7", "next_steps", "congratulations", "final"]  # session 10
    }

    twenty_session = {
        "1": ["s2_1_1", "s2_1_2", "s2_1_3", "s2_1_4", "t1_a", "t1_b", "t1_c", "t2_a", "t2_b", "t2_c", "t3_a", "t3_b", "t3_c", "s2_1_5", "s2_1_6", "final"],  # session 1
        "2": ["s2_2_1", "s2_2_2", "s2_2_3", "s2_2_4", "s2_2_5", "t4_a", "t4_b", "t4_c", "s2_2_6", "s2_2_7", "final"],  # session 2
        "3": ["s2_3_1", "s2_3_2", "s2_3_3", "s2_3_4", "s2_3_5", "t5_a", "t5_b", "t5_c", "s2_3_6", "s2_3_7", "final"],  # session 3
        "4": ["s2_4_1", "s2_4_2", "s2_4_3", "s2_4_4", "s2_4_5", "t6_a", "t6_b", "t6_c", "t8_a", "t8_b", "t8_c", "s2_4_6", "s2_4_7", "final"],  # session 4
        "5": ["s2_5_1", "s2_5_2", "s2_5_3", "s2_5_4", "s2_5_5", "t7_a", "t7_b", "t7_cc", "t7_d", "s2_5_6", "s2_5_7", "final"],  # session 5
        "6": ["s2_6_1", "s2_6_2", "s2_6_3", "s2_6_4", "s2_6_5", "t9_a", "t9_b", "t9_c", "t13_a", "t13_b", "t13_c", "t10_a", "t10_b", "t10_c", "t10_d", "t10_e", "s2_6_6", "s2_6_7", "final"],  # session 6
        "7": ["s2_7_1", "s2_7_2", "s2_7_3", "s2_7_4", "s2_7_5", "s2_7_6", "s2_7_7", "s2_7_8", "final"],  # session 7
        "8": ["s2_8_1", "s2_8_2", "s2_8_3", "s2_8_4", "s2_8_5", "t11_a", "t11_b", "t11_c", "t11_d", "t12_a", "t12_b", "t12_c", "s2_8_6", "s2_8_7", "final"],  # session 8
        "9": ["s2_9_1", "s2_9_2", "s2_9_3", "s2_9_4", "s2_9_5", "s2_9_6", "s2_9_7", "s2_9_8", "s2_9_9", "final"],  # session 9
        "10": ["s2_10_1", "s2_10_2", "s2_10_3", "s2_10_4", "s2_10_5", "t14_a", "t14_b", "t14_c", "t15_a", "t15_b", "t15_c", "t16_a", "t16_b", "t16_c", "s2_10_6", "s2_10_7", "final"],  # session 10
        "11": ["s2_11_1", "s2_11_2", "s2_11_3", "s2_11_4", "s2_11_5", "t17_a", "t17_b", "t17_d", "t17_e", "final"],  # session 11
        "12": ["s2_12_1", "s2_12_2", "s2_12_3", "s2_12_4", "s2_12_5", "t18_a", "t18_b", "t18_c", "t19_a", "s2_12_6", "s2_12_7", "final"],  # session 12
        "13": ["s2_13_1", "s2_13_2", "s2_13_3", "s2_13_4", "s2_13_5", "t20_a", "t20_b", "t20_c", "t21_aa", "t21_b", "t21_cc", "s2_13_6", "s2_13_7", "final"],  # session 13
        "14": ["s2_14_1", "s2_14_2", "s2_14_3", "s2_14_4", "s2_14_5", "s2_14_6", "s2_14_7", "s2_14_8", "final"],  # session 14
        "15": ["s2_15_1", "s2_15_2", "s2_15_3", "s2_15_4", "s2_15_5", "t22_a", "t22_b", "t22_c", "t23_a", "t23_b", "t23_c", "s2_15_6", "s2_15_7", "final"],  # session 15
        "16": ["s2_16_1", "s2_16_2", "s2_16_3", "s2_16_4", "s2_16_5", "t24_a", "t24_b", "t24_c", "t25_a", "t25_b", "t25_c", "t26_a", "t26_b", "t26_c", "s2_16_6", "s2_16_7", "final"],  # session 16
        "17": ["s2_17_1", "s2_17_2", "s2_17_3", "s2_17_4", "s2_17_5", "t29_a", "t29_b", "t29_c", "t28_a", "t28_b", "t28_c", "t28_d", "t28_e", "s2_17_6", "s2_17_7", "final"],  # session 17
        "18": ["s2_18_1", "s2_18_2", "s2_18_3", "s2_18_4", "s2_18_5", "t31_a", "t31_b", "t31_c", "t31_d", "t31_e", "s2_18_6", "t32_a", "t32_b", "t32_c", "s2_18_7", "s2_18_8", "final"],  # session 18
        "19": ["s2_19_1", "s2_19_2", "s2_19_3", "s2_19_4", "s2_19_5", "t30_a", "t30_b", "t30_c", "s2_19_6", "s2_19_7", "final"],  # session 19
        "20": ["s2_20_1", "s2_20_2", "s2_20_3", "s2_20_4", "s2_20_5", "s2_20_6", "t27_a", "t27_b", "t27_c", "next_steps", "congratulations", "final"]  # session 20
    }

    intensive_session = {
        "1": ["s3_1_1", "s3_1_2", "s1_1_3", "s1_1_4", "t1_a", "t1_b", "t1_c", "t2_a", "t2_b", "t2_c", "t3_a", "t3_b", "t3_c", "t4_a", "t4_b", "t4_c", "t5_a", "t5_b", "t5_c", "s1_1_20", "break", "s1_2_5", "t6_a", "t6_b", "t6_c", "t7_a", "t7_b", "t7_c", "t7_d", "t8_a", "t8_b", "t8_c", "s1_2_6", "final"],  # session 1-2
        "2": ["s3_2_1", "s3_2_2", "s1_3_3", "s1_3_5", "t9_a", "t9_b", "t9_c", "t10_a", "t10_b", "t10_c", "t10_d", "t10_e", "s1_3_8", "t11_a", "t11_b", "t11_c", "t11_d", "s1_3_10", "s1_3_12", "break", "s1_4_5", "t12_a", "t12_b", "t12_c", "t13_a", "t13_b", "t13_c", "t14_a", "t14_b", "t14_c", "t15_a", "t15_b", "t15_c", "t16_a", "t16_b", "t16_c", "s1_4_6", "final"],  # session 3-4
        "3": ["s3_3_1", "s3_3_2", "s1_5_3", "s1_5_5", "t17_a", "t17_b", "t18_a", "t18_b", "t18_c", "t19_a", "t17_d", "t17_e", "break", "s1_6_5", "t20_a", "t20_b", "t20_c", "t21_a", "t21_b", "t21_c", "s1_6_6", "s1_6_7", "final"],  # session 5-6
        "4": ["s3_4_1", "s3_4_2", "s1_7_3", "s1_7_5", "t22_a", "t22_b", "t22_c", "s1_7_6", "s1_7_7", "s1_7_8", "break", "s1_8_5", "t23_a", "t23_b", "t23_c", "s1_8_6", "s1_8_7", "final"],  # session 7-8
        "5": ["s3_5_1", "s3_5_2", "s1_9_3", "s1_9_4", "s1_9_5", "t24_a", "t24_b", "t24_c", "t25_a", "t25_b", "t25_c", "t26_a", "t26_b", "t26_c", "t28_a", "t28_b", "t28_c", "t28_d", "t28_e", "t31_a", "t31_b", "t31_c", "t31_d", "t31_e", "t32_a", "t32_b", "t32_c", "s1_9_9", "s1_9_10", "s1_10_5", "s1_10_6", "t29_a", "t29_b", "t29_c", "t30_a", "t30_b", "t30_c", "t27_a", "t27_b", "t27_c", "next_steps", "congratulations", "final"]  # session 9-10
    }

    # Map curriculum names to session dictionaries
    curricula = {
        "ten_session": ten_session,
        "twenty_session": twenty_session,
        "intensive_session": intensive_session
    }
    
    # Map curriculum names to folder names (used in missing_only mode)
    curriculum_folder_mapping = {
        "ten_session": "10",
        "twenty_session": "20",
        "intensive_session": "intensive"
    }

    # Parse command line arguments
    parser = argparse.ArgumentParser(description="Capture screenshots of Zume Training slides")
    parser.add_argument("--width", "-w", type=int, default=3000, help="Screenshot width")
    parser.add_argument("--height", "-ht", type=int, default=1680, help="Screenshot height")
    parser.add_argument("--wait", "-wt", type=int, default=5, help="Wait time in seconds for each page to load")
    parser.add_argument("--curriculum", "-c", default="all", help="Curriculum to capture (ten_session, twenty_session, intensive_session, or 'all')")
    parser.add_argument("--resume", "-r", action="store_true", help="Resume from last processed slide")
    parser.add_argument("--missing-only", "-m", action="store_true", help="Only process missing screenshots")
    
    args = parser.parse_args()
    
    # Load configuration
    config = load_config()
    
    # Display configuration information
    print(f"🌐 Language: {config['language_code']}")
    print(f"📁 Project path: {config['project_path']}")
    print(f"📂 Output structure: {config['project_path']}/[10|20|intensive]/")
    
    # Determine which curricula to capture
    curricula_to_capture = []
    if args.curriculum.lower() == "all":
        curricula_to_capture = list(curricula.keys())
    else:
        if args.curriculum in curricula:
            curricula_to_capture = [args.curriculum]
        else:
            print(f"Warning: Curriculum '{args.curriculum}' not found. Valid options are: {', '.join(curricula.keys())}")
            return
    
    # Loop through selected curricula
    for curriculum_name in curricula_to_capture:
        sessions_dict = curricula[curriculum_name]
        
        print(f"\n=== Processing curriculum: {curriculum_name} ===")
        
        starting_session = None
        starting_index = 0
        
        if args.resume:
            # Load progress from file if resuming
            starting_session, starting_index = load_progress(config, curriculum_name)
        elif args.missing_only:
            # Find missing screenshots
            missing_items = find_missing_screenshots(config, curriculum_name, sessions_dict)
            if not missing_items:
                print(f"No missing screenshots for {curriculum_name}/{config['language_code']}")
                continue
            
            print(f"Found {len(missing_items)} missing screenshots for {curriculum_name}/{config['language_code']}")
            # Process each missing screenshot
            for session_num, idx, slide_id in missing_items:
                # Determine the type parameter based on curriculum name
                type_param = ""
                if curriculum_name == "ten_session":
                    type_param = "10"
                elif curriculum_name == "twenty_session":
                    type_param = "20"
                elif curriculum_name == "intensive_session":
                    type_param = "intensive"
                
                url = f"https://zume.training/{config['language_code']}/presenter?session={session_num}&type={type_param}&view=slideshow&screenshot=&slide={slide_id}"
                
                # Get current timestamp
                timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
                
                # Use correct folder name for output path
                folder_name = curriculum_folder_mapping.get(curriculum_name, curriculum_name)
                curriculum_dir = get_slides_output_dir(config, folder_name)
                output_path = os.path.join(curriculum_dir, f"{timestamp}_session_{session_num}_{slide_id}.png")
                
                take_screenshot(
                    url,
                    output_path,
                    args.width,
                    args.height,
                    args.wait
                )
            continue
        
        # Process the curriculum from the starting session and index
        process_curriculum(
            curriculum_name,
            sessions_dict,
            config,
            args.width,
            args.height,
            args.wait,
            starting_session,
            starting_index
        )

if __name__ == "__main__":
    main()
