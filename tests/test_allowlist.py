import pytest
from datetime import timedelta

from hoa_bot import PERMIT_LENGTH


def test_empty_commit(gen_allowlist):
    allowlist = gen_allowlist({})
    assert allowlist.output is None
    allowlist.commit()
    assert allowlist.output is None


def test_commit_nochange(gen_allowlist):
    allowlist = gen_allowlist({'a': pytest.TODAY})
    allowlist.commit()
    assert allowlist.output is None


def test_simple_add(gen_allowlist):
    allowlist = gen_allowlist({})
    assert allowlist.update('piketty', pytest.TODAY)
    assert allowlist.output is None
    allowlist.commit()
    assert allowlist.output[allowlist.PERMIT_KEY] == {'piketty': pytest.TODAY}
    assert allowlist.permits() == {'piketty': pytest.TODAY}


def test_simple_delete(gen_allowlist):
    d = {'piketty': pytest.TODAY}
    allowlist = gen_allowlist(d)
    allowlist.delete('piketty')
    assert allowlist.output is None
    allowlist.commit()
    assert allowlist.output[allowlist.PERMIT_KEY] == {}
    assert allowlist.permits() == {}


def test_add_update(gen_allowlist):
    d = {'piketty': pytest.TODAY}
    allowlist = gen_allowlist(d)
    assert not allowlist.update('piketty', pytest.TODAY)
    assert allowlist.update('summers', pytest.YESTERDAY)
    allowlist.commit()
    expected_output = {'piketty': pytest.TODAY, 'summers': pytest.YESTERDAY}
    assert allowlist.output[allowlist.PERMIT_KEY] == expected_output
    assert allowlist.permits() == expected_output


def test_add_older_permit(gen_allowlist):
    d = {'piketty': pytest.TODAY}
    allowlist = gen_allowlist(d)
    assert not allowlist.update('piketty', pytest.YESTERDAY)
    allowlist.commit()
    assert allowlist.output is None  # No change
    assert allowlist.permits() == d


def test_add_newer_permit(gen_allowlist):
    d = {'piketty': pytest.TODAY}
    allowlist = gen_allowlist(d)
    assert allowlist.update('piketty', pytest.TOMORROW)
    allowlist.commit()
    expected_output = {'piketty': pytest.TOMORROW}
    assert allowlist.output[allowlist.PERMIT_KEY] == expected_output
    assert allowlist.permits() == expected_output


def test_add_expired_permit(gen_allowlist):
    d = {}
    allowlist = gen_allowlist(d)
    assert not allowlist.update(
        'piketty', pytest.TODAY - timedelta(days=PERMIT_LENGTH + 1)
    )
    allowlist.commit()
    assert allowlist.output is None  # No change
    assert allowlist.permits() == {}
