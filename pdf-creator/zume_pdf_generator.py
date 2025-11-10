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
                # First wait for page to load
                await page.goto(url, wait_until='load', timeout=self.timeout)
                
                # For languages with complex fonts like Gujarati, also wait for network to be idle
                # This ensures font files are downloaded
                if lang == 'gu':
                    try:
                        await page.wait_for_load_state('networkidle', timeout=30000)
                        logger.debug(f"Network idle confirmed for Gujarati session {session}")
                    except Exception as e:
                        logger.warning(f"Network idle timeout for session {session} (continuing anyway): {str(e)}")
                        # Fallback: wait a bit for fonts to load
                        await page.wait_for_timeout(2000)
                
                # Set zoom level
                await page.evaluate("document.body.style.zoom = '" + str(self.zoom) + "'")
                
                # Wait for fonts to load (critical for languages with custom fonts like Gujarati)
                # This ensures all web fonts are fully loaded and rendered before generating the PDF
                try:
                    font_info = await page.evaluate("""
                        async () => {
                            // Get all font families used on the page
                            const getAllFontFamilies = () => {
                                const fonts = new Set();
                                const walker = document.createTreeWalker(
                                    document.body,
                                    NodeFilter.SHOW_ELEMENT,
                                    null
                                );
                                
                                let node;
                                while (node = walker.nextNode()) {
                                    const computedStyle = window.getComputedStyle(node);
                                    const fontFamily = computedStyle.fontFamily;
                                    if (fontFamily) {
                                        // Parse font family string (can have multiple fonts)
                                        fontFamily.split(',').forEach(font => {
                                            const cleanFont = font.trim().replace(/['"]/g, '');
                                            if (cleanFont && cleanFont !== 'inherit' && cleanFont !== 'initial') {
                                                fonts.add(cleanFont);
                                            }
                                        });
                                    }
                                }
                                return Array.from(fonts);
                            };
                            
                            const fontFamilies = getAllFontFamilies();
                            
                            // Wait for all stylesheets to load (they may contain @font-face rules)
                            const stylesheets = Array.from(document.styleSheets);
                            for (const sheet of stylesheets) {
                                try {
                                    if (sheet.cssRules) {
                                        // Stylesheet loaded, check for @font-face rules
                                        for (const rule of sheet.cssRules) {
                                            if (rule.type === CSSRule.FONT_FACE_RULE) {
                                                // Found a @font-face rule, font will need to load
                                            }
                                        }
                                    }
                                } catch (e) {
                                    // Cross-origin stylesheet, ignore
                                }
                            }
                            
                            // Wait for font API to be ready
                            if (document.fonts && document.fonts.ready) {
                                await document.fonts.ready;
                            }
                            
                            // Also wait for any pending font loads from @font-face
                            // Wait for fonts to be registered in the FontFaceSet
                            let fontLoadAttempts = 0;
                            while (fontLoadAttempts < 10) {
                                if (document.fonts && document.fonts.size > 0) {
                                    // Fonts are registered, break
                                    break;
                                }
                                await new Promise(resolve => setTimeout(resolve, 100));
                                fontLoadAttempts++;
                            }
                            
                            // Wait for all fonts to actually load with retries
                            let maxRetries = 30; // 30 * 250ms = 7.5 seconds max (increased for complex fonts)
                            let allFontsLoaded = false;
                            let fontStatuses = [];
                            
                            while (maxRetries > 0 && !allFontsLoaded) {
                                allFontsLoaded = true;
                                fontStatuses = [];
                                
                                if (document.fonts && document.fonts.size > 0) {
                                    // Check all fonts in the document
                                    for (const font of document.fonts.values()) {
                                        const status = font.status;
                                        fontStatuses.push({
                                            family: font.family,
                                            style: font.style,
                                            weight: font.weight,
                                            status: status
                                        });
                                        if (status !== 'loaded' && status !== 'unloaded') {
                                            // 'unloaded' means font file hasn't been requested yet, which is OK
                                            // But 'loading' or 'error' means we need to wait
                                            if (status === 'loading') {
                                                allFontsLoaded = false;
                                            } else if (status === 'error') {
                                                console.warn(`Font load error: ${font.family}`);
                                            }
                                        }
                                    }
                                    
                                    // Also check if specific font families are loaded by testing them
                                    if (fontFamilies.length > 0) {
                                        for (const family of fontFamilies.slice(0, 5)) { // Check first 5 families
                                            try {
                                                const loaded = document.fonts.check(`16px "${family}"`);
                                                if (!loaded) {
                                                    // Font family not loaded yet
                                                    allFontsLoaded = false;
                                                }
                                            } catch (e) {
                                                // Font check failed, continue
                                            }
                                        }
                                    }
                                } else {
                                    // If no fonts registered yet, wait a bit more
                                    allFontsLoaded = false;
                                }
                                
                                if (!allFontsLoaded) {
                                    await new Promise(resolve => setTimeout(resolve, 250));
                                    maxRetries--;
                                }
                            }
                            
                            // Log font statuses for debugging
                            if (fontStatuses.length > 0) {
                                const loadedCount = fontStatuses.filter(f => f.status === 'loaded').length;
                                const loadingCount = fontStatuses.filter(f => f.status === 'loading').length;
                                console.log(`Font loading status: ${loadedCount} loaded, ${loadingCount} loading, ${fontStatuses.length} total`);
                            }
                            
                            // Additional wait to ensure font rendering is complete
                            // Increased wait time for complex fonts like Gujarati
                            await new Promise(resolve => setTimeout(resolve, 2000));
                            
                            // Force multiple layout recalculations to ensure fonts are rendered
                            document.body.offsetHeight;
                            document.body.offsetHeight;
                            
                            // Verify fonts are actually rendering by checking if actual page text is visible
                            // Find first text node with non-ASCII characters (likely using custom fonts)
                            const walker = document.createTreeWalker(
                                document.body,
                                NodeFilter.SHOW_TEXT,
                                null
                            );
                            let hasVisibleText = false;
                            let node;
                            while (node = walker.nextNode()) {
                                const text = node.textContent.trim();
                                // Check for non-ASCII characters (indicating custom fonts needed)
                                if (text.length > 0 && /[^\x00-\x7F]/.test(text)) {
                                    const parent = node.parentElement;
                                    if (parent) {
                                        const rect = parent.getBoundingClientRect();
                                        const style = window.getComputedStyle(parent);
                                        if (rect.width > 0 && rect.height > 0 && 
                                            style.visibility !== 'hidden' && 
                                            style.display !== 'none') {
                                            hasVisibleText = true;
                                            break;
                                        }
                                    }
                                }
                            }
                            
                            return {
                                allFontsLoaded: allFontsLoaded,
                                fontFamilies: fontFamilies,
                                fontCount: document.fonts ? document.fonts.size : 0,
                                textRendering: hasVisibleText,
                                fontStatuses: fontStatuses
                            };
                        }
                    """)
                    
                    if font_info:
                        font_statuses = font_info.get('fontStatuses', [])
                        loaded_fonts = [f for f in font_statuses if f.get('status') == 'loaded']
                        loading_fonts = [f for f in font_statuses if f.get('status') == 'loading']
                        
                        logger.info(f"Font info for session {session}: {len(font_info.get('fontFamilies', []))} font families found, "
                                  f"{font_info.get('fontCount', 0)} fonts registered, "
                                  f"{len(loaded_fonts)} loaded, {len(loading_fonts)} loading, "
                                  f"all loaded: {font_info.get('allFontsLoaded', False)}, "
                                  f"text rendering: {font_info.get('textRendering', False)}")
                        
                        if font_info.get('fontFamilies'):
                            logger.debug(f"Font families used: {', '.join(font_info['fontFamilies'][:5])}")
                        
                        if loaded_fonts:
                            font_details = []
                            for f in loaded_fonts[:3]:
                                family = f.get('family', 'unknown')
                                weight = f.get('weight', '')
                                style = f.get('style', '')
                                font_details.append(f"{family} ({weight} {style})")
                            logger.debug(f"Loaded fonts: {', '.join(font_details)}")
                        
                        if loading_fonts:
                            logger.warning(f"Still loading fonts: {', '.join([f.get('family', 'unknown') for f in loading_fonts[:3]])}")
                    
                    if not font_info.get('allFontsLoaded', False):
                        logger.warning(f"Some fonts may not be fully loaded for session {session}, but continuing with PDF generation")
                    
                    # Additional wait specifically for Gujarati and other complex script languages
                    if lang == 'gu':
                        logger.debug(f"Additional wait for Gujarati font rendering")
                        await page.wait_for_timeout(1500)
                        # Force another layout recalculation
                        await page.evaluate("document.body.offsetHeight")
                        
                except Exception as font_error:
                    logger.warning(f"Font loading check failed (continuing anyway): {str(font_error)}")
                    # Fallback: wait longer for fonts to potentially load, especially for Gujarati
                    fallback_wait = 4000 if lang == 'gu' else 2500
                    await page.wait_for_timeout(fallback_wait)
                    # Force layout recalculation
                    await page.evaluate("document.body.offsetHeight")
                
                # Generate PDF with font embedding enabled (default in Playwright, but explicit)
                logger.info(f"Generating PDF: {filename}")
                # Note: Playwright automatically embeds fonts used on the page in the PDF
                # But we ensure fonts are fully loaded before this step
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
            # Launch browser with optimizations for font rendering
            # Note: System fonts should be accessible by default in Playwright
            browser = await p.chromium.launch(
                headless=True,
                args=[
                    '--disable-features=TranslateUI',  # Disable translation UI
                    '--disable-ipc-flooding-protection',  # Allow more resources
                ]
            )
            page = await browser.new_page()
            
            # Set extra HTTP headers to ensure proper language handling
            await page.set_extra_http_headers({
                'Accept-Language': f'{lang},en;q=0.9'
            })
            
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