#!/usr/bin/env python3

import configparser
from datetime import date, datetime, timedelta
import copy
import praw
import yaml
import logging

PERMIT_LENGTH = 180

PM_EXPIRE_SUBJECT = "Your time has expired"
PM_EXPIRE_TEXT = """The Honorable {user},

The chair has noticed that you haven't posted a RI, a policy proposal or a good
contribution in the Reddit Economics Network in the last 6 months.

As a result, you must yield your remaining time, and let debate continue
amongst more established members of this chamber.

You can find more details about parliamentary procedure here:
https://www.reddit.com/r/badeconomics/comments/mtks9k/rbadeconomics_endorses_the_universal_fillibuster/

Please contact the parliamentarians for any further questions:
https://www.reddit.com/message/compose?to=%2Fr%2Fbadeconomics
"""

PM_GRANTED_SUBJECT = "The Chair recognizes the Honorable {user}"
PM_GRANTED_TEXT = """Senator {user},

We noticed that you have recently posted a RI, a policy proposal or a good
contribution in the Reddit Economics Network, thereby pleasing the leadership.

As a result, we have decided to grant you the floor for a duration
of 6 months. You are now allowed to post in the Senate Discussion Sticky

Your time will expire on the {expires}.
You can renew this time on the floor at any time by posting another good
contribution in the Reddit Economics Network, valid for another 6 months
starting from the date of your post.

Please remember however that the chair reserves the right to revoke your time
can be revoked at any time if you were to behave in an unparliamentary manner,
such as inciting insurrection, attempting secession, or expressing incorrect
opinions on the REN or elsewhere.

You can find more details about our parliamentary procedure here:
https://www.reddit.com/r/badeconomics/comments/mtks9k/rbadeconomics_endorses_the_universal_fillibuster/

Please contact the parliamentarians for any further questions:
https://www.reddit.com/message/compose?to=%2Fr%2Fbadeconomics
"""


class WikiAllowlist:
    PERMIT_KEY = 'contributors'
    PERMALLOWED_KEY = 'whitelist'

    def __init__(self, subreddit):
        self.subreddit = subreddit
        self.allowlist = None
        self.to_update = {}
        self.to_delete = []

        self.reload()

    def reload(self):
        wiki_page = self.subreddit.wiki['zoning_whitelist']
        self.allowlist = yaml.safe_load(wiki_page.content_md)

    def commit(self):
        """Commit the pending changes to the allowlist"""
        # Reload to avoid race conditions between edits
        self.reload()

        allowlist_new = copy.deepcopy(self.allowlist)
        allowlist_new[self.PERMIT_KEY].update(self.to_update)
        for u in self.to_delete:
            allowlist_new[self.PERMIT_KEY].pop(u)
        if self.allowlist != allowlist_new:
            wiki_page = self.subreddit.wiki['zoning_whitelist']
            wiki_page.edit(yaml.safe_dump(allowlist_new))

        self.reload()

    def update(self, user: str, start_date: date):
        if (
            (date.today() - start_date).days <= PERMIT_LENGTH
            and (user not in self.permits()
                 or self.permits()[user] < start_date)
        ):
            self.to_update[user] = start_date
            self.permits().update(self.to_update)
            return True
        else:
            return False

    def delete(self, user: str):
        self.permits().pop(user)
        self.to_delete.append(user)

    def permits(self):
        return self.allowlist[self.PERMIT_KEY]

    def permallowed(self):
        return self.allowlist[self.PERMALLOWED_KEY]

    def __getitem__(self, user: str):
        return self.permits()[user]


class WallBot:
    def __init__(self, config):
        self.config = config
        self.reddit = praw.Reddit(
            client_id=config['reddit']['client_id'],
            client_secret=config['reddit']['client_secret'],
            username=config['reddit']['username'],
            password=config['reddit']['password'],
            user_agent='BadEconomics Zoning Bot',
            ratelimit_seconds=120,
        )
        self.subreddit = self.reddit.subreddit('badeconomics')
        self.allowlist = WikiAllowlist(self.subreddit)

    def run(self):
        self.allow_from_RIs()
        self.allow_from_modmail()
        self.remove_expired_permits()
        self.grant_permits()
        self.archive_modmail_notifs()
        self.allowlist.commit()

    def allow_from_RIs(self, backlog=50):
        """Automatically add people with submissions marked as sufficient"""

        for submission in self.subreddit.new(limit=backlog):
            if not submission.author:  # deleted users
                continue
            author = str(submission.author)
            submission_date = date.fromtimestamp(submission.created_utc)
            if submission.link_flair_text == 'Sufficient':
                added = self.allowlist.update(author, submission_date)
                if added:
                    logging.info("[RI] Marked %s for a permit", author)

    def allow_from_modmail(self, backlog=25):
        """Automatically add people with submissions marked as sufficient"""

        for conv in self.subreddit.modmail.conversations(limit=backlog):
            if not conv.participant:  # deleted users
                continue

            participant = str(conv.participant)
            for message in conv.messages:
                if (
                    '!allow' in message.body_markdown
                    and message.author in self.subreddit.moderator()
                ):
                    command_date = datetime.fromisoformat(message.date).date()
                    added = self.allowlist.update(participant, command_date)
                    if added:
                        logging.info(
                            "[MODMAIL] Marked %s for a permit", participant
                        )
                        conv.reply(
                            "Confirmed! Granted cloture to {} for {} days."
                            .format(participant, PERMIT_LENGTH)
                        )

    def grant_permits(self):
        """
        Look at the allowlist for new permits, add users to the contributor
        list and notify them that they have been added.
        """

        for user_str, date_start in self.allowlist.permits().items():
            user = self.reddit.redditor(user_str)
            if user not in self.subreddit.contributor():
                try:
                    self.subreddit.contributor.add(user)
                except Exception:  # banned
                    continue

                # Don't spam permallowed users with permit PMs
                if user_str in self.allowlist.permallowed():
                    continue

                logging.info("Granting /u/%s a permit.", user_str)

                expires = date_start + timedelta(PERMIT_LENGTH)
                user.message(
                    PM_GRANTED_SUBJECT.format(user=user_str),
                    PM_GRANTED_TEXT.format(user=user_str, expires=expires)
                )

        # Ensure that permallowed users are always contributors
        for contributor in self.allowlist.permallowed():
            user = self.reddit.redditor(contributor)
            if contributor not in self.subreddit.contributor():
                self.subreddit.contributor.add(user)

    def remove_expired_permits(self):
        """
        Look at the allowlist for expired permits, delete users from the
        allowlist, remove them from the contributor list and notify them that
        they have been removed.
        """

        for user_str, date_start in self.allowlist.permits().copy().items():
            user = self.reddit.redditor(user_str)
            if user_str in self.allowlist.permallowed():
                continue

            delta = (date.today() - date_start).days
            if delta > PERMIT_LENGTH:
                logging.info(
                    "Removing /u/%s's expired permit (%s days).",
                    user_str,
                    delta,
                )
                self.allowlist.delete(user_str)
                if user in self.subreddit.contributor():
                    self.subreddit.contributor.remove(user)
                    user.message(
                        PM_EXPIRE_SUBJECT.format(user=user_str),
                        PM_EXPIRE_TEXT.format(user=user_str)
                    )

    def archive_modmail_notifs(self, backlog=25):
        """Archive annoying contributor notifications in modmail"""

        for conv in self.subreddit.modmail.conversations(limit=backlog):
            if conv.subject == 'you are an approved user':
                conv.archive()


def main():
    config = configparser.ConfigParser()
    config.read('settings.conf')
    bot = WallBot(config)
    bot.run()


if __name__ == '__main__':
    main()
