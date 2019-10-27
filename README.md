# Homeowner Association Bot

The [/r/badeconomics](https://www.reddit.com/r/badeconomics/) subreddit has
implemented a [zoning
regime](https://www.reddit.com/r/badeconomics/comments/cccui4/exclusionary_zoning_is_coming_to_rbadeconomics/).

This bot helps preserving the character of our neighborhood by automatically
maintaining a list of neighbors in possession of a zoning permit, to allow them
to post in the Mixed Use Development sticky.

## Features

- Watches the last posts to grant a permit to the RIs that have been tagged as
  sufficient
- Makes permit expires after a predetermined duration
- Notifies people when a permit has been granted to them
- Notifies people when their permit has expired
- Maintain the current list of permits in the subreddit wiki


## Usage

The script is a oneshot script, not a daemon. You should put in a cron or a
systemd timer to make it run every 5 minutes
