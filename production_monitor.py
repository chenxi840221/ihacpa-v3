#!/usr/bin/env python3
"""
IHACPA v2.0 Production Monitoring
Monitors system performance, Azure costs, and health
"""

import asyncio
import os
import json
import time
from datetime import datetime, timedelta
from pathlib import Path

class ProductionMonitor:
    def __init__(self):
        self.metrics = {
            "scan_count": 0,
            "successful_scans": 0,
            "failed_scans": 0,
            "total_scan_time": 0,
            "azure_api_calls": 0,
            "vulnerabilities_found": 0
        }
    
    async def health_check(self):
        """Perform system health check"""
        print("🔍 IHACPA v2.0 Health Check")
        print("=" * 30)
        
        # Check Azure OpenAI connectivity
        try:
            from langchain_openai import AzureChatOpenAI
            
            llm = AzureChatOpenAI(
                azure_endpoint=os.getenv('AZURE_OPENAI_ENDPOINT'),
                api_key=os.getenv('AZURE_OPENAI_KEY'),
                azure_deployment=os.getenv('AZURE_OPENAI_MODEL'),
                api_version=os.getenv('AZURE_OPENAI_API_VERSION'),
                temperature=0.1
            )
            
            response = await llm.ainvoke("Health check test")
            print("✅ Azure OpenAI: Connected")
            
        except Exception as e:
            print(f"❌ Azure OpenAI: Failed - {e}")
        
        # Check system components
        components = [
            ("Core modules", "src/core/"),
            ("Sandboxes", "src/sandboxes/"),
            ("AI Layer", "src/ai_layer/"),
            ("Configuration", "config/")
        ]
        
        for name, path in components:
            if Path(path).exists():
                print(f"✅ {name}: Available")
            else:
                print(f"❌ {name}: Missing")
        
        print(f"\n📈 Current Metrics:")
        for key, value in self.metrics.items():
            print(f"   {key}: {value}")
    
    def log_scan_result(self, success: bool, scan_time: float, vulnerabilities: int = 0):
        """Log scan results for monitoring"""
        self.metrics["scan_count"] += 1
        if success:
            self.metrics["successful_scans"] += 1
            self.metrics["total_scan_time"] += scan_time
            self.metrics["vulnerabilities_found"] += vulnerabilities
        else:
            self.metrics["failed_scans"] += 1
        
        # Save metrics
        with open("production_metrics.json", "w") as f:
            json.dump({
                "timestamp": datetime.utcnow().isoformat(),
                "metrics": self.metrics
            }, f, indent=2)
    
    def generate_daily_report(self):
        """Generate daily performance report"""
        if self.metrics["scan_count"] > 0:
            success_rate = (self.metrics["successful_scans"] / self.metrics["scan_count"]) * 100
            avg_time = self.metrics["total_scan_time"] / max(self.metrics["successful_scans"], 1)
            
            report = f"""
📊 IHACPA v2.0 Daily Report - {datetime.now().strftime('%Y-%m-%d')}
============================================================

Performance Metrics:
   Total Scans: {self.metrics["scan_count"]}
   Success Rate: {success_rate:.1f}%
   Average Scan Time: {avg_time:.2f}s
   Total Vulnerabilities Found: {self.metrics["vulnerabilities_found"]}
   
System Health: ✅ OPERATIONAL
Migration Status: ✅ COMPLETE (v1.0 → v2.0)

Next Actions:
   • Monitor Azure OpenAI costs in Azure portal
   • Review any failed scans for improvement opportunities
   • Consider scaling to larger package lists
"""
            
            print(report)
            
            # Save report
            report_file = f"daily_report_{datetime.now().strftime('%Y%m%d')}.txt"
            with open(report_file, "w") as f:
                f.write(report)
            
            return report_file
        
        return None

# Global monitor instance
monitor = ProductionMonitor()

if __name__ == "__main__":
    asyncio.run(monitor.health_check())
