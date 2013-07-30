-- ----------------------------
--  Table structure for `job`
-- ----------------------------
DROP TABLE IF EXISTS `job`;
CREATE TABLE `job` (
  `job_id` int(10) unsigned NOT NULL AUTO_INCREMENT,
  `state` int(11) NOT NULL DEFAULT '0',
  `zombie_head` int(10) DEFAULT NULL,
  `query` text NOT NULL,
  `description` varchar(255) DEFAULT 'I am a lazy piece of shit and I did not enter a description',
  `last_count` int(10) unsigned zerofill DEFAULT NULL,
  `last_run` datetime DEFAULT NULL,
  `submission_cooldown_seconds` int DEFAULT 3600,
  `analysis_state` int(11) DEFAULT '0',
  PRIMARY KEY (`job_id`)
) ENGINE=InnoDB AUTO_INCREMENT=2511 DEFAULT CHARSET=utf8 ROW_FORMAT=COMPACT;

-- ----------------------------
--  Table structure for `submission`
-- ----------------------------
DROP TABLE IF EXISTS `submission`;
CREATE TABLE `submission` (
  `job_id` int(10) unsigned NOT NULL,
  `subreddit_id` varchar(20) NOT NULL,
  `submission_id` varchar(20) NOT NULL,
  `subreddit` text NOT NULL,
  `title` text NOT NULL,
  `author` text NOT NULL,
  `url` text NOT NULL,
  `permalink` text NOT NULL,
  `thumbnail` text NOT NULL,
  `name` text NOT NULL,
  `selftext` text NOT NULL,
  `over_18` boolean NOT NULL,
  `is_self` boolean NOT NULL,
  `created_utc` datetime NOT NULL,
  `num_comments` int(10) NOT NULL,
  `ups` int(10) NOT NULL,
  `downs` int(10) NOT NULL,
  `score` int(10) NOT NULL,
  `analysis_state` int(10) DEFAULT '0',
  `last_run` datetime DEFAULT NULL,
  PRIMARY KEY (`submission_id`,`job_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8 ROW_FORMAT=COMPACT;

-- ----------------------------
--  Table structure for `submission_score_history`
-- ----------------------------
DROP TABLE IF EXISTS `submission_score_history`;
CREATE TABLE `submission_score_history` (
  `job_id` int(10) unsigned NOT NULL,
  `submission_id` varchar(20) NOT NULL,
  `timestamp` datetime NOT NULL,
  `ups` int(10) NOT NULL,
  `downs` int(10) NOT NULL,
  `score` int(10) NOT NULL,
  PRIMARY KEY (`submission_id`,`job_id`,`ups`,`downs`,`score`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8 ROW_FORMAT=COMPACT;

-- ----------------------------
--  Table structure for `comment`
-- ----------------------------
DROP TABLE IF EXISTS `comment`;
CREATE TABLE `comment` (
  `job_id` int(10) unsigned NOT NULL,
  `submission_id` varchar(20) NOT NULL,
  `comment_id` varchar(20) NOT NULL,
  `parent_id` varchar(20),
  `author` text,
  `body` text NOT NULL,
  `created_utc` datetime NOT NULL,
  `ups` int(10) NOT NULL,
  `downs` int(10) NOT NULL,
  `analysis_state` int(10) DEFAULT '0',
  PRIMARY KEY (`comment_id`,`job_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8 ROW_FORMAT=COMPACT;

-- ----------------------------
--  Table structure for `comment_score_history`
-- ----------------------------
DROP TABLE IF EXISTS `comment_score_history`;
CREATE TABLE `comment_score_history` (
  `job_id` int(10) unsigned NOT NULL,
  `comment_id` varchar(20) NOT NULL,
  `timestamp` datetime NOT NULL,
  `ups` int(10) NOT NULL,
  `downs` int(10) NOT NULL,
  PRIMARY KEY (`comment_id`,`job_id`,`ups`,`downs`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8 ROW_FORMAT=COMPACT;

-- ----------------------------
--  Table structure for `history`
-- ----------------------------
DROP TABLE IF EXISTS `job_history`;
CREATE TABLE `job_history` (
  `history_id` int(10) unsigned NOT NULL AUTO_INCREMENT,
  `job_id` int(10) unsigned NOT NULL,
  `oauth_id` int(10) unsigned NOT NULL,
  `timestamp` datetime NOT NULL,
  `status` varchar(7) NOT NULL,
  `total_results` int(10) unsigned zerofill DEFAULT NULL,
  PRIMARY KEY (`history_id`)
) ENGINE=InnoDB AUTO_INCREMENT=39936178 DEFAULT CHARSET=utf8 ROW_FORMAT=COMPACT;