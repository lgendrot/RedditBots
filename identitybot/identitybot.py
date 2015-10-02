import praw
import re
import OAuth2Util
import pymongo
import datetime
import time

user_agent = 'AMA identifier: v0.2 (by /u/Molag_balls)'
r = praw.Reddit(user_agent)

#this should point to your oauth config file, you need to create this on your own.
#See https://github.com/SmBe19/praw-OAuth2Util for more information
o = OAuth2Util.OAuth2Util(r, configfile="oauthconfig.ini")
o.refresh(force=True)

#Connect to mongodb
try:
	conn = pymongo.MongoClient()
	print "Connected successfully!"
except pymongo.errors.ConnectionFailure, e:
	print "Could not connect to MongoDB: %s" % e

db = conn.IdentityBot
collection = db.CommentIDs


def in_database(comment_id): #Is the entry in the database already?
	if collection.find({"comment_id": comment_id}).count() > 0:
		return True
	else:
		return False

def already_done_to_db(already_done):
	for id in already_done:
		collection.update_one(
			{"comment_id": id},
			{
				"$set": 
				{
					"collected_at": datetime.datetime.now().strftime("%s") 
				}
			},
			upsert=True
		)


#Loop 'forever'
while True:

	#Get all comments in subreddit(s) of interest
	print "Getting comments..."
	all_comments = r.get_comments('botwatch', limit=None)
	already_done = []

	print "Searching through comments..."
	#Look through every comment
	for comment in all_comments:
		#If the comment starts with "!identify, and it's not in the database already"
		if comment.body.lower().startswith('!identify') and not in_database(comment.id):
			
			#If no username is present, use the author of the parent comment
			if comment.body.lower() == "!identify":
				parent_comment = r.get_info(thing_id=comment.parent_id)
				parent = r.get_redditor(parent_comment.author)
			
			#Else use the username provided
			elif re.search(r'/u/([A-Za-z0-9_-]*)', comment.body):
				parent = r.get_redditor(re.search(r'/u/([A-Za-z0-9_-]*)', comment.body).group(1))
			
			#Get all of the submissions made by user in question
			parent_submissions = parent.get_submitted('new', 'all', limit=None)
			amas_found = []
			for submission in parent_submissions:
				#Regex expression finds possible AMA posts, no matter the subreddit.
				if re.search(r'((?:i am|iam|iama|we are) .* (:?ama|amaa|ask me almost anything|aua|ausa|ask us anything|ask me anything).*)',
												  str(submission.title.encode('utf-8', 'ignore')).lower()):
					#amas_found will be a list of tuples containing the title, permalink, and number of comments in the AMA in question
					amas_found.append((submission.title.encode('utf-8', 'ignore'), submission.permalink, submission.num_comments))
			
			#Only if we've actually found any AMAs will we do anything
			if amas_found:
				comment_table_header = "Title|Comments\n---|---\n"

				#Build the table for the comment
				comment_table = comment_table_header
				for ama in amas_found:
					title = ama[0]
					if len(title) > 75:
						title = title[:72] + "..."
					link = ama[1]
					n_comments = ama[2]
					comments_string = str(n_comments)+" Comments"
					comments_link = "["+comments_string+"]"+"("+link.encode('utf-8', 'ignore')+")"
					comment_table = comment_table + title + '|' + comments_link + '\n'

				#Build the body of the comment. Needs prettifying
				body = "User /u/"+str(parent.name) +" has posted the following AMAs:\n\n" + comment_table + "\n\n^(I'm just a bot, be nice. If I've got something wrong, message /u/Molag_balls.)"
				
				#We don't want the script to break if we get a rate limit
				print 'Commenting...'
				try:
					comment.reply(body)
					already_done.append(comment.id)
				except Exception, e:
					print e
					continue


	already_done_to_db(already_done)
	already_done = []
	print "Sleeping for 5 minutes"
	time.sleep(180)




