# Tools for Analyzing Linguistic Keyness (TALK)

Tools for Analyzing Linguistic Keyness or TALK is a public repository that contains a codebase for harvesting and analyzing language-based Twitter data using keyness analysis. 

Keyness analysis is a statistical method used to identify words that characterize a study corpus relative to a reference corpus ([Baker 2004](https://journals.sagepub.com/doi/10.1177/0075424204269894); [Egbert & Biber 2019](https://www.euppublishing.com/doi/10.3366/cor.2019.0162); [Gabrielatos 2018](https://www.taylorfrancis.com/chapters/edit/10.4324/9781315179346-11/keyness-analysis-costas-gabrielatos?context=ubx&refId=c6b7218d-1181-4496-9950-c0585419a626); [Gries 2021](https://ricl.aelinco.es/index.php/ricl/article/view/150); [Rayson & Potts 2021](https://link.springer.com/chapter/10.1007/978-3-030-46216-1_6)). As such, a portion of this codebase is concerned with collecting, processing, and filtering Twitter data to form study and reference corpora. However, you do not need to work with Twitter data to use these code files; the general approach taken here can also be taken for data from any source, and the calculation of keyness (in `keyness.py`) can be directly applied to any CSV file that pairs study and reference texts in the designated format. Regardless of where your data comes from, we recommend reading through the Procedure and Detailed Steps sections below to understand the pipeline and procedure this repository is designed for.

This codebase was developed in the process of doing research on how people talk about bisexuality on Twitter. Therefore, some of the code reflects what we needed for our use case (e.g. `stopwords.txt`), but these files are easily modified to fit your needs. The research project is still ongoing, so we will continue to update this repository as we write. We'll link our first paper on the subject soon -- stay tuned!

We intend for this repository to be accessible to researchers regardless of technical background, i.e. we want our code to be easy to use for everyone. To that end, we focus on writing doc strings and comments with as little jargon as possible. 

## API authorization

Users must be authorized to interact with Twitter's API. You'll need to have a developer account and create an app to get your own API token. Apply for API access through the [Twitter Development website](https://developer.twitter.com/en) to get your API access keys and create your own app.

## Necessary tools

Some of the code in this repository draws on the [NSFW Detection Machine Learning Model](https://github.com/GantMan/nsfw_model) and [Tweetbotornot](https://github.com/mkearney/tweetbotornot). You will need to install these tools from their respective GitHub repositories to classify images ([NSFW Detection Machine Learning Model](https://github.com/GantMan/nsfw_model)) and to classify users as bots ([Tweetbotornot](https://github.com/mkearney/tweetbotornot)). 

## Procedure

Assuming you want to construct two corpora (a study and a reference) for a comparative analysis (e.g. keyness or keywords analysis), we recommend you proceed through the following steps to create matching corpora. Depending on your use case or research question, you may want to tweak or skip the steps involving filtering Tweets based on some criteria.

1. Configure your API settings, and create a `keys.json` file that stores your credentials  
2. Configure your query (`query_config.json`) and search criteria (`study_terms.txt`; `study_exclusions.txt`)  
3. Harvest the Tweets for the study corpus (`harvest_tweets.py`)  
4. Harvest the Tweets for the reference corpus (`harvest_tweets.py`)  
5. Label Tweets for exclusion, using your own criteria; this is a flexible process, but we have included several examples of exclusion criteria, and ways to convert those criteria into labels, in `filtering.ipynb`  
6. Pair Tweets across the study and reference corpora (`align_corpora.py`)  
7. Calculate keyness (`keyness.py`)  

There are some files in this repository that are incorporated into other files used in the pipeline above, but can also be run separately:  
- `count_timebins.py` is used to bin Tweets by time posted, and count the number of Tweets per bin; it is necessary to bin and count the study Tweets in this way, in order to know the criteria for harvesting reference Tweets. This code is embedded in `harvest_tweets.py`, but can also be run separately, for example if you need to redefine the timebins that you originally defined when harvesting your study Tweets.  
- `count_tweet_words.py` is used to normalize Tweets and extract individual words for counting. It is used in `keyness.py`, but can also be useful in the filtering process. to identify common words in the study corpus that seem to be drawn from a different domain than you intend (see `filtering.ipynb`).  
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

### Step 1: Configure your API settings

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

We recommend having this JSON file open while you complete the next step so you can easily copy-paste everything to configure <code>twarc2</code>. 

### Step 2: Install and configure twarc2

[Twarc2](https://twarc-project.readthedocs.io/en/latest/twarc2_en_us/#configure) is a Python library for archiving Twitter JSON data that is key to our codebase. Assuming you already have Python 3 installed (if not, click [here](https://www.python.org/downloads/)), you can install <code>twarc2</code> from the terminal using [pip](https://pip.pypa.io/en/stable/installation/) install: 

<code>pip install --upgrade twarc</code>

Mac users can also install <code>twarc</code> using [Homebrew](https://brew.sh/):

<code>brew install twarc</code>

Next you need to tell twarc what your API access credentials are and grant it access to to your App. Type <code>twarc2 configure</code> into the terminal and follow the prompts. First, it will ask for your Bearer Token. Then it will ask you `Add API keys and secrets for user mode authentication [y or n]?` -- type <code>y</code> into the terminal. Then enter your API Key and API Secret. Finally it will ask you whether you'd like to obtain your user keys by (1) generating access keys by visiting Twitter or (2) manually entering your access token and secret. Type <code>2</code> into the terminal and enter your Access Token and Access Token Secret. Now you're almost ready to start harvesting Tweets! First you will need to configure your query and search criteria.

### Step 3: Configure your query and search criteria

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

### Step 4: Harvest the Tweets for the study corpus

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

### Step 5: Harvest the Tweets for the reference corpus

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

### Step 6: Label Tweets for exclusion

Tweets in each corpus can optionally be given a *label* that assigns them to a group. When pairing Tweets across corpora, members of a pair will be from the same group wherever possible. The calculation of keyness scores can be restricted to Tweets from particular groups. In this way, labelling can be used to filter the data, at levels of a filtering hierarchy.

The notebook `filtering.ipynb` illustrates how labelling for user- and Tweet-based filtering might work.

If you want to label Tweets, you can do so by adding a `label` column to the Tweet CSVs, and entering the labels for each Tweet in that column. In our `filtering.ipynb` file, the labeled CSVs are saved as `study_labeled.csv` and `reference_labeled.csv`.

Labelling is not required; you can proceed with the analysis with unlabelled Tweet CSVs.

### Step 7: Pair Tweets across the study and reference corpora

Once the study and reference Tweets are harvested, they need to be paired with each other by timebin and (if labeled) group. This ensures that they are as comparable to each other as possible.

To pair Tweets across corpora, use the file `align_corpora.py`. With unlabeled data, this would look something like:

```
python align_corpora.py study.csv reference.csv paired.csv --unlabeled [OPTIONAL-ARGS]
```

In this case, the only *optional args* that may be of interest are those that relate to the definition of timebins; if the timebins were changed from the default (1 hour) when harvesting the reference Tweets, you should provide those same definitions here through the `--timebin-unit` and `--timebin-interval` arguments. For full details, see `python align_corpora.py --help`.

With labeled data, it would look something like:

```
python align_corpora.py study_labeled.csv reference_labeled.csv paired.csv [OPTIONAL-ARGS]
```

In this case, *optional args* of interest include the following:  
- `--label-column LABEL`; the name of the column where Tweet labels are stored (defaults to `label`)  
- `--label-hierarchy STRICTEST_LABEL LESS_STRICT_LABEL EVEN_LESS_STRICT_LABEL...`; if surplus reference Tweets from one group are allowed to backfill for another in case there aren't enough reference Tweets in that group, this argument specifies the hierarchy through which this backfilling is explored: Tweets with a stricter label are allowed to backfill for Tweets with a less strict label, but not vice versa. For example, our analysis assigns labels based on the level at which Tweets would be filtered out: `user-excluded` Tweets would be filtered out at the first level of filtering, `tweet-excluded` Tweets would be filtered out at the second level of filtering, and `included` Tweets would be retained through all levels of filtering; this means that the `included` label is the strictest one to apply, `tweet-excluded` is less strict, and `user-excluded` is the least strict. By providing the argument `--label-hierarchy included tweet-excluded user-excluded`, we pair `included` Tweets that survive all levels of filtering first, and if there are leftover reference Tweets, we allow them to be considered as backfill for pairing with `tweet-excluded` study Tweets that would be filtered out at the second level of filtering if there are not enough `tweet-excluded` reference Tweets. If Tweets are labeled into groups but the `--label-hierarchy` argument is not provided, no backfilling is permitted: study Tweets can *only* be paired with reference Tweets with the same label. This means that, if there aren't enough reference Tweets, some of the study Tweets are omitted from the paired dataset.

The output of `align_corpora.py` is a CSV file that combines all the information from the study and reference CSVs. The columns are copied from each file, with prefixes `study_` and `reference_` to designate the source of the information. Each row is no longer a single Tweet, but rather a *pair* of Tweets that are matched by timebin (and, if required, by label). A new `pair_id` column contains a unique ID for each pair of Tweets, and (if matching is conducted by group) a `label` column indicates which group the pair belongs to.

### Step 8: Calculate keyness

Once you have a CSV file that pairs each study Tweet with a reference Tweet, the file `keyness.py` can be used to calculate keyness scores for words in these corpora. Basic usage is as follows, assuming the input CSV file is `paired.csv`:

```
python keyness.py paired.csv keyness.csv [OPTIONAL-ARGS]
```

The following *optional args* can be used to adjust the data that is included in the keyness analysis:  
- `--keep-labels LABEL_1 LABEL_2...`; labels of Tweet pairs that are to be kept for inclusion in the calculation (if no labels are provided, all Tweets are kept). This can be used to perform keyness analysis with different groups of data filtered out; for example, with our labels, `--keep-labels included tweet-excluded` filters out Tweet pairs with the `user-excluded` label (yielding what we call the "user-filtered analysis"), while `--keep-labels included` also filters out Tweet pairs with the `tweet-excluded` label (yielding what we call the "tweet-filtered analysis").  
- `--exclude-terms-path STUDY_TERMS.TXT`; path to a file containing words that should not be included in the keyness analysis, such as the query terms that were originally used to harvest the Tweets (because they are each included in a lot of study Tweets but no reference Tweets, so will be highly key by definition). Each term to exclude should be written on a separate line of this file. Note that excluding terms from the analysis in this way is highly preferable to conducting the analysis with them included and then deleting their keyness scores, because it prevents their counts from influencing the keyness scores of other terms.

By default, the keyness analysis is conducted over the entire corpora. It can additionally be conducted over *bins* of the corpus, defined by time; for example, a separate keyness analysis can be conducted over the Tweets occuring in each month that the corpora span. The following additional *optional args* control aspects of this bin-based analysis:  
- `--use-bins`; provide this flag in order to conduct the keyness analysis over bins, as well as over the entire dataset  
- `--bin-time-unit UNIT`; the time unit over which bins are defined. Valid options are `days`, `weeks`, `months`, `years` (note the plural `s` on the end of each one!). Defaults to `months`  
- `--bin-time-interval NUMBER`; the number of time-units within each bin (defaults to `1`). For example, `--bin-time-interval 3` alongside `--bin-time-unit months` would conduct a keyness analysis for the data split into 3-month bins.  
- `--bin-formatting STRFTIME_CODE`; can be used to format the bin names as they appear in the resultant CSV file, using [strftime format codes](https://docs.python.org/3/library/datetime.html#strftime-and-strptime-format-codes); for example, `--bin-formatting %Y_%m` would create bins with names like `2023_05` (for May 2023; for longer bins, the name indicates the start of the bin). If this argument is not provided, bin names default to `bin_` followed by the timestamp of the start of the bin.  
- `--include-bin-counts`; if this flag is provided, in addition to conducting a keyness analysis across the overall corpora based on the frequency of each word, an analysis will also be conducted based on the *number* of bins within with each word occurs.

Since `keyness.py` is designed to work for any data that pairs text from a study corpus with text from a reference corpus, it has multiple options for specifying the format of the input data. See `python keyness.py --help` for more information.

The output CSV will have the following columns:  
- `word`  
- `keyness_g`: the keyness score of the word, with positive keyness scores indicating more-than-expected occurrences in the study corpus, and negative keyness scores indicating fewer-than-expected occurences in the study corpus  
- `study`: the count of the word in the study corpus  
- `reference`: the count of the word in the reference corpus  

If the analysis is conducted by time-based bins, there will be one copy of each of the `keyness_g`, `study`, and `reference` columns for each bin, prefixed by the bin name, and one for the overall corpora, prefixed by `overall_count`.

## Cite

DOI coming soon

## Contributors 

Simon Todd (he/him)
<br>
[GitHub](https://github.com/sjtodd) | [Personal Website](https://sjtodd.github.io/) 

& 

Chloe Willis (she/they)
<br>
[GitHub](https://github.com/chloemwillis) | [Personal Website](https://chloemwillis.com/)
