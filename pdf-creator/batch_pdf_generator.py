#!/usr/bin/env python3
"""
Batch Zume PDF Generator

This script runs zume_pdf_generator.py with arrays of types and languages,
looping through all combinations to generate multiple PDF sets.

Author: Generated for Zume Training
"""

import asyncio
import argparse
import os
import sys
import subprocess
from datetime import datetime
from pathlib import Path
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('batch_pdf_generation.log'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)


class BatchPDFGenerator:
    """Main class for batch generating Zume training PDFs."""
    
    def __init__(self, types: list, languages: list, output_dir: str = "output", 
                 base_url: str = "https://zume.training", timeout: int = 60000, 
                 max_retries: int = 2, zoom: float = 0.8, start_session: int = 1, 
                 single_session: int = None):
        self.types = types
        self.languages = languages
        self.output_dir = output_dir
        self.base_url = base_url
        self.timeout = timeout
        self.max_retries = max_retries
        self.zoom = zoom
        self.start_session = start_session
        self.single_session = single_session
        
        # Validate types
        valid_types = ["10", "20", "intensive"]
        for type_param in self.types:
            if type_param not in valid_types:
                raise ValueError(f"Invalid type '{type_param}'. Must be one of: {', '.join(valid_types)}")
    
    def build_command(self, type_param: str, lang: str) -> list:
        """Build the command to run zume_pdf_generator.py with the given parameters."""
        cmd = [
            sys.executable, "zume_pdf_generator.py",
            "--type", type_param,
            "--lang", lang,
            "--output-dir", self.output_dir,
            "--base-url", self.base_url,
            "--timeout", str(self.timeout),
            "--max-retries", str(self.max_retries),
            "--zoom", str(self.zoom),
            "--start-session", str(self.start_session)
        ]
        
        if self.single_session is not None:
            cmd.extend(["--session", str(self.single_session)])
        
        return cmd
    
    async def run_single_generation(self, type_param: str, lang: str) -> dict:
        """Run a single PDF generation for the given type and language."""
        cmd = self.build_command(type_param, lang)
        
        logger.info(f"🔄 Running generation for type={type_param}, lang={lang}")
        logger.info(f"Command: {' '.join(cmd)}")
        
        start_time = datetime.now()
        
        try:
            # Run the subprocess
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=self.timeout // 1000 + 60  # Convert to seconds and add buffer
            )
            
            end_time = datetime.now()
            duration = end_time - start_time
            
            if result.returncode == 0:
                logger.info(f"✅ Successfully completed generation for type={type_param}, lang={lang} (Duration: {duration})")
                return {
                    "success": True,
                    "type": type_param,
                    "lang": lang,
                    "duration": duration,
                    "stdout": result.stdout,
                    "stderr": result.stderr
                }
            else:
                logger.error(f"❌ Failed generation for type={type_param}, lang={lang} (Duration: {duration})")
                logger.error(f"Return code: {result.returncode}")
                if result.stderr:
                    logger.error(f"Error output: {result.stderr}")
                return {
                    "success": False,
                    "type": type_param,
                    "lang": lang,
                    "duration": duration,
                    "stdout": result.stdout,
                    "stderr": result.stderr,
                    "return_code": result.returncode
                }
                
        except subprocess.TimeoutExpired:
            logger.error(f"⏰ Timeout for type={type_param}, lang={lang}")
            return {
                "success": False,
                "type": type_param,
                "lang": lang,
                "error": "Timeout",
                "duration": datetime.now() - start_time
            }
        except Exception as e:
            logger.error(f"💥 Exception for type={type_param}, lang={lang}: {str(e)}")
            return {
                "success": False,
                "type": type_param,
                "lang": lang,
                "error": str(e),
                "duration": datetime.now() - start_time
            }
    
    async def run_batch_generation(self) -> dict:
        """Run batch generation for all type and language combinations."""
        total_combinations = len(self.types) * len(self.languages)
        logger.info(f"🚀 Starting batch PDF generation")
        logger.info(f"Types: {self.types}")
        logger.info(f"Languages: {self.languages}")
        logger.info(f"Total combinations: {total_combinations}")
        
        results = {
            "total": total_combinations,
            "successful": 0,
            "failed": 0,
            "combinations": []
        }
        
        start_time = datetime.now()
        current = 0
        
        for type_param in self.types:
            for lang in self.languages:
                current += 1
                logger.info(f"\n📊 Progress: {current}/{total_combinations}")
                
                result = await self.run_single_generation(type_param, lang)
                results["combinations"].append(result)
                
                if result["success"]:
                    results["successful"] += 1
                else:
                    results["failed"] += 1
                
                # Small delay between runs to be respectful
                await asyncio.sleep(2)
        
        end_time = datetime.now()
        results["total_duration"] = end_time - start_time
        
        return results
    
    def print_summary(self, results: dict):
        """Print a summary of the batch generation results."""
        logger.info(f"\n{'='*60}")
        logger.info(f"BATCH PDF GENERATION SUMMARY")
        logger.info(f"{'='*60}")
        logger.info(f"Total combinations: {results['total']}")
        logger.info(f"Successful: {results['successful']}")
        logger.info(f"Failed: {results['failed']}")
        logger.info(f"Total time: {results['total_duration']}")
        
        if results["failed"] > 0:
            logger.info(f"\nFailed combinations:")
            for combo in results["combinations"]:
                if not combo["success"]:
                    logger.info(f"  • type={combo['type']}, lang={combo['lang']}")
                    if "error" in combo:
                        logger.info(f"    Error: {combo['error']}")
                    elif "return_code" in combo:
                        logger.info(f"    Return code: {combo['return_code']}")
        
        logger.info(f"\nOutput directory: {Path(self.output_dir).absolute()}")


async def main():
    """Main function to run the batch PDF generator."""
    parser = argparse.ArgumentParser(
        description="Batch generate PDF books from Zume training website",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python batch_pdf_generator.py --types 10 20 --languages en es
  python batch_pdf_generator.py --types 10 intensive --languages am en es
  python batch_pdf_generator.py --types 10 --languages en --output-dir my_pdfs
  python batch_pdf_generator.py --types 10 20 --languages en --session 5
        """
    )
    
    parser.add_argument(
        "--types", 
        nargs="+",
        required=True,
        help="Type parameters (10, 20, intensive) - can specify multiple"
    )
    
    parser.add_argument(
        "--languages", 
        nargs="+",
        required=True,
        help="Language codes (e.g., am, en, es) - can specify multiple"
    )
    
    parser.add_argument(
        "--output-dir", 
        default="output",
        help="Output directory for PDFs (default: output)"
    )
    
    parser.add_argument(
        "--base-url", 
        default="https://zume.training",
        help="Base URL for Zume training (default: https://zume.training)"
    )
    
    parser.add_argument(
        "--timeout", 
        type=int,
        default=60000,
        help="Page load timeout in milliseconds (default: 60000)"
    )
    
    parser.add_argument(
        "--max-retries", 
        type=int,
        default=2,
        help="Maximum retry attempts for failed sessions (default: 2)"
    )
    
    parser.add_argument(
        "--zoom", 
        type=float,
        default=0.8,
        help="Zoom level for PDF generation (default: 0.8)"
    )
    
    parser.add_argument(
        "--start-session", 
        type=int, 
        default=1,
        help="Starting session number (default: 1)"
    )
    
    parser.add_argument(
        "--session", 
        type=int,
        help="Generate only a specific session number (overrides --start-session)"
    )
    
    args = parser.parse_args()
    
    try:
        # Create batch generator instance
        batch_generator = BatchPDFGenerator(
            types=args.types,
            languages=args.languages,
            output_dir=args.output_dir,
            base_url=args.base_url,
            timeout=args.timeout,
            max_retries=args.max_retries,
            zoom=args.zoom,
            start_session=args.start_session,
            single_session=args.session
        )
        
        # Run batch generation
        results = await batch_generator.run_batch_generation()
        
        # Print summary
        batch_generator.print_summary(results)
        
        # Exit with error code if any generations failed
        if results["failed"] > 0:
            sys.exit(1)
            
    except KeyboardInterrupt:
        logger.info("\n🛑 Batch generation interrupted by user")
        sys.exit(1)
    except Exception as e:
        logger.error(f"❌ Unexpected error: {str(e)}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main()) 