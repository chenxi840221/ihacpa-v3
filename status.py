#!/usr/bin/env python3
"""Quick status check for IHACPA v2.0"""

import json
from datetime import datetime
from pathlib import Path

print("🔷 IHACPA v2.0 Production Status")
print("=" * 40)

# Check if migration completed
if Path("legacy/v1.0").exists():
    print("✅ Migration: COMPLETE (v1.0 archived)")
else:
    print("⚠️ Migration: In progress")

# Check metrics
if Path("production_metrics.json").exists():
    with open("production_metrics.json") as f:
        data = json.load(f)
        metrics = data["metrics"]
        
    print(f"📊 Recent Performance:")
    print(f"   Scans: {metrics['scan_count']}")
    print(f"   Success Rate: {metrics['successful_scans']}/{metrics['scan_count']}")
    print(f"   Vulnerabilities Found: {metrics['vulnerabilities_found']}")
else:
    print("📊 No metrics available yet")

print(f"\n⏰ Status as of: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
print("\n📋 Commands:")
print("   python production_monitor.py  # Full health check")
print("   python main.py                # Run v2.0 scanner")
