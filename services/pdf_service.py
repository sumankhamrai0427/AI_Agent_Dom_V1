import os
import json
import csv
from utils.logger import logger

try:
    import openpyxl
    OPENPYXL_AVAILABLE = True
except ImportError:
    OPENPYXL_AVAILABLE = False
    logger.warning("openpyxl is not available. Using CSV fallback for spreadsheet reports.")

class PDFService:
    @staticmethod
    def generate_excel_report(task_id, data, logs, output_path):
        """Generates an Excel/CSV spreadsheet report containing owner details and audit trails."""
        logger.info(f"Generating spreadsheet report for task {task_id} at {output_path}")
        
        if OPENPYXL_AVAILABLE:
            try:
                wb = openpyxl.Workbook()
                
                # Sheet 1: Summary Data
                ws_summary = wb.active
                ws_summary.title = "Summary Data"
                ws_summary.append(["Key", "Value"])
                for k, v in data.items():
                    # Handle nested lists/dicts
                    val = json.dumps(v) if isinstance(v, (dict, list)) else str(v)
                    ws_summary.append([k, val])
                
                # Sheet 2: Audit Logs
                ws_logs = wb.create_sheet(title="Audit Trails")
                ws_logs.append(["Timestamp", "Agent Name", "Step Name", "Action", "URL", "Result", "Status"])
                for log in logs:
                    ws_logs.append([
                        str(log.timestamp),
                        log.agent_name,
                        log.step_name or "",
                        log.action or "",
                        log.url or "",
                        log.result or "",
                        log.status
                    ])
                
                wb.save(output_path)
                logger.info(f"Excel report successfully generated: {output_path}")
                return output_path
            except Exception as e:
                logger.error(f"Excel report generation failed: {e}. Falling back to CSV.")
        
        # Fallback to CSV format
        csv_path = output_path.replace(".xlsx", ".csv")
        try:
            with open(csv_path, 'w', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                writer.writerow(["=== SUMMARY DATA ==="])
                for k, v in data.items():
                    val = json.dumps(v) if isinstance(v, (dict, list)) else str(v)
                    writer.writerow([k, val])
                
                writer.writerow([])
                writer.writerow(["=== AUDIT TRAILS ==="])
                writer.writerow(["Timestamp", "Agent Name", "Step Name", "Action", "URL", "Result", "Status"])
                for log in logs:
                    writer.writerow([
                        str(log.timestamp),
                        log.agent_name,
                        log.step_name or "",
                        log.action or "",
                        log.url or "",
                        log.result or "",
                        log.status
                    ])
            logger.info(f"CSV report successfully generated: {csv_path}")
            return csv_path
        except Exception as e:
            logger.error(f"CSV report generation failed: {e}")
            raise e

    @staticmethod
    def generate_html_report(task_id, data, logs, gis_data, output_path):
        """Generates a premium, styled HTML report package (which can be printed to PDF) with audit trail and plot overview."""
        logger.info(f"Generating HTML report for task {task_id} at {output_path}")
        
        # Determine utility type
        utility_type = data.get("document", {}).get("utility_type", "LAND")
        report_title = "Electricity Bill Verification Report" if utility_type == "ELECTRICITY" else "Land Record Verification Report"
        document_card_title = "Extracted Customer Bill (PDF/OCR)" if utility_type == "ELECTRICITY" else "Extracted Owner Deed (PDF/OCR)"
        
        # Parse verification conflicts or status
        is_valid = data.get("verification", {}).get("is_valid", True)
        status_text = "VERIFIED / MATCHED" if is_valid else "CONFLICT DETECTED"
        status_color = "#10B981" if is_valid else "#EF4444"
        
        # Audit logs rows
        log_rows = ""
        for log in logs:
            log_rows += f"""
            <tr>
                <td>{log.timestamp.strftime('%H:%M:%S')}</td>
                <td><span class="badge badge-agent">{log.agent_name}</span></td>
                <td>{log.step_name or ''}</td>
                <td><code>{log.action or ''}</code></td>
                <td>{log.status}</td>
            </tr>
            """

        # Generate Document and Portal table HTML dynamically
        if utility_type == "ELECTRICITY":
            doc_table_html = f"""
            <table style="margin-top:0;">
                <tr><td>Customer Name</td><td><b>{data.get('document', {}).get('owner_name', 'N/A')}</b></td></tr>
                <tr><td>Consumer ID</td><td>{data.get('document', {}).get('consumer_id', 'N/A')}</td></tr>
                <tr><td>Installation ID</td><td>{data.get('document', {}).get('installation_no', 'N/A')}</td></tr>
                <tr><td>Bill Amount</td><td>{data.get('document', {}).get('bill_amount', 'N/A')}</td></tr>
                <tr><td>Bill Month</td><td>{data.get('document', {}).get('bill_month', 'N/A')}</td></tr>
            </table>
            """
        else:
            doc_table_html = f"""
            <table style="margin-top:0;">
                <tr><td>Owner Name</td><td><b>{data.get('document', {}).get('owner_name', 'N/A')}</b></td></tr>
                <tr><td>Father Name</td><td>{data.get('document', {}).get('father_name', 'N/A')}</td></tr>
                <tr><td>Village / Dist</td><td>{data.get('document', {}).get('village', 'N/A')} / {data.get('document', {}).get('district', 'N/A')}</td></tr>
                <tr><td>Khata / Khasra</td><td>{data.get('document', {}).get('khata', 'N/A')} / {data.get('document', {}).get('khasra', 'N/A')}</td></tr>
                <tr><td>Area</td><td>{data.get('document', {}).get('area', 'N/A')}</td></tr>
            </table>
            """

        portal_has_data = data.get("portal") and any(data.get("portal").values())
        if portal_has_data:
            if utility_type == "ELECTRICITY":
                portal_table_html = f"""
                <table style="margin-top:0;">
                    <tr><td>Customer Name</td><td><b>{data.get('portal', {}).get('owner_name', 'N/A')}</b></td></tr>
                    <tr><td>Consumer ID</td><td>{data.get('portal', {}).get('consumer_id', 'N/A')}</td></tr>
                    <tr><td>Installation ID</td><td>{data.get('portal', {}).get('installation_no', 'N/A')}</td></tr>
                    <tr><td>Bill Amount</td><td>{data.get('portal', {}).get('bill_amount', 'N/A')}</td></tr>
                    <tr><td>Bill Month</td><td>{data.get('portal', {}).get('bill_month', 'N/A')}</td></tr>
                </table>
                """
            else:
                portal_table_html = f"""
                <table style="margin-top:0;">
                    <tr><td>Owner Name</td><td><b>{data.get('portal', {}).get('owner_name', 'N/A')}</b></td></tr>
                    <tr><td>Father Name</td><td>{data.get('portal', {}).get('father_name', 'N/A')}</td></tr>
                    <tr><td>Village / Dist</td><td>{data.get('portal', {}).get('village', 'N/A')} / {data.get('portal', {}).get('district', 'N/A')}</td></tr>
                    <tr><td>Khata / Khasra</td><td>{data.get('portal', {}).get('khata', 'N/A')} / {data.get('portal', {}).get('khasra', 'N/A')}</td></tr>
                    <tr><td>Area</td><td>{data.get('portal', {}).get('area', 'N/A')}</td></tr>
                </table>
                """
        else:
            portal_table_html = f"""
            <div style="text-align: center; padding: 25px 0; color: #DC2626;">
                <svg style="width:48px;height:48px;fill:#DC2626;margin-bottom:8px;" viewBox="0 0 24 24"><path d="M13 13H11V7H13M13 17H11V15H13M12 2C6.47 2 2 6.47 2 12s4.47 10 10 10 10-4.47 10-10S17.53 2 12 2z"/></svg>
                <div style="font-weight: 700; font-size: 16px;">NO DATA FOUND</div>
                <div style="font-size: 13px; margin-top: 4px; color: #991B1B;">No record matches this {"Consumer ID" if utility_type == "ELECTRICITY" else "Khata"} on the government portal.</div>
            </div>
            """

        conflicts_html = ""
        conflicts_list = data.get("verification", {}).get("conflicts", [])
        if not is_valid:
            conflicts_html = f"""
            <div class="card" style="border: 1px solid #FCA5A5; background-color: #FEF2F2; margin-bottom: 25px; border-radius: 8px;">
                <div style="font-weight: 700; color: #DC2626; font-size: 16px; margin-bottom: 10px; display: flex; align-items: center; gap: 8px;">
                    <svg style="width:20px;height:20px;fill:#DC2626" viewBox="0 0 24 24"><path d="M12 2C6.5 2 2 6.5 2 12S6.5 22 12 22 22 17.5 22 12 17.5 2 12 2M13 17H11V15H13V17M13 13H11V7H13V13Z"/></svg>
                    Discrepancies / Conflicts Detected
                </div>
                <ul style="color: #991B1B; margin: 0; padding-left: 20px; font-size: 14px; line-height: 1.6;">
            """
            for conflict in conflicts_list:
                conflicts_html += f"<li>{conflict}</li>"
            conflicts_html += """
                </ul>
            </div>
            """
        else:
            conflicts_html = """
            <div class="card" style="border: 1px solid #A7F3D0; background-color: #ECFDF5; margin-bottom: 25px; display: flex; align-items: center; gap: 8px; color: #065F46; font-weight: 600; font-size: 14px; border-radius: 8px;">
                <svg style="width:20px;height:20px;fill:#059669" viewBox="0 0 24 24"><path d="M12 2C6.5 2 2 6.5 2 12S6.5 22 12 22 22 17.5 22 12 17.5 2 12 2M10 17L5 12L6.41 10.59L10 14.17L17.59 6.58L19 8L10 17Z"/></svg>
                All records matched successfully with the government database. No conflicts found.
            </div>
            """

        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>Verification Report - Task #{task_id}</title>
            <link href="https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;600;700&display=swap" rel="stylesheet">
            <style>
                body {{
                    font-family: 'Outfit', sans-serif;
                    background-color: #F8FAFC;
                    color: #1E293B;
                    margin: 0;
                    padding: 40px;
                }}
                .report-container {{
                    max-width: 900px;
                    margin: 0 auto;
                    background: white;
                    border-radius: 16px;
                    box-shadow: 0 10px 30px rgba(0, 0, 0, 0.05);
                    padding: 40px;
                    border: 1px solid #E2E8F0;
                }}
                .header {{
                    display: flex;
                    justify-content: space-between;
                    align-items: center;
                    border-bottom: 2px solid #F1F5F9;
                    padding-bottom: 20px;
                    margin-bottom: 30px;
                }}
                .title {{
                    font-size: 28px;
                    font-weight: 700;
                    color: #0F172A;
                }}
                .status-badge {{
                    background-color: {status_color};
                    color: white;
                    padding: 8px 16px;
                    border-radius: 50px;
                    font-weight: 600;
                    font-size: 14px;
                }}
                .section-title {{
                    font-size: 18px;
                    font-weight: 600;
                    color: #334155;
                    margin-top: 30px;
                    margin-bottom: 15px;
                    border-left: 4px solid #6366F1;
                    padding-left: 10px;
                }}
                .grid {{
                    display: grid;
                    grid-template-columns: 1fr 1fr;
                    gap: 20px;
                }}
                .card {{
                    background: #F8FAFC;
                    border-radius: 8px;
                    padding: 20px;
                    border: 1px solid #E2E8F0;
                }}
                table {{
                    width: 100%;
                    border-collapse: collapse;
                    margin-top: 10px;
                }}
                th, td {{
                    padding: 12px;
                    text-align: left;
                    border-bottom: 1px solid #E2E8F0;
                    font-size: 14px;
                }}
                th {{
                    background-color: #F1F5F9;
                    color: #475569;
                    font-weight: 600;
                }}
                .badge {{
                    font-size: 11px;
                    padding: 3px 8px;
                    border-radius: 4px;
                    font-weight: 600;
                }}
                .badge-agent {{
                    background-color: #EEF2F6;
                    color: #4F46E5;
                }}
                .map-frame {{
                    width: 100%;
                    height: 350px;
                    border: none;
                    border-radius: 8px;
                    margin-top: 10px;
                    background: #EEE;
                }}
            </style>
        </head>
        <body>
            <div class="report-container">
                <div class="header">
                    <div>
                        <div class="title">{report_title}</div>
                        <div style="color: #64748B; font-size: 14px; margin-top: 5px;">Task ID: #{task_id} | State: {data.get('state', 'Unknown')}</div>
                    </div>
                    <div class="status-badge">{status_text}</div>
                </div>

                {conflicts_html}

                <div class="grid">
                    <div class="card">
                        <div style="font-weight:600; margin-bottom: 10px; color:#475569;">{document_card_title}</div>
                        {doc_table_html}
                    </div>

                    <div class="card">
                        <div style="font-weight:600; margin-bottom: 10px; color:#475569;">Portal Live Record (Government Search)</div>
                        {portal_table_html}
                    </div>
                </div>

                {f'''
                <div class="section-title">GIS Plot Boundary Details</div>
                <div class="card">
                    <div><b>Centroid Coordinates:</b> {gis_data.get('centroid', 'N/A')} | <b>UTM Zone:</b> {gis_data.get('utm_zone', 'N/A')}</div>
                    <div><b>Adjacent Plots:</b> {', '.join(gis_data.get('adjacent_plots', [])) if gis_data.get('adjacent_plots') else 'None'}</div>
                    <iframe class="map-frame" src="{gis_data.get('map_html_url', '')}"></iframe>
                </div>
                ''' if gis_data else ''}

                <div class="section-title">Audit Trail & Task Execution History</div>
                <table>
                    <thead>
                        <tr>
                            <th>Time</th>
                            <th>Agent</th>
                            <th>Step</th>
                            <th>Action</th>
                            <th>Status</th>
                        </tr>
                    </thead>
                    <tbody>
                        {log_rows}
                    </tbody>
                </table>
            </div>
        </body>
        </html>
        """
        
        try:
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(html_content)
            logger.info(f"HTML report successfully generated: {output_path}")
            return output_path
        except Exception as e:
            logger.error(f"HTML report generation failed: {e}")
            raise e
