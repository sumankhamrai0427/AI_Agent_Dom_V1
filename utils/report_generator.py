import io
import json
from datetime import datetime
from typing import List, Dict, Any

import pandas as pd

# Placeholder functions to fetch data. Replace with actual data sources.

def get_audit_steps() -> List[Dict[str, Any]]:
    """Return a list of audit steps.
    Each step is a dict with keys: 'timestamp', 'action', 'coordinates', 'extracted_elements'.
    """
    # Example dummy data – replace with real implementation.
    return [
        {
            "timestamp": datetime.utcnow().isoformat(),
            "action": "fetch_page",
            "coordinates": {"x": 120, "y": 250},
            "extracted_elements": ["title", "price"]
        },
        {
            "timestamp": datetime.utcnow().isoformat(),
            "action": "parse_data",
            "coordinates": {"x": 0, "y": 0},
            "extracted_elements": ["price"]
        }
    ]

def generate_summary_html() -> str:
    """Render a premium HTML summary of the audit steps.
    Uses simple string templating – you can replace with Jinja2 in Flask templates.
    """
    steps = get_audit_steps()
    rows = "".join(
        f"""
        <tr>
            <td>{i + 1}</td>
            <td>{step['timestamp']}</td>
            <td>{step['action']}</td>
            <td>{json.dumps(step['coordinates'])}</td>
            <td>{', '.join(step['extracted_elements'])}</td>
        </tr>
        """
        for i, step in enumerate(steps)
    )
    html = f"""
    <!DOCTYPE html>
    <html lang='en'>
    <head>
        <meta charset='UTF-8'>
        <meta name='viewport' content='width=device-width, initial-scale=1.0'>
        <title>Verification Summary Report</title>
        <style>
            body {{
                font-family: 'Inter', sans-serif;
                background: linear-gradient(135deg, #1e1e2f, #3b3b58);
                color: #e0e0ff;
                margin: 0;
                padding: 2rem;
            }}
            .container {{
                background: rgba(255,255,255,0.08);
                border-radius: 12px;
                backdrop-filter: blur(12px);
                padding: 2rem;
                max-width: 1000px;
                margin: auto;
            }}
            table {{
                width: 100%;
                border-collapse: collapse;
                margin-top: 1rem;
            }}
            th, td {{
                padding: 0.75rem;
                text-align: left;
                border-bottom: 1px solid rgba(255,255,255,0.1);
            }}
            th {{
                background: rgba(255,255,255,0.12);
            }}
        </style>
    </head>
    <body>
        <div class='container'>
            <h1>Verification Summary Report</h1>
            <table>
                <thead>
                    <tr>
                        <th>#</th>
                        <th>Timestamp (UTC)</th>
                        <th>Action</th>
                        <th>Coordinates</th>
                        <th>Extracted Elements</th>
                    </tr>
                </thead>
                <tbody>
                    {rows}
                </tbody>
            </table>
        </div>
    </body>
    </html>
    """
    return html

def generate_excel_audit() -> bytes:
    """Create an Excel file (in memory) containing the audit steps.
    Returns the binary content.
    """
    steps = get_audit_steps()
    df = pd.DataFrame(steps)
    # Expand coordinates dict into separate columns for readability.
    if not df.empty and isinstance(df.loc[0, 'coordinates'], dict):
        coord_df = df['coordinates'].apply(pd.Series)
        coord_df = coord_df.rename(columns=lambda c: f"coord_{c}")
        df = pd.concat([df.drop(columns=['coordinates']), coord_df], axis=1)
    buffer = io.BytesIO()
    with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
        df.to_excel(writer, index=False, sheet_name='Audit')
    buffer.seek(0)
    return buffer.read()

def generate_geojson() -> str:
    """Generate a simple GeoJSON FeatureCollection based on audit step coordinates.
    Each step becomes a Point feature.
    """
    steps = get_audit_steps()
    features = []
    for step in steps:
        coord = step.get('coordinates', {})
        lon = coord.get('x', 0)
        lat = coord.get('y', 0)
        features.append({
            "type": "Feature",
            "properties": {
                "action": step.get('action'),
                "timestamp": step.get('timestamp')
            },
            "geometry": {
                "type": "Point",
                "coordinates": [lon, lat]
            }
        })
    geojson = {
        "type": "FeatureCollection",
        "features": features
    }
    return json.dumps(geojson, indent=2)

def generate_pdf_bytes() -> bytes:
    """Render the HTML summary to PDF bytes using WeasyPrint.
    Returns binary PDF data.
    """
    try:
        from weasyprint import HTML
    except ImportError:
        raise RuntimeError("WeasyPrint is required for PDF generation. Install it via pip.")
    html_content = generate_summary_html()
    pdf_bytes = HTML(string=html_content).write_pdf()
    return pdf_bytes
