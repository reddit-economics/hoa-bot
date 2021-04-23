import pytest
import yaml

from datetime import date, timedelta
from unittest.mock import MagicMock, patch

from hoa_bot import WallBot, WikiAllowlist


def pytest_configure():
    pytest.TODAY = date.today()
    pytest.YESTERDAY = pytest.TODAY - timedelta(days=1)
    pytest.TOMORROW = pytest.TODAY + timedelta(days=1)


@pytest.fixture
def gen_allowlist():
    def f(permits=None, permallowed=None):
        if permits is None:
            permits = {}
        if permallowed is None:
            permallowed = []
        subreddit = MagicMock()
        wiki_page = subreddit.wiki['zoning_whitelist']
        wiki_page.content_md = yaml.safe_dump({
            WikiAllowlist.PERMIT_KEY: permits,
            WikiAllowlist.PERMALLOWED_KEY: permallowed,
        })

        allowlist = WikiAllowlist(subreddit)
        allowlist.output = None

        def save_output(yml):
            allowlist.output = yaml.safe_load(yml)
            wiki_page.content_md = yml

        wiki_page.edit.side_effect = save_output
        return allowlist

    return f


class TestRedditor:
    def __init__(self, username):
        self.username = username
        self.message = MagicMock()

    def __eq__(self, value):
        if self.username == value:
            return True
        if hasattr(value, 'username') and self.username == value.username:
            return True


class TestRedditorFactory:
    def __init__(self):
        self.redditors = {}

    def __call__(self, username):
        if username not in self.redditors:
            self.redditors[username] = TestRedditor(username)
        return self.redditors[username]


@pytest.fixture
def gen_subreddit(gen_allowlist):
    def f(
        posts=None,
        modmail=None,
        contributors=None,
        moderators=None,
    ):
        if posts is None:
            posts = []
        if modmail is None:
            modmail = []
        if contributors is None:
            contributors = []
        if moderators is None:
            moderators = []

        res = MagicMock()
        redditor_factory = TestRedditorFactory()
        res.redditor_factory = redditor_factory
        res.moderator.return_value = moderators
        res.contributor.return_value = [
            redditor_factory(u) for u in contributors
        ]

        res.posts = [
            MagicMock(
                subject=p.get('subject'),
                author=p.get('author'),
                created_utc=p.get('created_utc'),
                link_flair_text=p.get('link_flair_text'),
            )
            for p in posts
        ]
        res.new.return_value = res.posts

        res.modmail_conversations = [
            MagicMock(
                subject=c.get('subject'),
                participant=c.get('participant'),
                messages=[
                    MagicMock(
                        author=m.get('author'),
                        date=m.get('date'),
                        body_markdown=m.get('body_markdown'),
                    )
                    for m in c.get('messages', [])
                ]
            )
            for c in modmail
        ]
        res.modmail.conversations.return_value = res.modmail_conversations
        return res

    return f


class TestWallBot(WallBot):
    def __init__(self, config):
        self.config = config


@pytest.fixture
@patch('praw.Reddit')
def gen_bot(monkeypatch, gen_allowlist, gen_subreddit):
    def f(
        posts=None,
        modmail=None,
        contributors=None,
        moderators=None,
        permits=None,
        permallowed=None,
    ):
        res = TestWallBot(
            {
                'reddit': {
                    'client_id': 'ADJFHKDSFHS',
                    'client_secret': '8932847bdsfkdhs',
                    'username': 'abc123',
                    'password': 'hunter2',
                }
            }
        )
        res.allowlist = gen_allowlist(permits=permits, permallowed=permallowed)
        res.subreddit = gen_subreddit(
            posts=posts,
            modmail=modmail,
            contributors=contributors,
            moderators=moderators
        )
        res.reddit = MagicMock()
        res.reddit.redditor = res.subreddit.redditor_factory
        return res

    return f
