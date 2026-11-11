#!/usr/bin/env python3
"""
OSS-LBM Knowledge Package - Entry Point

Main entry point for validating and managing the OSS-LBM knowledge package.
Provides CLI interface for validation, claim extraction, and reporting.
"""

import sys
import json
import argparse
from pathlib import Path
from datetime import datetime

# Add lib to path
sys.path.insert(0, str(Path(__file__).parent))

from lib.validator import KnowledgeValidator
from lib.claim_extractor import ClaimExtractor


def cmd_validate(args):
    """Validate the knowledge package."""
    package_dir = Path(args.package_dir)
    
    print(f"Validating knowledge package: {package_dir}")
    print("=" * 60)
    
    validator = KnowledgeValidator(package_dir)
    valid, result = validator.validate_package()
    
    if valid:
        print("✓ Validation PASSED")
        print(f"  Claims: {result['counts']['claims']}")
        print(f"  Evidence: {result['counts']['evidence']}")
        print(f"  Provenance: {result['counts']['provenance']}")
        
        if result['warnings']:
            print(f"\nWarnings ({len(result['warnings'])}):")
            for w in result['warnings']:
                print(f"  ⚠ {w}")
        
        return 0
    else:
        print("✗ Validation FAILED")
        print(f"\nErrors ({len(result['errors'])}):")
        for e in result['errors']:
            print(f"  ✗ {e}")
        
        if result['warnings']:
            print(f"\nWarnings ({len(result['warnings'])}):")
            for w in result['warnings']:
                print(f"  ⚠ {w}")
        
        return 1


def cmd_extract(args):
    """Extract claims from a repository."""
    repo_path = Path(args.repo)
    framework = args.framework
    commit = args.commit
    
    print(f"Extracting claims from {framework} at {repo_path}")
    print("=" * 60)
    
    extractor = ClaimExtractor(repo_path, framework, commit)
    
    # Example extraction (would be customized per framework)
    print("Note: Claim extraction requires manual specification of claims.")
    print("Use ClaimExtractor.extract_class_claim() or extract_function_claim()")
    print("in a custom script to extract specific claims.")
    
    return 0


def cmd_report(args):
    """Generate a validation report."""
    package_dir = Path(args.package_dir)
    output_file = Path(args.output) if args.output else None
    
    validator = KnowledgeValidator(package_dir)
    valid, result = validator.validate_package()
    
    report = {
        "package": str(package_dir),
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "validation": result,
        "status": "passed" if valid else "failed"
    }
    
    if output_file:
        output_file.write_text(json.dumps(report, indent=2))
        print(f"Report written to {output_file}")
    else:
        print(json.dumps(report, indent=2))
    
    return 0 if valid else 1


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="OSS-LBM Knowledge Package Manager",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Validate the knowledge package
  python entry.py validate --package-dir .
  
  # Generate validation report
  python entry.py report --package-dir . --output report.json
  
  # Extract claims from a repository
  python entry.py extract --repo /path/to/pylbm --framework pylbm
        """
    )
    
    subparsers = parser.add_subparsers(dest='command', help='Available commands')
    
    # Validate command
    validate_parser = subparsers.add_parser('validate', help='Validate knowledge package')
    validate_parser.add_argument('--package-dir', default='.',
                                help='Path to knowledge package directory')
    
    # Extract command
    extract_parser = subparsers.add_parser('extract', help='Extract claims from repository')
    extract_parser.add_argument('--repo', required=True, help='Path to repository')
    extract_parser.add_argument('--framework', required=True, help='Framework name')
    extract_parser.add_argument('--commit', help='Commit hash (default: auto-detect)')
    
    # Report command
    report_parser = subparsers.add_parser('report', help='Generate validation report')
    report_parser.add_argument('--package-dir', default='.',
                              help='Path to knowledge package directory')
    report_parser.add_argument('--output', help='Output file path (default: stdout)')
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return 1
    
    # Dispatch to command handler
    handlers = {
        'validate': cmd_validate,
        'extract': cmd_extract,
        'report': cmd_report
    }
    
    return handlers[args.command](args)


if __name__ == "__main__":
    sys.exit(main())
