#!/usr/bin/env python

import imaplib, getpass, email
from wordcloud import WordCloud
import argparse
import re
from nltk.tokenize import word_tokenize, sent_tokenize
from nltk.corpus import stopwords
from collections import defaultdict

### process command line args
parser = argparse.ArgumentParser(description='Make wordcloud from sent emails content.')
parser.add_argument('--n', type=int, dest='n', default=10000,
                    help="Number of emails to retrieve.")
parser.add_argument('--from', action="append", dest='from_email', required=True,
                    help="Generate a word cloud only from this e-mail address")
parser.add_argument('--mailbox', dest='mailbox', default='[Gmail]/All Mail', help='Specific different mailbox')
args = parser.parse_args()
assert args.n > 1

reply_line_regexp = re.compile('(On ([A-Za-z]{3,12}(,)? )?(([A-Za-z]{3,12} [0-3]?[0-9](,)?)|([0-3]?[0-9] [A-Za-z]{3,12}(,)?)) 20[0-9][0-9])|(-{4,})|(From:)')

def get_first_text_block( email_message_instance):
    maintype = email_message_instance.get_content_maintype()
    if maintype == 'multipart':
        text = None
        for part in email_message_instance.get_payload():
            if part.get_content_maintype() == 'text':
                text = part.get_payload()
        if text is None:
            return None
        return re.split(reply_line_regexp, text)[0]
    elif maintype == 'text':
        text = email_message_instance.get_payload()
    return re.split(reply_line_regexp, text)[0]

mail = imaplib.IMAP4_SSL('imap.gmail.com')
while True:
    usr = raw_input("Enter username: ")
    pwd = getpass.getpass("Enter your password: ")
    try:
        mail.login(usr, pwd)
        break
    except:
        print "Unable to login under those credentials."
        exit(-1)

print "Connected to gmail.."
mail.select(args.mailbox) # connect to all main
#result, data = mail.uid('search', None, "ALL") # search and return uids instead
if len(args.from_email) <= 1:
    search_query = '(FROM "%s")' % args.from_email[0]
else:
    search_query = '(OR'
    for e in args.from_email:
        search_query += ' (FROM "%s")' % e
    search_query += ')'

print "Using '%s' as a query" % search_query
result, data = mail.uid('search', None, search_query) # search and return uids instead

print "Retrieving %s emails.." % args.n
latest_email_uids = data[0].split()[(-1*args.n):-1]
corpus = []
for uid in latest_email_uids:
    result, data = mail.uid('fetch', uid, '(RFC822)')
    raw_email = data[0][1]
    email_message = email.message_from_string(raw_email)
    text = get_first_text_block(email_message)
    if text:
        corpus.append(text)
corpus = ''.join(corpus)
with open("corpus.txt", "w") as of:
    print >>of, corpus

word_counts = defaultdict(lambda: 0)

print "Parsing emails.."
not_char = re.compile('[^a-z]')
strip_punc = re.compile('[^\w\d\-\.]\Z')
for word in word_tokenize(corpus):
    word = word.lower()
    #word = re.sub( strip_punc, '', word)
    #if not_char.search(word): continue
    if word not in stopwords.words('english') and len(word) > 2 and len(word) < 20:
        word_counts[word] += 1

print "Creating wordcloud in wordcloud.png.."
print word_counts
wordcloud = WordCloud(font_path='OpenSans-Bold.ttf',
                      background_color='black',
                      stopwords=stopwords.words('english'),
                      width=1800,
                      height=1400)
wordcloud.fit_words(word_counts.items())
wordcloud.to_file('./wordcloud.png')

