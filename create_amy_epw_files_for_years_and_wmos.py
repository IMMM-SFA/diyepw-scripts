import diyepw
import os
import argparse
from _parse_years import parse_years
from typing import List

"""
Allows a set of WMOs and years to be defined for which a set of AMY EPW files will be generated.
"""

# Set path to the directory we'll write created AMY EPW files to.
output_path  = os.path.abspath(os.path.join('outputs', 'amy_epw_files_for_years_and_wmos'))
if not os.path.exists(output_path):
    os.mkdir(output_path)

# Set path to the files where errors should be written
epw_file_violations_path = os.path.join(output_path, 'epw_validation_errors.csv')
errors_path = os.path.join(output_path, 'errors.csv')

parser = argparse.ArgumentParser(
    description=f"""
        Generate AMY EPW files for a set of years and WMO indices. The generated files will be written to 
        {output_path}. A list of any files that could not be generated due to validation or other errors will be written 
        to {epw_file_violations_path} and {errors_path}.
    """
)

# argparse by default puts all named arguments into a group called "optional arguments",
# which is really confusing if it includes arguments that are actually required. So we
# manually create a group named "required arguments" so that mandatory arguments will be
# shown as such in the --help output.
required_args_group = parser.add_argument_group('required arguments')
required_args_group.add_argument('--years',
                    type=str,
                    help="""The years for which to generate AMY EPW files. This is a comma-separated list that can
                            include individual years (--years=2000,2003,2006), a range (--years=2000-2005), or
                            a combination of both (--years=2000,2003-2005,2007)""",
                    required=True
)
required_args_group.add_argument('--wmo-indices',
                    type=str,
                    help="""The WMO indices (weather station IDs) for which to generate AMY EPW files. This is a 
                            comma-separated list (--wmo-indices=700023,723043,773212). Note that currently only WMO
                            indices beginning with 7 (North America) are supported.""",
                    required=True
)

parser.add_argument('--max-records-to-interpolate',
                    default=6,
                    type=int,
                    help="""The maximum number of consecutive records to interpolate. See the documentation of the
                            pandas.DataFrame.interpolate() method's "limit" argument for more details. Basically,
                            if a sequence of fields up to the length defined by this argument are missing, those 
                            missing values will be interpolated linearly using the values of the fields immediately 
                            preceding and following the missing field(s). If a sequence of fields is longer than this
                            limit, then those fields' values will be imputed instead (see --max-records-to-impute)
                            """
)
parser.add_argument('--max-records-to-impute',
                    default=48,
                    type=int,
                    help=f"""The maximum number of records to impute. For groups of missing records larger than the
                            limit set by --max-records-to-interpolate but up to --max-records-to-impute, we replace the 
                            missing values using the average of the value two weeks prior and the value two weeks after 
                            the missing value. If there are more consecutive missing records than this limit, then the 
                            file will not be processed, and will be added to the error file at {errors_path}."""
)
parser.add_argument('--max-missing-amy-rows',
                    default=700,
                    type=int,
                    help=f"""The AMY files corresponding to each requested WMO/year combination will be checked against
                         this maximum - any file that is missing more than this number of total observations with
                         more than this number of total missing rows will not be generated. Instead, an entry will
                         be added to {errors_path}."""
)
args = parser.parse_args()

def get_wmo_indices_list(wmo_indices_str) -> List[int]:
    """
    Transforms the wmo-indices argument, which should be a comma-separated list of WMO indices, into a sorted list of
    integers
    :param wmo_indices_str:
    :return:
    """
    wmo_indices_str = wmo_indices_str.replace(" ", "") # Ignore any spaces

    # Split on "," and convert each value to an integer
    wmo_indices_list = [int(wmo_index) for wmo_index in wmo_indices_str.split(",")]

    return wmo_indices_list

years = parse_years(args.years)
wmo_indices = get_wmo_indices_list(args.wmo_indices)

diyepw.create_amy_epw_files_for_years_and_wmos(
    years=years,
    wmo_indices=wmo_indices,
    max_records_to_impute=args.max_records_to_impute,
    max_records_to_interpolate=args.max_records_to_interpolate,
    max_missing_amy_rows=args.max_missing_amy_rows,
    amy_epw_dir=output_path,
    allow_downloads=True
)