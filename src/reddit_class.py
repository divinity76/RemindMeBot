import logging.handlers
import praw
import configparser
import traceback
import requests
import time

import static
import utils
from classes.queue import Queue

log = logging.getLogger("bot")


class Reddit:
	def __init__(self, user, no_post):
		self.no_post = no_post
		try:
			self.reddit = praw.Reddit(
				user,
				user_agent=static.USER_AGENT)
		except configparser.NoSectionError:
			log.error("User "+user+" not in praw.ini, aborting")
			raise ValueError
		static.ACCOUNT_NAME = self.reddit.user.me().name
		log.info("Logged into reddit as /u/" + static.ACCOUNT_NAME)
		self.processed_comments = Queue(100)

	def get_messages(self):
		log.debug("Fetching unread messages")
		return self.reddit.inbox.unread(limit=500)

	def reply_message(self, message, body):
		log.debug(f"Replying to message: {message.id}")
		if self.no_post:
			log.info(body)
		else:
			message.reply(body)

	def reply_comment(self, comment, body):
		log.debug(f"Replying to message: {comment.id}")
		if self.no_post:
			log.info(body)
			return "xxxxxx"
		else:
			return comment.reply(body).id

	def send_message(self, username, subject, body):
		log.debug(f"Sending message to u/{username}")
		if self.no_post:
			log.info(body)
		else:
			self.reddit.redditor(username).message(subject, body)

	def get_comment(self, comment_id):
		log.debug(f"Fetching comment by id: {comment_id}")
		if comment_id == "xxxxxx":
			return None
		else:
			return self.reddit.comment(comment_id)

	def edit_comment(self, body, comment=None, comment_id=None):
		if comment is None:
			comment = self.get_comment(comment_id)
		log.debug(f"Editing comment: {comment.id}")

		if self.no_post:
			log.info(body)
		else:
			comment.edit(body)

	def delete_comment(self, comment):
		log.debug(f"Deleting comment: {comment.id}")
		if not self.no_post:
			try:
				comment.delete()
			except Exception:
				log.warning(f"Error deleting comment: {comment.comment_id}")
				log.warning(traceback.format_exc())
				return False
		return True

	def get_keyword_comments(self, keyword, last_seen):
		log.debug(f"Fetching comments for keyword: {keyword} : {utils.get_datetime_string(last_seen)}")
		url = f"https://api.pushshift.io/reddit/comment/search?q={keyword}&limit=100&sort=desc"
		try:
			requestTime = time.perf_counter()
			json = requests.get(url, headers={'User-Agent': static.USER_AGENT})
			requestSeconds = int(time.perf_counter() - requestTime)
			if requestSeconds > 5:
				log.warning(f"Long request time for search term: {keyword} : seconds: {str(requestSeconds)}")
			if json.status_code != 200:
				log.warning(f"Could not parse data for search term: {keyword} status: {str(json.status_code)}")
				return []
			comments = json.json()['data']
		except Exception as err:
			log.warning(f"Could not parse data for search term: {keyword}")
			log.warning(traceback.format_exc())
			return []

		if not len(comments):
			log.warning(f"No comments found for search term: {keyword}")
			return []

		result_comments = []
		for comment in comments:
			date_time = utils.datetime_from_timestamp(comment['created_utc'])
			if last_seen > date_time:
				break

			if not self.processed_comments.contains(comment['id']):
				result_comments.append(comment)

		log.debug(f"Found comments: {len(result_comments)}")
		return result_comments
