import argparse
import sys
import os
from datetime import date

from luma_core.report_generator import generate_report

def main():
    parser = argparse.ArgumentParser(description="Generate Weekly/Monthly Project Report")
    parser.add_argument("--project-path", required=True, help="Path to the project root")
    parser.add_argument("--period", choices=["weekly", "monthly"], default="weekly", help="Report period")
    parser.add_argument("--date", help="Reference date in YYYY-MM-DD format (default: today)")
    parser.add_argument("--output", help="Output path for the markdown report")
    
    args = parser.parse_args()
    
    if args.date:
        try:
            ref_date = date.fromisoformat(args.date)
        except ValueError:
            print("Error: --date must be in YYYY-MM-DD format")
            sys.exit(1)
    else:
        ref_date = date.today()
        
    report_content = generate_report(args.project_path, period=args.period, reference_date=ref_date)
    
    output_path = args.output
    if not output_path:
        base_dir = os.path.join(args.project_path, "docs", "reports")
        os.makedirs(base_dir, exist_ok=True)
        
        if args.period == "weekly":
            year, week, _ = ref_date.isocalendar()
            filename = f"weekly_{year}-W{week:02d}.md"
        else:
            filename = f"monthly_{ref_date.strftime('%Y-%m')}.md"
            
        output_path = os.path.join(base_dir, filename)
        
    # ensure parent dir exists for explicit output paths
    os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
        
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(report_content)
        
    print(f"Report generated successfully at: {output_path}")

if __name__ == "__main__":
    main()
