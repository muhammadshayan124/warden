import time

from warden.confirmation import ConfirmationStore


def test_verify_succeeds_for_matching_action_and_fingerprint():
    store = ConfirmationStore(ttl_seconds=120.0)
    token = store.create("delete_file", "delete:/tmp/x")
    assert store.verify(token, "delete_file", "delete:/tmp/x") is True


def test_token_is_single_use():
    store = ConfirmationStore(ttl_seconds=120.0)
    token = store.create("delete_file", "delete:/tmp/x")
    assert store.verify(token, "delete_file", "delete:/tmp/x") is True
    assert store.verify(token, "delete_file", "delete:/tmp/x") is False


def test_verify_rejects_wrong_action():
    store = ConfirmationStore(ttl_seconds=120.0)
    token = store.create("delete_file", "delete:/tmp/x")
    assert store.verify(token, "kill_process", "delete:/tmp/x") is False


def test_verify_rejects_wrong_fingerprint_reused_across_targets():
    store = ConfirmationStore(ttl_seconds=120.0)
    token = store.create("delete_file", "delete:/tmp/a")
    # A token minted for deleting file A must not authorize deleting file B.
    assert store.verify(token, "delete_file", "delete:/tmp/b") is False


def test_verify_rejects_unknown_token():
    store = ConfirmationStore(ttl_seconds=120.0)
    assert store.verify("not-a-real-token", "delete_file", "delete:/tmp/x") is False


def test_verify_rejects_expired_token():
    store = ConfirmationStore(ttl_seconds=0.01)
    token = store.create("delete_file", "delete:/tmp/x")
    time.sleep(0.05)
    assert store.verify(token, "delete_file", "delete:/tmp/x") is False
