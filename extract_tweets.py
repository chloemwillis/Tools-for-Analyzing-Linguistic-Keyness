"""
===============================================================================
EXTRACT_TWEETS.PY
Authors: Simon Todd & Chloe Willis
Date: July 2023

This code extracts Tweets and metadata from JSONL to CSV format. It is incorporated
within harvest_tweets.py, so it does not have to be used directly unless you decide
to extract additional fields after harvesting.

Note: for media, URLs, etc., this code only extracts the FIRST instance in a
Tweet to CSV (since CSV format is not designed for nested cells).
===============================================================================
"""

import json
import csv
import argparse

def jsonl_to_csv(in_path, out_path, fields=None, renamings=None):
    """Converts a provided .jsonl of tweets to a CSV file at a provided path,
    extracting the designated fields.
    
    Arguments
    ---------
    in_path: str; path to the input .jsonl (or .json) file
    out_path: str; path to the output .csv file
    fields: list(str); list of field names to extract
    """
    with open(in_path, encoding="utf-8") as in_file:
        convert_to_csv(in_file, out_path, fields=fields, renamings=renamings)

        
def convert_to_csv(results_iter, out_path, fields=None, renamings=None):
    """Converts a provided iterator of search results to a CSV file at a provided path,
    extracting the designated fields.
    
    Arguments
    ---------
    results_iter: iter(dict); iterator over tweet search results pages, each formatted
                  as a dict
    out_path: str; path to the output .csv file
    fields: list(str); list of field names to extract
    renamings: dict(str, str); dictionary mapping from field names to column headings,
               to rename the extracted fields
    """
    # Fill in default values of fields
    # Fields that are about the tweet start with tweet.,
    # fields that are about the user start with user.,
    # fields that are about the place from which the tweet was posted start with tweet.place_,
    # fields that are about the tweet to which this tweet is a reply start with reply.,
    # fields that are about the FIRST media item in the tweet start with tweet.media_,
    if fields is None:
        fields = [
        "tweet.id",
        "tweet.text",
        "tweet.created_at",
        "tweet.lang",
        "tweet.retweet_count",
        "tweet.reply_count",
        "tweet.like_count",
        "tweet.quote_count",
        "tweet.place_id",
        "tweet.place_type",
        "tweet.place_full_name",
        "tweet.media_key",
        "tweet.media_type",
        "tweet.media_url",
        "tweet.media_alt_text",
        "tweet.media_view_count",
        "tweet.contains_url",
        "tweet.reply_type",
        "reply.id",
        "reply.text",
        "reply.author_id",
        "user.id",
        "user.username",
        "user.name",
        "user.location",
        "user.description",
        "user.created_at",
        "user.followers_count",
        "user.following_count",
        "user.tweet_count"
        ]
           
    with open(out_path, "w", encoding="utf-8", newline='') as out_file:
        writer = csv.writer(out_file)
        if renamings is None:
            writer.writerow(fields)
        else:
            renamed_fields = [renamings.get(field, field) for field in fields]
            writer.writerow(renamed_fields)
        for results_page in results_iter:
            if isinstance(results_page, str):
                results_page = json.loads(results_page.strip())
            for row in parse_page(results_page, fields):
                if renamings is not None:
                    row = rename_fields(row, renamings)
                writer.writerow(row)


def rename_fields(row, renamings):
    """Rename the keys of a dictionary.
    
    Arguments
    ---------
    row: dict; the dictionary whose keys are to be renamed.
    renamings: dict(str, str); a map from old names to new names.
    """
    return dict((renamings.get(key, key), value) for (key, value) in row)


def parse_page(page, fields):
    """Parse a page of results by extracting the required fields, and yields
    rows to be written to CSV, one at a time.
    
    Arguments
    ---------
    page: a JSON output of the Twitter API v2
    fields: list(str); list of field names to extract
    
    Yields
    ------
    row: list(str); a row to be written to CSV, where fields are in the order
         given in fields
    """    
    # Extract reverse lookups
    user_lookup = make_reverse_lookup(page["includes"]["users"], "user.", fields)
    place_lookup = dict()
    if "places" in page["includes"]:
        place_lookup = make_reverse_lookup(page["includes"]["places"], "tweet.place_", fields)
    reply_lookup = dict()
    if "tweets" in page["includes"]:
        reply_lookup = make_reverse_lookup(page["includes"]["tweets"], "reply.", fields)
    media_lookup = dict()
    if "media" in page["includes"]:
        media_lookup = make_reverse_lookup(page["includes"]["media"], "tweet.media_", fields)
    
    rows = list()
    for tweet in page["data"]:
        row = extract_fields(tweet, fields, user_lookup, place_lookup, reply_lookup, media_lookup)
        yield row


def extract_fields(tweet, fields, user_lookup, place_lookup, reply_lookup, media_lookup):
    """Extracts the required fields from a single tweet and returns a row to
    be written to CSV.
    
    Arguments
    ---------
    tweet: dict(str, dict/str); a dictionary representation of a Tweet object
           from the Twitter API v2
    fields: list(str); list of field names to extract
    user_lookup: dict(str, dict(str, str)); a dictionary that maps from user IDs
                 to all the fields that are relevant for that user
    place_lookup: dict(str, dict(str, str)); a dictionary that maps from place IDs
                  to all the fields that are relevant for that place
    reply_lookup: dict(str, dict(str, str)); a dictionary that maps from reply IDs
                  to all the fields that are relevant for that reply
    media_lookup: dict(str, dict(str, str)); a dictionary that maps from media keys
                  to all the fields that are relevant for that media
    
    Returns
    -------
    row: list(str); a row to be written to CSV, where fields are in the order
         given in fields
    """
    # Prepick the user and place dictionaries
    user_info = user_lookup[tweet["author_id"]]
    place_info = dict()
    try:
        place_info = place_lookup[tweet["geo"]["place_id"]]
    except KeyError:
        pass
    
    # Special check for whether this is a reply,
    # and load reply dictionary if so
    reply_type = None
    reply_info = {field: None for field in fields if field.startswith("reply.")}
    if "referenced_tweets" in tweet:
        reply_type = tweet["referenced_tweets"][0]["type"]
        try:
            reply_info = reply_lookup[tweet["referenced_tweets"][0]["id"]]
        except KeyError:
            pass
        
    # Check for whether there are media, and load media dictionary if so
    media_info = {field: None for field in fields if field.startswith("tweet.media_")}
    if "attachments" in tweet and "media_keys" in tweet["attachments"]:
        media_info = media_lookup[tweet["attachments"]["media_keys"][0]]
        
    # Check if the tweet contains any urls
    contains_url = None
    expanded_url = None
    if "entities" in tweet and "urls" in tweet["entities"]:
        contains_url = True
        expanded_url = tweet["entities"]["urls"][0].get("expanded_url")
    
    row = list()
    for field in fields:
        if field.startswith("user."):
            row.append(user_info.get(field))
        elif field.startswith("tweet.place_"):
            row.append(place_info.get(field))
        elif field.startswith("tweet.media_"):
            row.append(media_info.get(field))
        elif field.startswith("reply."):
            row.append(reply_info.get(field))
        elif field == "tweet.reply_type":
            row.append(reply_type)
        elif field == "tweet.contains_url":
            row.append(contains_url)
        elif field == "tweet.expanded_url":
            row.append(expanded_url)
        elif field.startswith("tweet."):
            field = field[6:]
            if field in tweet:
                row.append(tweet[field])
            elif field in tweet["public_metrics"]:
                row.append(tweet["public_metrics"][field])
            else:
                raise Exception('Unrecognized field: {}'.format(field))
        else:
            raise Exception('Unrecognized field: {}'.format(field))
            
    return row
    

def make_reverse_lookup(entries, prefix, fields):
    """Creates a dictionary that can be used to look up entries by ID and get
    back a dictionary filtered to the relevant fields.
    
    Arguments
    ---------
    entries: list(dict); a list of entries, where each entry is a dictionary that
             at least has the key "id"
    prefix: str; a prefix to identify which fields in the provided list are to be
            included in the results
    fields: list(str); a list of fields to be extracted, only those of which with
            the designated prefix are relevant for these entries
    
    Returns
    -------
    entry_dict: id -> entry; a dictionary that maps from the "id" value to the
                remaining designated fields of an entry
    """
    relevant_fields = [field[len(prefix):] for field in fields if field.startswith(prefix)]
    
    entry_dict = {field: None for field in fields if field.startswith(prefix)}
    for entry in entries:
        relevant_entry = dict()
        for (key, value) in entry.items():
            if key in relevant_fields:
                relevant_entry[prefix + key] = value
            elif key == "place_type" and "type" in relevant_fields:
                relevant_entry[prefix + "type"] = value
            elif key == "media_key" and "key" in relevant_fields:
                relevant_entry[prefix + "key"] = value
            elif "expanded_url" in relevant_fields and key == "entities" and "url" in value:
                relevant_entry[prefix + "expanded_url"] = value["url"]["urls"][0].get("expanded_url")
        if "public_metrics" in entry:
            for (key, value) in entry["public_metrics"].items():
                if key in relevant_fields:
                    relevant_entry[prefix + key] = value
        if "media_key" in entry:
            entry_dict[entry["media_key"]] = relevant_entry
        else:
            entry_dict[entry["id"]] = relevant_entry
        
    return entry_dict


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description = "Extract tweets from JSONL to CSV format")
    parser.add_argument("in_path", metavar="INPUT", type=str, help="Path to the input .jsonl file")
    parser.add_argument("out_path", metavar="OUTPUT", type=str, help="Path to the output .csv file")
    parser.add_argument("--fields", type=str, nargs="+", help="Fields to extract.")
    args = parser.parse_args()
    
    jsonl_to_csv(args.in_path, args.out_path, args.fields)
