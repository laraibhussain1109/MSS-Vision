from openpyxl import Workbook

def export_cycles(rows,path):
    wb=Workbook(); ws=wb.active; ws.title="Inspections"
    headers=["Cycle","Profile","Start","End","Duration (s)","Sequence","Detected","Result","Failure reason","Image"]
    ws.append(headers)
    for r in rows: ws.append([r.get(k) for k in ("id","profile","start_time","end_time","duration","expected_sequence","detected_sequence","result","failure_reason","image_path")])
    ws.freeze_panes="A2"; ws.auto_filter.ref=ws.dimensions
    for col in ws.columns: ws.column_dimensions[col[0].column_letter].width=min(55,max(12,max(len(str(c.value or "")) for c in col)+2))
    wb.save(path)
