#!/usr/bin/env python3

import configparser
from datetime import date, datetime, timedelta
import copy
import praw
import yaml

PERMIT_LENGTH = 180

PM_EXPIRE_SUBJECT = "Your time has expired"
PM_EXPIRE_TEXT = """The Honorable {user},

The chair has noticed that you haven't posted a RI, a policy proposal or a good
contribution in the Reddit Economics Network in the last 6 months.

As a result, you must yield your remaining time, and let debate continue amongst
more established members of this chamber.

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


def main():
    config = configparser.ConfigParser()
    config.read('settings.conf')

    reddit = praw.Reddit(
        client_id=config['reddit']['client_id'],
        client_secret=config['reddit']['client_secret'],
        username=config['reddit']['username'],
        password=config['reddit']['password'],
        user_agent='BadEconomics Zoning Bot',
        ratelimit_seconds=120,
    )

    badeconomics = reddit.subreddit('badeconomics')

    wiki_zoning = badeconomics.wiki['zoning_whitelist']
    zoning = yaml.safe_load(wiki_zoning.content_md)
    sub_contributors = list(map(str, badeconomics.contributor()))

    # We defer the deletions/additions to avoid locking the wiki
    to_delete = []
    to_update = {}

    # Automatically add people with submissions marked as sufficient
    for submission in badeconomics.new(limit=50):
        if not submission.author:  # deleted users
            continue
        author = str(submission.author)
        submission_date = date.fromtimestamp(submission.created_utc)
        delta = (date.today() - submission_date).days

        if (submission.link_flair_text == 'Sufficient'
            and delta <= PERMIT_LENGTH
            and (author not in zoning['contributors']
                 or zoning['contributors'][author] < submission_date)):
            to_update[author] = submission_date
            zoning['contributors'].update(to_update)
            print('[RI] Marked {} for a permit'.format(author))

    # Check for !whitelist commands in modmail
    for conv in badeconomics.modmail.conversations(limit=25):
        participant = str(conv.participant)
        for message in conv.messages:
            command_date = datetime.fromisoformat(message.date).date()
            delta = (date.today() - command_date).days
            if (
                '!whitelist' in message.body_markdown
                and message.author in badeconomics.moderator()
                and delta <= PERMIT_LENGTH
                and (participant not in zoning['contributors']
                     or zoning['contributors'][participant] < command_date)
            ):
                to_update[participant] = command_date
                zoning['contributors'].update(to_update)
                print('[MODMAIL] Marked {} for a permit'.format(participant))
                conv.reply(
                    "Confirmed! Granted cloture to {} for {} days."
                    .format(participant, PERMIT_LENGTH)
                )

    # Update contributor list from wiki
    for contributor, date_start in zoning['contributors'].items():
        user = reddit.redditor(contributor)
        delta = (date.today() - date_start).days

        if contributor not in zoning['whitelist'] and delta > PERMIT_LENGTH:
            print("Removing /u/{}'s expired permit ({} days)."
                  .format(contributor, delta))
            if contributor in sub_contributors:
                badeconomics.contributor.remove(user)
                user.message(
                    PM_EXPIRE_SUBJECT.format(user=contributor),
                    PM_EXPIRE_TEXT.format(user=contributor))
            to_delete.append(contributor)
        else:
            if contributor not in sub_contributors:
                try:
                    badeconomics.contributor.add(user)
                except Exception:  # banned
                    continue

                if contributor not in zoning['whitelist']:
                    print("Granting /u/{} a permit."
                          .format(contributor, delta))
                    expires = date.today() + timedelta(PERMIT_LENGTH)
                    user.message(
                        PM_GRANTED_SUBJECT.format(user=contributor),
                        PM_GRANTED_TEXT.format(user=contributor,
                                               expires=expires))

    # Add contributors
    for contributor in zoning['whitelist']:
        user = reddit.redditor(contributor)
        if contributor not in sub_contributors:
            badeconomics.contributor.add(user)

    # Archive annoying contributor notifications in modmail
    for conv in badeconomics.modmail.conversations(limit=25):
        if conv.subject == 'you are an approved user':
            conv.archive()


    # Reload + atomic edit
    wiki_zoning = badeconomics.wiki['zoning_whitelist']
    zoning = yaml.safe_load(wiki_zoning.content_md)
    zoning_new = copy.deepcopy(zoning)
    zoning_new['contributors'].update(to_update)
    for u in to_delete:
        zoning_new['contributors'].pop(u)
    if zoning != zoning_new:
        wiki_zoning.edit(yaml.safe_dump(zoning_new))


if __name__ == '__main__':
    main()
