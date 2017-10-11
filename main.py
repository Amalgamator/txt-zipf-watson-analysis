import sys
import os
import re
import json
import operator
import requests
from string import digits
from watson_developer_cloud import PersonalityInsightsV2 as PersonalityInsights 
from collections import Counter
from pymongo import MongoClient


c = MongoClient('localhost',27017)
# define the db name. Default = 'txtanalysis'
db = c.txtanalysis
# define the collection name to store the {author/zipf/watson} documents in. Default: 'corpii'
col = db.corpii


def analyze(text):
    # analyzing the text (a str) with Watson API
    pi_result = PersonalityInsights(username="insert_api_username", password="insert_api_pw").profile(text)
    return pi_result

def flatten(orig):
	# flatten the result from the Watson PI API. I'm sure there's a prettier way but I plain copied this out of laziness.
    data = {}
    for c in orig['tree']['children']:
        if 'children' in c:
            for c2 in c['children']:
                if 'children' in c2:
                    for c3 in c2['children']:
                        if 'children' in c3:
                            for c4 in c3['children']:
                                if (c4['category'] == 'personality'):
                                    data[c4['id']] = c4['percentage']
                                    if 'children' not in c3:
                                        if (c3['category'] == 'personality'):
                                            data[c3['id']] = c3['percentage']
    return data

def cleanup(str_to_clean):
    # remove numbers
    str_to_clean = str_to_clean.translate({ord(k): None for k in digits})
    
    # adapted from answer in https://stackoverflow.com/questions/6116978/python-replace-multiple-strings
    # replace non-word symbols (the ['] in can't stays, f.e.)
    rep = {"™":" ", # artifact from pdf to txt conversion
           "Š":" ", # artifact from pdf to txt conversion
           "€":" ", # artifact from pdf to txt conversion
           "\n":" ",
           "[":" ",
           "]":" ",
           "..":" ",
           "...":" ",
           "(":" ",
           ")":" ",
           ":":" ",
           ".":" ",
           "--":" ",
           "?":" ",
           ",":" ",
           "^":" ",
           "!":" ",
           "~":" ",
           "/":" ",
           "*":" ",
           " '":" ",
           "' ":" ",
           "`":"",
           "  ":" ",
           "$":" ",
           "\"":" ",
           ";":" ",
           "–":" ",
           "#":" ",
           "—":" "}
    # the replacement in one pass over the string!
    rep = dict((re.escape(k), v) for k, v in rep.items())
    pattern = re.compile("|".join(rep.keys()))
    cleaned_str = pattern.sub(lambda m: rep[re.escape(m.group(0))], str_to_clean)
    return cleaned_str

def zipfme(data, author):
    data = cleanup(data).lower()
    counter = Counter(data.split(' '))
    wdoc = json.loads(json.dumps(counter))
    doc = {}
    doc['author'] = author
    doc['words'] = wdoc
    doc = json.loads(json.dumps(doc))
    print("Inserting words...")
    col.insert(doc)

def watsonme(data, author):
    # analyze the author corpus
    result = analyze(file_text)
    # flatten the results received from the WatsonAPI
    flatresult = flatten(result)
    personality = json.loads(json.dumps(flatresult))
    print("Updating personality...")
    col.update({'author': author}, {'$set':{'personality': personality}})

rootdir = 'path_to_the_txt-files'

i = 0
for file in os.listdir(rootdir):
    # The files in my directory were named: Author - Title.txt (sometimes Number - Author - Title.txt)
    # Hence the following lines
    ext = str(file).split("-",1)
    exte = len(ext)
    if ".txt" in ext[exte-1]:
        i += 1
        author = ext[0].lower() # Remove differences in capitalization of author names.
        author = author.replace(" ","") # Remove irregular whitespace in and around author names.
        print(i, author)
        
        if i > 0: # define scope, start and or end of the file list in this conditional. you could make it a function too
            # Note that I always use the open() and close() method instead of 'with open as file', as the 'with open' statement caused memory issues!
            fileObj = open(rootdir+"/"+file,'r')
            file_text = fileObj.read()
            fileObj.close()
            
            print("Zipf's Law - Word frequency list generation...")
            zipfme(file_text, author)
            
            """ for live purposes
            try: # zipfme(file_text, author)
            except:
                error_log = open("-ZIPF-ERRORS.TXT", 'a')
                error_log.write(str(file) + '\n' + str(sys.exc_info()) + '\n')
                error_log.close()
            """
            
            print("WATSON API - Text personality analysis")
            watsonme(file_text, author)
            
            """ for live purposes
            try # watsonme(file_text, author)
            except:
                error_log = open("-WATSON-ERRORS.TXT", 'a')
                error_log.write(str(file) + '\n' + str(sys.exc_info()) + '\n')
                error_log.close()
            """

input("Press [ENTER] to exit.")
