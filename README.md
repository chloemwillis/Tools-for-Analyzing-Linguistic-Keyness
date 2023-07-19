# Tools for Analyzing Linguistic Keyness (TALK)

Tools for Analyzing Linguistic Keyness or TALK is a public repository that contains a codebase for harvesting and analyzing language-based Twitter data using keyness analysis. 

Keyness analysis is a statistical method used to identify words that characterize a study corpus relative to a reference corpus ([Baker 2004](https://journals.sagepub.com/doi/10.1177/0075424204269894); [Egbert & Biber 2019](https://www.euppublishing.com/doi/10.3366/cor.2019.0162); [Gabrielatos 2018](https://www.taylorfrancis.com/chapters/edit/10.4324/9781315179346-11/keyness-analysis-costas-gabrielatos?context=ubx&refId=c6b7218d-1181-4496-9950-c0585419a626); [Gries 2021](https://ricl.aelinco.es/index.php/ricl/article/view/150); [Rayson & Potts 2021](https://link.springer.com/chapter/10.1007/978-3-030-46216-1_6)). As such, a portion of this codebase is concerned with collecting, processing, and filtering Twitter data to form study and reference corpora. However, you do not need to work with Twitter data to use these code files; parts of the codebase (e.g. filtering.ipynb; keyness.py) are applicable to other use cases as well. Regardless of where your data comes from, we recommend reading through the Steps section below to understand the pipeline and procedure this repository is designed for.

This codebase was developed in the process of doing research on how people talk about bisexuality on Twitter. Therefore, some of the code reflects what we needed for our use case (e.g. stopwords.txt), but these files are easily modified to fit your needs. The research project is still ongoing, so we will continue to update this repository as we write. We'll link our first paper on the subject soon-- stay tuned!

We intend for this repository to be accessible to researchers regardless of technical background, i.e. we want our code to be easy to use for everyone. To that end, we focus on writing doc strings and comments with as little jargon as possible. 

## API authorization

Users must be authorized to interact with Twitter's API. You'll need to have a developer account and create an app to get your own API token. Apply for API access through the [Twitter Development website](https://developer.twitter.com/en) to get your API access keys and create your own app.

## Necessary tools

Some of the code in this repository draws on the [NSFW Detection Machine Learning Model](https://github.com/GantMan/nsfw_model) and [Tweetbotornot](https://github.com/mkearney/tweetbotornot). You will need to install these tools from their respective GitHub repositories to classify images ([NSFW Detection Machine Learning Model](https://github.com/GantMan/nsfw_model)) and to classify users as bots ([Tweetbotornot](https://github.com/mkearney/tweetbotornot)). 

## Procedure

Assuming you want to construct two corpora (a study and a reference) for a comparative analysis (e.g. keyness or keywords analysis), we recommend you proceed through the following steps to create matching corpora. Depending on your use case or research question, you may want to tweak or skip the steps involving filtering Tweets based on some criteria.

1. Configure your API settings
2. Configure your query (query_config.json) and search criteria (see study_terms.txt; study_exclusions.txt)
3. Harvest the Tweets for the study corpus (see harvest_tweets.py)
4. Harvest the Tweets for the reference corpus (see harvest_tweets.py)
4. Label Tweets for exclusion on the basis of user, nsfw images, or stopwords (see filtering.ipynb; classify_images.py; stopwords.txt; tweetbotornot.R)
5. Pair Tweets (see align_corpora.py)
8. Calculate keyness and measures of dispersion (see keyness.py)

There are some files in this repository that can be run separately. For example, extract_tweet.py is embedded in harvest_tweets.py, but can also be run separately to convert JSONs into CSVs. Whether a file can be run separately is written in the doc string at the top of the file.

## Calls 

Certain files in this codebase need to be run through the terminal. What you write in the terminal will typically look something like this:

<code>python filename.py input_filepath output_filepath --optional-args</code>

To find out what the arguments are and which ones are optional, go to the section of the .py file that starts with <code>if __name__ == "__main__"</code>. In the lines that follow, look at the first item in the parentheses after <code>parser.add_argument</code>. Optional arguments have two dashes <code>--</code> at the beginning. All other arguments are not optional. Look at the <code>type=</code> item in the parentheses to figure out whether the argument should be a string, an integer, or something else. Look at the <code>default=</code> item in the parentheses to figure out what the default value is for that argument. 

Below is a concrete example of what you might type into the terminal to run align_corpora.py:

<code>python align_corpora.py study_labeled.csv reference_labeled.csv paired.csv --label-hierarchy included tweet-excluded user-excluded</code>

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
