import os
import argparse
import diyepw
import pandas as pd
from glob import iglob

output_dir_path = 'outputs/analyze_noaa_data_output'

parser = argparse.ArgumentParser(
    description='Perform an analysis of a set of NOAA ISA Lite files, determining which are '
                'suitable for conversion to AMY EPW files.'
)

# argparse by default puts all named arguments into a group called "optional arguments",
# which is really confusing if it includes arguments that are actually required. So we
# manually create a group named "required arguments" so that mandatory arguments will be
# shown as such in the --help output.
required_args_group = parser.add_argument_group('required arguments')
required_args_group.add_argument(
    '--inputs',
    type=str,
    help='A path to a directory. Any ISD Lite files in that directory or any of its subdirectories will be processed. '
         'The files may optionally be compressed. The files must be named according to the format '
         '<WMO Index>-<WBAN>-<Year>".',
    required=True
)

parser.add_argument('--max-missing-rows',
                    default=700,
                    type=int,
                    help='ISD files with more than this number of missing rows will be excluded from the output')
parser.add_argument('--max-consecutive-missing-rows',
                    default=48,
                    type=int,
                    help='ISD files with more than this number of consecutive missing rows will be excluded from the output')
args = parser.parse_args()

# Make a directory to store results if it doesn't already exist.
if not os.path.exists(output_dir_path):
    os.makedirs(output_dir_path)

if not os.path.exists(args.inputs) or not os.path.isdir(args.inputs):
    raise Exception(f'The path {args.inputs} does not appear to be a valid directory path')

# Recursively search for all files under the passed path, excluding directories
input_files = [file for file in iglob(args.inputs + '/**/*', recursive=True) if not os.path.isdir(file)]

analysis_results = diyepw.analyze_noaa_isd_lite_files(
    input_files,
    max_missing_rows=args.max_missing_rows,
    max_consecutive_missing_rows=args.max_consecutive_missing_rows
)

# Write the dataframes to CSVs for the output files.
num_files_with_too_many_rows_missing = len(analysis_results['too_many_total_rows_missing'])
if num_files_with_too_many_rows_missing > 0:
    path = os.path.join(output_dir_path, 'missing_total_entries_high.csv')
    path = os.path.abspath(path) # Change to absolute path for readability
    print(
        num_files_with_too_many_rows_missing,
        "records excluded because they were missing more than", args.max_missing_rows,
        "rows. Information about these files will be written to", path
    )
    pd.DataFrame(analysis_results['too_many_total_rows_missing']).to_csv(path, index=False)

num_files_with_too_many_consec_rows_missing = len(analysis_results['too_many_consecutive_rows_missing'])
if num_files_with_too_many_consec_rows_missing > 0:
    path = os.path.join(output_dir_path, 'missing_consec_entries_high.csv')
    path = os.path.abspath(path) # Change to absolute path for readability
    print(
        num_files_with_too_many_consec_rows_missing,
        "records excluded because they were missing more than", args.max_consecutive_missing_rows,
        "consecutive rows. Information about these files will be written to", path
    )
    pd.DataFrame(analysis_results['too_many_consecutive_rows_missing']).to_csv(path, index=False)

num_good_files = len(analysis_results['good'])
if num_good_files > 0:
    path = os.path.join(output_dir_path, 'files_to_convert.csv')
    path = os.path.abspath(path) # Change to absolute path for readability
    print(
        num_good_files,
        "records are complete enough to be processed. Information about these files will be written to", path
    )
    pd.DataFrame(analysis_results['good']).to_csv(path, index=False)

print('Done! {count} files processed.'.format(count=sum([
    num_good_files,
    num_files_with_too_many_consec_rows_missing,
    num_files_with_too_many_rows_missing
])))