#!/usr/bin/env python
"""
Jupiter Test Suite Runner
========================

Runs all tests for the Jupiter AI Assistant project.
"""

import os
import sys
import argparse
import unittest
import json
import time
import datetime
import shutil
from pathlib import Path
import html

# Ensure the current directory is in the path
script_dir = os.path.dirname(os.path.abspath(__file__))
if script_dir not in sys.path:
    sys.path.insert(0, script_dir)

# Add parent directory to path to allow importing Jupiter modules
parent_dir = os.path.abspath(os.path.join(script_dir, '..'))
if parent_dir not in sys.path:
    sys.path.insert(0, parent_dir)

# Try to import test utilities
try:
    from test_utils.test_environment import setup_test_environment, cleanup_test_environment
except ImportError:
    print("Warning: Could not import test utilities. Make sure test_utils is properly set up.")
    
    # Define placeholder functions
    def setup_test_environment():
        print("Warning: Using placeholder for setup_test_environment")
        return {}
        
    def cleanup_test_environment():
        print("Warning: Using placeholder for cleanup_test_environment")
        pass

def create_test_report(result, start_time, end_time, output_file):
    """
    Create an HTML test report
    """
    # Calculate statistics
    run_time = end_time - start_time
    run_count = result.testsRun
    failure_count = len(result.failures)
    error_count = len(result.errors)
    skip_count = len(result.skipped)
    success_count = run_count - failure_count - error_count - skip_count
    
    # Create HTML report
    html_report = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>Jupiter Test Report</title>
        <style>
            body {{ font-family: Arial, sans-serif; margin: 20px; }}
            h1 {{ color: #333366; }}
            .summary {{ background-color: #f0f0f0; padding: 10px; margin-bottom: 20px; }}
            .success {{ color: green; }}
            .failure {{ color: red; }}
            .error {{ color: darkred; }}
            .skip {{ color: orange; }}
            table {{ border-collapse: collapse; width: 100%; }}
            th, td {{ border: 1px solid #ddd; padding: 8px; text-align: left; }}
            tr:nth-child(even) {{ background-color: #f2f2f2; }}
            th {{ background-color: #333366; color: white; }}
            .details {{ margin-top: 10px; border-left: 3px solid #ccc; padding-left: 10px; }}
            pre {{ background-color: #f9f9f9; padding: 10px; overflow: auto; }}
        </style>
    </head>
    <body>
        <h1>Jupiter Test Report</h1>
        <div class="summary">
            <h2>Summary</h2>
            <p><strong>Run Date:</strong> {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
            <p><strong>Run Time:</strong> {run_time:.2f} seconds</p>
            <p><strong>Tests Run:</strong> {run_count}</p>
            <p><strong>Successes:</strong> <span class="success">{success_count}</span></p>
            <p><strong>Failures:</strong> <span class="failure">{failure_count}</span></p>
            <p><strong>Errors:</strong> <span class="error">{error_count}</span></p>
            <p><strong>Skipped:</strong> <span class="skip">{skip_count}</span></p>
            <p><strong>Success Rate:</strong> {success_count/max(run_count,1)*100:.1f}%</p>
        </div>
    """
    
    # Add failures section if there are failures
    if failure_count > 0:
        html_report += """
        <h2>Failures</h2>
        <table>
            <tr>
                <th>Test</th>
                <th>Details</th>
            </tr>
        """
        
        for test, trace in result.failures:
            test_name = test.id()
            html_report += f"""
            <tr>
                <td>{html.escape(test_name)}</td>
                <td>
                    <div class="details">
                        <pre>{html.escape(trace)}</pre>
                    </div>
                </td>
            </tr>
            """
        
        html_report += """
        </table>
        """
    
    # Add errors section if there are errors
    if error_count > 0:
        html_report += """
        <h2>Errors</h2>
        <table>
            <tr>
                <th>Test</th>
                <th>Details</th>
            </tr>
        """
        
        for test, trace in result.errors:
            test_name = test.id()
            html_report += f"""
            <tr>
                <td>{html.escape(test_name)}</td>
                <td>
                    <div class="details">
                        <pre>{html.escape(trace)}</pre>
                    </div>
                </td>
            </tr>
            """
        
        html_report += """
        </table>
        """
    
    # Add skipped section if there are skipped tests
    if skip_count > 0:
        html_report += """
        <h2>Skipped Tests</h2>
        <table>
            <tr>
                <th>Test</th>
                <th>Reason</th>
            </tr>
        """
        
        for test, reason in result.skipped:
            test_name = test.id()
            html_report += f"""
            <tr>
                <td>{html.escape(test_name)}</td>
                <td>{html.escape(reason)}</td>
            </tr>
            """
        
        html_report += """
        </table>
        """
    
    # Close HTML
    html_report += """
    </body>
    </html>
    """
    
    # Write report to file
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(html_report)

def run_tests(categories=None, verbose=False):
    """
    Run the tests from specified categories
    """
    # Define test directories
    test_dirs = {
        'unit': 'unit_tests',
        'integration': 'integration_tests',
        'functional': 'functional_tests',
        'ui': 'ui_tests'
    }
    
    # Get absolute path to the script directory
    script_dir = os.path.dirname(os.path.abspath(__file__))
    
    # Determine which dirs to include
    dirs_to_test = []
    if categories:
        for category in categories:
            if category in test_dirs:
                dirs_to_test.append(test_dirs[category])
    else:
        # Default: run all except UI tests
        dirs_to_test = [test_dirs[cat] for cat in ['unit', 'integration', 'functional']]
    
    # Create test suite
    test_suite = unittest.TestSuite()
    loader = unittest.TestLoader()
    
    # Manual test loading instead of discovery to avoid path issues
    for test_dir_name in dirs_to_test:
        test_dir_path = os.path.join(script_dir, test_dir_name)
        if os.path.exists(test_dir_path):
            print(f"Loading tests from {test_dir_name}")
            
            # Make sure __init__.py exists to make it a proper package
            init_file = os.path.join(test_dir_path, "__init__.py")
            if not os.path.exists(init_file):
                print(f"Warning: Creating missing __init__.py in {test_dir_path}")
                with open(init_file, 'w') as f:
                    f.write("# Auto-generated by test runner\n")
            
            # Get all test files
            for filename in os.listdir(test_dir_path):
                if filename.startswith('test_') and filename.endswith('.py'):
                    module_name = f"{test_dir_name}.{filename[:-3]}"  # Remove .py
                    try:
                        # Try to import the module
                        __import__(module_name)
                        module = sys.modules[module_name]
                        
                        # Add tests from this module
                        tests = loader.loadTestsFromModule(module)
                        test_suite.addTests(tests)
                        print(f"  Added tests from {module_name}")
                    except Exception as e:
                        print(f"  Error loading tests from {module_name}: {e}")
    
    # Run tests
    verbosity = 2 if verbose else 1
    runner = unittest.TextTestRunner(verbosity=verbosity)
    
    # Time the test run
    start_time = time.time()
    result = runner.run(test_suite)
    end_time = time.time()
    
    # Create test results directory if it doesn't exist
    results_dir = os.path.join(script_dir, 'test_results')
    os.makedirs(results_dir, exist_ok=True)
    
    # Create timestamped test report
    timestamp = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
    report_file = os.path.join(results_dir, f'jupiter_test_report_{timestamp}.html')
    create_test_report(result, start_time, end_time, report_file)
    
    print(f"\nTest report saved to: {report_file}")
    
    # Return True if all tests passed
    return result.wasSuccessful()

def main():
    """Main function to run tests"""
    parser = argparse.ArgumentParser(description="Run Jupiter tests")
    parser.add_argument("--categories", nargs="+", 
                        choices=["unit", "integration", "functional", "ui", "all"],
                        help="Test categories to run (default: unit,integration,functional)")
    parser.add_argument("--verbose", "-v", action="store_true",
                        help="Verbose output")
    parser.add_argument("--no-cleanup", action="store_true",
                        help="Don't clean up test environment after running")
    args = parser.parse_args()
    
    # Handle 'all' category
    if args.categories and 'all' in args.categories:
        args.categories = ["unit", "integration", "functional", "ui"]
    
    # Create test environment
    print("Setting up test environment...")
    setup_test_environment()
    
    # Run tests
    print(f"Running Jupiter tests...")
    success = run_tests(args.categories, args.verbose)
    
    # Clean up if requested
    if not args.no_cleanup:
        print("Cleaning up test environment...")
        cleanup_test_environment()
    
    # Return exit code based on test success
    return 0 if success else 1

if __name__ == "__main__":
    sys.exit(main())