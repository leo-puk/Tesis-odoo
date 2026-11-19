"""Command-line adapter for acquisition and deletion, not R2 search."""
import argparse
import json
from . import capture_plan, delete_units


def main():
    # Inputs: No explicit arguments.
    # Does: Dispatch the selected command and handle terminal output.
    # Output: CLI output and exit status.
    parser = argparse.ArgumentParser(description='Acquire reviewed sources into temp_data')
    commands = parser.add_subparsers(dest='command', required=True)
    capture = commands.add_parser('capture')
    capture.add_argument('plan')
    capture.add_argument('--catalog', required=True)
    capture.add_argument('--output', default='temp_data')
    delete = commands.add_parser('delete')
    delete.add_argument('session_id')
    delete.add_argument('unit_ids', nargs='+')
    delete.add_argument('--output', default='temp_data')
    args = parser.parse_args()
    if args.command == 'capture':
        result = capture_plan(args.plan, args.output, catalog_path=args.catalog)
    else:
        result = delete_units(args.session_id, args.unit_ids, args.output)
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
