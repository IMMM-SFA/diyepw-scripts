import xarray
import pandas as pd
import numpy as np
import os
import diyepw

def convert_wind_vectors_to_speed_and_dir(u: pd.Series(float), v: pd.Series(float)) -> tuple:
    """
    Convert wind data in vector form into speed and dir
    :param u: The east/west component of the wind's movement
    :param v: The north/south component of the wind's movement
    :return: tuple(float, float) The wind's speed (in meters/sec) and direction (in degrees)
    """
    # Use the Pythagorean Theorem to get the amplitude of the combined vectors, which is the
    # hypotenuse of a right triangle with the two vectors as the two sides
    wind_speed = np.sqrt(u**2+v**2)

    # Take the arctangent of v/u to derive the angle of the hypotenuse, which gives us our wind direction
    wind_dir = np.degrees(np.arctan2(v, u))

    return wind_speed, wind_dir

wmo_index = 722195
year = 2009
allow_downloads = True

# Get the latitude and longitude of the requested WMO Index from the Weather_Stations_by_County.csv file
weather_station_table = pd.read_csv('/Users/benjamin/Code/diyepw/diyepw/diyepw/data/Weather_Stations_by_County.csv')
weather_station_row = weather_station_table[weather_station_table["Station WMO Identifier"]==wmo_index].iloc[0]
lat  = weather_station_row["Station Latitude"]
long = weather_station_row["Station Longitude"]

# We need to process each WRF file for a year (collected together in a directory), and stitch all their data together
# into a single Pandas array
data_frame = pd.DataFrame()
year_folder = f"/Users/benjamin/Code/diyepw/wrf_{year}"
for filename in os.listdir(year_folder):
    # Parse the NetCDF file and extract out the data closest to that lat/long
    ds = xarray.open_dataset(os.path.join(year_folder, filename))

    # The NetCDF file does not have indexes. It's not clear to me whether this is due to indices missing
    # from the file (I don't know whether NetCDF supports indexes of this sort at all) or if it's just
    # down to the dimensions and coordinates (and data variables - Times is a variable instead of a coordinate)
    # not having identical names and xarray would automatically apply the missing indices if it did. In any
    # case, we can get around this by creating the missing indices:
    ds = ds.reindex(Time=ds.Times, west_east=ds.XLONG[0,0,:], south_north=ds.XLAT[0,:,0])
    ds = ds.drop_vars(["XLONG", "XLAT", "Times"])

    # Pull out just the data for the lat/long coordinate that is the closest to the weather station we are
    # retrieving data for
    ds = ds.sel({ "south_north":lat, "west_east":long }, method='nearest', tolerance=1, drop=True)

    # Convert the DataSet, which is now one-dimensional, having data for each variable with respect only to
    # time, into a two-dimensional (time x variable) Pandas array. We use transpose() because this conversion
    # results in time being the columns and variables being the rows, which is not suitable for export to CSV
    ds = ds.to_array().to_pandas().transpose()

    data_frame = pd.concat([data_frame, ds])

data_frame.sort_index(inplace=True)

tmy_file = diyepw.get_tmy_epw_file(wmo_index, allow_downloads=allow_downloads)
meteorology = diyepw.Meteorology.from_tmy3_file(tmy_file)

# TODO: REMOVE THIS! Temporary measure necessary because we don't have a full year of data for testing
meteorology._observations = meteorology._observations.truncate(after=len(data_frame)-1)

# Atmospheric Pressure, requires no conversion
meteorology.set("Patm", data_frame.PSFC)

# Liquid precipitation depth - just sum up the values, as liquid precipitation is split across three
# variables in WRF NetCDF
meteorology.set("LiqPrecDepth", np.sum([data_frame.RAINC, data_frame.RAINSH, data_frame.RAINNC]))

# Dry-bulb temperature - Convert K -> C
meteorology.set("Tdb", data_frame.T2 + 273.15)

# - Wind Direction & Speed (V10, U10 - convert from vectors)
wind_speed, wind_dir = convert_wind_vectors_to_speed_and_dir(data_frame.U10, data_frame.V10)
meteorology.set("Wspeed", wind_speed)
meteorology.set("Wdir", wind_dir)

meteorology.write_epw("out.epw")