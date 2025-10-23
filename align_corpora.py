"""
===============================================================================
ALIGN_CORPORA.PY
Authors: Simon Todd & Chloe Willis
Date: July 2022

This code aligns a study and reference corpus, pairing entries across corpora
based (optionally) on the time when they were created and/or manual labels (e.g.,
indicating the filtering step at which they would be removed from the dataset).
Close pairing is essential for maintaining symmetry between the two corpora.

Entries are first sorted into groups based on time and label (level of filtering),
and then randomly paired within these groups. If there are leftover reference
entries in a group after pairing all the study entries in that group, these
leftovers can be used to backfill in case there are not enough reference entries
in the same time period with a higher level label (e.g., if there are not enough
reference Tweets that would be filtered out by user-level criteria, gaps can be
filled by Tweets that would survive user-level filtering but may be filtered out
by Tweet-level criteria). If there are not enough entries in the reference corpus
to match all the entries in the study corpus in a particular group, after or in
the absence of backfilling as described above, the unmatched study entries are
discarded.
===============================================================================
"""

import dateutil.parser
import csv
import argparse
from count_timebins import bin_time
import random


def process_corpus(corpus_filepath, use_timebins=True, timebin_unit="hours", 
                   timebin_interval=1, time_column="time", 
                   use_labels=True, label_column="label", shuffle=False):
    """Reads a CSV corpus of entries and groups it by timebin and label,
    returning a dictionary that maps from timebin start time to a dictionary
    that maps from label to entries in that timebin with that label. If timebins
    and/or labels are not being used to group entries, the corresponding 
    dictionary has None as the key.
    
    Arguments
    ---------
    corpus_filepath: str; path to the CSV file for the corpus
    use_timebins: bool (default True); whether to construct and use timebins to
                  group entries across corpora
    timebin_unit: str (default "hours"); the unit in which timebins are defined
                  (valid options: "days", "hours", "minutes", "seconds")
    timebin_interval: int (default 1); the number of time units to be included
                      in a timebin
    time_column: str (default "time"); the name of the column in
                 the CSV file where the timestamp of the entry is stored
    use_labels: bool (default True); whether to use labels in defining groups
                     (if False, just uses timebins)
    label_column: str (default "label"); the name of the column in the CSV file
                  where the label of the entry is stored
    shuffle: bool (default False); whether to shuffle the entries within each
             group prior to returning the dictionary
    """
    grouped_entries = dict()
    with open(corpus_filepath, encoding="utf-8") as in_file:
        reader = csv.DictReader(in_file)
        
        for row in reader:
            
            if use_timebins:
                time = row[time_column]
                timebin_start = get_timebin_start(time, timebin_unit, timebin_interval)
            else:
                timebin_start = None
            if timebin_start not in grouped_entries:
                grouped_entries[timebin_start] = dict()
            
            label = None
            if use_labels:
                label = row[label_column]
            if label not in grouped_entries[timebin_start]:
                grouped_entries[timebin_start][label] = list()
            
            grouped_entries[timebin_start][label].append(row)
    
    if shuffle:
        shuffle_grouped_entries(grouped_entries)
    
    return grouped_entries


def get_timebin_start(time_str, timebin_unit, timebin_interval):
    """Returns a string representing the start time of the timebin in which an
    entry is included.
    
    Arguments
    ---------
    time_str: str; the timestamp at which the entry was created
    timebin_unit: str; the unit in which timebins are defined
                  (valid options: "days", "hours", "minutes", "seconds")
    timebin_interval: int; the number of time units to be included
                      in a timebin
    """
    time_parsed = dateutil.parser.isoparse(time_str)
    timebin = bin_time(time_parsed, interval=timebin_interval, unit=timebin_unit)
    start_time = timebin.split("_")[0]
    return start_time


def shuffle_grouped_entries(grouped_entries):
    """Shuffles the grouped entries at the innermost layer of a 2-level dictionary"""
    for labeled_entries in grouped_entries.values():
        for entries in labeled_entries.values():
            random.shuffle(entries)


def pair_entries(study_groups, reference_groups, label_hierarchy=None):
    """A generator that yields one pair of entries across a study and reference corpus
    at a time, matched by group. If there are leftover reference entries
    in a group after pairing all the study entries in that group, these leftovers 
    can be used to backfill in case there are not enough reference entries
    in the same time period with a higher level of filtering (e.g., if there are
    not enough reference Tweets that would be filtered out by user-level criteria,
    gaps can be filled by Tweets that would survive user-level filtering but may
    be filtered out by Tweet-level criteria). If there are not enough entries in the
    reference corpus to match all the entries in the study corpus in a particular
    group, after or in the absence of backfilling as described above, the unmatched
    study entries are discarded (and a message is shown summarizing the discards).
    
    Arguments
    ---------
    study_groups: dict; a nested dictionary of grouped entries in the study corpus,
                  mapping from timebin start, to label, to a list of entries.
    reference_groups: dict; a nested dictionary of grouped entries in the reference corpus,
                      mapping from timebin start, to label, to a list of entries.
    label_hierarchy: a list/tuple of the labels in the corpora, arranged from
                     lowest-level (with most filtering applied) to highest-level
                     (with least filtering applied); for example, ["included",
                     "tweet-excluded", "user-excluded"]. This hierarchy is used
                     to determine where entries can backfill. If no list is provided,
                     no backfilling is permitted.
    """
    for timebin_start in study_groups:
        entry_number = 0
        labels = label_hierarchy
        if label_hierarchy is None:
            labels = list(study_groups[timebin_start].keys())
        
        for (label_index, label) in enumerate(labels):
            study_entries = study_groups[timebin_start].get(label, [])
            reference_entries = reference_groups[timebin_start].get(label, [])
            
            # Pair each study entry
            while study_entries:
                study_entry = study_entries.pop()
                entry_number += 1
                pair_id = "{}_{}".format(timebin_start, entry_number)
                
                # If there aren't any reference entries with this label,
                # backfill from higher-level labels
                while label_hierarchy and label_index > 0 and not reference_entries:
                    label_index -= 1
                    reference_entries = reference_groups[timebin_start].get(label_hierarchy[label_index], [])
                
                # Get a reference entry and return the pair of entries
                # If no reference entry is available, move on to the next study group
                if reference_entries:
                    reference_entry = reference_entries.pop()
                    yield (study_entry, reference_entry, pair_id, label)
                else:
                    break


def rename_columns(row, corpus_name, label_column="label"):
    """Renames the columns in a csv row dictionary, to prepend corpus name and exclude label"""
    renamed_row = {"{}_{}".format(corpus_name, col_name): value for (col_name, value) in row.items()
                   if col_name != label_column}
    return renamed_row


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description = "Aligns study and reference corpora, pairing entries based on timebin and label")
    parser.add_argument("study_path", type=str, help="Path to the study corpus CSV of entries")
    parser.add_argument("reference_path", type=str, help="Path to the reference corpus CSV of entries")
    parser.add_argument("output_path", type=str, help="Path to the output CSV file")
    parser.add_argument("--no-timebins", dest="use_timebins", action="store_false", help="Flag to not use timebins to group entries")
    parser.add_argument("--time-column", default="time", type=str, help="Name of column where entry times are stored")
    parser.add_argument("--timebin-interval", default=1, type=int, help="The timebin interval size (without units)")
    parser.add_argument("--timebin-unit", default="hours", type=str, help="The unit of the timebin interval (valid options: \"days\", \"hours\", \"minutes\", \"seconds\")")
    parser.add_argument("--label-column", default="label", type=str, help="Name of column where entry labels are stored")
    parser.add_argument("--label-hierarchy", default=None, type=str, nargs="+", help="List of labels, separated by spaces, in \
                        order of low-level (survives all filters) to high-level (removed by the first filter)")
    parser.add_argument("--unlabeled", dest="use_labels", action="store_false", help="Do not group entries by label")
    parser.add_argument("--id-column", default="pair_id", type=str, help="Name of column where paired entry IDs will be stored")
    parser.add_argument("--seed", default=0, type=int, help="Random seed")
    args = parser.parse_args()
    
    # Set random seed, to ensure reproducibility
    random.seed(args.seed)
    
    # Group entries
    study_groups = process_corpus(args.study_path, use_timebins=args.use_timebins, timebin_unit=args.timebin_unit,
                   timebin_interval=args.timebin_interval, time_column=args.time_column, use_labels=args.use_labels,
                   label_column=args.label_column, shuffle=False)
    reference_groups = process_corpus(args.reference_path, use_timebins=args.use_timebins, timebin_unit=args.timebin_unit,
                       timebin_interval=args.timebin_interval, time_column=args.time_column, use_labels=args.use_labels,
                       label_column=args.label_column, shuffle=True)
    
    # Get column headers for output file
    with open(args.study_path, encoding="utf-8") as in_file:
        reader = csv.reader(in_file)
        generic_headers = next(reader)
    generic_headers = [header for header in generic_headers if header != args.label_column]
    headers = ["{}_{}".format(corpus, header) for corpus in ["study", "reference"] for header in generic_headers]
    headers.append(args.id_column)
    if args.use_labels:
        headers.append(args.label_column)
    
    # Create output file
    with open(args.output_path, "w", encoding="utf-8", newline="") as out_file:
        writer = csv.DictWriter(out_file, fieldnames=headers)
        writer.writeheader()
        
        # Pair entries and save them
        for (study_cols, reference_cols, pair_id, label) in pair_entries(study_groups, reference_groups, args.label_hierarchy):
            study_cols = rename_columns(study_cols, "study", label_column=args.label_column)
            reference_cols = rename_columns(reference_cols, "reference", label_column=args.label_column)
            row = dict(**study_cols, **reference_cols)
            row[args.id_column] = pair_id
            if args.use_labels:
                row[args.label_column] = label
            
            writer.writerow(row)