#!/usr/bin/env python3

from datetime import datetime, date, timedelta
import copy
import praw
import yaml

PERMIT_LENGTH = 180

PM_EXPIRE_SUBJECT = "Your zoning permit has expired"
PM_EXPIRE_TEXT = """Hi {user},

We noticed that you haven't posted a RI, a policy proposal or a good
contribution in the Reddit Economics Network in the last 6 months.

As a result, and in order to preserve the character of our neighborhood, your
zoning permit has expired. You can no longer post in the Mixed Use Development
sticky.

You can find more details about our Exclusionary Zoning policy here:
https://www.reddit.com/r/badeconomics/comments/cccui4/exclusionary_zoning_is_coming_to_rbadeconomics/

Please contact the moderators for any further questions:
https://www.reddit.com/message/compose?to=%2Fr%2Fbadeconomics
"""

PM_GRANTED_SUBJECT = "Won't you be my neighbor?"
PM_GRANTED_TEXT = """Hi {user},

We noticed that you have recently posted a RI, a policy proposal or a good
contribution in the Reddit Economics Network, thereby demonstrating your
potential to be a good neighbor.

As a result, we have decided to grant you a zoning permit valid for a duration
of 6 months. You are now allowed to post in the Mixed Use Development Sticky.

Your permit will expire on the {expires}.
You can renew this permit at any time by posting another good contribution in
the Reddit Economics Network, valid for another 6 months starting from the date
of your post.

Please remember however that in order to preserve the character of our
neighborhood, your zoning permit can be revoked at any time if you were to
express incorrect opinions on the REN or elsewhere.

You can find more details about our Exclusionary Zoning policy here:
https://www.reddit.com/r/badeconomics/comments/cccui4/exclusionary_zoning_is_coming_to_rbadeconomics/

Please contact the moderators for any further questions:
https://www.reddit.com/message/compose?to=%2Fr%2Fbadeconomics
"""


def main():
    reddit = praw.Reddit()
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
            print('Marked {} for a permit'.format(author))

    # Update contributor list from wiki
    # Uncomment when ready
    for contributor, date_start in zoning['contributors'].items():
        user = reddit.redditor(contributor)
        delta = (date.today() - date_start).days

        if contributor not in zoning['whitelist'] and delta > PERMIT_LENGTH:
            print("Removing /u/{}'s expired permit ({} days)."
                  .format(contributor, delta))
            if contributor in sub_contributors:
                badeconomics.contributor.remove(user)
                user.message(
                    PM_EXPIRE_SUBJECT,
                    PM_EXPIRE_TEXT.format(user=contributor))
            to_delete.append(contributor)
        else:
            if contributor not in sub_contributors:
                try:
                    badeconomics.contributor.add(user)
                except:  # banned
                    continue

                if contributor not in zoning['whitelist']:
                    print("Granting /u/{} a permit."
                        .format(contributor, delta))
                    expires = date.today() + timedelta(PERMIT_LENGTH)
                    user.message(
                        PM_GRANTED_SUBJECT,
                        PM_GRANTED_TEXT.format(user=contributor,
                                               expires=expires))

    for contributor in zoning['whitelist']:
        user = reddit.redditor(contributor)
        if contributor not in sub_contributors:
            badeconomics.contributor.add(user)


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
