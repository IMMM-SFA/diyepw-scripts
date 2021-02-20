import diyepw
import os
import argparse
from _parse_years import parse_years

_this_dir = os.path.dirname(os.path.realpath(__file__))

# Set path to the directory we'll write created AMY EPW files to.
output_path = os.path.abspath(os.path.join(_this_dir, 'outputs', 'amy_epw_files_for_years_and_wmos'))
if not os.path.exists(output_path):
    os.mkdir(output_path)

parser = argparse.ArgumentParser(
    description=f"""
        Generate AMY (actual meteorological year) EPW files by injecting AMY data from WRF NetCDF files into TMY 
        (typical meteorological year) EPW files.
    """
)
parser.add_argument('--wmo-indexes',
                    type=str,
                    help="""A comma-separated list of WMO indexes for which to generate AMY EPW files."""
)
parser.add_argument('--years',
                    type=str,
                    help=f"""A list of years for which to generate AMY EPW files. This is a comma-separated list 
                            that can include individual years (--years=2000,2003,2006), a range (--years=2000-2005), or
                            a combination of both (--years=2000,2003-2005,2007)"""
)
args = parser.parse_args()

wmo_indexes = [int(x) for x in args.wmo_indexes.split(',')]
years = parse_years(args.years)

diyepw.create_amy_epw_files_from_wrf_netcdf(
    wmo_indexes,
    years,
    "/Users/benjamin/Code/diyepw/wrfs",
    output_path,
    allow_downloads = True
)