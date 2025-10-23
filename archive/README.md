# Tools for Analyzing Linguistic Keyness (TALK): Archive

At the time that we developed our codebase, the Twitter (now X) API allowed researchers to harvest large volumes of Tweets for free. That is no longer the case, and we cannot guarantee that the code to harvest Tweets still works. This archive contains the harvesting code and its documentation.

This codebase was developed in the process of doing research on how people talk about bisexuality on Twitter. Some of the materials in this archived section reflect what we needed for our use case (e.g. `study_terms.txt`), but these files are easily modified to fit your needs. 

## Table of contents

1. [Contents of the archive](#contents-of-the-archive)  
2. [Necessary tools](#necessary-tools)  
3. [Overview](#overview)  
4. [Detailed steps](#detailed-steps)  
   1. [Configure your API settings](#configure-your-api-settings)  
   1. [Congfigure your query and search criteria](#configure-your-query-and-search-criteria)  
   2. [Harvest the Tweets for the study corpus](#harvest-the-tweets-for-the-study-corpus)  
   3. [Harvest the Tweets for the reference corpus](#harvest-the-tweets-for-the-reference-corpus)  


## Contents of the archive

The contents of this archive are as follows:  
- `classify_images.py`: code to load images from Tweets and classify them into 5 classes: *drawings*, *hentai*, *neutral*, *porn*, or *sexy*. The underlying model is from the [NSFW image classifier](https://github.com/GantMan/nsfw_model).  
- `extract_tweets.py`: code to extract Tweets and metadata from JSONL to CSV format. 
   > *Note: this code is incorporated within `harvest_tweets.py`, so it does not have to be used directly unless you decide to extract additional fields after harvesting.*  
- `filtering.ipynb`: Jupyter Notebook demonstrating various criteria we used to filter Tweets for our project exploring keywords associated with bisexuality-related hashtags. We use various methods to identify and filter out users that are likely to be bots, Tweets that are irrelevant or porn, and users who overwhelmingly post Tweets that are irrelevant or porn.  
- `harvest_tweets.py`: code to harvest Tweets using the Twitter API (no longer useable for general research purposes)  
- `query_config.json`: example config file template used for Tweet harvesting  
- `README.md`: this documentation file  
- `study_exclusions.txt`: terms that were used to exclude Tweets from being harvested in our study  
- `study_terms.txt`: terms that were used to harvest Tweets in our study  
- `tweetbotornot.R`: R script for scraping user timeline data from Twitter and using it to identify potential bots  

## Necessary tools

Users must be authorized to interact with Twitter's API. You'll need to have a developer account and create an app to get your own API token. Apply for API access through the [Twitter Development website](https://developer.twitter.com/en) to get your API access keys and create your own app.

Some of the code in this archive draws on the [NSFW Detection Machine Learning Model](https://github.com/GantMan/nsfw_model) and [Tweetbotornot](https://github.com/mkearney/tweetbotornot). You will need to install these tools from their respective GitHub repositories to classify images ([NSFW Detection Machine Learning Model](https://github.com/GantMan/nsfw_model)) and to classify users as bots ([Tweetbotornot](https://github.com/mkearney/tweetbotornot)). 

This archive also makes use of <code>twarc2</code>. [Twarc2](https://twarc-project.readthedocs.io/en/latest/twarc2_en_us/#configure) is a Python library for archiving Twitter JSON data. You don't need to manually configure <code>twarc2</code> with your API access credentials to use our codebase (assuming you follow the procedure outlined below), but you will need to if you want to use the full range of what <code>twarc2</code> has to offer. Assuming you already have Python 3 installed (if not, click [here](https://www.python.org/downloads/)), you can install <code>twarc2</code> from the terminal using [pip](https://pip.pypa.io/en/stable/installation/) install: 

<code>pip install --upgrade twarc</code>

Mac users can also install <code>twarc</code> using [Homebrew](https://brew.sh/):

<code>brew install twarc</code>

Next you need to tell twarc what your API access credentials are and grant it access to to your App. Type <code>twarc2 configure</code> into the terminal and follow the prompts. First, it will ask for your Bearer Token. Then it will ask you `Add API keys and secrets for user mode authentication [y or n]?` -- type <code>y</code> into the terminal. Then enter your API Key and API Secret. Finally it will ask you whether you'd like to obtain your user keys by (1) generating access keys by visiting Twitter or (2) manually entering your access token and secret. Type <code>2</code> into the terminal and enter your Access Token and Access Token Secret. Now you're ready to use <code>twarc2</code> independent of this codebase.

## Overview

Assuming you want to construct two corpora (a study and a reference) for a comparative analysis (e.g. keyness or keywords analysis), we recommend you proceed through the following steps to create matching corpora. Depending on your use case or research question, you may want to tweak or skip the steps involving filtering Tweets based on some criteria.

1. Configure your API settings, and create a `keys.json` file that stores your credentials  
2. Configure your query (`query_config.json`) and search criteria (`study_terms.txt`; `study_exclusions.txt`)  
3. Harvest the Tweets for the study corpus (`harvest_tweets.py`)  
4. Harvest the Tweets for the reference corpus (`harvest_tweets.py`)  
5. Label Tweets for exclusion, using your own criteria; this is a flexible process, but we have included several examples of exclusion criteria, and ways to convert those criteria into labels, in `filtering.ipynb`  

After completing these steps, you will have data that is appropriate for keyness analysis via the main codebase.

There are some files in this repository that are incorporated into other files used in the pipeline above, but can also be run separately:  
- `extract_tweets.py` is used to convert the JSONL files created when harvesting Tweets into CSV format. It is embedded in `harvest_tweets.py`, but can also be run separately to extract additional/different fields to CSV from Tweets you have already harvested.  

In addition, the files `tweetbotornot.R` and `classify_images.py` are intended to be used separately for specific kinds of filtering (respectively, identifying bots and detecting sexually explicit images).

## Detailed steps

The files in this codebase are designed to be run through the terminal. What you write in the terminal will typically look something like this:

```
python filename.py input_filepath output_filepath --optional-args
```

Below, we describe the calls for files listed in the steps above, specifying the important arguments. More information, including about additional arguments and default values, can be obtained by calling each file with the `--help` option, as in:

```
python filename.py --help
```

### Configure your API settings

First, you will need to [sign up for a Twitter developer account](https://developer.twitter.com/en/docs/twitter-api/getting-started/getting-access-to-the-twitter-api). You will need to have a Twitter account to sign up for a developer account. At the time of writing, there are [four levels](https://developer.twitter.com/en/docs/twitter-api/getting-started/about-twitter-api#v2-access-level) of API access (i.e. four types of developer accounts): Free, Basic, Pro, and Enterprise. For our project, we received Academic Access that allowed us to perform a full archive search of Twitter all the way back to 2006. Academic Access has since been deprecated and it is unclear if or when it will return. Full archive searches are now limited to Pro and Enterprise accounts.

During the sign-up process, you will create a Project and an associated developer App. A Project is like a container for an App that has a specific purpose. Once you have a developer app, you will be able to find or generate the following **credentials**: 

* API Key and Secret (aka Consumer Key and Secret): Essentially the username and password for your app
* Access Token and Secret: Credentials that represent requests made on behalf of the user who owns the App
* App only Access Token (aka Bearer Token): Credential used for making requests to endpoints that respond with information publically available on Twitter

**Don't lose these credentials.** Keep them secret, keep them safe. They are essential for making requests to harvest data from Twitter. 

Once you have set up your API access and located your credentials, you should save these credentials to a JSON file so that they can be read in by this codebase. You can create a JSON file using a plain text editor (like Notepad in Windows or TextEdit in Mac; not Microsoft Word or similar editors that let you change font, size, etc.). Create a new text file and save it in the directory of this codebase, with a filename like `keys.json`. The contents of the file should look as follows:

```
{
    "consumer_key": "PASTE YOUR CONSUMER KEY BETWEEN THESE QUOTATION MARKS",
    "consumer_secret": "PASTE YOUR CONSUMER SECRET KEY BETWEEN THESE QUOTATION MARKS",
    "access_token": "PASTE YOUR ACCESS TOKEN BETWEEN THESE QUOTATION MARKS",
    "access_token_secret": "PASTE YOUR ACCESS TOKEN SECRET KEY BETWEEN THESE QUOTATION MARKS",
    "bearer_token": "PASTE YOUR BEARER TOKEN BETWEEN THESE QUOTATION MARKS"
}
```

### Configure your query and search criteria

The file `query_config.json` contains the settings that will be applied to your searches for both the study and reference corpus. The settings used for our search are as follows:

```
{
  "query": "lang:en -is:retweet -is:quote",
  "expansions": "author_id,geo.place_id,referenced_tweets.id,referenced_tweets.id.author_id,attachments.media_keys",
  "user_fields": "created_at,description,id,location,name,protected,public_metrics,username",
  "place_fields": "full_name,id,country,geo,place_type",
  "tweet_fields": "id,text,attachments,author_id,conversation_id,created_at,entities,lang,public_metrics,referenced_tweets",
  "media_fields": "media_key,type,url,public_metrics,alt_text"
}
```

The `query` field in this file defines aspects that will be added to the query for all Twitter searches. In this case, it specifies the language (English) and excludes retweets and quotes. Any [standard query operators](https://developer.twitter.com/en/docs/twitter-api/tweets/search/integrate/build-a-query) for the Twitter API can be used here. Each search will also have its own terms it is looking for or avoiding, as described for `study_terms.txt` and `study_exclusions.txt` below.

The `expansions` field in this file designates the kinds of information that will be harvested in addition to the Tweets themselves. In our case, this includes information about the user who posted the Tweet, the location where they posted it from, any Tweets they reference and the authors of those Tweets, and media (e.g. images) that are attached to the Tweet. This set of expansions is fairly extensive: a keyness analysis does not *need* all (or perhaps even any!) of this information, but obtaining this information means it can be used for nuanced filtering (e.g. based on user characteristics or image properties) and detailed further analysis. See the [Twitter API documentation](https://developer.twitter.com/en/docs/twitter-api/expansions) for additional expansions that can be requested.

The `user_fields`, `place_fields`, `tweet_fields`, and `media_fields` fields in this file designate the specific details that will be harvested for each expansion. The fields listed here should cover the vast majority of analyses you might want to perform. See the [Twitter API documentation](https://developer.twitter.com/en/docs/twitter-api/fields) for information about these fields, and additional fields that can be requested.

The file `study_terms.txt` contains the query terms that will be used to search for the study Tweets, with one term per line. Each Tweet in the study corpus will be required to contain *at least one* of these terms. Search terms can be words, hashtags, emoji, etc. Multi-word search terms such as *happy birthday* can be used; just put *happy birthday* on its own line, with a space between the words. For our study, the search terms were the following hashtags:

```
#bi
#bipride
#bisexuality
#bisexualpride
#bisexuals
#bivisibilityday
#biweek
```

The file `study_exclusions.txt` contains terms that *must not* be included in any study Tweets, also written one per line. These can be used to narrow down searches by excluding unwanted domains; for example, we noticed that the term *#bi* was found in a lot of Tweets about Business Intelligence or the rapper B.I, so we manually curated a list of terms that were characteristic of such domains in an attempt to exclude them from our data. Our exclusions were as follows:

```
#powerbi
#businessintelligence
#businessanalytics
#analysis
#analytics
#microsoft
Microsoft
query
analytics
analysis
hanbin
#hanbin
@shxx131bi131
```


### Harvest the Tweets for the study corpus

To harvest study Tweets, use the `harvest_tweets.py` file. You'll write something like the following in the Terminal:

```
python harvest_tweets.py [OPTIONAL-CORE-ARGS] study study_terms.txt [OPTIONAL-STUDY-ARGS]
```

In this and all following Terminal code descriptions, square brackets [] indicate things that are *optional* and CAPITAL LETTERS indicate things that you should replace with appropriate values.

The *optional core args* let you change aspects of harvesting that are common to both the study and reference corpus. The arguments are as follows:  
- `--dir PATH/TO/DIRECTORY`; the path to the directory where the input files are located, and in which the output files will be created (defaults to the same directory as the script)  
- `--config QUERY_CONFIG.JSON`; the name of the query config file (defaults to `query_config.json`)  
- `--keys KEYS.JSON`; the name of the file containing your API authentication keys  
- `--csv-fields FIELD_1 FIELD_2 FIELD_3...`; the names of the fields you want to extract from the harvested Twitter data and save to CSV. Multiple fields can be provided, separated by spaces. The naming convention follows the field names from the [Twitter API documentation](https://developer.twitter.com/en/docs/twitter-api/fields), and are such that:  
    - fields that are about the Tweet start with `tweet.`,  
    - fields that are about the user start with `user.`,  
    - fields that are about the location start with `place.`,  
    - fields that are about the Tweet to which this Tweet is a reply start with `reply.`, and  
    - fields that are about media attached to the Tweet start with `tweet.media_`.  
  For example, the default fields are `tweet.id user.username tweet.created_at tweet.text`, which will extract a unique ID for the Tweet, the username of the author, the timestamp at which the Tweet was posted, and the Tweet text. 

After entering any optional core args that you want to have non-default values, the word `study` must be provided in order to tell the script that you will be harvesting study Tweets. Then, you must indicate the name of the file that contains the terms that will be used to identify study Tweets (`study_terms.txt`).

The *optional study args* are specific to harvesting study Tweets. Notable optional arguments are as follows:  
- `--exclude-terms STUDY_EXCLUSIONS.TXT`; the name of the file containing the terms that must not be included in any study Tweets (if you do not provide this argument, no terms will be excluded)  
- `--start-date YYYY-MM-DD`; the earliest date from which Tweets should be harvested (if you do not provide this argument, Tweets will only be harvested from the past 30 days)  
- `--end-date YYYY-MM-DD`; the latest date from which Tweets should be harvested; note this is EXCLUSIVE, so that e.g. `2023-06-01` harvests Tweets from *before* June 2023, but *not on June 1* (if you do not provide this argument, Tweets will be harvested up until the present day)  
- `--max-tweets NUMBER`; the maximum number of Tweets to harvest, which is based on your API access limitations. The default is 10000000 (10 million), which was previously the limit for academic access to the Twitter API; at present, limits are substantially lower  
- `--filename-stem STUDY`; the part that will go before `.jsonl` (raw Tweets data) and `.csv` (processed Tweet data) in the output files that are created (default is `study`)  

When harvesting the study Tweets, they are binned by hour by default, such that the same number of Tweets in each hour-bin is requested when harvesting the reference corpus. This binning creates a file `timebin_counts_study.json` (where `study` is replaced by whatever you may have entered for the `--filename-stem` argument). To change the definition of time bins while harvesting the study corpus, use the arguments `--timebin-unit` and `--timebin-interval` (see `python harvest.py study --help`). If you want to change the definition of time bins after harvesting the study corpus (but before harvesting the reference corpus), use `count_timebins.py`.  

The crucial output of harvesting study Tweets is a CSV file containing the Tweets (by default, `study.csv`)


### Harvest the Tweets for the reference corpus

To harvest reference Tweets, use `harvest_tweets.py` again, this time via a call like:

```
python harvest_tweets.py [OPTIONAL-CORE-ARGS] reference study_terms.txt [OPTIONAL-REFERENCE-ARGS]
```

The same *optional core args* should be used here as when harvesting the study Tweets.

The *optional reference args* are specific to harvesting reference Tweets. Notable optional arguments are as follows:  
- `--timebin-counts TIMEBIN_COUNTS_STUDY.JSON`; name of the file that contains the counts of study Tweets in each time bin (the default value, `timebin_counts_study.json`, will be fine as long as you didn't change `--filename-stem` when harvesting the study Tweets)  
- `--count-multiplier NUMBER`; a multiplier that indicates the scaling factor of the reference corpus relative to the study corpus; the default value of `1.25` means that 25% extra reference Tweets will be harvested in each time bin, in order to ensure that there are enough reference Tweets to pair with study Tweets after filtering  
- `--filename-stem REFERENCE`; the part that will go before `.jsonl` (raw Tweets data) and `.csv` (processed Tweet data) in the output files that are created (default is `reference`)  

The crucial output of harvesting reference Tweets is a CSV file containing the Tweets (by default, `reference.csv`)