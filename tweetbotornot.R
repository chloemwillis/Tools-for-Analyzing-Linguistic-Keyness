# Authors: Simon Todd & Chloe Willis
# Date: November 2022

# This code uses the R package tweetbotornot2 (Kearney 2020) to: 
# (1) harvest timeline data for all users in your corpora
# (2) calculate a probability of whether the user is a bot based on their timeline data

# tweetbotornot2 requires an OLD version of rtweet (v0.7.0). 
# Use the following to install it:
# require(devtools)
# install_version("rtweet", version = "0.7.0", repos = "http://cran.us.r-project.org")

# To use rtweet, you need to authenticate it with your API keys.
# The code below assumes that you have used your API keys to create an authentication
# token, and then saved that token to file. To do this, enter the following code:
# token <- create_token(
#   app = "NAME_OF_YOUR_TWITTER_APP",
#   consumer_key = "COPY_YOUR_API_KEY_HERE",
#   consumer_secret = "COPY_YOUR_API_SECRET_KEY_HERE")
# saveRDS(token, "token.rds")

# Note: rtweet uses Twitter API v1.1, which appears to have had its ability to pull
# Tweets deprecated. Some of the features that tweetbotornot2 uses do not appear
# to be available through the Twitter API v2 (see the list of features in
# cols_and_types below). For this reason, combined with the current limitations
# imposed on Twitter for academic research, we have decided that it is not
# worthwhile to create a new interface for harvesting timeline data to provide
# input features to tweetbotornot2 using the Twarc2 interface to the Twitter v2 API.
# We will revisit this decision if academic Twitter access is restored.

# This code assumes that you have a CSV file of Tweets, as output by
# harvest_tweets.py, where usernames are in a column titled "user.username".
# The first part of this code extracts a vector of unique usernames;
# you can also separately form such a list yourself, and use the remainder of the
# code to get the timeline data and tweetbotornot ratings.

# Note that there is a rate limit on collecting timeline data.
# Read more about the rate limit and tweetbotornot2 in general here:
# https://github.com/mkearney/tweetbotornot2

# This code generates a lot of files, which will be stored in subdirectories
# "feature_chunks" and "timeline_chunks" within the output directory you designate

library(tidyverse)
library(rtweet)
library(tweetbotornot2)
library(data.table)

# Enter your desired output directory on the next line
output_directory = "."
# Enter the desired name of the output file CSV on the next line
output_name = "user_probs.csv"
# Enter the paths to your Tweet CSV files on the next line
input_paths = list("study.csv", "reference.csv")
# Enter the path to your API authentication token on the next line
token = readRDS("token.rds")

# This part of the code limits how many batches/users are processed at a time
# This is important for managing the rate limit
batch_process_size = 500
user_chunk_size = 100

# Create output subdirectories if they don't exist
dir.create(paste0(output_directory, "/feature_chunks"), recursive=TRUE, showWarnings=FALSE)
dir.create(paste0(output_directory, "/timeline_chunks"), recursive=TRUE, showWarnings=FALSE)

# Get the unique users
users = map_dfr(input_paths, read_csv) %>%
    pull(user.username) %>% 
    distinct()

# Column types to make saving/loading files of timeline data seamless
cols_and_types <- list(user_id="c",
                       screen_name="c",
                       account_created_at="T",
                       text="c",
                       created_at="T",
                       display_text_width="d",
                       profile_background_url="c",
                       profile_banner_url="c",
                       profile_expanded_url="c",
                       place_full_name="c",
                       reply_to_status_id="c",
                       media_type="c",
                       hashtags="c",
                       urls_expanded_url="c",
                       media_expanded_url="c",
                       ext_media_expanded_url="c",
                       mentions_user_id="c",
                       source="c",
                       profile_image_url="c",
                       lang="c",
                       is_retweet="l",
                       is_quote="l",
                       statuses_count="i",
                       followers_count="i",
                       friends_count="i",
                       favourites_count="i",
                       verified="l"
)

# Break users into chunks, to manage rate limit
users <- chunk_users(users, n=user_chunk_size)

# Resume from point of failure
start_chunk = suppressWarnings(
  max(as.numeric(str_extract(list.files(paste0(output_directory, "/feature_chunks")), "\\d+")))
)

# Print start message
cat(sprintf("%s: Starting timeline search and feature extraction \n", format(Sys.time(), "%b %e %H:%M")))

for (i in seq_along(users)) {
  ## if resuming, catch up
  if (i <= start_chunk) {
    next
  }
  
  ## set oops counter
  oops <- 0L
  
  ## check rate limit- if fewer calls remain than are required for a chunk, sleep until reset
  rl <- rtweet::rate_limit(query = "get_timelines", token=rtweet::bearer_token(token))
  while (rl[["remaining"]] < user_chunk_size) {
    ## prevent infinite loop
    oops <- oops + 1L
    if (oops > 3L) {
      stop("rate_limit() isn't returning rate limit data", call. = FALSE)
    }
    cat(sprintf("%s: Hit rate limit on chunk %d / %d; Sleeping for %.1f minutes... \n", format(Sys.time(), "%b %e %H:%M"), i, length(users), round(max(as.numeric(rl[["reset"]], "mins"), 0.5) + 7, 1)))
    Sys.sleep(max(as.numeric(rl[["reset"]], "secs"), 30) + 7*60) # add 7 minutes, for max 100k requests/day
    rl <- rtweet::rate_limit(query = "get_timelines", token=rtweet::bearer_token(token))
  }
  
  ## get user timeline data
  timelines <- suppressWarnings(rtweet::get_timelines(users[[i]], n=200, check=FALSE, token=rtweet::bearer_token(token)))
  
  # trim timeline data to only include required columns
  timelines = timelines[, names(cols_and_types)]
  
  # save timeline chunk
  write_csv(rtweet::flatten(timelines), paste0(output_directory, "/timeline_chunks/timelines_", i, ".csv"), na="")
  
  # extract features
  features = preprocess_bot(timelines, batch_size=batch_process_size)
  
  # save feature chunk
  save(features, file=paste0(output_directory, "/feature_chunks/features_", i, ".Rdata"), compress=FALSE)
  
  # print iteration update
  # if (i %% 100 == 0) {
  #   cat(sprintf("%s: Finished chunk %d / %d \n", format(Sys.time(), "%b %e %H:%M"), i, length(timelines)))
  # }
}

cat(sprintf("%s: Finished timeline search and feature extraction;  now running model \n", format(Sys.time())))

## load feature tables and merge into a single table
load(paste0(output_directory, "/feature_chunks/features_1.Rdata"))
final_feature = suppressWarnings(
  max(as.numeric(str_extract(list.files(paste0(output_directory, "/feature_chunks")), "\\d+")))
)
all_features = features
for (i in 2:final_feature) {
  load(paste0(output_directory, "/feature_chunks/features_", i, ".Rdata"))
  all_features = rbind(all_features, features)
}
# set required attribute for predict_bot
data.table::setattr(all_features, ".ogusrs", all_features$user_id)

# find probabilities
probs = suppressWarnings(predict_bot(all_features, batch_size=batch_process_size))
write_csv(probs, paste0(output_directory, "/", output_name), na="")
