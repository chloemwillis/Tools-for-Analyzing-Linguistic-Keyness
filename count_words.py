"""
===============================================================================
COUNT_WORDS.PY
Authors: Simon Todd & Chloe Willis
Date: February 2023

This code counts the number of words in an iter of entries (e.g., Tweets, posts,
articles, sentences, etc.). For the purposes of this counting, a 'word' is a
series of characters surrounded by whitespace. To ensure clean counts, the text
of each entry is normalized, i.e. punctuation is removed, strings of emoji are
separated and removed, and words are made lowercase. The output is a word
frequency dictionary that contains unique words and their counts. 
===============================================================================
"""

import csv
import emoji
import argparse
import re

def space_out_emoji(string):
    """Inserts whitespace around all emoji in a provided string."""
    return emoji.replace_emoji(string, replace=lambda chars, data_dict: " " + chars + " ")

def space_out_punctuation(string):
    """Inserts whitespace around punctuation in a provided string."""
    string = string.replace("&amp;", " & ")
    string = string.replace("&lt;", " <")
    string = string.replace("&gt;", " >")
    string = string.replace(",", ", ")
    string = string.replace("…", "… ")
    string = re.sub(r"\.{2,}", ". ", string)
    string = string.replace("b!tch", "b*tch")
    string = string.replace("sh!t", "sh*t")
    string = re.sub(r"!(?:1?!)*", "! ", string)
    string = string.replace("•", " •")
    string = string.replace("‘", " '")
    string = string.replace("n’t", "n't")
    string = re.sub(r"’(s|d|ll|re|ve|m|all)", r"'\1", string)
    string = string.replace("’", "' ")
    string = string.replace("“", "\"")
    string = string.replace("”", "\"")
    string = string.replace("\"", " \" ")
    string = string.replace("http", " http")
    string = re.sub(r"#+", " #", string)
    string = re.sub(r"\s+", " ", string)
    return string

def remove_emoji(string):
    """Removes all emoji from a provided string."""
    return emoji.replace_emoji(string, replace=" ")
        
def normalize(word, emoji_to_text=False, remove_links=True):
    """Normalizes a provided word by lowercasing and stripping edge
    punctuation (excluding left-aligned @ and #).
    If emoji_to_text is True, converts emoji to their text shortcuts.
    If remove_links is True, removes links from the text.
    """
    word = word.lower()
    word = word.strip(",.?/[]\\{}|=+-–—_()*^!~`>‘’'\"“”…•&")
    word = word.rstrip("@#<:;")
    if remove_links and word.startswith("http") or word.startswith("www"):
        word = word.replace(word, "")
    if word.startswith("<") and word != "<3":
        word = word.lstrip(",.?/[]\\{}|=+-—_()*^!~`<>:;‘’'\"“”…•&")
    if emoji_to_text and emoji.is_emoji(word):
        word = emoji.EMOJI_DATA[word]["en"]
    if ("/" in word or "?" in word) and not (word.startswith("http") or word.startswith("www") or "." in word):
        word = [normalize(subword) for subword in re.split(r"[/?]", word)]
    return(word)
    
def extract_words(string, include_emoji=True, emoji_to_text=False,
                 remove_links=True):
    """Extracts a list of normalized words from a provided string.
    If include_emoji is True, emoji are included in the list.
    If emoji_to_text is True, emoji are converted to text form.
    If remove_links is True, removes links from the text.
    """
    string = space_out_punctuation(string)
    # Either remove or space out emoji
    if include_emoji:
        string = space_out_emoji(string)
    else:
        string = remove_emoji(string)
    
    words = list()
    for word in string.split():
        word = normalize(word, emoji_to_text=emoji_to_text,
                        remove_links=remove_links)
        if isinstance(word, list):
            for subword in word:
                if subword:
                    words.append(subword)
        elif word:
            words.append(word)
            
    return words

def get_entries(in_path, column_name="text"):
    """Reads a CSV in which each row corresponds to an entry and yields a
    generator over the text for each entry, based on looking up the column
    with a given name.
    """
    with open(in_path, encoding="utf-8") as in_file:
        reader = csv.DictReader(in_file)
        for row in reader:
            yield row[column_name]

def count_words_in_entries(entries, **kwargs):
    """Returns a dictionary counting how often each word occurs in an iter
    of entries (strings).
    """
    counter = dict()
    for entry in entries:
        words = extract_words(entry, **kwargs)
        for word in words:
            counter[word] = counter.get(word, 0) + 1
    return counter

def dump_counts(counter, out_path, sort_by_count=True):
    """Saves counts to a tab-separated text file, format WORD \t COUNT.
    If sort_by_count is True, words are sorted first by count and then alphabetically;
    otherwise, words are sorted alphabetically (but not by count).
    """
    if sort_by_count:
        items = sorted(counter.items(), key=lambda pair: (-pair[1], pair[0]))
    else:
        items = sorted(counter.items())
        
    with open(out_path, "w", encoding="utf-8") as out_file:
        out_file.write("WORD\tCOUNT")
        for (word, count) in items:
            out_file.write("\n{}\t{}".format(word, count))

            
if __name__=="__main__":
    parser = argparse.ArgumentParser(description = "Count words from entries in CSV format")
    parser.add_argument("in_path", metavar="INPUT", type=str, help="Path to the input .csv file")
    parser.add_argument("out_path", metavar="OUTPUT", type=str, help="Path to the output file")
    parser.add_argument("--text-column", default="text", type=str, help="Name of column where entry text is stored")
    parser.add_argument("--no-emoji", dest="include_emoji", action="store_false", help="Exclude emoji from counts")
    parser.add_argument("--text-emoji", dest="emoji_to_text", action="store_true", help="Convert emoji to text")
    parser.add_argument("--sort-alpha", dest="sort_by_count", action="store_false", help="Sort words alphabetically (not by count)")
    parser.add_argument("--keep-links", dest="remove_links", action="store_false", help="Keep links in the text")
    args = parser.parse_args()
    
    entries = get_entries(args.in_path, column_name=args.text_column)
    counter = count_words_in_entries(entries, include_emoji=args.include_emoji, emoji_to_text=args.emoji_to_text,
                                     remove_links=args.remove_links)
    dump_counts(counter, args.out_path, sort_by_count=args.sort_by_count)
