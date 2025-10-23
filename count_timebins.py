"""
===============================================================================
COUNT_TIMEBINS.PY
Authors: Simon Todd & Chloe Willis
Date: July 2023

This code bins and counts entries in a CSV file by time. It is incorporated within
align_corpora.py, so it does not have to be used directly unless you want to
examine the distribution of data across time, e.g. to compare different criteria
for binning entries by time.
===============================================================================
"""

import dateutil.parser
import datetime
import csv
from collections import Counter
import json
import argparse

def floor_time(dt, to=1, unit="days"):
    """Floors a datetime object by rounding it down to a multiple of a
    given unit.
    
    Arguments
    ---------
    dt: datetime.datetime; the time to floor
    to: int (default 1); the value to round down to (without units)
    unit: str (default "days"); the unit of the value to round down to
              (valid options: "days", "hours", "minutes", "seconds")
    """
    if to < 1 or not isinstance(to, int):
        raise Exception("Invalid to parameter: {}".format(to))
    
    if unit=="days":
        bin_interval = datetime.timedelta(days=to) / datetime.timedelta(days=1)
        old_time_offset = (dt.replace(tzinfo=None) - dt.min).days
        new_time_offset = old_time_offset // to * to
        return dt - datetime.timedelta(days=old_time_offset - new_time_offset, 
                                       hours=dt.hour,
                                       minutes=dt.minute,
                                       seconds=dt.second,
                                       microseconds=dt.microsecond)
    
    elif unit in ["hours", "minutes", "seconds"]:
        bin_interval = datetime.timedelta(**{unit: to}).total_seconds()
        old_time_offset = (dt.replace(tzinfo=None) - dt.min).seconds
        new_time_offset = old_time_offset // bin_interval * bin_interval
        return dt - datetime.timedelta(days=0, 
                                       seconds=old_time_offset - new_time_offset, 
                                       microseconds=dt.microsecond)
    
    else:
        raise Exception("Unknown unit: {}".format(unit))

def bin_time(dt, interval=1, unit="days"):
    """Bins a datetime object and returns the lower (inclusive) and
    upper (exclusive) limits of that bin. Limits are returned in string
    format, using datetime.isoformat().
    
    Arguments
    ---------
    dt: datetime.datetime; the time to bin
    interval: int (default 1); the bin interval size (without units)
    unit: str (default "days"); the unit of the bin interval
              (valid options: "days", "hours", "minutes", "seconds")
    """
    lower_limit = floor_time(dt, to=interval, unit=unit)
    upper_limit = lower_limit + datetime.timedelta(**{unit: interval})
    return "{}_{}".format(lower_limit.isoformat(), upper_limit.isoformat())

def bin_entries_by_time(in_path, column_name="time", interval=1, unit="days"):
    """Bins entries into time intervals and returns a dictionary counting
    how many entries occur in a given interval.
    
    Arguments
    ---------
    in_path: str; the path to a parsed CSV file of entries
    column_name: str; the name of the column containing the time of the entries
    interval: int (default 1); the bin interval size (without units)
    unit: str (default "days"); the unit of the bin interval
              (valid options: "days", "hours", "minutes", "seconds")
    """
    counter = Counter()
    with open(in_path, encoding="utf-8") as in_file:
        reader = csv.DictReader(in_file)
        for row in reader:
            time_str = row[column_name]
            time_parsed = dateutil.parser.isoparse(time_str)
            time_bin = bin_time(time_parsed, interval=interval, unit=unit)
            counter[time_bin] += 1
    return counter

def dump_counts(counter, out_path):
    """Saves a counter to file in JSON format"""
    with open(out_path, "w", encoding="utf-8") as out_file:
        json.dump(counter, out_file, indent=4)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description = "Bin entries in CSV format by time and count them")
    parser.add_argument("in_paths", metavar="INPUTS", nargs="+", type=str, help="Paths to the input .csv files")
    parser.add_argument("out_path", metavar="OUTPUT", type=str, help="Path to the output .json file")
    parser.add_argument("--column", default="time", type=str, help="Name of column where timestamps are stored")
    parser.add_argument("--interval", default=1, type=int, help="The bin interval size (without units)")
    parser.add_argument("--unit", default="days", type=str, help="The unit of the bin interval (valid options: \"days\", \"hours\", \"minutes\", \"seconds\")")
    args = parser.parse_args()
    
    overall_counter = Counter()
    for path in args.in_paths:
        counter = bin_entries_by_time(path, column_name=args.column, interval=args.interval, unit=args.unit)
        overall_counter += counter
    dump_counts(overall_counter, args.out_path)
