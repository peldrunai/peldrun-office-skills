# scripts/clean_svg.py
import re
import sys
from pathlib import Path
import xml.etree.ElementTree as ET

def clean_svg_styles(svg_path: Path):
    """Converts style="..." attributes into standard SVG attributes."""
    content = svg_path.read_text(encoding="utf-8")
    
    # Regular expression to find style="..."
    def replace_style(match):
        style_content = match.group(1)
        attributes = []
        # Split by ; and then by :
        for declaration in style_content.split(';'):
            if ':' in declaration:
                prop, value = declaration.split(':', 1)
                prop = prop.strip()
                value = value.strip()
                # Ignore properties that aren't standard SVG presentation attributes
                if prop in ['fill', 'stroke', 'stroke-width', 'fill-rule', 'clip-rule', 'fill-opacity', 'stroke-opacity', 'stop-color', 'stop-opacity']:
                    attributes.append(f'{prop}="{value}"')
        return ' '.join(attributes)

    # Replace style="..." with the extracted attributes
    cleaned_content = re.sub(r'style="([^"]*)"', replace_style, content)
    
    # Write back
    svg_path.write_text(cleaned_content, encoding="utf-8")
    print(f"Cleaned: {svg_path}")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python clean_svg.py <path_to_svg>")
        sys.exit(1)
    
    svg_file = Path(sys.argv[1])
    if svg_file.exists():
        clean_svg_styles(svg_file)
    else:
        print("File not found!")