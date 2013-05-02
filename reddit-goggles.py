import argparse, collections, configparser, json, math, mysql.connector as sql, praw, os, requests, sys, time
from datetime import datetime
from pprint import pprint
from mysql.connector import errorcode

# Print strings in verbose mode
def verbose(info) :
	if args.verbose:
		print(info)

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

	query = ("SELECT job_id, zombie_head, state, query, description \
			FROM job \
			WHERE job.state > 0 AND zombie_head = %s \
			ORDER BY job_id")

	cursor.execute(query,[args.head])
	return cursor

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
		# Convert unprintable utf8 strings to ascii bytes and decode back to a string
		verbose("     Query: " + cursor.statement.encode("ascii", "ignore").decode())
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
		# Convert unprintable utf8 strings to ascii bytes and decode back to a string
		verbose("     Query: " + cursor.statement.encode("ascii", "ignore").decode())
	finally :
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
		# Convert unprintable utf8 strings to ascii bytes and decode back to a string
		verbose("     Query: " + cursor.statement.encode("ascii", "ignore").decode())
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
		# Convert unprintable utf8 strings to ascii bytes and decode back to a string
		verbose("     Query: " + cursor.statement.encode("ascii", "ignore").decode())
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
		# Convert unprintable utf8 strings to ascii bytes and decode back to a string
		verbose("     Query: " + cursor.statement.encode("ascii", "ignore").decode())
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
		# Convert unprintable utf8 strings to ascii bytes and decode back to a string
		verbose("     Query: " + cursor.statement.encode("ascii", "ignore").decode())
	finally:
		cursor.close()

# Recursively parse all of the comments
def parseCommentTree(conn, job_id, submission_id, comment) :
	success = addComment(conn, job_id, submission_id, comment)
	if success :
		addCommentScoreHistory(conn, job_id, comment)
		
		for reply in comment.replies :
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

	# Display startup info
	print("vvvvv Start:", datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
	verbose("Verbose Mode: Enabled")
	#print("Head:", args.head)
	print("Delay:", args.delay)

	epoch_min = math.floor(time.time() / 60)
	verbose("Epoch Minutes: " + str(epoch_min))

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
		for (job_id, zombie_head, state, query, description) in jobs :
			
			# Throttle the job frequency
			if (epoch_min % state != 0) :
				verbose("Throttled frequency for job: " + str(job_id))
				#continue
			
			print("+++++ Job ID:", job_id, "\tQuery:", query, "\tDescription:", description)

			# Convert the generator to a list for progress status
			submissions = list(r.search(query))

			current = 1
			total = len(submissions)

			for submission in submissions :				
				# Insert the submission in the DB
				success = addSubmission(conn, job_id, submission)

				# Show status logging
				if args.verbose :
					sys.stdout.write("\rProgress: {}/{}".format(current, total))
				current = current + 1

				if success :
					addSubmissionScoreHistory(conn, job_id, submission)

					submission.replace_more_comments(limit=None, threshold=0)
					for comment in submission.comments :
						parseCommentTree(conn, job_id, submission.id, comment)

			addJobHistory(conn, job_id, True, total)
			updateJobStats(conn, job_id, total)

			verbose("")
			print("Total Results:", total)
			run_total_count = run_total_count + total

	except sql.Error as err :
		print(err)
		print("Terminating.")
		sys.exit(1)
	
	else :
		conn.close()
	
	finally :
		print("$$$$$ Run total count: " + str(run_total_count))
		print("^^^^^ Stop:", datetime.now().strftime('%Y-%m-%d %H:%M:%S'))