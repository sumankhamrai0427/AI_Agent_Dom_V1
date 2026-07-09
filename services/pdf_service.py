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
                from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
                from openpyxl.utils import get_column_letter
                
                wb = openpyxl.Workbook()
                
                # Colors
                navy_blue_fill = PatternFill(start_color="1E3A8A", end_color="1E3A8A", fill_type="solid")
                light_blue_fill = PatternFill(start_color="DBEAFE", end_color="DBEAFE", fill_type="solid")
                gray_fill = PatternFill(start_color="F3F4F6", end_color="F3F4F6", fill_type="solid")
                
                green_fill = PatternFill(start_color="D1FAE5", end_color="D1FAE5", fill_type="solid")
                red_fill = PatternFill(start_color="FEE2E2", end_color="FEE2E2", fill_type="solid")
                orange_fill = PatternFill(start_color="FEF3C7", end_color="FEF3C7", fill_type="solid")
                
                green_text_color = "065F46"
                red_text_color = "991B1B"
                orange_text_color = "92400E"
                
                thin_border_side = Side(border_style="thin", color="CBD5E1")
                thin_border = Border(left=thin_border_side, right=thin_border_side, top=thin_border_side, bottom=thin_border_side)
                
                font_title = Font(name="Calibri", size=16, bold=True, color="FFFFFF")
                font_header = Font(name="Calibri", size=11, bold=True, color="1E293B")
                font_bold = Font(name="Calibri", size=11, bold=True)
                font_regular = Font(name="Calibri", size=11)
                
                # ==========================================
                # Sheet 1: Audit Trails (Active Sheet)
                # ==========================================
                ws_logs = wb.active
                ws_logs.title = "Audit Trail"
                ws_logs.views.sheetView[0].showGridLines = True
                
                # Title block
                ws_logs.merge_cells("A1:E1")
                title_cell = ws_logs["A1"]
                title_cell.value = "Audit Trail & Task Execution History"
                title_cell.font = font_title
                title_cell.fill = navy_blue_fill
                title_cell.alignment = Alignment(horizontal="center", vertical="center")
                ws_logs.row_dimensions[1].height = 40
                
                # Subtitle info
                ws_logs.merge_cells("A2:E2")
                sub_cell = ws_logs["A2"]
                sub_cell.value = f"Task ID: #{task_id} | State: {data.get('state', 'N/A')}"
                sub_cell.font = Font(name="Calibri", size=11, italic=True, color="FFFFFF")
                sub_cell.fill = navy_blue_fill
                sub_cell.alignment = Alignment(horizontal="center", vertical="center")
                ws_logs.row_dimensions[2].height = 20
                
                # Spacer
                ws_logs.append([])
                ws_logs.row_dimensions[3].height = 10
                
                # Table Headers
                headers = ["Time", "Agent", "Step", "Action", "Status"]
                ws_logs.append(headers)
                ws_logs.row_dimensions[4].height = 25
                for col_idx in range(1, 6):
                    cell = ws_logs.cell(row=4, column=col_idx)
                    cell.font = font_header
                    cell.fill = light_blue_fill
                    cell.alignment = Alignment(horizontal="center", vertical="center")
                    cell.border = thin_border
                
                # Table Data
                row_idx = 5
                for log in logs:
                    time_str = log.timestamp.strftime('%H:%M:%S') if hasattr(log.timestamp, 'strftime') else str(log.timestamp)
                    ws_logs.append([
                        time_str,
                        log.agent_name,
                        log.step_name or "",
                        log.action or "",
                        log.status
                    ])
                    ws_logs.row_dimensions[row_idx].height = 20
                    
                    # Style cells
                    for col_idx in range(1, 6):
                        cell = ws_logs.cell(row=row_idx, column=col_idx)
                        cell.font = font_regular
                        cell.border = thin_border
                        
                        # Alignments
                        if col_idx in [1, 2, 5]:
                            cell.alignment = Alignment(horizontal="center", vertical="center")
                        else:
                            cell.alignment = Alignment(horizontal="left", vertical="center")
                            
                        # Agent highlighting
                        if col_idx == 2:
                            cell.font = font_bold
                            
                        # Status coloring
                        if col_idx == 5:
                            status_val = str(cell.value).upper()
                            cell.font = font_bold
                            if status_val == "SUCCESS":
                                cell.fill = green_fill
                                cell.font = Font(name="Calibri", size=11, bold=True, color=green_text_color)
                            elif status_val in ["FAILURE", "ERROR"]:
                                cell.fill = red_fill
                                cell.font = Font(name="Calibri", size=11, bold=True, color=red_text_color)
                            else:
                                cell.fill = orange_fill
                                cell.font = Font(name="Calibri", size=11, bold=True, color=orange_text_color)
                                
                    row_idx += 1
                
                # Auto-adjust column widths
                for col in ws_logs.columns:
                    max_len = 0
                    for cell in col:
                        # Don't check merged cell content length for auto-width to avoid huge columns
                        if cell.coordinate in ["A1", "B1", "C1", "D1", "E1", "A2", "B2", "C2", "D2", "E2"]:
                            continue
                        if cell.value:
                            max_len = max(max_len, len(str(cell.value)))
                    col_letter = get_column_letter(col[0].column)
                    ws_logs.column_dimensions[col_letter].width = max(max_len + 4, 12)
                
                # ==========================================
                # Sheet 2: Verification Details
                # ==========================================
                ws_summary = wb.create_sheet(title="Verification Summary")
                ws_summary.views.sheetView[0].showGridLines = True
                
                ws_summary.merge_cells("A1:D1")
                s_title = ws_summary["A1"]
                s_title.value = "Verification & Matching Report Summary"
                s_title.font = font_title
                s_title.fill = navy_blue_fill
                s_title.alignment = Alignment(horizontal="center", vertical="center")
                ws_summary.row_dimensions[1].height = 40
                
                utility_type = data.get("document", {}).get("utility_type", "LAND")
                is_valid = data.get("verification", {}).get("is_valid", True)
                status_text = "VERIFIED / MATCHED" if is_valid else "CONFLICT DETECTED"
                
                ws_summary.merge_cells("A2:D2")
                s_status = ws_summary["A2"]
                s_status.value = f"STATUS: {status_text}"
                s_status.font = font_bold
                s_status.alignment = Alignment(horizontal="center", vertical="center")
                s_status.fill = green_fill if is_valid else red_fill
                s_status.font = Font(name="Calibri", size=11, bold=True, color=green_text_color if is_valid else red_text_color)
                ws_summary.row_dimensions[2].height = 25
                
                ws_summary.append([]) # spacing row
                
                # Headers for Comparison
                ws_summary.append(["Field Name", "Document Value (Extracted)", "Portal Value (Government)", "Match Status"])
                ws_summary.row_dimensions[4].height = 25
                for col_idx in range(1, 5):
                    cell = ws_summary.cell(row=4, column=col_idx)
                    cell.font = font_header
                    cell.fill = light_blue_fill
                    cell.border = thin_border
                    cell.alignment = Alignment(horizontal="center", vertical="center")
                
                # Set up comparison fields
                fields = []
                if utility_type == "ELECTRICITY":
                    fields = [
                        ("owner_name", "Customer Name"),
                        ("consumer_id", "Consumer ID"),
                        ("installation_no", "Installation ID"),
                        ("bill_amount", "Bill Amount"),
                        ("bill_month", "Bill Month")
                    ]
                elif utility_type == "SHARE_MARKET":
                    fields = [
                        ("symbol", "Stock Symbol"),
                        ("name", "Company Name"),
                        ("price", "Current Price"),
                        ("change", "Change Today")
                    ]
                else: # LAND
                    fields = [
                        ("owner_name", "Owner Name"),
                        ("father_name", "Father Name"),
                        ("village", "Village"),
                        ("district", "District"),
                        ("khata", "Khata Number"),
                        ("khasra", "Khasra/Plot"),
                        ("area", "Area")
                    ]
                
                doc_obj = data.get("document", {})
                port_obj = data.get("portal", {})
                
                s_row = 5
                for key, label in fields:
                    doc_val = doc_obj.get(key, "N/A")
                    port_val = port_obj.get(key, "N/A")
                    
                    is_match = "Matched"
                    if doc_val != "N/A" and port_val != "N/A":
                        if str(doc_val).strip().lower() != str(port_val).strip().lower():
                            is_match = "Mismatch"
                    else:
                        is_match = "N/A"
                        
                    ws_summary.append([label, str(doc_val), str(port_val), is_match])
                    ws_summary.row_dimensions[s_row].height = 20
                    
                    for col_idx in range(1, 5):
                        cell = ws_summary.cell(row=s_row, column=col_idx)
                        cell.font = font_regular
                        cell.border = thin_border
                        
                        if col_idx == 1:
                            cell.font = font_bold
                            cell.fill = gray_fill
                        
                        if col_idx == 4:
                            cell.alignment = Alignment(horizontal="center", vertical="center")
                            cell.font = font_bold
                            if cell.value == "Matched":
                                cell.fill = green_fill
                                cell.font = Font(name="Calibri", size=11, bold=True, color=green_text_color)
                            elif cell.value == "Mismatch":
                                cell.fill = red_fill
                                cell.font = Font(name="Calibri", size=11, bold=True, color=red_text_color)
                            else:
                                cell.fill = gray_fill
                                
                    s_row += 1
                
                # Conflicts / Discrepancies Section
                conflicts = data.get("verification", {}).get("conflicts", [])
                if conflicts:
                    s_row += 1
                    ws_summary.cell(row=s_row, column=1).value = ""
                    s_row += 1
                    
                    ws_summary.merge_cells(start_row=s_row, start_column=1, end_row=s_row, end_column=4)
                    c_hdr = ws_summary.cell(row=s_row, column=1)
                    c_hdr.value = "Discrepancies / Conflicts Identified"
                    c_hdr.font = font_header
                    c_hdr.fill = red_fill
                    c_hdr.alignment = Alignment(horizontal="left", vertical="center")
                    ws_summary.row_dimensions[s_row].height = 22
                    
                    s_row += 1
                    for conflict in conflicts:
                        ws_summary.merge_cells(start_row=s_row, start_column=1, end_row=s_row, end_column=4)
                        c_cell = ws_summary.cell(row=s_row, column=1)
                        c_cell.value = f" - {conflict}"
                        c_cell.font = Font(name="Calibri", size=11, color=red_text_color)
                        c_cell.border = Border(left=thin_border_side, right=thin_border_side)
                        ws_summary.row_dimensions[s_row].height = 18
                        s_row += 1
                        
                    # Add bottom border to last conflict row
                    for col_idx in range(1, 5):
                        ws_summary.cell(row=s_row-1, column=col_idx).border = Border(left=thin_border_side, right=thin_border_side, bottom=thin_border_side)
                
                # AI Insights Section
                ai_analysis = data.get("ai_analysis", {})
                if ai_analysis and not ai_analysis.get("insufficient_data"):
                    s_row += 1
                    ws_summary.cell(row=s_row, column=1).value = ""
                    s_row += 1
                    
                    ws_summary.merge_cells(start_row=s_row, start_column=1, end_row=s_row, end_column=4)
                    ai_hdr = ws_summary.cell(row=s_row, column=1)
                    ai_hdr.value = "AI Insights & Recommendations"
                    ai_hdr.font = font_header
                    ai_hdr.fill = light_blue_fill
                    ai_hdr.alignment = Alignment(horizontal="left", vertical="center")
                    ws_summary.row_dimensions[s_row].height = 22
                    
                    s_row += 1
                    ws_summary.merge_cells(start_row=s_row, start_column=1, end_row=s_row, end_column=4)
                    ai_sum = ws_summary.cell(row=s_row, column=1)
                    ai_sum.value = f"Summary: {ai_analysis.get('summary', '')}"
                    ai_sum.font = font_regular
                    ai_sum.alignment = Alignment(wrap_text=True, vertical="top")
                    ws_summary.row_dimensions[s_row].height = 45
                    
                    s_row += 1
                    ws_summary.merge_cells(start_row=s_row, start_column=1, end_row=s_row, end_column=4)
                    ai_rec = ws_summary.cell(row=s_row, column=1)
                    ai_rec.value = f"Recommendation: {ai_analysis.get('recommendation', '')}"
                    ai_rec.font = font_regular
                    ai_rec.alignment = Alignment(wrap_text=True, vertical="top")
                    ws_summary.row_dimensions[s_row].height = 55
                    
                    # Add border around AI insights
                    for r in [s_row-1, s_row]:
                        for col_idx in range(1, 5):
                            ws_summary.cell(row=r, column=col_idx).border = Border(
                                left=thin_border_side, 
                                right=thin_border_side,
                                bottom=thin_border_side if r == s_row else Side(style=None)
                            )
                
                # Auto-adjust column widths
                for col in ws_summary.columns:
                    max_len = 0
                    for cell in col:
                        if cell.row in [1, 2]: # Skip merged titles
                            continue
                        # Skip long AI text wrapping rows to keep column size reasonable
                        if ai_analysis and not ai_analysis.get("insufficient_data") and cell.row in [s_row, s_row-1]:
                            continue
                        if cell.value:
                            max_len = max(max_len, len(str(cell.value)))
                    col_letter = get_column_letter(col[0].column)
                    ws_summary.column_dimensions[col_letter].width = max(max_len + 4, 18)
                
                # ==========================================
                # Sheet 3: Bill History
                # ==========================================
                bill_history = data.get("portal", {}).get("bill_history", []) if isinstance(data.get("portal"), dict) else []
                if bill_history:
                    ws_history = wb.create_sheet(title="Bill History")
                    ws_history.views.sheetView[0].showGridLines = True
                    
                    ws_history.merge_cells("A1:E1")
                    h_title = ws_history["A1"]
                    h_title.value = "Historical Billing Records (Government Portal)"
                    h_title.font = font_title
                    h_title.fill = navy_blue_fill
                    h_title.alignment = Alignment(horizontal="center", vertical="center")
                    ws_history.row_dimensions[1].height = 40
                    
                    ws_history.append([])
                    
                    ws_history.append(["Invoice Number", "Bill Month", "Due Date", "Amount Before Due", "Amount After Due"])
                    ws_history.row_dimensions[3].height = 25
                    for col_idx in range(1, 6):
                        cell = ws_history.cell(row=3, column=col_idx)
                        cell.font = font_header
                        cell.fill = light_blue_fill
                        cell.border = thin_border
                        cell.alignment = Alignment(horizontal="center", vertical="center")
                        
                    h_row = 4
                    for bill in bill_history:
                        ws_history.append([
                            bill.get("invoice_number", ""),
                            bill.get("bill_month", ""),
                            bill.get("bill_due_date", ""),
                            bill.get("amount_before_due", ""),
                            bill.get("amount_after_due", "")
                        ])
                        ws_history.row_dimensions[h_row].height = 20
                        
                        for col_idx in range(1, 6):
                            cell = ws_history.cell(row=h_row, column=col_idx)
                            cell.font = font_regular
                            cell.border = thin_border
                            if col_idx in [4, 5]:
                                cell.alignment = Alignment(horizontal="right", vertical="center")
                            else:
                                cell.alignment = Alignment(horizontal="center", vertical="center")
                        h_row += 1
                        
                    for col in ws_history.columns:
                        max_len = 0
                        for cell in col:
                            if cell.row == 1:
                                continue
                            if cell.value:
                                max_len = max(max_len, len(str(cell.value)))
                        col_letter = get_column_letter(col[0].column)
                        ws_history.column_dimensions[col_letter].width = max(max_len + 4, 15)
                
                wb.save(output_path)
                logger.info(f"Excel report successfully generated: {output_path}")
                return output_path
                
            except Exception as e:
                import traceback
                logger.error(f"Excel report generation failed: {e}. {traceback.format_exc()}. Falling back to CSV.")
        
        # Fallback to CSV format
        csv_path = output_path.replace(".xlsx", ".csv")
        try:
            with open(csv_path, 'w', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                writer.writerow(["=== AUDIT TRAIL & TASK EXECUTION HISTORY ==="])
                writer.writerow(["Time", "Agent", "Step", "Action", "Status"])
                for log in logs:
                    time_str = log.timestamp.strftime('%H:%M:%S') if hasattr(log.timestamp, 'strftime') else str(log.timestamp)
                    writer.writerow([
                        time_str,
                        log.agent_name,
                        log.step_name or "",
                        log.action or "",
                        log.status
                    ])
                
                writer.writerow([])
                writer.writerow(["=== VERIFICATION SUMMARY ==="])
                utility_type = data.get("document", {}).get("utility_type", "LAND")
                writer.writerow(["Utility Type", utility_type])
                writer.writerow(["State", data.get("state", "N/A")])
                is_valid = data.get("verification", {}).get("is_valid", True)
                writer.writerow(["Verification Status", "VERIFIED / MATCHED" if is_valid else "CONFLICT DETECTED"])
                
                writer.writerow([])
                writer.writerow(["Field Name", "Document Value (Extracted)", "Portal Value (Government)", "Match Status"])
                
                fields = []
                if utility_type == "ELECTRICITY":
                    fields = [
                        ("owner_name", "Customer Name"),
                        ("consumer_id", "Consumer ID"),
                        ("installation_no", "Installation ID"),
                        ("bill_amount", "Bill Amount"),
                        ("bill_month", "Bill Month")
                    ]
                elif utility_type == "SHARE_MARKET":
                    fields = [
                        ("symbol", "Stock Symbol"),
                        ("name", "Company Name"),
                        ("price", "Current Price"),
                        ("change", "Change Today")
                    ]
                else:
                    fields = [
                        ("owner_name", "Owner Name"),
                        ("father_name", "Father Name"),
                        ("village", "Village"),
                        ("district", "District"),
                        ("khata", "Khata Number"),
                        ("khasra", "Khasra/Plot"),
                        ("area", "Area")
                    ]
                
                doc_obj = data.get("document", {})
                port_obj = data.get("portal", {})
                conflicts = data.get("verification", {}).get("conflicts", [])
                
                for key, label in fields:
                    doc_val = doc_obj.get(key, "N/A")
                    port_val = port_obj.get(key, "N/A")
                    is_match = "Matched"
                    if doc_val != "N/A" and port_val != "N/A":
                        if str(doc_val).strip().lower() != str(port_val).strip().lower():
                            is_match = "Mismatch"
                    else:
                        is_match = "N/A"
                    writer.writerow([label, str(doc_val), str(port_val), is_match])
                
                if conflicts:
                    writer.writerow([])
                    writer.writerow(["=== DISCREPANCIES / CONFLICTS ==="])
                    for conflict in conflicts:
                        writer.writerow([conflict])
                        
                ai_analysis = data.get("ai_analysis", {})
                if ai_analysis and not ai_analysis.get("insufficient_data"):
                    writer.writerow([])
                    writer.writerow(["=== AI ANALYSIS ==="])
                    writer.writerow(["Summary", ai_analysis.get("summary", "")])
                    writer.writerow(["Recommendation", ai_analysis.get("recommendation", "")])
 
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
        if utility_type == "ELECTRICITY":
            report_title = "Electricity Bill Verification Report"
            document_card_title = "Extracted Customer Bill (PDF/OCR)"
        elif utility_type == "SHARE_MARKET":
            report_title = "Share Market Analysis Report"
            document_card_title = "Target Stock Info"
        else:
            report_title = "Land Record Verification Report"
            document_card_title = "Extracted Owner Deed (PDF/OCR)"
        
        # Parse verification conflicts or status
        is_valid = data.get("verification", {}).get("is_valid", True)
        status_text = "VERIFIED / MATCHED" if is_valid else "CONFLICT DETECTED"
        status_color = "#10B981" if is_valid else "#EF4444"

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
        elif utility_type == "SHARE_MARKET":
            doc_table_html = f"""
            <table style="margin-top:0;">
                <tr><td>Target Symbol</td><td><b>{data.get('document', {}).get('symbol', 'N/A')}</b></td></tr>
                <tr><td>Task Objective</td><td>Market Analysis & Trend Prediction</td></tr>
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
            elif utility_type == "SHARE_MARKET":
                portal_table_html = f"""
                <table style="margin-top:0;">
                    <tr><td>Company Name</td><td><b>{data.get('portal', {}).get('name', 'N/A')}</b></td></tr>
                    <tr><td>Current Price</td><td>{data.get('portal', {}).get('api_price') or data.get('portal', {}).get('price', 'N/A')}</td></tr>
                    <tr><td>Today's Change</td><td>{data.get('portal', {}).get('change', 'N/A')}</td></tr>
                    <tr><td>Today's High</td><td>{data.get('portal', {}).get('api_high', 'N/A')}</td></tr>
                    <tr><td>Today's Low</td><td>{data.get('portal', {}).get('api_low', 'N/A')}</td></tr>
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

        bill_history_html = ""
        bill_history = data.get("portal", {}).get("bill_history", []) if isinstance(data.get("portal"), dict) else []
        if bill_history:
            bill_rows = ""
            for bill in bill_history:
                bill_rows += f"""
                <tr>
                    <td>{bill.get('invoice_number', '')}</td>
                    <td>{bill.get('bill_month', '')}</td>
                    <td>{bill.get('bill_due_date', '')}</td>
                    <td>{bill.get('amount_before_due', '')}</td>
                    <td>{bill.get('amount_after_due', '')}</td>
                </tr>
                """
            
            bill_history_html = f"""
            <div class="section-title">Historical Bills</div>
            <div class="card" style="padding: 0; overflow-x: auto;">
                <table style="margin-top: 0; width: 100%;">
                    <thead>
                        <tr>
                            <th>Invoice Number</th>
                            <th>Bill Month</th>
                            <th>Due Date</th>
                            <th>Amt (Before Due)</th>
                            <th>Amt (After Due)</th>
                        </tr>
                    </thead>
                    <tbody>
                        {bill_rows}
                    </tbody>
                </table>
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

                {bill_history_html}

                {f'''
                <div class="section-title">GIS Plot Boundary Details</div>
                <div class="card">
                    <div><b>Centroid Coordinates:</b> {gis_data.get('centroid', 'N/A')} | <b>UTM Zone:</b> {gis_data.get('utm_zone', 'N/A')}</div>
                    <div><b>Adjacent Plots:</b> {', '.join(gis_data.get('adjacent_plots', [])) if gis_data.get('adjacent_plots') else 'None'}</div>
                    <iframe class="map-frame" src="{gis_data.get('map_html_url', '')}"></iframe>
                </div>
                ''' if gis_data else ''}

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
