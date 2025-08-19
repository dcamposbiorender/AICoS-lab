#!/usr/bin/env python3
"""
Comprehensive Test Report Generator for AI Chief of Staff System

Generates detailed HTML reports with:
- Test execution summary
- Performance metrics
- Coverage analysis
- Failure analysis
- Trend tracking
"""

import json
import time
from pathlib import Path
from typing import Dict, List, Any
from datetime import datetime
import argparse

import click
from jinja2 import Template


class TestReportGenerator:
    """Generates comprehensive test execution reports."""
    
    def __init__(self, reports_dir: Path = None):
        """Initialize report generator."""
        self.reports_dir = reports_dir or Path("reports")
        self.reports_dir.mkdir(exist_ok=True)
        
        # Report template
        self.html_template = self._get_html_template()
    
    def generate_comprehensive_report(self) -> str:
        """Generate comprehensive HTML report."""
        print("📊 Generating comprehensive test report...")
        
        # Collect all report data
        report_data = {
            "timestamp": datetime.now().isoformat(),
            "summary": self._collect_test_summary(),
            "performance": self._collect_performance_metrics(),
            "coverage": self._collect_coverage_data(),
            "failures": self._collect_failure_analysis(),
            "trends": self._collect_trend_data()
        }
        
        # Generate HTML report
        html_content = self.html_template.render(**report_data)
        
        # Save report
        report_path = self.reports_dir / f"comprehensive_report_{int(time.time())}.html"
        with open(report_path, 'w') as f:
            f.write(html_content)
        
        print(f"📄 Report generated: {report_path}")
        return str(report_path)
    
    def _collect_test_summary(self) -> Dict[str, Any]:
        """Collect test execution summary."""
        summary = {
            "total_tests": 0,
            "passed": 0,
            "failed": 0,
            "skipped": 0,
            "duration": 0,
            "categories": {}
        }
        
        # Look for category results
        for result_file in self.reports_dir.glob("*_results.json"):
            try:
                with open(result_file) as f:
                    data = json.load(f)
                
                category = result_file.stem.replace("_results", "")
                category_summary = data.get("summary", {})
                
                summary["categories"][category] = category_summary
                summary["total_tests"] += category_summary.get("total", 0)
                summary["passed"] += category_summary.get("passed", 0)
                summary["failed"] += category_summary.get("failed", 0)
                summary["skipped"] += category_summary.get("skipped", 0)
                
            except (json.JSONDecodeError, KeyError):
                continue
        
        # Calculate success rate
        if summary["total_tests"] > 0:
            summary["success_rate"] = (summary["passed"] / summary["total_tests"]) * 100
        else:
            summary["success_rate"] = 0
        
        return summary
    
    def _collect_performance_metrics(self) -> Dict[str, Any]:
        """Collect performance test metrics."""
        performance = {
            "search_performance": {},
            "indexing_performance": {},
            "compression_performance": {},
            "memory_usage": {}
        }
        
        # Look for performance data
        perf_file = self.reports_dir / "performance_metrics.json"
        if perf_file.exists():
            try:
                with open(perf_file) as f:
                    performance.update(json.load(f))
            except (json.JSONDecodeError, FileNotFoundError):
                pass
        
        return performance
    
    def _collect_coverage_data(self) -> Dict[str, Any]:
        """Collect test coverage data."""
        coverage = {
            "overall_coverage": 0,
            "by_module": {},
            "uncovered_lines": []
        }
        
        # Look for coverage data
        coverage_file = self.reports_dir / "coverage" / "coverage.json"
        if coverage_file.exists():
            try:
                with open(coverage_file) as f:
                    coverage.update(json.load(f))
            except (json.JSONDecodeError, FileNotFoundError):
                pass
        
        return coverage
    
    def _collect_failure_analysis(self) -> Dict[str, Any]:
        """Collect and analyze test failures."""
        failures = {
            "total_failures": 0,
            "failure_categories": {},
            "top_failures": [],
            "flaky_tests": []
        }
        
        # Analyze failure patterns
        for result_file in self.reports_dir.glob("*_results.json"):
            try:
                with open(result_file) as f:
                    data = json.load(f)
                
                test_failures = data.get("tests", [])
                for test in test_failures:
                    if test.get("outcome") == "failed":
                        failures["total_failures"] += 1
                        
                        # Categorize failure
                        failure_type = self._categorize_failure(test.get("call", {}).get("longrepr", ""))
                        failures["failure_categories"][failure_type] = failures["failure_categories"].get(failure_type, 0) + 1
                        
                        # Add to top failures
                        failures["top_failures"].append({
                            "test_name": test.get("nodeid", "unknown"),
                            "error": test.get("call", {}).get("longrepr", "")[:200] + "..." if len(test.get("call", {}).get("longrepr", "")) > 200 else test.get("call", {}).get("longrepr", ""),
                            "category": failure_type
                        })
                        
            except (json.JSONDecodeError, KeyError):
                continue
        
        # Sort top failures
        failures["top_failures"] = failures["top_failures"][:10]  # Top 10
        
        return failures
    
    def _collect_trend_data(self) -> Dict[str, Any]:
        """Collect trend data over time."""
        trends = {
            "test_count_trend": [],
            "success_rate_trend": [],
            "performance_trend": []
        }
        
        # Look for historical data
        trends_file = self.reports_dir / "trends.json"
        if trends_file.exists():
            try:
                with open(trends_file) as f:
                    trends.update(json.load(f))
            except (json.JSONDecodeError, FileNotFoundError):
                pass
        
        return trends
    
    def _categorize_failure(self, error_message: str) -> str:
        """Categorize failure based on error message."""
        error_lower = error_message.lower()
        
        if "assertion" in error_lower:
            return "Assertion Error"
        elif "timeout" in error_lower:
            return "Timeout"
        elif "connection" in error_lower or "network" in error_lower:
            return "Network Error"
        elif "permission" in error_lower or "access" in error_lower:
            return "Permission Error"
        elif "memory" in error_lower:
            return "Memory Error"
        elif "import" in error_lower or "module" in error_lower:
            return "Import Error"
        else:
            return "Other"
    
    def _get_html_template(self) -> Template:
        """Get HTML template for report generation."""
        template_content = """
<!DOCTYPE html>
<html>
<head>
    <title>AI Chief of Staff - Comprehensive Test Report</title>
    <meta charset="utf-8">
    <style>
        body { font-family: Arial, sans-serif; margin: 40px; background: #f5f5f5; }
        .container { max-width: 1200px; margin: 0 auto; background: white; padding: 30px; border-radius: 8px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }
        h1 { color: #2c3e50; border-bottom: 3px solid #3498db; padding-bottom: 10px; }
        h2 { color: #34495e; margin-top: 30px; }
        .summary-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(250px, 1fr)); gap: 20px; margin: 20px 0; }
        .metric-card { background: #ecf0f1; padding: 20px; border-radius: 6px; text-align: center; }
        .metric-value { font-size: 2em; font-weight: bold; color: #2c3e50; }
        .metric-label { color: #7f8c8d; margin-top: 5px; }
        .success { color: #27ae60; }
        .warning { color: #f39c12; }
        .error { color: #e74c3c; }
        table { width: 100%; border-collapse: collapse; margin: 20px 0; }
        th, td { padding: 12px; text-align: left; border-bottom: 1px solid #bdc3c7; }
        th { background: #34495e; color: white; }
        .progress-bar { width: 100%; height: 20px; background: #ecf0f1; border-radius: 10px; overflow: hidden; }
        .progress-fill { height: 100%; background: linear-gradient(90deg, #27ae60, #2ecc71); transition: width 0.3s ease; }
        .timestamp { color: #7f8c8d; font-size: 0.9em; }
        .failure-box { background: #fdf2f2; border-left: 4px solid #e74c3c; padding: 15px; margin: 10px 0; }
        .category-badge { display: inline-block; background: #3498db; color: white; padding: 4px 8px; border-radius: 12px; font-size: 0.8em; margin: 2px; }
    </style>
</head>
<body>
    <div class="container">
        <h1>AI Chief of Staff - Comprehensive Test Report</h1>
        <div class="timestamp">Generated: {{ timestamp }}</div>
        
        <h2>📊 Test Execution Summary</h2>
        <div class="summary-grid">
            <div class="metric-card">
                <div class="metric-value {{ 'success' if summary.success_rate >= 95 else 'warning' if summary.success_rate >= 85 else 'error' }}">
                    {{ "%.1f"|format(summary.success_rate) }}%
                </div>
                <div class="metric-label">Success Rate</div>
            </div>
            <div class="metric-card">
                <div class="metric-value">{{ summary.total_tests }}</div>
                <div class="metric-label">Total Tests</div>
            </div>
            <div class="metric-card">
                <div class="metric-value success">{{ summary.passed }}</div>
                <div class="metric-label">Passed</div>
            </div>
            <div class="metric-card">
                <div class="metric-value error">{{ summary.failed }}</div>
                <div class="metric-label">Failed</div>
            </div>
        </div>
        
        <div class="progress-bar">
            <div class="progress-fill" style="width: {{ summary.success_rate }}%"></div>
        </div>
        
        <h2>🎯 Test Categories</h2>
        <table>
            <tr>
                <th>Category</th>
                <th>Total</th>
                <th>Passed</th>
                <th>Failed</th>
                <th>Success Rate</th>
            </tr>
            {% for category, stats in summary.categories.items() %}
            <tr>
                <td>{{ category.title() }}</td>
                <td>{{ stats.total or 0 }}</td>
                <td class="success">{{ stats.passed or 0 }}</td>
                <td class="error">{{ stats.failed or 0 }}</td>
                <td>
                    {% if stats.total and stats.total > 0 %}
                        {{ "%.1f"|format((stats.passed or 0) / stats.total * 100) }}%
                    {% else %}
                        N/A
                    {% endif %}
                </td>
            </tr>
            {% endfor %}
        </table>
        
        <h2>⚡ Performance Metrics</h2>
        <div class="summary-grid">
            {% if performance.search_performance %}
            <div class="metric-card">
                <div class="metric-value">{{ performance.search_performance.get('avg_response_time', 'N/A') }}</div>
                <div class="metric-label">Avg Search Time (s)</div>
            </div>
            {% endif %}
            {% if performance.indexing_performance %}
            <div class="metric-card">
                <div class="metric-value">{{ performance.indexing_performance.get('records_per_second', 'N/A') }}</div>
                <div class="metric-label">Indexing Rate (rec/s)</div>
            </div>
            {% endif %}
            {% if performance.compression_performance %}
            <div class="metric-card">
                <div class="metric-value">{{ performance.compression_performance.get('compression_ratio', 'N/A') }}%</div>
                <div class="metric-label">Compression Ratio</div>
            </div>
            {% endif %}
            {% if performance.memory_usage %}
            <div class="metric-card">
                <div class="metric-value">{{ performance.memory_usage.get('peak_mb', 'N/A') }}MB</div>
                <div class="metric-label">Peak Memory</div>
            </div>
            {% endif %}
        </div>
        
        <h2>📈 Test Coverage</h2>
        <div class="progress-bar">
            <div class="progress-fill" style="width: {{ coverage.overall_coverage or 0 }}%"></div>
        </div>
        <p>Overall Coverage: {{ coverage.overall_coverage or 0 }}%</p>
        
        {% if failures.total_failures > 0 %}
        <h2>❌ Failure Analysis</h2>
        <p>Total Failures: <span class="error">{{ failures.total_failures }}</span></p>
        
        <h3>Failure Categories</h3>
        {% for category, count in failures.failure_categories.items() %}
        <span class="category-badge">{{ category }}: {{ count }}</span>
        {% endfor %}
        
        <h3>Top Failures</h3>
        {% for failure in failures.top_failures[:5] %}
        <div class="failure-box">
            <strong>{{ failure.test_name }}</strong>
            <br>
            <small>{{ failure.error }}</small>
        </div>
        {% endfor %}
        {% endif %}
        
        <h2>📊 System Statistics</h2>
        <table>
            <tr>
                <th>Metric</th>
                <th>Value</th>
                <th>Status</th>
            </tr>
            <tr>
                <td>Test Execution Time</td>
                <td>{{ summary.duration or 'N/A' }} seconds</td>
                <td class="{{ 'success' if (summary.duration or 0) < 1800 else 'warning' }}">
                    {{ 'Good' if (summary.duration or 0) < 1800 else 'Slow' }}
                </td>
            </tr>
            <tr>
                <td>Memory Usage</td>
                <td>{{ performance.memory_usage.get('peak_mb', 'N/A') }}MB</td>
                <td class="{{ 'success' if (performance.memory_usage.get('peak_mb', 0) or 0) < 500 else 'warning' }}">
                    {{ 'Good' if (performance.memory_usage.get('peak_mb', 0) or 0) < 500 else 'High' }}
                </td>
            </tr>
            <tr>
                <td>Search Performance</td>
                <td>{{ performance.search_performance.get('avg_response_time', 'N/A') }}s</td>
                <td class="{{ 'success' if (performance.search_performance.get('avg_response_time', 0) or 0) < 1.0 else 'warning' }}">
                    {{ 'Good' if (performance.search_performance.get('avg_response_time', 0) or 0) < 1.0 else 'Slow' }}
                </td>
            </tr>
        </table>
        
        <div class="timestamp">
            Report generated by AI Chief of Staff Comprehensive Test Suite
        </div>
    </div>
</body>
</html>
        """
        
        return Template(template_content)


@click.command()
@click.option("--reports-dir", type=click.Path(), default="reports", help="Reports directory")
@click.option("--output", type=click.Path(), help="Output file path")
@click.option("--open-browser", is_flag=True, help="Open report in browser")
def main(reports_dir: str, output: str, open_browser: bool):
    """Generate comprehensive test report."""
    generator = TestReportGenerator(Path(reports_dir))
    report_path = generator.generate_comprehensive_report()
    
    if output:
        # Copy to specified output location
        import shutil
        shutil.copy2(report_path, output)
        print(f"📄 Report copied to: {output}")
    
    if open_browser:
        import webbrowser
        webbrowser.open(f"file://{Path(report_path).absolute()}")
        print("🌐 Report opened in browser")


if __name__ == "__main__":
    main()