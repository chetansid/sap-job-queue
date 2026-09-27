import time

def process_sap_report(report_name: str, pages: int) -> dict:
    print(f"Starting: {report_name} ({pages} pages)")
    time.sleep(pages * 0.5)
    print(f"Finished: {report_name}")
    return {
        "report_name": report_name,
        "pages_processed": pages,
        "status": "completed"
    }