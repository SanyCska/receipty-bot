"""CSV extraction and parsing utilities"""
import io
import csv
import logging
from typing import List, Dict

logger = logging.getLogger(__name__)


def extract_csv_strict(text: str) -> str:
    """
    Strictly extract CSV from response, removing all extra text.
    Returns only the CSV content.
    """
    if not text:
        return ""
    
    # Remove markdown code blocks
    text = text.strip()
    
    # Remove ```csv blocks
    if "```csv" in text.lower():
        parts = text.split("```csv")
        if len(parts) > 1:
            text = parts[1].split("```")[0].strip()
    
    # Remove ``` blocks (generic code blocks)
    if "```" in text:
        parts = text.split("```")
        if len(parts) > 1:
            # Find the part that looks most like CSV
            for part in parts:
                if "," in part and ("original_product_name" in part.lower() or 
                                    "product" in part.lower() and "price" in part.lower()):
                    text = part.strip()
                    break
            else:
                # If no clear CSV part, take the middle part (usually the content)
                text = parts[1].strip() if len(parts) > 1 else text
    
    # Split into lines
    lines = text.split('\n')
    
    # Find the header line (should contain column names)
    header_idx = -1
    header_keywords = ['original_product_name', 'translated_product_name', 'category', 'subcategory', 'price']
    
    for i, line in enumerate(lines):
        line_lower = line.lower()
        # Check if this line contains CSV header keywords
        if any(keyword in line_lower for keyword in header_keywords):
            # Count commas to verify it's a CSV line
            if line.count(',') >= 4:
                header_idx = i
                break
    
    # If header not found, try to find first line with enough commas
    if header_idx == -1:
        for i, line in enumerate(lines):
            if line.count(',') >= 4 and line.strip():
                header_idx = i
                break
    
    if header_idx == -1:
        # No header found, try to use the whole text
        logger.warning("Could not find CSV header, using entire response")
        header_idx = 0
    
    # Extract CSV lines starting from header
    csv_lines = lines[header_idx:]
    
    # Remove empty lines and lines that don't look like CSV (fewer than 3 commas)
    csv_lines = [line for line in csv_lines if line.strip() and line.count(',') >= 3]
    
    # Remove explanatory text at the end (lines that don't have the CSV structure)
    # A valid CSV line should have roughly the same number of commas as the header
    if csv_lines:
        expected_commas = csv_lines[0].count(',')
        valid_lines = [csv_lines[0]]  # Keep header
        
        for line in csv_lines[1:]:
            # Allow some variance in comma count (data might have commas in quoted fields)
            comma_count = line.count(',')
            # If line has significantly fewer commas, it's likely not CSV data
            if comma_count >= expected_commas - 1:  # Allow 1 comma difference
                valid_lines.append(line)
            else:
                # Stop at first invalid line
                break
        
        csv_lines = valid_lines
    
    result = '\n'.join(csv_lines).strip()
    
    # Final validation: ensure we have at least a header and some data
    if result and ',' in result:
        logger.info(f"Extracted CSV: {len(csv_lines)} lines (header + {len(csv_lines)-1} data rows)")
        return result
    else:
        logger.warning("CSV extraction failed, returning original text")
        return text.strip()


def parse_csv(csv_content: str) -> List[Dict[str, str]]:
    """Parse CSV content and return list of dictionaries"""
    try:
        # Clean up the CSV content
        lines = csv_content.strip().split('\n')
        
        # Find the header row
        header_found = False
        start_idx = 0
        for i, line in enumerate(lines):
            if 'original_product_name' in line.lower() or 'translated_product_name' in line.lower():
                header_found = True
                start_idx = i
                break
        
        if not header_found:
            # Try to find any CSV-like structure
            for i, line in enumerate(lines):
                if ',' in line and len(line.split(',')) >= 3:
                    start_idx = i
                    break
        
        csv_content_clean = '\n'.join(lines[start_idx:])
        
        csv_reader = csv.DictReader(io.StringIO(csv_content_clean))
        products = []
        for row in csv_reader:
            # Ensure all required keys exist
            product = {
                'original_product_name': row.get('original_product_name', ''),
                'translated_product_name': row.get('translated_product_name', ''),
                'category': row.get('category', 'Unknown'),
                'subcategory': row.get('subcategory', 'Unknown'),
                'price': row.get('price', '0')
            }
            products.append(product)
        
        return products
    except Exception as e:
        logger.error(f"Error parsing CSV: {e}")
        logger.error(f"CSV content: {csv_content[:500]}")
        return []

