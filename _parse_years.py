from typing import List
import datetime

def parse_years(years_str:str) -> List[int]:
    """
    Transform a years argument string, which can be formatted like "2000, 2001, 2005-2010" (individual years or
    ranges, comma separated, not necessarily sorted, with optional spaces), into a sorted list of integers
    """
    # Transform the years argument from a string to a sorted list
    years_list = []
    years_str = years_str.replace(" ", "")  # Ignore any spaces
    for year_arg_part in years_str.split(","):  # We'll process each comma-separated entry in the list of years
        if "-" in year_arg_part:  # If there is a hyphen, then it's a range like "2000-2010"
            start_year, end_year = year_arg_part.split("-")
            years_list += range(int(start_year), int(end_year) + 1)
        else:  # If there is no hyphen, it's just a single year
            years_list.append(int(year_arg_part))
    years_list.sort()

    # Validate that the years are between 1900 and the present
    this_year = datetime.datetime.now().year
    if min(years_list) < 1900 or max(years_list) > this_year:
        raise Exception(f"Years must be in the range 1900-{this_year}")

    return years_list