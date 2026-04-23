import pytest

pytest.importorskip("apprise")

from radar.notify.apprise import AppriseNotifier


def test_apprise_rejects_all_invalid_urls():
    with pytest.raises(ValueError):
        AppriseNotifier(urls="not-a-real-scheme://nothing")


def test_apprise_registers_valid_url():
    notifier = AppriseNotifier(urls="ntfy://test-topic")
    assert notifier.name == "apprise"
