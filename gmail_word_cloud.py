#!/usr/bin/env python3

from operator import itemgetter
import datetime
import imaplib
import getpass
import email
from wordcloud import WordCloud
import argparse
import re
from nltk.tokenize import word_tokenize, sent_tokenize
from nltk.corpus import stopwords
from collections import defaultdict
import numpy as np
import numpy.random
import matplotlib.pyplot as plt
from tqdm import tqdm

# process command line args
parser = argparse.ArgumentParser(description='Make wordcloud from sent emails content.')
parser.add_argument('--n', type=int, dest='n', default=10000,
                    help="Number of emails to retrieve.")
parser.add_argument('--from', action="append", dest='from_email', required=True,
                    help="Generate a word cloud only from this e-mail address")
parser.add_argument('--mailbox', dest='mailbox',
                    default='"[Gmail]/All Mail"', help='Specific different mailbox')
args = parser.parse_args()
assert args.n > 1

reply_line_regexp = re.compile(
    '(On ([A-Za-z]{3,12}(,)? )?(([A-Za-z]{3,12} [0-3]?[0-9](,)?)|([0-3]?[0-9] [A-Za-z]{3,12}(,)?)) 20[0-9][0-9])|(-{4,})|(\>+)|(From:)')

def get_first_text_block(email_message_instance):
    charset = email_message_instance.get_content_charset('iso-8859-1')
    maintype = email_message_instance.get_content_maintype()
    if maintype == 'multipart':
        text = None
        for part in email_message_instance.get_payload():
            if part.get_content_maintype() == 'text':
                text = part.get_payload(decode=True)
                break
        if text is None:
            return None
    elif maintype == 'text':
        text = email_message_instance.get_payload(decode=True)
    ret = re.split(reply_line_regexp, text.decode(charset, 'replace'))[0]
    return ret

# login
mail = imaplib.IMAP4_SSL('imap.gmail.com')
while True:
    usr = input("Enter username (usually your full email): ")
    pwd = getpass.getpass("Enter your password (use an app password if two-factor auth is enabled): ")
    try:
        mail.login(usr, pwd)
        break
    except:
        print("Unable to login under those credentials.")
        exit(-1)

print("Connected to gmail..")
mail.select(args.mailbox)  # connect to the mailbox
if len(args.from_email) <= 1:
    search_query = f'(FROM "{args.from_email[0]}")'
else:
    search_query = '(OR'
    for e in args.from_email:
        search_query += f' (FROM "{e}")'
    search_query += ')'

print(f"Using '{search_query}' as a query")
result, data = mail.uid('search', None, search_query)  # search and return uids

print(f"Retrieving {args.n} emails..")
latest_email_uids = data[0].split()[(-1*args.n):-1]
corpus = []
email_datetime = np.zeros((7, 24), dtype=numpy.int)
for uid in tqdm(latest_email_uids):
    result, data = mail.uid('fetch', uid, '(RFC822)')
    raw_email = data[0][1]
    email_message = email.message_from_bytes(raw_email)
    date_tuple = email.utils.parsedate_tz(email_message['Date'])
    if date_tuple:
        local_date = datetime.datetime.fromtimestamp(
            email.utils.mktime_tz(date_tuple))
        email_datetime[local_date.weekday(), local_date.hour] += 1
    text = get_first_text_block(email_message)
    if text:
        corpus.append(text)
corpus = ''.join(corpus)

# count words
word_counts = defaultdict(lambda: 0)
print("Parsing emails..")
not_char = re.compile('[^a-z]')
strip_punc = re.compile('[^\w\d\-\.]\Z')
total_count = 0
for word in word_tokenize(corpus):
    word = word.lower()
    if word not in stopwords.words('english') and len(word) > 2 and len(word) < 20:
        word_counts[word] += 1
        total_count += 1

# remove words with just one occurence
word_counts2 = defaultdict(lambda: 0)
total_count = float(total_count)
for word in word_counts:
    if word_counts[word] > 1:
        word_counts2[word] = word_counts[word] / total_count

print("Creating wordcloud in wordcloud.png..")
print(word_counts2)
wordcloud = WordCloud(font_path='OpenSans-Bold.ttf',
                      background_color='black',
                      width=1920,
                      height=1080)
wordcloud.fit_words(word_counts2)
wordcloud.to_file('./wordcloud.png')

# generate email heatmap
print(email_datetime)
cols = ["Midnight", "6 AM", "Noon", "6 PM"]
rows = ['M', 'Tu', 'W', 'Th', 'F', 'Sa', 'Su']
plt.pcolor(email_datetime)
plt.xticks(np.arange(0, 24, 6) + 0.5, cols)
plt.yticks(np.arange(0, 7) + 0.5, rows)
plt.colorbar()
plt.title("When the Most Emails are Being Received?")
plt.xlabel("Time of Day")
plt.ylabel("Day of Week")
plt.savefig("./heatmap.png", dpi=300)
