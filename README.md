# DIYEPW-Scripts
DIYEPW is a tool developed by Pacific Northwest National Laboratory that allows the quick and easy
generation of a set of EPW files for a given set of WMOs and years. It is provided as both a set
of scripts (https://github.com/IMMM-SFA/diyepw-scripts) and as a Python package (https://github.com/IMMM-SFA/diyepw).
This allows DIYEPW to be used as a command-line tool, or as a package to incorporate EPW file 
generation into a custom script.

Both workflows, and the functions provided by the package, are tools to achieve the same
goal, which is the generation of AMY (actual meteorological year) EPW files, which is done
by injecting AMY data into TMY (typical meteorological year) EPW files. The generated EPW files
have the following fields replaced with observed data:

1. dry bulb temperature
1. dew point temperature
1. pressure
1. wind direction
1. wind speed

Because observed weather data commonly contains gaps, DIYEPW will attempt to fill in any such gaps to ensure that in 
each record a value is present for all of the hourly timestamps for the variables shown above. To do so, it will use one 
of two strategies to impute or interpolate values for any missing fields in the data set:

#### Interpolation: Handling for small gaps
Small gaps (by default up to 6 consecutive hours of consecutive missing data for a field), are handled by linear 
interpolation, so that for example if the dry bulb temperature has a gap with neighboring observed values like 
(20, X, X, X, X, 25), DIYEPW will replace the missing values to give (20, 21, 22, 23, 24, 25).

#### Imputation: Handling for large gaps
Large gaps (by default up to 48 consecutive hours of missing data for a field) are filled using an imputation strategy
whereby each missing field is set to the average of the field's value two weeks in the past and in the future from
the missing timestamp.

If a gap exists in the data that is larger than the maximum allowed for the imputation strategy, that file will be
rejected and no EPW file will be generated.

The maximum number of missing values that the interpolation strategy will be used for, and the maximum number of
missing values that can be imputed, can be changed from their defaults. In the scripts, `create_amy_epw_files.py`
and `create_amy_epw_files_for_years_and_wmos.py`, that generate EPW files, the options `--max-records-to-interpolate`
and `--max-records-to-impute` can be set to override the defaults. The related package functions, 
`create_amy_epw_file()` and `create_amy_epw_files_for_years_and_wmos()`, both accept the optional arguments
`max_records_to_interpolate` and `max_records_to_impute`, which likewise override the defaults of 6 and 48.

## Installation
These scripts require the DIYEPW package to be installed. For instructions on package installation,
and for more details about the workings of the package, see https://github.com/IMMM-SFA/diyepw
  
## Scripts
This section describes the scripts available as part of this project. The scripts are located
in the `scripts/` directory. Every script has a manual page that can be accessed by passing 
the "--help" option to the script. For example:
 
```
python analyze_noaa_data.py --help
```

### Workflow 1: AMY EPW generation based on years and WMO indices
This workflow uses only a single script, `create_amy_epw_files_for_years_and_wmos.py`, and
generates AMY EPW files for a set of years and WMO indices. It accomplishes this by combining
TMY (typical meteorological year) EPW files with AMY (actual meteorological year) data. The
TMY EPW file for a given WMO is downloaded by the software as needed from energyplus.net. The
AMY data comes from NOAA ISD Lite files that are likewise downloaded as needed, from 
ncdc.noaa.gov.

This script can be called like this:

```
python create_amy_epw_files_for_years_and_wmos.py --years=2010-2015, --wmo-indices=723403,7722780`
```

The options `--years` and `--wmo-indices` are required. There are a number of other optional
options that can also be set. All available options, their effects, and the values they accept,
can be seen by calling this script with the `--help` option:

```
python create_amy_epw_files_for_years_and_wmos.py --help
```

### Workflow 2: AMY EPW generation based on existing ISD Lite files
This workflow is very similar to Workflow 1, but instead of downloading NOAA's ISD Lite files
as needed, it reads in a set of ISD Lite files provided by the user and generates one AMY EPW
file corresponding to each.

This workflow involves two steps:

#### 1. analyze_noaa_data.py

The script analyze_noaa_data.py will check a set of ISD Lite files against a set of requirements,
and generate a CSV file listing the ISD Lite files that are suitable for conversion to EPW. The
script is called like this:

```
python analyze_noaa_data.py --inputs=/path/to/your/inputs/directory
```

The script will look for any file within the directory passed to --inputs, including in 
subdirectories or subdirectories of subdirectories. The files must be named like 
"999999-88888-2020.gz", where the first number is a WMO index and the final number is the
year - the middle number is ignored. The easiest way to get files that are suitable for use
for this script is to download them from NOAA's catalog at 
https://www1.ncdc.noaa.gov/pub/data/noaa/isd-lite/.

The ".gz" (gzip commpressed) format of the ISD Lite files is the format provided by NOAA,
but is not required. You may also provide ISD Lite files in CSV (.csv) format, or in a 
different compression format like ZIP (.zip). The file extension is used to determine what
format the file is and must match the file's format. Pass the `--help` option 
(`python analyze_noaa_data.py --help`) for more information on what compressed formats are supported.

The script is primarily checking that the ISD Lite files are in concordance with the following limits:

1. Total number of rows missing
1. Maximum number of consecutive rows missing

and will produce the following files (as applicable) under `outputs/analyze_noaa_data_output/`:

1. `missing_total_entries_high.csv`: A list of files where the total number of rows missing exceeds a threshold.
   The threshold is set to rule out files where more than 700 (out of 8760 total) entries are missing entirely
   by default, but a custom value can be set with the --max-missing-rows option:
       
    ```
    python analyze_noaa_data.py --max-missing-rows=700
    ```
   
1. `missing_consec_entries_high.csv`: A list of files where the maximum consecutive number of rows missing exceeds 
   a threshold. The threshold is currently set to a maximum of 48 consecutive empty rows, but a custom value can 
   be set with the --max-consecutive-missing-rows option:
   
   ```
   python analyze_noaa_data.py --max-consecutive-missing-rows=48
   ```
   
1. `files_to_convert.csv`: A list of the files that are deemed to be usable because they are neither missing too many
   total nor too many consecutive rows. This file determines which EPWs will be generated by the next script, and
   it can be freely edited before running that script.

#### 2. create_amy_epw_files.py

The script create_amy_epw.py reads the files_to_convert.csv file generated in the previous step, and for each
ISD Lite file listed, generates an AMY EPW file. It can be called like this:

```
python create_amy_epw_files.py --max-records-to-interpolate=6 --max-records-to-impute=48
```

Both `--max-records-to-interpolate` and `--max-records-to-impute` are optional and can be used to override the
default size of the gaps that can be filled in observed data using the two strategies, which are described in more
detail at the top of this document.