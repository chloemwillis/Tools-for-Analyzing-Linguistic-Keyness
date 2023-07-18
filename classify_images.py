"""
===============================================================================
CLASSIFY_IMAGES.PY
Authors: Simon Todd & Chloe Willis
Date: August 2022

Adapted from https://github.com/GantMan/nsfw_model
Requires release 1.2.0 of the above to be installed; the path to the
mobilenet_v2_140_224 directory from that release must be provided as the
argument --saved-model-path

Our adaptation adds the ability to load images from URL, processes them
with a generator rather than a list for efficiency, and saves the output to file.
It is designed to work directly with a JSONL of Tweets harvested from Twitter, 
such that it will return a CSV file with the Tweet ID, image URL, and probabilities.
(Tweets without images, or Tweets for which the image is no longer accessible,
will not be included in this output file)

This code examines images from Tweets and classifies them as potentially NSFW.
It does so by generating a probability distribution for each image 
over five classes: drawings, hentai, neutral, porn, and sexy. 
===============================================================================
"""

import argparse
import json
import os

import numpy as np
import tensorflow as tf
from tensorflow import keras
import tensorflow_hub as hub

from PIL import Image
from urllib import request
from io import BytesIO
import csv
from collections import ChainMap
from datetime import datetime, timezone
from tzlocal import get_localzone

from extract_tweets import parse_page

IMAGE_DIM = 224   # required/default image dimensionality


def extract_images(tweet_filepaths):
    """Extracts the images from JSONL files containing Tweets,
    and returns a dictionary mapping from Tweet ID to image URL
    for Tweets that have images.
    
    Arguments
    ---------
    tweet_filepaths: list(str); list of paths to JSONL files containing Tweets
    """
    image_urls = dict()
    for tweet_filepath in tweet_filepaths:
        with open(tweet_filepath, encoding="utf-8") as tweet_results:
            for results_page in tweet_results:
                if isinstance(results_page, str):
                    results_page = json.loads(results_page.strip())
                for parsed_tweet in parse_page(results_page, ["tweet.id", "tweet.media_url"]):
                    if parsed_tweet["tweet.media_url"] is not None:
                        image_urls[parsed_tweet["tweet.id"]] = parsed_tweet["tweet.media_url"]
    return image_urls


def load_from_url(image_url, image_size):
    """Loads an image from URL"""
    
    res = request.urlopen(image_url).read()
    image = Image.open(BytesIO(res)).resize(image_size)
    
    return image


def load_images(image_urls, image_size, verbose=False, img_batch_size=3200, **kwargs):
    """Function for loading images into numpy arrays for passing to model.predict
    inputs:
        image_urls: dict mapping from Tweet ID to image URL
        image_size: size into which images should be resized
        verbose: show all of the image path and sizes loaded
        img_batch_size: number of images to load at once (for best efficiency, make multiple of 32)
    
    outputs: generators, split into batches:
        loaded_images: loaded images on which keras model can run predictions
        loaded_image_identifiers: Tweet IDs and image URLs for images which the function is able to process
    """
    required_shape = image_size + (3,)
    loaded_images = []
    loaded_image_paths = []
    batch_number = 1

    for (tweet_id, img_url) in image_urls:
        try:
            image = load_from_url(img_url, image_size)
            image = keras.preprocessing.image.img_to_array(image)
            assert image.shape == required_shape, "Image array has incorrect size: {}".format(image.shape)
            image /= 255
            if verbose:
                print("Loaded", img_url, "size:", image_size)
            
            loaded_images.append(image)
            loaded_image_identifiers.append((tweet_id, img_url))
            if len(loaded_images) == img_batch_size:
                yield (np.asarray(loaded_images), loaded_image_identifiers)
                print("{}: Completed batch {}".format(datetime.now(timezone.utc).astimezone(get_localzone()).strftime("%b %e %H:%M"), batch_number))
                loaded_images = []
                loaded_image_identifiers = []
                batch_number += 1
        
        except Exception as ex:
            if verbose:
                print("Image Load Failure: ", img_url, ex)
    
    if loaded_images:
        yield (np.asarray(loaded_images), loaded_image_identifiers)
        print("{}: Completed batch {}".format(datetime.now(timezone.utc).astimezone(get_localzone()).strftime("%b %e %H:%M"), batch_number))

def load_model(model_path):
    if model_path is None or not os.path.exists(model_path):
    	raise ValueError("saved_model_path must be the valid directory of a saved model to load.")
    
    model = tf.keras.models.load_model(model_path, custom_objects={'KerasLayer': hub.KerasLayer},compile=False)
    return model


def classify(model, tweet_image_urls, image_dim=IMAGE_DIM, verbose=False, **kwargs):
    """ Classify given a model, input dict mapping from tweet ID to image URL, and image dimensionality....
    Returns a generator that yields the output for a single image at a time, as a dictionary with keys
    tweet.id, tweet.media_url, p_drawing, p_hentai, p_neutral, p_porn, p_sexy
    """
    image_batches = load_images(tweet_image_urls, (image_dim, image_dim), **kwargs)
    for (images, image_identifiers) in image_batches:
        probs = classify_nd(model, images, **kwargs)
        for (image_properties, probs) in zip(image_identifiers, probs):
            (tweet_id, image_url) = image_properties
            row = dict(**probs)
            row["tweet.id"] = tweet_id
            row["image"] = image_url
            yield row


def classify_nd(model, nd_images, verbose=False, **kwargs):
    """ Classify given a model, image array (numpy)...."""

    model_preds = model.predict(nd_images, verbose=int(verbose))
    # preds = np.argsort(model_preds, axis = 1).tolist()
    
    categories = ['p_drawing', 'p_hentai', 'p_neutral', 'p_porn', 'p_sexy']

    probs = [dict(zip(categories, single_preds)) for single_preds in model_preds]
    return probs


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Classify images in Tweets")
    parser.add_argument('tweet_filepaths', type=str, nargs="+", 
                        help='The paths to JSONL files containing Tweets to classify. \
                              Provide multiple paths, separated by spaces.')
    parser.add_argument('--saved_model_path', dest='saved_model_path', type=str, required=True, 
                        help='The path to the mobilenet_v2_140_224 directory containing \
                              the model to load')
    parser.add_argument('--image_dim', dest='image_dim', type=int, default=IMAGE_DIM,
                        help="The square dimension of the model's input shape")
    parser.add_argument('--output', dest="out_path", type=str, default="image_probs.csv",
                        help="The path to a CSV file in which to save the results")
    parser.add_argument('--verbose', action="store_true", help="Print messages")
    parser.add_argument('--img_batch', type=int, default=3200, 
                        help="Number of images to load into memory at once")
    args = parser.parse_args()
    
    image_urls = extract_images(args.tweet_filepaths)
    model = load_model(args.model_path)
    
    print("{}: Starting".format(datetime.now(timezone.utc).astimezone(get_localzone()).strftime("%b %e %H:%M")))
    image_preds = classify(model, image_urls, args.image_dim, verbose=args.verbose)
    
    with open(args.output, "w", encoding="utf-8", newline="") as out_file:
        writer = csv.DictWriter(out_file, ["tweet.id", "image", 'p_drawing', 'p_hentai', 'p_neutral', 'p_porn', 'p_sexy'])
        writer.writeheader()
        writer.writerows(image_preds)
    
    print("{}: Finished".format(datetime.now(timezone.utc).astimezone(get_localzone()).strftime("%b %e %H:%M")))