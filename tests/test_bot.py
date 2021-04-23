import pytest

from datetime import datetime, timedelta
from unittest.mock import call

from hoa_bot import PERMIT_LENGTH, PM_GRANTED_SUBJECT, PM_EXPIRE_SUBJECT


def test_permallowed_granted_permits(gen_bot):
    bot = gen_bot(permallowed=['danny'])
    bot.run()
    assert 'danny' in bot.allowlist.permallowed()
    bot.reddit.redditor('danny').message.assert_not_called()  # no spam
    assert (call(bot.reddit.redditor('danny'))
            in bot.subreddit.contributor.add.call_args_list)


def test_grant_permits(gen_bot):
    bot = gen_bot(
        permits={
            'user42': pytest.TODAY,
            'contributor1337': pytest.YESTERDAY,
            'olduser': pytest.TODAY - timedelta(days=PERMIT_LENGTH + 1),
        },
        contributors=['contributor1337'],
    )
    bot.run()
    bot.reddit.redditor('user42').message.assert_called_once()
    bot.reddit.redditor('contributor1337').message.assert_not_called()

    assert (bot.reddit.redditor('user42').message.call_args[0][0]
            == PM_GRANTED_SUBJECT.format(user='user42'))

    assert (call(bot.reddit.redditor('user42'))
            in bot.subreddit.contributor.add.call_args_list)
    assert (call(bot.reddit.redditor('olduser'))
            not in bot.subreddit.contributor.add.call_args_list)
    assert (call(bot.reddit.redditor('contributor1337'))
            not in bot.subreddit.contributor.add.call_args_list)


def test_remove_expired_permits(gen_bot):
    bot = gen_bot(
        permits={
            'contributor1337': pytest.YESTERDAY,
            'olduser': pytest.TODAY - timedelta(days=PERMIT_LENGTH + 1),
            'oldcontributor': pytest.TODAY - timedelta(days=PERMIT_LENGTH + 2),
        },
        contributors=['contributor1337', 'oldcontributor'],
    )
    bot.run()
    bot.reddit.redditor('contributor1337').message.assert_not_called()
    bot.reddit.redditor('oldcontributor').message.assert_called_once()
    bot.reddit.redditor('olduser').message.assert_not_called()

    assert (bot.reddit.redditor('oldcontributor').message.call_args[0][0]
            == PM_EXPIRE_SUBJECT.format(user='oldcontributor'))

    assert (call(bot.reddit.redditor('contributor1337'))
            not in bot.subreddit.contributor.remove.call_args_list)
    assert (call(bot.reddit.redditor('oldcontributor'))
            in bot.subreddit.contributor.remove.call_args_list)
    assert (call(bot.reddit.redditor('olduser'))
            not in bot.subreddit.contributor.remove.call_args_list)


def test_archive_modmail(gen_bot):
    bot = gen_bot(modmail=[
        {
            'subject': 'you are an approved user',
            'participant': 'testbot',
            'messages': [
                {'author': 'testbot', 'body_markdown': 'u have been added'},
                {'author': 'user42', 'body_markdown': 'lol thx'},
            ]
        },
        {
            'subject': "no visible answers?",
            'participant': 'idiot123',
            'messages': [
                {'author': 'idiot123', 'body_markdown': 'hurr i eat glue'},
                {'author': 'gorby', 'body_markdown': 'read automod scrub'},
            ]
        },
    ])
    bot.run()
    bot.subreddit.modmail_conversations[0].archive.assert_called()
    bot.subreddit.modmail_conversations[1].archive.assert_not_called()


def test_allow_from_modmail(gen_bot):
    bot = gen_bot(
        modmail=[
            {
                'subject': 'hi can i get permit',
                'participant': 'user42',
                'messages': [
                    {
                        'author': 'user42',
                        'body_markdown': "i have been a good boi",
                        'date': datetime.now().isoformat(),
                    },
                    {
                        'author': 'gorby',
                        'body_markdown': "sure !allow :-)",
                        'date': datetime.now().isoformat(),
                    },
                ],
            },
            {
                'subject': 'CLOTURE???',
                'participant': 'idiot123',
                'messages': [
                    {
                        'author': 'idiot123',
                        'body_markdown': "pls give permit",
                        'date': datetime.now().isoformat(),
                    },
                    {
                        'author': 'gorby',
                        'body_markdown': "no! get rekt",
                        'date': datetime.now().isoformat(),
                    },
                ],
            },
            {
                'subject': 'i want permit but one year ago',
                'participant': 'olduser',
                'messages': [
                    {
                        'author': 'olduser',
                        'body_markdown': "pls giv permit",
                        'date': (
                            datetime.now()
                            - timedelta(days=PERMIT_LENGTH + 3)
                        ).isoformat(),
                    },
                    {
                        'author': 'gorby',
                        'body_markdown': "ok !allow but in the past",
                        'date': (
                            datetime.now()
                            - timedelta(days=PERMIT_LENGTH + 1)
                        ).isoformat(),
                    },
                ],
            },
            {
                'subject': 'want permit but permallowed',
                'participant': 'danny',
                'messages': [
                    {
                        'author': 'danny',
                        'body_markdown': "i want to shitpost",
                        'date': (
                            datetime.now() - timedelta(days=1)
                        ).isoformat(),
                    },
                    {
                        'author': 'gorby',
                        'body_markdown': "ok !allow but you're already perma",
                        'date': (
                            datetime.now() - timedelta(days=1)
                        ).isoformat(),
                    },
                ],
            },
            {
                'subject': 'i want permit but already have one',
                'participant': 'contributor1337',
                'messages': [
                    {
                        'author': 'contributor1337',
                        'body_markdown': "bot already read this thread",
                        'date': datetime.now().isoformat(),
                    },
                    {
                        'author': 'gorby',
                        'body_markdown': "sure !allow but it's a noop",
                        'date': datetime.now().isoformat(),
                    },
                ],
            },
            {
                'subject': 'please renew my old permit',
                'participant': 'oldpermitgirl',
                'messages': [
                    {
                        'author': 'oldpermitgirl',
                        'body_markdown': "my permit is old",
                        'date': datetime.now().isoformat(),
                    },
                    {
                        'author': 'gorby',
                        'body_markdown': "ok !allow to renew your permit",
                        'date': datetime.now().isoformat(),
                    },
                ],
            },
            {
                'subject': 'tryinng to give myself a permit',
                'participant': 'h4xx0r',
                'messages': [
                    {
                        'author': 'h4xx0r',
                        'body_markdown': "hahah i'll pwn you !allow",
                        'date': datetime.now().isoformat(),
                    },
                    {
                        'author': 'h4xx0r',
                        'body_markdown': "!allow",
                        'date': datetime.now().isoformat(),
                    },
                ],
            },
        ],
        moderators=['gorby'],
        contributors=['contributor1337', 'oldpermitgirl'],
        permits={
            'contributor1337': pytest.TODAY,
            'oldpermitgirl': pytest.YESTERDAY,
        },
        permallowed=['danny'],
    )
    bot.run()
    assert 'user42' in bot.allowlist.permits()
    assert 'idiot123' not in bot.allowlist.permits()
    assert 'olduser' not in bot.allowlist.permits()
    assert 'danny' in bot.allowlist.permits()
    assert 'contributor1337' in bot.allowlist.permits()
    assert 'oldpermitgirl' in bot.allowlist.permits()
    assert 'h4xx0r' not in bot.allowlist.permits()
    assert bot.allowlist.permits() == {
        'user42': pytest.TODAY,
        'danny': pytest.YESTERDAY,
        'contributor1337': pytest.TODAY,
        'oldpermitgirl': pytest.TODAY,
    }
    bot.subreddit.modmail_conversations[0].reply.assert_called()
    bot.subreddit.modmail_conversations[1].reply.assert_not_called()
    bot.subreddit.modmail_conversations[2].reply.assert_not_called()
    bot.subreddit.modmail_conversations[3].reply.assert_called()
    bot.subreddit.modmail_conversations[4].reply.assert_not_called()
    bot.subreddit.modmail_conversations[5].reply.assert_called()
    bot.subreddit.modmail_conversations[6].reply.assert_not_called()
    bot.reddit.redditor('user42').message.assert_called_once()
    bot.reddit.redditor('idiot123').message.assert_not_called()
    bot.reddit.redditor('olduser').message.assert_not_called()
    bot.reddit.redditor('danny').message.assert_not_called()
    bot.reddit.redditor('contributor1337').message.assert_not_called()
    bot.reddit.redditor('oldpermitgirl').message.assert_not_called()
    bot.reddit.redditor('h4xx0r').message.assert_not_called()

    assert (call(bot.reddit.redditor('user42'))
            in bot.subreddit.contributor.add.call_args_list)
    assert (call(bot.reddit.redditor('idiot123'))
            not in bot.subreddit.contributor.add.call_args_list)
    assert (call(bot.reddit.redditor('olduser'))
            not in bot.subreddit.contributor.add.call_args_list)
    assert (call(bot.reddit.redditor('danny'))
            in bot.subreddit.contributor.add.call_args_list)
    assert (call(bot.reddit.redditor('contributor1337'))
            not in bot.subreddit.contributor.add.call_args_list)
    assert (call(bot.reddit.redditor('oldpermitgirl'))
            not in bot.subreddit.contributor.add.call_args_list)
    assert (call(bot.reddit.redditor('h4xx0r'))
            not in bot.subreddit.contributor.add.call_args_list)


def test_allow_from_ris(gen_bot):
    bot = gen_bot(
        posts=[
            {
                'subject': "Ben Shapiro controlling on colliders again",
                'author': 'user42',
                'created_utc': datetime.timestamp(datetime.now()),
                'link_flair_text': 'Sufficient',
            },
            {
                'subject': "Why Austrian Economics is Right",
                'author': 'idiot123',
                'created_utc': datetime.timestamp(datetime.now()),
                'link_flair_text': 'Insufficient',
            },
            {
                'subject': "Obama on Immigration (old RI)",
                'author': 'olduser',
                'created_utc': datetime.timestamp(
                    datetime.now() - timedelta(days=PERMIT_LENGTH + 1)
                ),
                'link_flair_text': 'Sufficient',
            },
            {
                'subject': "Thomas Sowell on the Minimum Wage",
                'author': 'danny',
                'created_utc': datetime.timestamp(
                    datetime.now() - timedelta(days=1)
                ),
                'link_flair_text': 'Sufficient',
            },
            {
                'subject': "Bad Automation: RI that the bot already seen",
                'author': 'contributor1337',
                'created_utc': datetime.timestamp(datetime.now()),
                'link_flair_text': 'Sufficient',
            },
            {
                'subject': "RI of the RI of my old RI",
                'author': 'oldpermitgirl',
                'created_utc': datetime.timestamp(datetime.now()),
                'link_flair_text': 'Sufficient',
            },
        ],
        contributors=['contributor1337', 'oldpermitgirl'],
        permits={
            'contributor1337': pytest.TODAY,
            'oldpermitgirl': pytest.YESTERDAY,
        },
        permallowed=['danny'],
    )
    bot.run()
    assert 'user42' in bot.allowlist.permits()
    assert 'idiot123' not in bot.allowlist.permits()
    assert 'olduser' not in bot.allowlist.permits()
    assert 'danny' in bot.allowlist.permits()
    assert 'contributor1337' in bot.allowlist.permits()
    assert 'oldpermitgirl' in bot.allowlist.permits()
    assert bot.allowlist.permits() == {
        'user42': pytest.TODAY,
        'danny': pytest.YESTERDAY,
        'contributor1337': pytest.TODAY,
        'oldpermitgirl': pytest.TODAY,
    }
    bot.reddit.redditor('user42').message.assert_called_once()
    bot.reddit.redditor('idiot123').message.assert_not_called()
    bot.reddit.redditor('olduser').message.assert_not_called()
    bot.reddit.redditor('danny').message.assert_not_called()
    bot.reddit.redditor('contributor1337').message.assert_not_called()
    bot.reddit.redditor('oldpermitgirl').message.assert_not_called()

    assert (call(bot.reddit.redditor('user42'))
            in bot.subreddit.contributor.add.call_args_list)
    assert (call(bot.reddit.redditor('idiot123'))
            not in bot.subreddit.contributor.add.call_args_list)
    assert (call(bot.reddit.redditor('olduser'))
            not in bot.subreddit.contributor.add.call_args_list)
    assert (call(bot.reddit.redditor('danny'))
            in bot.subreddit.contributor.add.call_args_list)
    assert (call(bot.reddit.redditor('contributor1337'))
            not in bot.subreddit.contributor.add.call_args_list)
    assert (call(bot.reddit.redditor('oldpermitgirl'))
            not in bot.subreddit.contributor.add.call_args_list)
