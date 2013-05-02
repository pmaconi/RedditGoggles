RedditGoggles
==============
A Python 3.3 distributed Reddit scraper, based on TwitterGoggles.

Dependencies
------------
- mysql-connector-python
- praw

Setup and Installation
----------------------
1. Install Python 3.3 on the computer you use.  Recognize that many standard installations of Python are
   currently 2.x, and you may need to install Python 3.3 as well.  To execute with Python3, you type "python3"
2. Install the dependencies
	1. Make sure you have "pip" installed on your system (this is a package manager for Python3)
	2. From a command prompt, type:
```
pip install mysql-connector-python praw
```
3. Build database
	1. Create empty database
	2. Create new user for db or grant access to an existing user
	3. Run config/schema.sql
4. Set database config options in config/settings.cfg

5. Add your job(s) to the job table
	* state: an indication of how frequently the collection will occur, in minutes; must be 1 or greater to run at all
	* zombie_head: an INT, you'll use this to identify the head when you call RedditGoggles
	* query: a string passed to the Reddit search API
	* description: a note to yourself about what this job does, will print in verbose mode 
	* EXAMPLE:
```
INSERT INTO job (state, zombie_head, query, description) values (1, 1, "white%20house", "Search for submissions mentioning 'white house'");
```

Usage
-----

Note: Reddit strictly enforces rate limits on its API. The API wrapper used by this script will only send a request once every two seconds. It is up to the user to make sure that those restrictions are followed if running multiple instances of RedditGoggles at once.

```
usage: reddit-goggles.py [-h] [-v] [-d DELAY] head

positional arguments:
  head                  Specify the head # (zombie_head in the job table)

optional arguments:
  -h, --help            Show this help message and exit
  -v, --verbose         Show additional logs
  -d DELAY, --delay DELAY
						Delay execution by DELAY seconds
```

Unix Cron Example
-----------------
```
*/1 * * * * /usr/local/bin/python3 /home/reddit-goggles.py -v -d 2 1 >> ~/log/zombielog-head-1-1.txt
*/1 * * * * /usr/local/bin/python3 /home/reddit-goggles.py -v -d 17 2 >> ~/log/zombie-head-2-1.txt
*/1 * * * * /usr/local/bin/python3 /home/reddit-goggles.py -v -d 33 3 >> ~/log/zombielog-head-3-1.txt
*/1 * * * * /usr/local/bin/python3 /home/reddit-goggles.py -v -d 47 4 >> ~/log/zombielog-head-4-1.txt
```


