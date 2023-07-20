"""
===============================================================================
KEYNESS.PY
Authors: Simon Todd & Chloe Willis
Date: July 2023

This code calculates keyness scores for words used in a study and reference
corpus of Tweets. The Tweets are assumed to be paired across corpora and stored
together in a CSV file. The keyness scores are then saved to a CSV file.

By default, the keyness scores are calculated across the entire corpus. They
can also be calculated across time ranges of the corpus, using the --use-bins
flag. When binning the data, overall keyness scores can also be calculated
based on the number of bins each word occurs in (rather than its overall count
across all bins) by providing the --include-bin-counts flag.
===============================================================================
"""

from count_tweet_words import extract_words
from align_corpora import get_timebin_start
import datetime
import dateutil.parser
import csv
from collections import Counter
import pandas as pd
from scipy.stats import chi2_contingency
import numpy as np
import functools
import re

# Mapping between strftime codes and regex patterns
STRFTIME_REGEX_MAPS = {
    "%a": r"[A-Z][a-z]+",
    "%A": r"[A-Z][a-z]+",
    "%w": r"\d",
    "%d": r"\d{2}",
    "%b": r"[A-Z][a-z]+",
    "%B": r"[A-Z][a-z]+",
    "%m": r"\d{2}",
    "%y": r"\d{2}",
    "%Y": r"\d{4}",
    "%H": r"\d{2}",
    "%I": r"\d{2}",
    "%p": r"(?:[A-Z]{1,2}|[a-z]{1,2})",
    "%M": r"\d{2}",
    "%S": r"\d{2}",
    "%f": r"\d{6}",
    "%z": r"(?:[+-]\d{4}(?:\d{2}(?:\.\d{6})?)?)?",
    "%Z": r"(?:[A-Z]{2,4})?",
    "%j": r"\d{3}",
    "%U": r"\d{2}",
    "%W": r"\d{2}",
    "%c": r"[A-Z][a-z]+ (?:[A-Z][a-z]+ \d{2}|\d{2} [A-Z][a-z]+) \d{2}:\d{2}:\d{2} \d{4}",
    "%x": r"\d{2}(\W)\d{2}\1\d{2}(?:\d{2})?",
    "%X": r"\d{2}:\d{2}:\d{2}",
    "%%": r"%",
    "%G": r"\d{4}",
    "%u": r"\d",
    "%V": r"\d{2}"
}


def create_binned_wordcount_df(csv_filepath, corpora=("study", "reference"), col_sep="_",
                               tweet_col_suffix="tweet.text", use_bins=True, include_bin_counts=False,
                               timebin_unit="months",  timebin_interval=1, 
                               time_col_suffix="tweet.created_at", label_column="label", 
                               keep_labels=None, exclude_terms=None, timebin_formatting=None):
    """Converts a CSV of tweets to a DataFrame of counts of distinct
    words in the tweets by bin, for a provided set of columns.
    
    Arguments
    ---------
    csv_filepath: str; path to the CSV file containing Tweets paired
                  across corpora
    corpora: iter(str); list of the corpus names which are assumed 
             to be prefixes of the column headers in the CSV
    col_sep: str; separator between prefix (corpus) and suffix (type)
             of column headers
    tweet_col_suffix: str; suffix of the column containing Tweets
    use_bins: bool; whether to bin the counts by timebin (True), or just give
              overall counts across all corpora
    include_bin_counts: bool; whether to include columns that count how many bins
                        each word occurs in (as well as the columns that count how
                        many times it occurs in each bin)
    timebin_unit: str (default "months"); the unit in which timebins are defined
                  (valid options: "days", "weeks", "months", "years")
    timebin_interval: int (default 1); the number of time units to be included
                      in a timebin (for months, must be a divisor of 12)
    time_col_suffix: str; suffix of the column containing times at which
                     Tweets were posted
    label_column: str; the name of the column that contains labels that
                  can be used to filter the Tweets
    keep_labels: iter(str); list of labels of Tweets that will be used to
                 calculate counts (if None, all Tweets are used)
    exclude_terms: iter(str); list of terms to be excluded from counting
                   (e.g. because they are query terms)
    timebin_formatting: str; the strftime format codes for naming the timebins.
                        If None, names the timebins as the ISO format timestamp
                        of the bin start time, prefixed by bin_
    """
    # Determine the function to use for getting timebin start time
    if timebin_unit == "weeks":
        timebin_interval *= 7
        timebin_unit = "days"
    if timebin_unit == "days":
        get_starttime = get_timebin_start
    else:
        get_starttime = floor_large_time
    
    all_counters = dict()
    
    with open(csv_filepath, encoding="utf-8") as in_file:
        reader = csv.DictReader(in_file)
        
        for row in reader:
            # Check label and skip row if required
            if keep_labels is not None:
                label = row[label_column]
                if label not in keep_labels:
                    continue
            
            # Count words for corpora
            for corpus in corpora:
                tweet = row[corpus + col_sep + tweet_col_suffix]
                time = row[corpus + col_sep + time_col_suffix]
                tweet_bin = "overall_count"
                if use_bins:
                    tweet_bin_starttime = get_starttime(time_str, timebin_unit, timebin_interval)
                    if timebin_formatting is not None:
                        tweet_bin = dateutil.parser.isoparse(tweet_bin_starttime).strftime(timebin_formatting)
                    else:
                        tweet_bin = "bin_" + tweet_bin_starttime
                words = extract_words(tweet)
                
                # Exclude terms as required
                if exclude_terms is not None:
                    words = [word for word in words if word not in exclude_terms]
                
                # Update counter
                if tweet_bin not in all_counters:
                    all_counters[tweet_bin] = dict()
                bin_counters = all_counters[tweet_bin]
                if corpus not in bin_counters:
                    bin_counters[corpus] = Counter()
                bin_counters[corpus].update(words)
    
    # Convert to DataFrame with MultiIndex
    counts_df = pd.DataFrame.from_dict({(tweet_bin, corpus): counter 
                                        for (tweet_bin, bin_counter) in sorted(all_counters.items())
                                        for (corpus, counter) in bin_counter.items()
                                       }).fillna(0)
    
    # If not binning counts, return df that just contains overall counts;
    # if binning counts, add overall counts columns and (optionally) bin counts
    if use_bins:
        add_overall_counts(counts_df, timebin_formatting=timebin_formatting)
        if include_bin_counts:
            add_bin_counts(counts_df, timebin_formatting=timebin_formatting)
    else:
        counts_df = counts_df["overall_counts"]
    
    return counts_df


def floor_large_time(time_str, timebin_unit, timebin_interval=1):
    """Rounds a time down to a bin by month or year
    
    Arguments
    ---------
    time_str: str; ISO representation of a time
    timebin_unit: str; the unit in which timebins are defined ("months" / "years")
    timebin_interval: int (default 1); the number of time units to be included
                      in a timebin (for months, must be a divisor of 12)
    """
    if timebin_interval < 1 or not isinstance(timebin_interval, int):
        raise Exception("Invalid timebin_interval parameter: {}".format(timebin_interval))
    
    if timebin_unit not in ["months", "years"]:
        raise Exception("Unknown timebin_unit: {}".format(timebin_unit))
    
    dt = dateutil.parser.isoparse(time_str)
    floored_time = dt
    
    if timebin_unit == "months":
        if 12 % timebin_interval != 0:
            raise Exception("Month-based timebins must have a timebin_interval that is a divisor of 12")
        floored_month = dt.month - ((dt.month - 1) % timebin_interval)
        floored_time = datetime.datetime(dt.year, floored_month, 1)
    
    elif timebin_unit == "years":
        floored_year = dt.year - ((dt.year - 1) % timebin_interval)
        floored_time = datetime.datetime(floored_year, 1, 1)
    
    return floored_time.isoformat()


def add_overall_counts(counts_df, corpus_level=1, **kwargs):
    """Adds columns for the overall counts across bins for each word in each corpus."""
    nonbin_columns = get_nonbin_columns(counts_df, **kwargs)
    overall_counts = (counts_df
                  .drop(nonbin_columns, axis=1)
                  .groupby(level=corpus_level, axis=1, sort=False)
                  .agg(lambda df: 
                       apply_binned(df, lambda subdf: subdf.sum(axis=1), 
                                    drop_level=corpus_level)
                      )
                 )
    counts_df[[("overall_count", corpus) for corpus in overall_counts.columns]] = overall_counts


@functools.lru_cache(maxsize=None)
def get_nonbin_columns(binned_df, bin_level=0, **kwargs):
    """Gets a list of the column names in a dataframe that do not represent bins"""
    columns = binned_df.columns
    if isinstance(columns, pd.core.indexes.multi.MultiIndex):
        column_names = list(columns.levels[bin_level])
    else:
        column_names = list(columns)
    return [column_name for column_name in column_names if not is_bin(str(column_name), **kwargs)]


@functools.lru_cache(maxsize=None)
def is_bin(column_name, timebin_formatting=None, **kwargs):
    """Indicates whether a column represents a bin"""
    pattern = "bin_+"
    if timebin_formatting is not None:
        pattern = timebin_to_pattern(timebin_formatting)
    return bool(re.fullmatch(pattern, column_name))


@functools.lru_cache(maxsize=None)
def timebin_to_pattern(timebin_formatting):
    """Converts a provided strftime format for a timebin into a regex pattern
    that matches strings with that format
    """
    pattern = timebin_formatting
    for (format_code, re_pattern) in STRFTIME_REGEX_MAPS.items():
        pattern = pattern.replace(format_code, re_pattern)
    return pattern


def apply_binned(grouped_df, func, drop_level=0, drop_axis=1, *args, **kwargs):
    """Applies a function to a DataFrameGroupBy, by discarding a level of a multiindex."""
    plain_df = grouped_df.droplevel(level=drop_level, axis=drop_axis)
    return func(plain_df, *args, **kwargs)


def add_bin_counts(counts_df, corpus_level=1, **kwargs):
    """Adds columns that count the number of bins each word occurs in for each corpus."""
    nonbin_columns = get_nonbin_columns(counts_df, **kwargs)
    bin_counts = (counts_df
                  .drop(nonbin_columns, axis=1)
                  .groupby(level=corpus_level, axis=1, sort=False)
                  .agg(lambda df: 
                       apply_binned(df, lambda subdf: (subdf > 0).sum(axis=1), 
                                    drop_level=corpus_level)
                      )
                 )
    counts_df[[("bin_count", corpus) for corpus in bin_counts.columns]] = bin_counts


def score_keyness(counts, statistics=("g",), target_corpus="study", tidy_df=True,
                  nan=False, **kwargs):
    """Returns a DataFrame that augments word counts with keyness scores, based on 
    a designation of the name of the study corpus.
    
    Arguments
    ---------
    counts: DataFrame of word counts per corpus, where headers are corpus names
            and each row represents a different word (labeled as the index)
    statistics: tuple(str); the statistics to calculate as a measure of keyness.
                Currently only "g" (signed G-statistic) is available)
    target_corpus: str; name of the corpus that is the study corpus (the input DF
                   has a column of counts with this name)
    tidy_df: bool; whether to tidy the DataFrame by pulling out a word column and
             sorting by keyness
    nan: bool; whether to use np.nan for cases where the word was not observed in
         either corpus (True), or instead use a keyness value of 0.0 (False)
    """
    if isinstance(statistics, str):
        statistics = (statistics,)
    
    keyness_df = counts.copy()
    for statistic in statistics:
        keyness_df["keyness_" + statistic] = calculate_keyness_col(counts, statistic,
                                                                   target_corpus=target_corpus, 
                                                                   nan=nan, **kwargs)
    
    if tidy_df:
        keyness_df = keyness_df.reset_index().rename(columns={"index": "word"})
        sort_columns = ["keyness_" + statistic for statistic in statistics] + ["word"]
        sort_ascendings = [False] * len(statistics) + [True]
        keyness_df.sort_values(sort_columns, ascending=sort_ascendings, inplace=True, ignore_index=True)
    
    return keyness_df


def calculate_keyness_col(counts, statistic, target_corpus="study", nan=False, **kwargs):
    """Calculates a column of keyness values from word counts, based on a designation of
    the name of the study corpus.
    
    Arguments
    ---------
    counts: DataFrame of word counts per corpus, where headers are corpus names
            and each row represents a different word (labeled as the index)
    statistic: str; the statistic to calculate as a measure of keyness.
               Currently only "g" (signed G-statistic) is available)
    target_corpus: str; name of the corpus that is the study corpus (the input DF
                   has a column of counts with this name)
    nan: bool; whether to use np.nan for cases where the word was not observed in
         either corpus (True), or instead use a keyness value of 0.0 (False)
    """
    target_index = counts.columns.get_loc(target_corpus)
    totals = tuple(counts.sum())
    
    keyness_col = counts.apply(
        lambda row: calculate_keyness_statistic(row, totals, statistic, target_index=target_index,
                                                nan=nan, **kwargs), 
        axis=1)
    
    return keyness_col


def calculate_keyness_statistic(counts, totals, statistic, target_index=0, 
                                negatives=True, cache_sum_threshold=20, nan=False, **kwargs):
    """Returns a designated keyness statistic based on counts of a given word, either by
    retrieving it from a cache or calculating it anew.
    
    Arguments
    ---------
    counts: DataFrame; a row containing the counts for a given word across different
            corpora
    totals: tuple(int); a row containing the total counts across all words in each corpus
    statistic: str; the statistic to calculate as a measure of keyness.
               Currently only "g" (signed G-statistic) is available)
    target_index: int; the index of the column that represents the study corpus
    negatives: bool; whether to set the keyness statistic to be negative if the observed count
               in the study corpus is lower than the expected count
    cache_sum_threshold: int; if the total count of the word across all corpora (i.e, the
                         sum of counts) is less than or equal to this, the resulting
                         keyness statistic will be looked up in a cache rather than calculated,
                         to speed up processing of rare words
    nan: bool; whether to use np.nan as the resultant G-statistic when the word was not
         observed in either corpus (True), or use 0.0 (False)
    """
    total_count = counts.sum()
    if total_count == 0:
        if nan:
            return np.nan
        else:
            return 0.0
    
    if total_count <= cache_sum_threshold:
        get_statistic = eval("_cache_signed_" + statistic)
        return get_statistic(tuple(counts), totals, target_index=target_index,
                             negatives=negatives, **kwargs)
    
    get_statistic = eval("_calculate_signed_" + statistic)
    return get_statistic(counts, totals, target_index=target_index, negatives=negatives, **kwargs)


def _calculate_signed_g(counts, totals, target_index=0, negatives=True, **kwargs):
    """Calculates the G statistic for a row of counts, given a row of corresponding
    total counts.
    
    Arguments
    ---------
    counts: tuple(int); a row containing the counts for a given word across different
            corpora
    totals: tuple(int); a row containing the total counts across all words in each corpus
    target_index: int; the index of the column that represents the study corpus
    negatives: bool; whether to set the G-statistic to be negative if the observed count
               in the study corpus is lower than the expected count
    """
    table = np.array([counts, totals])
    (g, _, _, expected_table) = chi2_contingency(table, correction=False, lambda_=0)
    
    if negatives:
        observed_target = counts[target_index]
        expected_target = expected_table[0][target_index]
        if observed_target < expected_target:
            g = -g
    
    return g


@functools.lru_cache(maxsize=None)
def _cache_signed_g(counts, totals, target_index=0, negatives=True, **kwargs):
    """Uses caching to speed up the calculation of signed G."""  
    return _calculate_signed_g(counts, totals, target_index=target_index,
                               negatives=negatives, **kwargs)


def score_keyness_per_bin(counts_df, statistics=("g",), bin_level=0, target_corpus="study",
                          nan=True, **kwargs):
    """Returns a DataFrame with keyness scores for each word, for each timebin.
    
    Arguments
    ---------
    counts_df: DataFrame of word counts per corpus, split by timebin as one level
               of a multiindex, where each row has counts of a single word across bins/
               corpora (word identity is the row index). Within each timebin, headers 
               are corpus names.
    statistics: tuple(str); the statistics to calculate as a measure of keyness.
                Currently only "g" (signed G-statistic) is available)
    bin_level: int; the level of the multiindex that represents the timebins
    target_corpus: str; name of the corpus that is the study corpus (the input DF
                   has a column of counts with this name)
    nan: bool; whether to use np.nan for cases where the word was not observed in
         either corpus (True), or instead use a keyness value of 0.0 (False)
    """
    # We do want keyness for overall_count, just not other things
    nonbin_columns = get_nonbin_columns(counts_df, bin_level=bin_level, **kwargs)
    nonbin_columns = [column_name for column_name in nonbin_columns if not column_name.endswith("_count")]
    
    # Get DataFrame with keyness but no nonbin columns
    df_with_bin_keyness = (counts_df
                           .drop(nonbin_columns, axis=1)
                           .groupby(level=bin_level, axis=1, sort=False)
                           .apply(lambda df: 
                                  apply_binned(df, score_keyness, statistics=statistics, 
                                               target_corpus=target_corpus, nan=nan, 
                                               tidy_df=False, **kwargs)
                                 )
                          )
    
    # Add the nonbin columns back in
    nonbin_df = counts_df[nonbin_columns]
    df_with_bin_keyness = df_with_bin_keyness.merge(nonbin_df, how="left", left_index=True, right_index=True)

    return df_with_bin_keyness


def save_df(keyness_df, output_path, flatten=True, flat_col_sep=".", sort_by="keyness_g"):
    """Saves a keyness DataFrame to CSV.
    
    Arguments
    ---------
    keyness_df: DataFrame containing keyness scores and counts for words (rows) across
                corpora (columns); may be split across timebins (higher-level columns)
                by use of a multiindex.
    output_path: str; path to output CSV file
    flatten: bool; if True, flattens a column multiindex before saving
    flat_col_sep: str; the separator to use between multiindex values when creating
                  flattened column names
    sort_by: str; name of the column to sort by (with ties broken alphabetically)
    """
    # Get the column index value on which to sort
    if isinstance(keyness_df.columns, pd.core.indexes.multi.MultiIndex):
        if flatten:
            sort_by = "overall_count" + flat_col_sep + sort_by
        else:
        sort_by = ("overall_count", sort_by)
    
    # Flatten columns if required
    if flatten and isinstance(keyness_df.columns, pd.core.indexes.multi.MultiIndex):
        keyness_df.columns = [flat_col_sep.join(multicol_levels)
                              for multicol_levels in keyness_df.columns.values]
    
    # Save DataFrame to CSV
    df_to_save = (
        keyness_df
        .reset_index(names="word")
        .sort_values([sort_by, "word"], ascending=[False, True], ignore_index=True)
    )
    df_to_save.to_csv(output_path, index=False, encoding="utf-8")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description = "Calculate keyness scores for words from a CSV of \
                                                    Tweets paired across study and reference corpora")
    parser.add_argument("input_path", type="str", help="Path to the input CSV file of Tweets paired \
                        across a study and reference corpus")
    parser.add_argument("output_path", type="str", help="Path to the output CSV file")
    parser.add_argument("--corpus-names", type="str", nargs="+", default=["study", "reference"],
                        help="Names of corpora that are used as prefixes in column headers in the \
                        input CSV")
    parser.add_argument("--target-corpus", type="str", default="study", help="Name of the target \
                        (study) corpus that is used as a prefix in column headers in the input CSV")
    parser.add_argument("--input-col-sep", type="str", default="_", help="The character that is used \
                        to separate prefixes (corpus names) from suffixes (types of information) in \
                        column headers in the input CSV")
    parser.add_argument("--tweet-col-suffix", type="str", default="tweet.text", help="The suffix of \
                        the column headers in the input CSV that designate Tweet text")
    parser.add_argument("--time-col-suffix", type="str", default="tweet.created_at", help="The suffix \
                        of the column headers in the input CSV that designate Tweet post times")
    parser.add_argument("--label-column", type="str", default="label", help="The name of the column \
                        in the input CSV that designates the label of a pair of Tweets (e.g. indicating \
                        the level at which it is filtered out)")
    parser.add_argument("--use-bins", dest="use_bins", action="store_true", help="Bin Tweets by time and \
                        calculate keyness within each bin, in addition to calculating keyness across the \
                        dataset as a whole")
    parser.add_argument("--bin-time-unit", dest="timebin_unit", type="str", default="months", help="The \
                        unit of the time interval that is used to bin Tweets by time for keyness \
                        calculation (valid options: \"days\", \"weeks\", \"months\", \"years\"). Note: \
                        this does not refer to the timebins that were used for collecting the data, but \
                        rather the granularity of bins that will be used for analyzing keyness across time.")
    parser.add_argument("--bin-time-interval", dest="timebin_interval", type="int", default=1, help="The \
                        bin time interval size (without units). If binning by month, this must be a divisor \
                        of 12. Note: this does not refer to the timebins that were used for collecting the \
                        data, but rather the granularity of bins that will be used for analyzing keyness \
                        across time.")
    parser.add_argument("--bin-formatting", dest="timebin_formatting", type="str", default=None, help="The \
                        string formatting code to represent bins as column names, using strftime format \
                        codes; for example, %Y_%m would create bin names such as 2023_05 (for May 2023); see \
                        https://docs.python.org/3/library/datetime.html#strftime-and-strptime-format-codes \
                        for the list of codes. If this argument is not provided, bins are labeled by their \
                        full timestamp, with the prefix bin_")
    parser.add_argument("--keep-labels", type="str", nargs="+", default=None, help="The labels of Tweets to \
                        keep and use for the keyness analysis; paired Tweets with other labels in the input \
                        CSV will be filtered out from the analysis. If no labels are provided, all Tweets \
                        are used in the analysis.")
    parser.add_argument("--exclude-terms-path", type="str", default=None, help="The path to a TXT file \
                        containing terms that are to be excluded from the keyness analysis (one per line). \
                        This can be used to exclude the query terms by which the data were harvested, since \
                        query terms are assumed to be key.")
    parser.add_argument("--include-bin-counts", dest="include_bin_counts", action="store_true", help="In \
                        addition to performing a keyness analysis based on the number of times each word occurs \
                        in the study corpus relative to the reference corpus, also perform an analysis based \
                        on the number of timebins that the word occurs in")
    parser.add_argument("--no-signing", dest="negatives", action="store_false", help="Do not set the keyness \
                        statistic to be negative when the word is underrepresented in the study corpus relative \
                        to the reference corpus")
    parser.add_argument("--nan", dest="nan", action="store_true", help="Use numpy.nan for keyness when a word \
                        does not occur in either corpus (as opposed to 0.0, which is used if this flag is not \
                        provided)")
    
    args = parser.parse_args()
    
    # Load exclude terms
    if args.exclude_terms_path is None:
        exclude_terms = None
    else:
        with open(args.exclude_terms_path, encoding="utf-8") as in_file:
            exclude_terms = [line.strip() for line in in_file]
    
    # Get wordcount DataFrame
    counts_df = create_binned_wordcount_df(args.input_path, corpora=args.corpus_names, col_sep=args.input_col_sep,
                                           tweet_col_suffix=args.tweet_col_suffix, use_bins=args.use_bins,
                                           include_bin_counts=args.include_bin_counts, timebin_unit=args.timebin_unit,
                                           timebin_interval=args.timebin_interval, time_col_suffix=args.time_col_suffix,
                                           label_column=args.label_column, keep_labels=args.keep_labels,
                                           exclude_terms=exclude_terms, timebin_formatting=args.timebin_formatting)
    
    # Get keyness statistics
    if args.use_bins:
        keyness_df = score_keyness_per_bin(counts_df, target_corpus=args.target_corpus, nan=args.nan,
                                           timebin_formatting=args.timebin_formatting)
    else:
        keyness_df = score_keyness(counts_df, target_corpus=args.target_corpus, tidy_df=False, nan=args.nan)
    
    # Save results to CSV
    save_df(keyness_df, args.output_path)