import argparse, collections, configparser, json, math, mysql.connector as sql, praw, os, requests, sys, time
from datetime import datetime
from pprint import pprint
from mysql.connector import errorcode
from requests import HTTPError
from requests import ConnectionError
from fcntl import flock, LOCK_EX, LOCK_NB

# Print strings in verbose mode
def verbose(info) :
	if args.verbose:
		printUTF8(info)

def printUTF8(info) :
	print(info.encode('ascii', 'replace').decode())

# Connect to MySQL using config entries
def connect() :
	db_params = {
		'user' : config["MySQL"]["user"],
		'password' : config["MySQL"]["password"],
		'host' : config["MySQL"]["host"],
		'port' : int(config["MySQL"]["port"]),
		'database' : config["MySQL"]['database'],
		'charset' : 'utf8',
		'collation' : 'utf8_general_ci',
		'buffered' : True
	}

	return sql.connect(**db_params)

# Get all jobs from the database
def getJobs(conn) :
	cursor = conn.cursor() 

	query = ("SELECT job_id, zombie_head, state, query, description, submission_cooldown_seconds \
			FROM job \
			WHERE job.state > 0 AND zombie_head = %s \
			ORDER BY job_id")

	cursor.execute(query,[args.head])
	return cursor

# Perform search
def search(r, query) :	
	# Attempt to reach Reddit
	attempt = 1
	while attempt <= 3 :
		try :
			submissions = list(r.search(query, limit=None))
			return submissions

		except (ConnectionError, HTTPError) as err :
			sleep_time = 2**(attempt - 1)
			verbose("Connection attempt " + str(attempt) + " failed. "
				"Sleeping for " + str(sleep_time) + " second(s).")
			time.sleep(sleep_time)
			attempt = attempt + 1

	print("***** Error: Unable to query Reddit. Terminating.")
	sys.exit(1)

# Replace 'MoreComments object'
def getReplies(reply) :
	attempt = 1
	while attempt <= 3 :
		try :
			comments = reply.comments(update=False)
			return comments

		except (ConnectionError, HTTPError) as err :
			sleep_time = 2**(attempt - 1)
			verbose("Connection attempt " + str(attempt) + " failed. "
				"Sleeping for " + str(sleep_time) + " second(s).")
			time.sleep(sleep_time)
			attempt = attempt + 1

		except (AttributeError, TypeError) :
			return None

	return None

# Add a submission to the DB
def addSubmission(conn, job_id, submission) :
	cursor = conn.cursor()

	query = "REPLACE INTO submission (job_id, submission_id, subreddit_id, " \
		"subreddit, title, author, url, permalink, thumbnail, name, selftext, " \
		"over_18, is_self, created_utc, num_comments, ups, downs, score) VALUES " \
		"(%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s) "
	values = [
		job_id,
		submission.id,
		submission.subreddit_id,
		submission.subreddit.display_name,
		submission.title,
		submission.author.name,
		submission.url,
		submission.permalink,
		submission.thumbnail,
		submission.name,
		submission.selftext,
		submission.over_18,
		submission.is_self,
		datetime.fromtimestamp(submission.created_utc).strftime('%Y-%m-%d %H:%M:%S'),
		submission.num_comments,
		submission.ups,
		submission.downs,
		submission.score
	]
	
	try :
		cursor.execute(query, values)
		conn.commit()
		return True
	except sql.Error as err :
		verbose("")
		verbose(">>>> Warning: Could not add Submission: " + str(err))
		verbose("     Query: " + cursor.statement)
		return False
	finally :
		cursor.close()

# Add an entry to the submission score history
def addSubmissionScoreHistory(conn, job_id, submission) :
	cursor = conn.cursor()

	query = "INSERT INTO submission_score_history (job_id, submission_id, timestamp, ups, " \
		"downs, score) VALUES (%s, %s, %s, %s, %s, %s) ON DUPLICATE KEY UPDATE job_id=job_id"
	values = [
		job_id,
		submission.id,
		datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
		submission.ups,
		submission.downs,
		submission.score
	]
	
	try :
		cursor.execute(query, values)
		conn.commit()
	except sql.Error as err :
		verbose("")
		verbose(">>>> Warning: Could not add Submission score history: " + str(err))
		verbose("     Query: " + cursor.statement)
	finally :
		cursor.close()

# Get the submission's last run time
def getSubmissionRunTime(conn, job_id, submission_id) :
	cursor = conn.cursor()

	query = "SELECT last_run FROM submission WHERE job_id=%s AND submission_id=%s LIMIT 1"

	values = [
		job_id,
		submission_id
	]

	try :
		cursor.execute(query, values)

		for(last_run) in cursor :
			if (last_run[0] is not None) :
				return last_run[0]

		return -1

	except sql.Error as err :
		verbose(">>>> Warning: Could not get the submission last run time: " + str(err))
		verbose("     Query: " + cursor.statement)
	finally:
		cursor.close()

# Update the submission's last run time
def updateSubmissionRunTime(conn, job_id, submission_id) :
	cursor = conn.cursor()

	query = "UPDATE submission SET last_run=%s WHERE job_id=%s AND submission_id=%s"

	values = [
		datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
		job_id,
		submission_id
	]

	try :
		cursor.execute(query, values)
		conn.commit()
	except sql.Error as err :
		verbose(">>>> Warning: Could not update submission run time: " + str(err))
		verbose("     Query: " + cursor.statement)
	finally:
		cursor.close()

# Add a comment to the DB
def addComment(conn, job_id, submission_id, comment) :
	cursor = conn.cursor()

	query = "REPLACE INTO comment (job_id, submission_id, comment_id, " \
		"parent_id, author, body, created_utc, ups, downs) VALUES " \
		"(%s, %s, %s, %s, %s, %s, %s, %s, %s) "

	values = [
		job_id,
		submission_id,
		comment.id,
		comment.parent_id,
		None if comment.author is None else comment.author.name,
		comment.body,
		datetime.fromtimestamp(comment.created_utc).strftime('%Y-%m-%d %H:%M:%S'),
		comment.ups,
		comment.downs
	]
	
	try :
		cursor.execute(query, values)
		conn.commit()
		return True
	except sql.Error as err :
		verbose("")
		verbose(">>>> Warning: Could not add Comment: " + str(err))
		verbose("     Query: " + cursor.statement)
		return False
	finally :
		cursor.close()

# Add an entry to the comment score history
def addCommentScoreHistory(conn, job_id, comment) :
	cursor = conn.cursor()

	query = "INSERT INTO comment_score_history (job_id, comment_id, timestamp, ups, " \
		"downs) VALUES (%s, %s, %s, %s, %s) ON DUPLICATE KEY UPDATE job_id=job_id"
	values = [
		job_id,
		comment.id,
		datetime.fromtimestamp(comment.created_utc).strftime('%Y-%m-%d %H:%M:%S'),
		comment.ups,
		comment.downs
	]
	
	try :
		cursor.execute(query, values)
		conn.commit()
	except sql.Error as err :
		verbose("")
		verbose(">>>> Warning: Could not add Submission score history: " + str(err))
		verbose("     Query: " + cursor.statement)
	finally :
		cursor.close()

# Add an entry into the job history table
def addJobHistory(conn, job_id, success, total_results = 0) :
	return
	cursor = conn.cursor()

	query = "INSERT INTO job_history (job_id, timestamp, status, total_results) " \
		"VALUES(%s, %s, %s, %s, %s)"

	values = [
		job_id,
		datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
		"success" if success else "failure",
		total_results
	]

	try :
		cursor.execute(query, values)
		conn.commit()
	except sql.Error as err :
		verbose(">>>> Warning: Could not add job_history entry: " + str(err))
		verbose("     Query: " + cursor.statement)
	finally:
		cursor.close()

# Update the stored job's last run time and total results
def updateJobStats(conn, job_id, total_results) :
	cursor = conn.cursor()

	query = "UPDATE job SET last_count=%s, last_run=%s WHERE job_id=%s"

	values = [
		total_results,
		datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
		job_id
	]

	try :
		cursor.execute(query, values)
		conn.commit()
	except sql.Error as err :
		verbose(">>>> Warning: Could not update job: " + str(err))
		verbose("     Query: " + cursor.statement)
	finally:
		cursor.close()

# Recursively parse all of the comments
def parseCommentTree(conn, job_id, submission_id, comment) :
	global submission_count, submission_total, comment_count, comment_total

	if not isinstance(comment, praw.objects.MoreComments) :		
		success = addComment(conn, job_id, submission_id, comment)
		if success :
			comment_count = comment_count + 1
			# Show status logging
			if args.verbose :
				sys.stdout.write("\rProgress: Submission: {}/{}, Comment: {}/{}".format(submission_count, submission_total, comment_count, comment_total))
			addCommentScoreHistory(conn, job_id, comment)

			replies = comment.replies
			while len(replies) > 0 :
				reply = replies.pop(0)

				if isinstance(reply, praw.objects.MoreComments) :
					more_replies = getReplies(reply)

					if more_replies is not None :
						replies.extend(more_replies)
				else :
					parseCommentTree(conn, job_id, submission_id, reply)


# Main function
if __name__ == '__main__' :
	# Handle command line arguments
	parser = argparse.ArgumentParser(description="A Reddit variation of TwitterGoggles")
	parser.add_argument('head', type=int, help="Specify the head #")
	parser.add_argument('-v','--verbose', default=True, action="store_true", help="Show additional logs")
	parser.add_argument('-d','--delay', type=int, default=0, help="Delay execution by DELAY seconds")
	args = parser.parse_args()

	# Handle config settings	
	config = configparser.ConfigParser()
	script_dir = os.path.dirname(__file__)
	config_file = os.path.join(script_dir, 'config/settings.cfg')
	config.read(config_file)

	# Handle file locking
	lock = open(config["Misc"]["lockfile"], 'a')
	try :
		flock(lock, LOCK_EX | LOCK_NB)
	except IOError :
		print("Unable to lock file", config["Misc"]["lockfile"] + ".","Terminating.")
		sys.exit(1)

	# Display startup info
	print("vvvvv Start:", datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
	verbose("Verbose Mode: Enabled")
	print("Head:", args.head)
	print("Delay:", args.delay)

	if (args.delay > 0) :
		time.sleep(args.delay)

	print("Connecting to database...")

	try :
		run_total_count = 0
		conn = connect()
		print("Connected")

		# Get all of the jobs for this head
		jobs = getJobs(conn)

		if not jobs.rowcount :
			print("\nUnable to find any jobs to run. Please make sure there are entries in the 'job'"
				+ " table, that their 'zombie_head' value matches {}, and the 'state' value is greater"
				+ " than 0.\n".format(args.head))

		# Initialize the Reddit wrapper
		r = praw.Reddit(user_agent = config["Reddit"]["user-agent"])

		# Iterate over all of the jobs found
		for (job_id, zombie_head, state, query, description, submission_cooldown_seconds) in jobs :
			printUTF8("+++++ Job ID:" + str(job_id) + "\tQuery:" + query + "\tDescription:" + description)

			submissions = search(r, query)

			submission_count = 0
			submission_total = len(submissions)

			for submission in submissions :
				last_run = getSubmissionRunTime(conn, job_id, submission.id)

				if (last_run != -1 and (datetime.now() - last_run).total_seconds() < submission_cooldown_seconds) :
					print("Skipping submission id", submission.id, "because it has been parsed in the past", submission_cooldown_seconds, "second(s).")
					submission_count = submission_count + 1
					continue

				comment_count = 0
				# Insert the submission in the DB
				success = addSubmission(conn, job_id, submission)

				submission_count = submission_count + 1
				comment_total = submission.num_comments

				if success :
					addSubmissionScoreHistory(conn, job_id, submission)

					for comment in submission.comments :
						parseCommentTree(conn, job_id, submission.id, comment)

					updateSubmissionRunTime(conn, job_id, submission.id)
				
			addJobHistory(conn, job_id, True, submission_total)
			updateJobStats(conn, job_id, submission_total)

			verbose("")
			print("Total Results:", submission_total)
			run_total_count = run_total_count + submission_total

	except sql.Error as err :
		print(err)
		print("Terminating.")
		sys.exit(1)
	
	else :
		conn.close()
	
	finally :
		print("$$$$$ Run total count: " + str(run_total_count))
		print("^^^^^ Stop:", datetime.now().strftime('%Y-%m-%d %H:%M:%S'))