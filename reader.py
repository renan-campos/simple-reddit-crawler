#!/usr/bin/env python
import urllib2
import json
import time
import datetime
import os
import sys

import re
pattern = re.compile('[\W_]+')

# ----------------------
# Functions 
# ----------------------

def showUsage():
	print
	print "Usage:"
	print
	print "- To read all new threads from a subreddit:"
	print "python reader.py /r/yoursubreddithere"
	print
	print "- To get all the comments from the threads read"
	print "python reader.py --get-comments"
	print
	sys.exit()

# Read threads
def readThreads(subreddit):
	"""
	Extracts threads from json, returns in a list format. 
	"""
	threads = list()
	newThreads = 0
	for t in subreddit:
		
		# Get the thread info
		threadId = t['data']['id']
		title = t['data']['title']
		permalink = t['data']['permalink']
		score = t['data']['score']
		created = t['data']['created_utc']
		
		# Save it to the database. Duplicate threads will be ignored due to the UNIQUE KEY constraint
		threads.append({'id_thread':threadId, 'id_sub':title, 'url':permalink, 'score':int(score), 'created':created})
		newThreads += 1

	# Print a summary
	print "Got " + str(newThreads) + " threads."

	return threads
	
# Recursive function to read comments
def readComments(obj, threadId, threadUrl, comments=list()):
	"""
	Recursivley reads comments.
	"""
	for i in obj:

		# Basic info, present both in Title and Comment
		commentId = i['data']['id']
		content = ""
		url = ""
		score = 0
		created = 0
		if 'created_utc' in i['data']:
			created = i['data']['created_utc']
		else:
			print "*** WARNING: created_utc not found in this record -> " + commentId

		# Is it a comment?
		if 'body' in i['data']:

			url = threadUrl + commentId
			content = i['data']['body']
			ups = int(i['data']['ups'])
			downs = int(i['data']['downs'])
			score = ups - downs

		# Or is it the title post?
		elif 'selftext' in i['data']:

			url = i['data']['url']
			content = i['data']['selftext']
			score = i['data']['score']

		# Save!
		comments.append({'id_comment':commentId, 'id_thread':threadId, 'comment':content, 'url':url, 'score':int(score), 'created':created})

		# Does it have a reply?
		if 'replies' in i['data'] and len(i['data']['replies']) > 0:
			readComments(i['data']['replies']['data']['children'], threadId, threadUrl, comments)

	return comments
	
def requestJson(url, delay):
	"""
	Abides by Reddit's rules when sending a request for json of a subreddit.
	"""
	while True:
		try:
			# Reddit API Rules: "Make no more than thirty requests per minute"
			if delay < 2:
				delay = 2
			time.sleep(delay)

			req = urllib2.Request(url, headers=hdr)
			response = urllib2.urlopen(req)
			jsonFile = response.read()
			return json.loads(jsonFile)
		except Exception as e:
			print e

# ----------------------
# Script begins here
# ----------------------
if __name__ == '__main__':

	# Setup ------------------------------------------

	# Url, header and request delay
	# If we don't set an unique User Agent, Reddit will limit our requests per hour and eventually block them
	# Reddit needs a string of the form: <platform>:<app ID>:<version string> (by /u/<reddit username>)
	# Example: User-Agent: android:com.example.myredditapp:v1.2.3 (by /u/kemitche)
	userAgent = "nlp:com.dstc6.crawler:v1.0.0 (by /u/rennyren123)"
	if userAgent == "":
		print
		print "Error: you need to set an User Agent inside this script"
		print
		sys.exit()
	hdr = {'User-Agent' : userAgent}
	baseUrl = "http://www.reddit.com/"

	# Read args
	shouldReadComments = False
	shouldReadThreads = False
	if len(sys.argv) == 2:
		subreddit = sys.argv[1]
		subredditUrl = baseUrl + subreddit + "/new/.json"
		shouldReadComments = True
		delay = 30
		print "Reading threads from " + subredditUrl
	else:
		showUsage()

	print "Starting crawler"
	print "Press ctrl+c to stop"
	print
	

	# Scrub subreddit name
	if subreddit[:3] != "/r/":
		subreddit = "/r/%s" % subreddit
	fpath = subreddit[1:]
	os.mkdir(fpath) if not os.path.isdir(fpath) else "Already exists"

	# Log starting time
	startingTime = datetime.datetime.now()

	# Read threads
	print "Requesting threads from %s" % subreddit
	jsonObj = requestJson(subredditUrl, delay)
	
	threads = readThreads(jsonObj['data']['children'])
	
	for thread in threads:
		fname = os.path.join(fpath, "%s.txt" % pattern.sub('', thread['id_sub']))

		with open(fname, 'w') as f:
			# Read comments
			v = thread['url']
			k = thread['id_thread']
			# Prepare the http request
			jsonData = requestJson(baseUrl + urllib2.quote(v.encode('utf8')) + ".json", delay)
			
			data = jsonData[1]['data']['children']
			comments = readComments(data, k, v)
			for comment in comments:
				f.write("%s\n" % comment['comment'].encode('utf-8').strip())
				
		print "wrote: %s" % fname
	# Finishing time
	endingTime = datetime.datetime.now()

	print "Started: %s End: %s" % (startingTime, endingTime)
