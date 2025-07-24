import pandas as pd
from datetime import datetime
import numpy as np

'''This module provides functions to read data from a CSV file and process it for GUI display.'''

def count_lines(csv_filepath):
    # Open the file in binary mode ('rb') for efficient line counting
    with open(csv_filepath, 'rb') as f:
        # Iterate over each line in the file and count the total number of lines
        # sum(1 for _ in f) adds 1 for every line encountered, giving total line count
        return sum(1 for _ in f)
    
def read_last_n_rows(csv_filepath, n):
    # Count the total number of lines in the file (including the header line)
    total_lines = count_lines(csv_filepath)

    # Subtract 1 to exclude the header, giving the number of actual data rows
    data_lines = total_lines - 1

    # Determine how many of the earliest data rows to skip
    # This ensures that only the last `n` rows are read
    # If there are fewer than `n` rows, skip nothing
    rows_to_skip = max(0, data_lines - n)

    # Build the skiprows argument for pandas
    # If rows_to_skip > 0, skip lines 1 through rows_to_skip (line 0 is the header)
    # If rows_to_skip == 0, don’t skip any lines (read entire file)
    if rows_to_skip > 0:
        skip = range(1, rows_to_skip + 1)
    else:
        skip = None

    # Read the CSV file, skipping the early rows but keeping the header
    return pd.read_csv(csv_filepath, skiprows=skip)

def get_seconds_ago(dataframe):
    # Convert the 'Time' column in the dataframe from string to datetime objects
    # using the specified format: 'Year-Month-Day Hour:Minute:Second'
    dataframe['timestamp'] = pd.to_datetime(dataframe['Time'], format='%Y-%m-%d %H:%M:%S')

    # Get the current time as a datetime object
    current_time = datetime.now()

    # Calculate the time difference between current_time and each timestamp in seconds
    # The subtraction produces a timedelta object, and .dt.total_seconds() converts it to float seconds
    # The negative sign (-) in front makes the value represent "seconds ago" as a negative number,
    # meaning past times will be negative
    dataframe['seconds_ago'] = -(current_time - dataframe['timestamp']).dt.total_seconds()

    # Return the new 'seconds_ago' Series from the dataframe
    return dataframe['seconds_ago']

def get_pressure(dataframe):
    # Convert gauge values to numeric, coercing errors (like 'Off') to NaN
    gauge1 = pd.to_numeric(dataframe['Gauge 1'], errors='coerce')
    gauge2 = pd.to_numeric(dataframe['Gauge 2'], errors='coerce')

    # Identify rows where one gauge is on (not NaN) and the other is off (NaN)
    g1_On_g2_Off_indices = np.where(~gauge1.isna() & gauge2.isna())[0]
    g1_Off_g2_On_indices = np.where(gauge1.isna() & ~gauge2.isna())[0]

    # Identify rows where one gauge is positive and the other is negative
    g1_pos_g2_neg_indices = np.where((gauge1 > 0.0) & (gauge2 <= 0.0))[0]
    g1_neg_g2_pos_indices = np.where((gauge1 <= 0.0) & (gauge2 > 0.0))[0]

    #Identify rows where both gauges read a positive number
    g1_pos_g2_pos_indices = np.where((gauge1 > 0.0) & (gauge2 > 0.0))[0]

    # Initialize the pressure array with NaN for all rows, rows not filled later mean no valid pressure reading
    pressure = np.full(len(dataframe), np.nan)

    # Assign pressure values based on the gauge states
    pressure[g1_On_g2_Off_indices] = gauge1[g1_On_g2_Off_indices]
    pressure[g1_Off_g2_On_indices] = gauge2[g1_Off_g2_On_indices]

    pressure[g1_pos_g2_neg_indices] = gauge1[g1_pos_g2_neg_indices]
    pressure[g1_neg_g2_pos_indices] = gauge2[g1_neg_g2_pos_indices]

    pressure[g1_pos_g2_pos_indices] = np.minimum(gauge1[g1_pos_g2_pos_indices], gauge2[g1_pos_g2_pos_indices])

    #Invalidate pressure if units are off
    units = dataframe['Units']

    units_not_valid_indices = np.where(units == 'Off')[0]

    pressure[units_not_valid_indices] = np.nan

    #Convert to Torr
    units_Pascal_indices = np.where(units == 'Pascal')[0]
    pressure[units_Pascal_indices] = pressure[units_Pascal_indices] * 0.0075006168

    units_Bar_indices = np.where(units == 'Bar')[0]
    pressure[units_Bar_indices] = pressure[units_Bar_indices] * 750.06

    # Return the pressure values as a pandas Series with the same index as the input DataFrame
    return pd.Series(pressure, name='Pressure', index=dataframe.index)

def get_n_XY_datapoints(csv_filepath, n, datatype):
    dataframe = read_last_n_rows(csv_filepath, n)

    # Depending on the requested datatype, process and return the appropriate data
    if datatype == 'pressure':
        times = get_seconds_ago(dataframe)
        pressures = get_pressure(dataframe)
        return times, pressures
    else:
        # Raise an error if the datatype is not supported
        raise ValueError(f"Unsupported datatype: {datatype}. Supported types are: 'pressure'.")