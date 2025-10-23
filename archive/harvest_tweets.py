"""
===============================================================================
HARVEST_TWEETS.PY
Authors: Simon Todd & Chloe Willis
Date: July 2023

Use this code to harvest Tweets through Twitter API v2 via Twarc2.
Harvested Tweets will be saved in JSONL format with extensive information, and
converted to CSV format with a small number of fields.

This code harvests Tweets using a full archive search:
https://developer.twitter.com/en/docs/twitter-api/tweets/search/quick-start/full-archive-search
To run this code, you will need Twitter API v2 access; your API access information
(bearer token, API key) should be stored in a JSON file.

This code assumes you are building two corpora: 
(1) a study corpus containing Tweets related to the topic of interest; and 
(2) a reference corpus containing general Tweets that "match" your study corpus
    with respect to time but do not contain the query terms used to harvest 
    your study corpus.

This code can be used to harvest study or reference Tweets, by providing the 
"study" or "reference" option after shared optional keyword arguments, as in:
python harvest_tweets.py [shared args] study [study args] or
python harvest_tweets.py [shared args] reference [reference args]

In both cases, the query will have a fixed configuration specifying constraints
(e.g. language) and desired fields to return; this is provided in a JSON file.

The shared arguments are:
--dir: the path to the folder where input and output files are located
--keys: the name of the JSON file containing the API key information,
        (by default, keys.json, located in the folder specified by --dir)
--config: the name of the JSON file containing the fixed query configuration,
          (by default, query_config.json, located in the folder specified by --dir)
--csv-fields: the fields to extract to CSV (by default, tweet.id, user.username,
              tweet.created_at, and tweet.text)

Note: if you forget to extract a particular field when harvesting, you can
extract it from your JSONL data later using extract_tweets.py, without having
to re-harvest the Tweets.

For both study and reference tweets, the first argument written after "study" or
"reference" should be the name of a file containing the search terms for the study
corpus (Tweets in the study corpus must include at least one term, and Tweets in
the reference corpus may not contain any terms). This is a TXT file where each 
term should be provided on its own line (phrasal terms can also be used, by 
separating words on the same line by spaces). For example:
python harvest_tweets.py study study_terms.txt [optional arguments]

When harvesting study Tweets, output files will be named with the stem "study"
(e.g. study.jsonl, study.csv), unless you change it with the --filename-stem arg.
The argument --exclude-terms can be used to load a TXT file of terms that should not
appear in any study Tweet.
Use the arguments --start-date and --end-date to provide the dates to start and
end the search, in yyyy-mm-dd format (end date is EXCLUSIVE; timezone is UTC).
Unless the --no-counting flag is provided, Tweets will be binned and counted by time, 
creating a *_timebin-counts.json file containing the counts (where * is the stem).
The arguments --timebin-interval and --timebin-unit can be used to define a timebin).

Note: if you want to change the timebin definition after harvesting the study 
corpus, this can be accomplished without re-harvesting through count_timebins.py.

When harvesting reference Tweets, output files will be named with the stem "reference",
unless you change it with the --filename-stem argument.
Reference Tweets are harvested according to the timebins from the JSON file of binned
counts in the study corpus; load this file through the --timebin-counts argument.
In order to ensure that sufficient reference Tweets are harvested to be able to
match the study Tweets after filtering, the number of Tweets in each timebin can
be multiplied by a fixed multiplier, provided through the --count-multiplier arg.
===============================================================================
"""

# Allow imports from the parent directory, where non-archived code is located
import os
parent_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.append(parent_dir)

from twarc.client2 import Twarc2
from extract_tweets import jsonl_to_csv
from count_timebins import bin_tweets_by_time, dump_counts
from pathlib import Path
import argparse
import datetime
import json
import math


def authenticate_api(keys_path="keys.json"):
    """Authenticates access to the Twitter API using Twarc2, based on API keys
    provided in a JSON file.
    """
    with open(keys_path) as in_file:
        keys = json.load(in_file)
    return Twarc2(**keys)


def prepare_query(config_path="query_config.json",
                  include_path=None, exclude_path=None,
                  start_date=None, end_date=None):
    """Prepares the query to be provided to the Twitter API.
    For the study corpus, this query is used as-is; for the reference corpus,
    it is modified for each timebin.
    
    Arguments
    ---------
    config_path: str; path to a JSON query config file.
    include_path: str; path to a TXT file containing a set of terms to match,
                  one per line (returned Tweets contain at least one term).
    exclude_path: str; path to a TXT file containing a set of terms to exclude,
                  one per line (returned Tweets contain none of these terms).
    start_date: str; UTC date to start the search, in yyyy-mm-dd format.
    end_date: str; UTC date to end the search, in yyyy-mm-dd format; Tweets
                   posted on this day are not included in results.
    """
    def term_generator(term_path):
        """Yields a generator over terms in a TXT file."""
        with open(term_path, encoding="utf-8") as in_file:
            for line in in_file:
                term = line.strip()
                if " " in term:
                    term = '"{}"'.format(term)
                yield term
    
    def parse_date(date_str):
        """Parses a date string into a UTC timestamp"""
        return date_str + "T00:00:00Z"
    
    with open(config_path, encoding="utf-8") as config_file:
        query = json.load(config_file)
    query["max_results"] = 500
    
    if exclude_path is not None:
        exclude_terms = " -".join(term_generator(exclude_path))
        if exclude_terms:
            query["query"] += " -" + exclude_terms
    
    if include_path is not None:
        include_terms = " OR ".join(term_generator(include_path))
        if include_terms:
            query["query"] += " " + include_terms
    
    if start_date is not None:
        query["start_time"] = parse_date(start_date)
    
    if end_date is not None:
        query["end_time"] = parse_date(end_date)
    
    return query


def update_query_for_timebin(query, bin_str, num_tweets):
    """Updates the query (start/end times and results per page) for a timebin.
    Note: update is performed in-place.
    """
    (bin_start, bin_end) = bin_str.split("_")
    bin_start = datetime.datetime.fromisoformat(bin_start)
    bin_end = datetime.datetime.fromisoformat(bin_end)
    query["start_time"] = bin_start
    query["end_time"] = bin_end
    query["max_results"] = min(max(num_tweets, 10), 500)


def harvest(api, query, out_jsonl, num_tweets=10000000):
    """Harvests a desired number of Tweets according to a query
    and saves them to an open output JSONL file.
    """
    search_results = api.search_all(**query)
    
    total_tweets = 0
    for page in search_results:
        # Trim off extra tweets (references in includes field will be kept)
        page["data"] = page["data"][:(num_tweets - total_tweets)]

        # Write page to results file
        out_jsonl.write(json.dumps(page) + "\n")
        total_tweets += len(page["data"])
        
        # Exit when all tweets are extracted
        if total_tweets >= num_tweets:
            break


def harvest_bins(timebin_counts_path, api, query, out_jsonl, multiplier=1.25):
    """Harvests Tweets according to pre-specified timebins.
    
    Arguments
    ---------
    timebin_counts_path: str; path to a JSON file that defines timebins
                         and the number of study Tweets in each timebin.
    api: an authenticated instance of the Twarc2 Twitter API.
    query: dict; a Twitter API query.
    out_jsonl: file; an open JSONL file to save harvested Tweets.
    multiplier: float; a multiplier for the number of tweets to harvest
                       in each timebin (provided count * multiplier)
    """
    with open(timebin_counts_path, encoding="utf-8") as in_file:
        bins = json.load(in_file)
    total_bins = len(bins)
    
    for (bin_number, (bin_str, bin_size)) in enumerate(bins.items()):
        num_tweets = math.ceil(bin_size * multiplier)
        update_query_for_timebin(query, bin_str, num_tweets)
        if bin_number % 100 == 0:
            print("{} Starting bin {}/{}...".format(datetime.datetime.now().strftime("%d/%m %H:%M"), bin_number+1, total_bins))
        harvest(api, query, out_jsonl, num_tweets=num_tweets)


if __name__ == "__main__":
    # Top-level argument parser
    parser = argparse.ArgumentParser(description = "Harvest Tweets")
    parser.add_argument("--dir", dest="out_dir", type=Path, default="./",
                        help="Path to the directory where output files will be stored, \
                              and from which input files will be loaded")
    parser.add_argument("--config", dest="config_name", type=str, default="query_config.json", 
                        help="Name of the .json file specifying the query configuration")
    parser.add_argument("--keys", dest="keys_name", type=str, default="keys.json", 
                        help="Name of the .json file specifying the Twitter API keys")
    parser.add_argument("--csv-fields", dest="csv_fields", type=str, nargs="+",
                        default=["tweet.id", "user.username", "tweet.created_at", "tweet.text"],
                        help="Fields to extract to CSV")
    subparsers = parser.add_subparsers(help="Purpose of harvesting", required=True)
    
    # Subparser for harvesting study Tweets
    parser_study = subparsers.add_parser("study", description="Harvest study Tweets", 
                                         help="Harvest Tweets containing study terms between two dates")
    parser_study.add_argument("--study_terms", dest="include_name", type=str,
                              help="Name of the .txt file specifying the search terms to include")
    parser_study.add_argument("--exclude-terms", dest="exclude_name", type=str, default=None,
                              help="Name of the .txt file specifying the search terms to exclude")
    parser_study.add_argument("--start-date", dest="start_date", type=str, default=None,
                              help="Date to start the search, in format YYYY-MM-DD")
    parser_study.add_argument("--end-date", dest="end_date", type=str, default=None,
                              help="Date to end the search (the day before), in format YYYY-MM-DD")
    parser_study.add_argument("--max-tweets", dest="max_tweets", type=int, default=10000000,
                              help="Maximum number of Tweets to harvest, based on API limits")
    parser_study.add_argument("--no-counting", dest="count_timebins", action="store_false", 
                              help="Don't count the Tweets per timebin")
    parser_study.add_argument("--timebin-unit", dest="timebin_unit", type=str, default="hours", 
                              help="Unit of time by which to bin Tweets (days/hours/minutes/seconds)")
    parser_study.add_argument("--timebin-interval", dest="timebin_interval", type=int, default=1, 
                              help="Number of time units within each timebin")
    parser_study.add_argument("--filename-stem", dest="out_stem", type=str, default="study",
                              help="The name to use for output files (Tweet JSONL and CSV, as well as \
                                    timebin count JSON).")
    parser_study.set_defaults(purpose="study", timebin_counts_name=None)
    
    # Subparser for harvesting reference Tweets
    parser_ref = subparsers.add_parser("reference", description="Harvest reference Tweets", 
                                       help="Harvest Tweets that are time-matched to a study corpus, \
                                             but don't contain study terms")
    parser_ref.add_argument("--study_terms", dest="exclude_name", type=str,
                            help="Name of the .txt file specifying the search terms for the study \
                                  corpus, which are avoided in the reference corpus")
    parser_ref.add_argument("--timebin-counts", dest="timebin_counts_name", type=str, 
                            default="study_timebin-counts.json",
                            help="Name of the .json file specifying the search timebins and desired counts, \
                                  based on the study corpus")
    parser_ref.add_argument("--count-multiplier", dest="timebin_count_multiplier", type=float, default=1.25, 
                            help="Multiplier of timebin counts, to harvest extra reference Tweets per bin")
    parser_ref.add_argument("--filename-stem", dest="out_stem", type=str, default="reference",
                              help="The name to use for output files (Tweet JSONL and CSV).")
    parser_ref.set_defaults(purpose="reference", count_timebins=False, start_date=None, end_date=None)
    
    args = parser.parse_args()
    
    # Set up output directory and create paths
    args.out_dir.mkdir(parents=True, exist_ok=True)
    pathify = lambda name: args.out_dir.joinpath(name) if name is not None else None
    
    # Harvest Tweets
    print("{} Harvesting {} Tweets...".format(datetime.datetime.now().strftime("%d/%m %H:%M"), args.harvest))
    api = authenticate_api(args.keys_path)
    query = prepare_query(config_path=pathify(args.config_name), 
                          include_path=pathify(args.include_name), exclude_path=pathify(args.exclude_name),
                          start_date=args.start_date, end_date=args.end_date)
    with open(pathify(args.out_stem + ".jsonl"), "w", encoding="utf-8") as out_jsonl:
        
        if args.purpose == "study":
            harvest(api, query, out_jsonl, num_tweets=args.max_tweets)
        
        elif args.purpose == "reference":
            harvest_bins(pathify(args.timebin_counts_name), api, query, out_jsonl,
                         multiplier=args.timebin_count_multiplier)
    
    # Convert to CSV
    print("{} Converting to CSV...".format(datetime.datetime.now().strftime("%d/%m %H:%M")))
    jsonl_to_csv(pathify(args.out_stem + ".jsonl"), pathify(args.out_stem + ".csv"), fields=args.csv_fields)
    
    # Bin and count Tweets by time
    if args.count_timebins:
        print("{} Binning and counting Tweets by time...".format(datetime.datetime.now().strftime("%d/%m %H:%M")))
        counter = bin_tweets_by_time(pathify(args.out_stem + ".csv"), interval=args.timebin_interval, unit=args.timebin_unit)
        dump_counts(counter, pathify(args.out_stem + "_timebin-counts.json"))
    
    print("{} Finished!".format(datetime.datetime.now().strftime("%d/%m %H:%M")))