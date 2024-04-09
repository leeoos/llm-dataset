#!/usr/bin/env python

"""TASK 24 - SENTIPOLC 

This script is designed to convert a sentiment classification dataset from http://www.di.unito.it/~tutreeb/sentipolc-evalita16/index.html into a QA dataset suitable for training Large Language Models (LLMs)."""

# general imports 
import os
import sys
import shutil
import argparse

# online resources
import wget
import zipfile

# data manipulations
import re 
import csv
import json
import jsonlines
import pandas as pd

# FUNCTIONS

def progress_bar(current, total, width=80):
  """Plain progress bar to monitor download status"""

  progress_message = "Downloading: %d%% [%d / %d] bytes" % (current / total * 100, current, total)
  sys.stdout.write("\r" + progress_message)
  sys.stdout.flush()


def get_dat_from_url(data_url, data_out):
    """A function to download the dataset from given url"""

    if not os.path.exists(data_out):
      wget.download(url=data_url, out=data_out, bar=progress_bar)    
      print()

    print(f"Extracting {data_out}...")
    with zipfile.ZipFile(data_out, "r") as zip_ref:
      zip_ref.extractall("./data")
    
    # remove macos directory
    try:
      shutil.rmtree("./data/__MACOSX")
    except FileNotFoundError:
      pass


def move_data(data, dest="results"):
  """Just to move the final dtaset in the destination folder and once again avoid pushing large files."""

  os.makedirs(dest, exist_ok=True)
  for d in data:
    shutil.move(d, dest + "/" + d)
    print(f"Data: {d} moved to {dest}")


def check_quotes(data, FIXED_LEN=9, DEBUG=False):
  """ This function  check the presence of bad formatted double quotes inside the tweets """
  
  with open(data, newline='', encoding="utf-8") as csvfile:
      spamreader = csv.reader(csvfile, delimiter=',', quotechar='"')
      counter = 0

      # if a row contains more than the fixed number of columns 
      # then it means the quotes are bad fomatted
      for row in spamreader:
        if len(row) > FIXED_LEN:
          return True
      return False
  

def clean_text(string):
  """This function remove strange character and correct wierd formatting in the tweets e.g.:
  \\ ... some text ... \\ --> become a simple double quote "... some text..."
  long sequencies of ++ or ** (two or more) are removed
  """
  new_string = string.replace('\\\\', '"')
  new_string = new_string.replace('\\\"', '" ')
  first_quote_index = new_string.find('\"')
  if first_quote_index != -1: 
      # Split the text at the first occurrence of the double quote
      before_quote = new_string[:first_quote_index + 1]
      after_quote = new_string[first_quote_index + 1:]
      # Remove leading spaces from the part after the double quote
      after_quote = after_quote.lstrip(' ')
      new_string = before_quote + after_quote
  new_string = new_string.replace('""', '"')
  # new_string = re.sub(r'\*{2,}', '', new_string)  maybe to add maybe
  new_string = new_string.replace('‎', '',) #re.sub(r'‎', '', new_string)  
  return new_string


def format(data, FIXED_LEN=9, DEBUG=False) :
  """This function fixes the original csv dataset by removing extra quotes that messed up the standard column delimeters."""

  big_list = []
  with open(data, newline='', encoding="utf-8") as csvfile:
    spamreader = csv.reader(csvfile, delimiter=',', quotechar='|')
    counter = 0
    bad_formatted = 0

    for row in spamreader:
      counter += 1
      if len(row) > FIXED_LEN:
        # removing extra double quotes 
        new_row = [int(i.strip('"')) for i in row[:(FIXED_LEN -1)]]
        new_row.append(''.join(i for i in row[(FIXED_LEN - 1):])[1:-1])
        big_list.append(new_row)
        if DEBUG:
          print(f"before--> {len(row)}", end="-->")
          print(row)
          print(f"after --> {len(new_row)}", end="-->")
          print(new_row)

      else:
        # removing extra double quotes 
        new_row = [int(i.strip('"')) for i in row[:8]]
        new_row.append(row[8][1:-1])
        big_list.append(new_row)
        if DEBUG and "\\\\\\" in row:
          print(row)

  print(f"Len original data --> {counter}")
  print(f"Bad formatted samples --> {bad_formatted}")
  print(f"Len after manipulation --> {len(big_list)}")  
  return big_list


def check_consistency(data, FIXED_LEN=9):
  """This function is used to verify that for all the rows the number of columns is consistent."""

  for d in data:
    if len(d) > FIXED_LEN:
      print(f"First Bad sample --> {d}")
      return False
  return True


def make_dataframe(data):
  """This function will generate a pandas dataframe after checking (and correcting) the format of the provided csv."""

  columns=['idtwitter', 'subj', 'opos', 'oneg', 'iro', 'lpos', 'lneg', 'top', 'text']

  print(f"Dataset: {data}")
  to_correct = check_quotes(data, DEBUG=False)
  print(f"Contains bad formatted quotes --> {to_correct}") 
  if to_correct:
    data = format(data, DEBUG=False)
    if check_consistency(data):
      df = pd.DataFrame(data, columns=columns)
      print(df.head, end="\n")
      return df
  
    else:
      print(f"Error: the csv file {test_data} is bad formatted")
      return 1
  
  else:
    df = pd.read_csv(data)
    print(df.head, end="\n")
    return df


def df_to_jsonl(output_jsonl, pandas_df, TASK=1, DEBUG=False):
  """This is the main function used to generate the desired json dataset in output. This function produce a different output for each given sub-task in [1,2,3]."""

  with open(output_jsonl, "w",  encoding="utf-8") as jout:
    TOTAL_ROWS = len(pandas_df)
    DEBUG_COUNTER = 0
    ESCAPE_COUTER = 0 
    topics = ["generico", "politico", "socio politico"]

    for data in pandas_df.itertuples():
      if DEBUG:
        print(f"data index: {data.Index}")
        print(f"data idtwitter: {data.idtwitter}")
        print(f"data subj: {data.subj}")
        print(f"data opos: {data.opos}")
        print(f"data oneg: {data.oneg}")
        print(f"data iro: {data.iro}")
        print(f"data lpos: {data.lpos}")
        print(f"data lneg: {data.lneg}")
        print(f"data top: {data.top}")

      if TASK == 1:
        choices = ["oggettivo", "soggettivo"]
        label = 0 if data.subj == 0 else 1
      
      elif TASK == 2:
        choices = ["positivo", "negativo", "misto", "neutrale"]
        combos = {
          (1,0): 0,
          (0,1): 1,
          (1,1): 2,
          (0,0): 3
        }
        label = combos[(data.opos, data.oneg)]

      elif TASK == 3:
        choices = ["serio", "ironico"]
        label = 0 if data.iro == 0 else 1
            
      else:
        print(f"Wrong task: {TASK}")
        raise NameError
      
      cleaned_text = clean_text(data.text)


      if DEBUG and "\"" in data.text:
        print(data.text.replace("\"", "\\\""))
        print(cleaned_text)
        sequence = "\\"
        print(str(data.text).count(sequence))
        ESCAPE_COUTER += str(data.text).count(sequence)
      
      json_dict = {
        "id": data.idtwitter,
        "text": cleaned_text,
        "topic": topics[data.top],
        "choices":  choices,
        "label": label 
      }

      DEBUG_COUNTER += 1
      json_str = json.dumps(json_dict, ensure_ascii=False)

      if DEBUG_COUNTER < TOTAL_ROWS:  # If not the last row, add a newline character
        jout.write(json_str + '\n')
      else:  # For the last row, do not add a newline character
        jout.write(json_str)

      # if DEBUG and DEBUG_COUNTER > 10: 
      #   break

  print(f"Sub-task --> {TASK} \t Data dumped into jsonl --> {DEBUG_COUNTER}/{len(pandas_df)}")
  if DEBUG: 
    print("number of anomaly found: ", ESCAPE_COUTER)


# MAIN
if __name__ == '__main__' : 

  # set up command line args
  parser = argparse.ArgumentParser(description='Dataset Manipulation')
  parser.add_argument('--debug', '-d', action='store_true')
  args = parser.parse_args()
  DEBUG = args.debug 

  data_dir = "./data/"
  results_dir = "./results/"
  os.makedirs(data_dir, exist_ok=True)
  os.makedirs(results_dir, exist_ok=True)

  # clear previous results just to be sure
  try:
    shutil.rmtree(results_dir)
    print("Removed old results")
  except FileNotFoundError:
    pass

  # get train data
  train_data = data_dir + "training_set_sentipolc16.csv"
  if not os.path.exists(train_data):
    train_data_url = "http://www.di.unito.it/~tutreeb/sentipolc-evalita16/training_set_sentipolc16.csv.zip"
    train_data_out = "./data/sentipolc_train_data.zip"
    get_dat_from_url(train_data_url, train_data_out)

  else:
    print(f"Dataset: {train_data} already present")

  # get test data
  test_data = data_dir + "test_set_sentipolc16_gold2000.csv"
  if not os.path.exists(test_data):
    test_data_url = "http://www.di.unito.it/~tutreeb/sentipolc-evalita16/test_set_sentipolc16_gold2000.csv.zip"
    test_data_out = "./data/sentipolc_test_data.zip"
    get_dat_from_url(test_data_url, test_data_out)

  else:
    print(f"Dataset: {test_data} already present")

  # load data into dataframe
  train_df = make_dataframe(train_data)
  print("\n" + "-"*80 + "\n")
  test_df = make_dataframe(test_data)
  print()

  for sub_task in range(1, 4):
    train_output_jsonl = "sentipolc16_task" + str(sub_task) + "_train_data.jsonl"
    df_to_jsonl(train_output_jsonl, train_df, TASK=sub_task, DEBUG=DEBUG)
    test_output_jsonl = "sentipolc16_task" + str(sub_task) + "_test_data.jsonl"
    df_to_jsonl(test_output_jsonl, test_df, TASK=sub_task, DEBUG=DEBUG)
    move_data([train_output_jsonl, test_output_jsonl], "results")