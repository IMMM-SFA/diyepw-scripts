import xarray
import pandas as pd
import numpy as np
import os
import diyepw
from typing import Tuple, Dict
from functools import lru_cache

def convert_wind_vectors_to_speed_and_dir(u: pd.Series(float), v: pd.Series(float)) -> Tuple[pd.Series, pd.Series]:
    """
    Convert wind data in vector form into speed and dir
    :param u: The east/west component of the wind's movement
    :param v: The north/south component of the wind's movement
    :return: The wind's speed (in meters/sec) and direction (in degrees)
    """
    # Use the Pythagorean Theorem to get the amplitude of the combined vectors, which is the
    # hypotenuse of a right triangle with the two vectors as the two sides
    speed = np.sqrt(u**2+v**2)

    # Take the arctangent of v/u to derive the angle of the hypotenuse, which gives us our wind direction
    direction = np.degrees(np.arctan2(v, u))

    return speed, direction

@lru_cache()
def get_lat_long_by_wmo_index(wmo_index:int) -> Tuple[float, float]:
    """
    :param wmo_index: WMO ID of a weather station
    :return: The latitude and longitude of the weather station
    """
    weather_station_table = pd.read_csv('/Users/benjamin/Code/diyepw/diyepw/diyepw/data/Weather_Stations_by_County.csv')
    weather_station_row = weather_station_table[weather_station_table["Station WMO Identifier"] == wmo_index].iloc[0]
    return float(weather_station_row["Station Latitude"]), float(weather_station_row["Station Longitude"])

def get_wrf_data(wmo_indexes, year) -> Dict[int, pd.DataFrame]:
    """
    Retrieve WRF NetCDF data associated with a set of weathers stations for a given year.

    :param wmo_indexes: The WMO Indexes of the weather stations for which to retrieve data - the data will
        be retrieved for the lat/long coordinate in the WRF NetCDF file that is closest to the lat/long of
        the weather station.
    :param year: The year for which to retrieve observed data.
    :return: dict in the form { <wmo_index>: DataFrame }, where each DataFrame contains a year's observations
        for the lat/long closest to the weather station's location.
    """

    dfs_by_wmo_index = dict([(index, None) for index in wmo_indexes])

    # TODO: This needs to be passed as an argument
    year_folder = f"/Users/benjamin/Code/diyepw/wrf_{year}"
    filenames = os.listdir(year_folder)
    filenames.sort() # Not really necessary, but feels right, and makes it easier to watch progress through the files

    for filename in filenames:
        print(filename, "...") # TODO: Make this a log call

        # Parse the NetCDF file and extract out the data closest to that lat/long
        ds = xarray.open_dataset(os.path.join(year_folder, filename))

        # The WRF NetCDF files are not indexed properly. We have contacted LBNL about this and they've declined
        # to make any changes, so we have to reindex so that .sel() will work correctly. The original coordinate
        # variables (XLONG, XLAT, Times) are then unnecessary because the indexes contain the correct values.
        ds = ds.reindex(Time=ds.Times, west_east=ds.XLONG[0,0,:], south_north=ds.XLAT[0,:,0])
        ds = ds.drop_vars(["XLONG", "XLAT", "Times"])

        # Pull out just the data for the lat/long coordinate that is the closest to each weather station
        for wmo_index in wmo_indexes:
            print(wmo_index, "...")
            (lat, long) = get_lat_long_by_wmo_index(wmo_index)
            ds_at_lat_long = ds.sel({ "south_north":lat, "west_east":long }, method='nearest', tolerance=1, drop=True)

            # Convert the DataSet, which is now one-dimensional, having data for each variable with respect only to
            # time, into a two-dimensional (time x variable) Pandas array. We then transpose() because this conversion
            # results in time being the columns and variables being the rows.
            ds_at_lat_long = ds_at_lat_long.to_array().to_pandas().transpose()

            # Append the data to our DataFrame, which will ultimately contain the full year's data
            if dfs_by_wmo_index[wmo_index] is None:
                dfs_by_wmo_index[wmo_index] = ds_at_lat_long
            else:
                dfs_by_wmo_index[wmo_index] = pd.concat([dfs_by_wmo_index[wmo_index], ds_at_lat_long])

        print()

    return dfs_by_wmo_index

wmo_indexes = [722195, 724230]
years = [2009]
allow_downloads = True

for year in years:
    # We need to process each WRF file for a year (collected together in a directory), and stitch all their data together
    # into a single Pandas array
    dfs_by_wmo_index = get_wrf_data(wmo_indexes, year)

    for wmo_index in wmo_indexes:
        df = dfs_by_wmo_index[wmo_index]

        # The LBNL example data is missing records for the last two hours of the year. :(
        # TODO: Remove this when LBNL delivers complete data
        df.loc[b'2009-12-31_22:00:00'] = df.loc[b'2009-12-31_21:00:00']
        df.loc[b'2009-12-31_23:00:00'] = df.loc[b'2009-12-31_21:00:00']

        # Create a TMY meteorology instance, so that we can inject the observed AMY data from the WRF files and
        # generate an AMY EMP from the result
        tmy_file = diyepw.get_tmy_epw_file(wmo_index, allow_downloads=allow_downloads)
        meteorology = diyepw.Meteorology.from_tmy3_file(tmy_file)

        # Atmospheric Pressure, requires no conversion
        meteorology.set("Patm", df.PSFC)

        # Liquid precipitation depth - just sum up the values, as liquid precipitation is split across three
        # variables in WRF NetCDF
        meteorology.set("LiqPrecDepth", np.sum([df.RAINC, df.RAINSH, df.RAINNC]))

        # Dry-bulb temperature - Convert K -> C
        meteorology.set("Tdb", df.T2 + 273.15)

        # - Wind Direction & Speed (V10, U10 - convert from vectors)
        wind_speed, wind_dir = convert_wind_vectors_to_speed_and_dir(df.U10, df.V10)
        meteorology.set("Wspeed", wind_speed)
        meteorology.set("Wdir", wind_dir)

        # Relative humidity conversion algorithm taken from here: https://www.mcs.anl.gov/~emconsta/relhum.txt:
        #
        # define relative humidity matching the algorithm used for hindcasts
        # let pq0 = 379.90516
        # let a2 = 17.2693882
        # let a3 = 273.16
        # let a4 = 35.86
        # let /title="relative humidity" /units="fraction" f_rh2 = q2 / ( (pq0 / psfc) * exp(a2 * (t2 - a3) / (t2 - a4)) )
        #
        # where
        #       q2 = Q2 variable from wrf
        #       t2 = T2 variable from wrf
        #       psfc = surface pressure from WRF
        #
        # This calculates 2 m (approximately) relative humidity.
        meteorology.set("RH", df.Q2 / (379.90516 / df.PSFC) * np.exp(17.2693882 * (df.T2 - 273.16) / (df.T2 - 35.86)))

        # Now that we have replaced as much data from the TMY meteorology as possible from the data in the WRF NetCDF,
        # all that is left to do is write out the file as an EPW
        file_name = f"/Users/benjamin/Code/{wmo_index}_{year}.epw"
        meteorology.write_epw(file_name)
        print(f"Wrote data for WMO {wmo_index} and year {year}: {file_name}")