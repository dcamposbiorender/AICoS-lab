#!/usr/bin/env python3
"""
Comprehensive Test Runner for AI Chief of Staff System

Provides different test execution modes:
- quick: Critical path validation (5 minutes)
- standard: Unit + Integration + E2E (30 minutes)
- comprehensive: All tests including performance (2 hours)
- overnight: Full suite including endurance tests (8 hours)
"""

import sys
import argparse
import subprocess
import time
from pathlib import Path
from typing import List, Dict, Any
import json

import click
from colorama import init, Fore, Style
from tabulate import tabulate

# Initialize colorama for cross-platform colored output
init()

class TestRunner:
    """Orchestrates test execution with different modes and reporting."""
    
    def __init__(self):
        self.start_time = None
        self.results = {
            "total_tests": 0,
            "passed": 0,
            "failed": 0,
            "skipped": 0,
            "errors": 0,
            "duration": 0,
            "coverage": 0
        }
    
    def run_test_category(self, category: str, markers: str = None) -> Dict[str, Any]:
        """Run tests for a specific category."""
        print(f"\n{Fore.CYAN}Running {category} tests...{Style.RESET_ALL}")
        
        cmd = ["python3", "-m", "pytest", f"{category}/"]
        
        if markers:
            cmd.extend(["-m", markers])
        
        cmd.extend([
            "--tb=short",
            "--quiet",
            "-v"
        ])
        
        start = time.time()
        result = subprocess.run(cmd, capture_output=True, text=True)
        duration = time.time() - start
        
        # Parse results directly from pytest output
        output = result.stdout + result.stderr
        
        # Look for the summary line like "38 failed, 71 passed, 1 warning in 71.78s"
        import re
        summary_pattern = r"(\d+) failed,\s*(\d+) passed"
        simple_pattern = r"(\d+) passed"
        no_tests_pattern = r"collected 0 items"
        
        failed = 0
        passed = 0
        total = 0
        
        if re.search(no_tests_pattern, output):
            # No tests collected
            total = 0
        else:
            # Try to match the summary patterns
            match = re.search(summary_pattern, output)
            if match:
                failed = int(match.group(1))
                passed = int(match.group(2))
            else:
                match = re.search(simple_pattern, output)
                if match:
                    passed = int(match.group(1))
        
        total = failed + passed
        
        return {
            "category": category,
            "duration": duration,
            "total": total,
            "passed": passed,
            "failed": failed,
            "skipped": 0,
            "errors": 0,
            "success": result.returncode == 0
        }
    
    def quick_validation(self) -> None:
        """Run critical path tests only (5 minutes)."""
        print(f"{Fore.GREEN}🚀 Quick Validation Mode (Target: 5 minutes){Style.RESET_ALL}")
        
        categories = [
            ("unit", "not slow"),
            ("integration", "not slow and not requires_data"),
        ]
        
        for category, markers in categories:
            result = self.run_test_category(category, markers)
            self._update_results(result)
    
    def standard_testing(self) -> None:
        """Run unit + integration + e2e tests (30 minutes)."""
        print(f"{Fore.GREEN}🔬 Standard Testing Mode (Target: 30 minutes){Style.RESET_ALL}")
        
        categories = ["unit", "integration", "e2e"]
        
        for category in categories:
            result = self.run_test_category(category, "not slow")
            self._update_results(result)
    
    def comprehensive_testing(self) -> None:
        """Run all tests including performance (2 hours)."""
        print(f"{Fore.GREEN}🎯 Comprehensive Testing Mode (Target: 2 hours){Style.RESET_ALL}")
        
        categories = [
            "unit", "integration", "e2e", 
            "performance", "validation", "regression"
        ]
        
        for category in categories:
            result = self.run_test_category(category)
            self._update_results(result)
    
    def overnight_testing(self) -> None:
        """Run full suite including endurance tests (8 hours)."""
        print(f"{Fore.GREEN}🌙 Overnight Testing Mode (Target: 8 hours){Style.RESET_ALL}")
        
        categories = [
            "unit", "integration", "e2e", "performance", 
            "chaos", "validation", "regression", "security"
        ]
        
        for category in categories:
            result = self.run_test_category(category)
            self._update_results(result)
    
    def _update_results(self, result: Dict[str, Any]) -> None:
        """Update overall results with category results."""
        if "total" in result:
            self.results["total_tests"] += result["total"]
            self.results["passed"] += result["passed"]
            self.results["failed"] += result["failed"]
            self.results["skipped"] += result["skipped"]
            self.results["errors"] += result["errors"]
    
    def generate_summary_report(self) -> None:
        """Generate and display test execution summary."""
        self.results["duration"] = time.time() - self.start_time
        
        # Create summary table
        summary_data = [
            ["Total Tests", self.results["total_tests"]],
            ["Passed", f"{Fore.GREEN}{self.results['passed']}{Style.RESET_ALL}"],
            ["Failed", f"{Fore.RED}{self.results['failed']}{Style.RESET_ALL}"],
            ["Skipped", f"{Fore.YELLOW}{self.results['skipped']}{Style.RESET_ALL}"],
            ["Errors", f"{Fore.RED}{self.results['errors']}{Style.RESET_ALL}"],
            ["Duration", f"{self.results['duration']:.1f} seconds"],
        ]
        
        print(f"\n{Fore.CYAN}📊 Test Execution Summary{Style.RESET_ALL}")
        print(tabulate(summary_data, headers=["Metric", "Value"], tablefmt="grid"))
        
        # Overall status
        success_rate = (self.results["passed"] / max(self.results["total_tests"], 1)) * 100
        
        if self.results["failed"] == 0 and self.results["errors"] == 0:
            status = f"{Fore.GREEN}✅ ALL TESTS PASSED{Style.RESET_ALL}"
        elif success_rate >= 95:
            status = f"{Fore.YELLOW}⚠️  MOSTLY PASSING ({success_rate:.1f}%){Style.RESET_ALL}"
        else:
            status = f"{Fore.RED}❌ SIGNIFICANT FAILURES ({success_rate:.1f}%){Style.RESET_ALL}"
        
        print(f"\n{status}")
        
        # Save results to JSON
        with open("reports/test_summary.json", "w") as f:
            json.dump(self.results, f, indent=2)

@click.command()
@click.option("--mode", type=click.Choice(["quick", "standard", "comprehensive", "overnight"]), 
              default="standard", help="Test execution mode")
@click.option("--category", help="Run specific test category only")
@click.option("--markers", help="Run tests with specific pytest markers")
@click.option("--parallel", "-j", type=int, help="Number of parallel workers")
@click.option("--verbose", "-v", is_flag=True, help="Verbose output")
def main(mode: str, category: str, markers: str, parallel: int, verbose: bool):
    """Run AI Chief of Staff comprehensive test suite."""
    
    runner = TestRunner()
    runner.start_time = time.time()
    
    # Ensure reports directory exists
    Path("reports").mkdir(exist_ok=True)
    
    try:
        if category:
            # Run specific category
            result = runner.run_test_category(category, markers)
            runner._update_results(result)
        else:
            # Run mode-based test suite
            if mode == "quick":
                runner.quick_validation()
            elif mode == "standard":
                runner.standard_testing()
            elif mode == "comprehensive":
                runner.comprehensive_testing()
            elif mode == "overnight":
                runner.overnight_testing()
        
        runner.generate_summary_report()
        
        # Exit with error code if tests failed
        if runner.results["failed"] > 0 or runner.results["errors"] > 0:
            sys.exit(1)
            
    except KeyboardInterrupt:
        print(f"\n{Fore.YELLOW}Test execution interrupted by user{Style.RESET_ALL}")
        sys.exit(130)
    except Exception as e:
        print(f"\n{Fore.RED}Test execution failed: {e}{Style.RESET_ALL}")
        sys.exit(1)

if __name__ == "__main__":
    main()