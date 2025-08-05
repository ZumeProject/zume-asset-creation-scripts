#!/usr/bin/env python3
"""
Zume PDF Book Creator

This script automatically generates PDF books from the Zume training website
by loading web pages and converting them to PDF with specified parameters.

Author: Generated for Zume Training
"""

import asyncio
import argparse
import os
import sys
from datetime import datetime
from pathlib import Path
from playwright.async_api import async_playwright
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('pdf_generation.log'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)


class ZumePDFGenerator:
    """Main class for generating Zume training PDFs."""
    
    def __init__(self, base_url: str = "https://zume.training", output_dir: str = "output", 
                 timeout: int = 60000, max_retries: int = 2, zoom: float = 0.8):
        self.base_url = base_url
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(exist_ok=True)
        self.timeout = timeout
        self.max_retries = max_retries
        self.zoom = zoom
        
        # Define loop counts for different types
        self.type_loops = {
            "10": 10,
            "20": 20,
            "intensive": 5
        }
    
    def get_session_count(self, type_param: str) -> int:
        """Get the number of sessions based on type parameter."""
        return self.type_loops.get(str(type_param), 1)
    
    def generate_filename(self, type_param: str, session: int, lang: str) -> str:
        """Generate PDF filename based on parameters."""
        return f"{type_param}_{session}_{lang}.pdf"
    
    def build_url(self, type_param: str, session: int, lang: str) -> str:
        """Build the URL for the given parameters."""
        return f"{self.base_url}/{lang}/book/generator?type={type_param}&session={session}&lang={lang}"
    
    async def generate_single_pdf(self, page, type_param: str, session: int, lang: str) -> bool:
        """Generate a single PDF from the given parameters with retry logic."""
        url = self.build_url(type_param, session, lang)
        filename = self.generate_filename(type_param, session, lang)
        
        # Create language-specific subfolder
        lang_output_dir = self.output_dir / lang
        lang_output_dir.mkdir(exist_ok=True)
        filepath = lang_output_dir / filename
        
        for attempt in range(1, self.max_retries + 1):
            try:
                if attempt > 1:
                    logger.info(f"🔄 Retry attempt {attempt}/{self.max_retries} for session {session}")
                    
                logger.info(f"Loading URL: {url}")
                await page.goto(url, wait_until='networkidle', timeout=self.timeout)
                
                # Set zoom level
                await page.evaluate("document.body.style.zoom = '" + str(self.zoom) + "'")
                
                # Wait a bit for zoom to apply
                await page.wait_for_timeout(1000)
                
                # Generate PDF
                logger.info(f"Generating PDF: {filename}")
                await page.pdf(
                    path=str(filepath),
                    format="Letter",
                    print_background=True,
                    prefer_css_page_size=False,
                    margin={
                        "top": "1cm",
                        "bottom": "1cm",
                        "left": "1cm",
                        "right": "1cm"
                    }
                )
                
                logger.info(f"✅ Successfully generated: {filename}")
                return True
                
            except Exception as e:
                if attempt == self.max_retries:
                    logger.error(f"❌ Failed to generate PDF for session {session} after {self.max_retries} attempts: {str(e)}")
                else:
                    logger.warning(f"⚠️ Attempt {attempt} failed for session {session}: {str(e)}")
                    # Wait before retry
                    await asyncio.sleep(3)
                    
        return False
    
    async def generate_pdfs(self, type_param: str, lang: str, start_session: int = 1, single_session: int = None) -> dict:
        """Generate all PDFs for the given type and language, or a single session if specified."""
        session_count = self.get_session_count(type_param)
        results = {"success": 0, "failed": 0, "files": []}
        
        if single_session is not None:
            # Generate only the specified session
            logger.info(f"Starting PDF generation for type={type_param}, lang={lang}, session={single_session}")
            logger.info(f"Will generate 1 PDF for session {single_session}")
            sessions_to_generate = [single_session]
        else:
            # Generate all sessions starting from start_session
            logger.info(f"Starting PDF generation for type={type_param}, lang={lang}")
            logger.info(f"Will generate {session_count} PDFs starting from session {start_session}")
            sessions_to_generate = range(start_session, start_session + session_count)
        
        async with async_playwright() as p:
            # Launch browser
            browser = await p.chromium.launch(headless=True)
            page = await browser.new_page()
            
            # Set a reasonable viewport
            await page.set_viewport_size({"width": 1920, "height": 1080})
            
            try:
                for session in sessions_to_generate:
                    success = await self.generate_single_pdf(page, type_param, session, lang)
                    
                    if success:
                        results["success"] += 1
                        results["files"].append(self.generate_filename(type_param, session, lang))
                    else:
                        results["failed"] += 1
                    
                    # Small delay between requests to be respectful
                    await asyncio.sleep(1)
                
            finally:
                await browser.close()
        
        return results
    
    def print_summary(self, results: dict, lang: str):
        """Print a summary of the generation results."""
        total = results["success"] + results["failed"]
        lang_output_dir = self.output_dir / lang
        logger.info(f"\n{'='*50}")
        logger.info(f"PDF GENERATION SUMMARY")
        logger.info(f"{'='*50}")
        logger.info(f"Total processed: {total}")
        logger.info(f"Successful: {results['success']}")
        logger.info(f"Failed: {results['failed']}")
        logger.info(f"Output directory: {lang_output_dir.absolute()}")
        
        if results["files"]:
            logger.info(f"\nGenerated files:")
            for file in results["files"]:
                logger.info(f"  • {file}")


async def main():
    """Main function to run the PDF generator."""
    parser = argparse.ArgumentParser(
        description="Generate PDF books from Zume training website",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python zume_pdf_generator.py --type 10 --lang am
  python zume_pdf_generator.py --type intensive --lang en --start-session 2
  python zume_pdf_generator.py --type 20 --lang es --output-dir my_pdfs
  python zume_pdf_generator.py --type 10 --lang en --zoom 0.8
  python zume_pdf_generator.py --type 10 --lang en --session 5
        """
    )
    
    parser.add_argument(
        "--type", 
        required=True,
        help="Type parameter (10, 20, or intensive)"
    )
    
    parser.add_argument(
        "--lang", 
        required=True,
        help="Language code (e.g., am, en, es)"
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
    
    args = parser.parse_args()
    
    # Validate type parameter
    valid_types = ["10", "20", "intensive"]
    if args.type not in valid_types:
        logger.error(f"Invalid type '{args.type}'. Must be one of: {', '.join(valid_types)}")
        sys.exit(1)
    
    # Warn if both session and start-session are provided
    if args.session is not None and args.start_session != 1:
        logger.warning("⚠️  Both --session and --start-session provided. Using --session and ignoring --start-session.")
    
    # Create generator instance
    generator = ZumePDFGenerator(
        base_url=args.base_url,
        output_dir=args.output_dir,
        timeout=args.timeout,
        max_retries=args.max_retries,
        zoom=args.zoom
    )
    
    try:
        # Generate PDFs
        start_time = datetime.now()
        results = await generator.generate_pdfs(
            type_param=args.type,
            lang=args.lang,
            start_session=args.start_session,
            single_session=args.session
        )
        end_time = datetime.now()
        
        # Print summary
        generator.print_summary(results, args.lang)
        logger.info(f"Total time: {end_time - start_time}")
        
        # Exit with error code if any PDFs failed
        if results["failed"] > 0:
            sys.exit(1)
            
    except KeyboardInterrupt:
        logger.info("\n🛑 Generation interrupted by user")
        sys.exit(1)
    except Exception as e:
        logger.error(f"❌ Unexpected error: {str(e)}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main()) 