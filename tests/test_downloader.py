import threading

from src.downloader import TASKS, _classify_error


def _e(msg):
    return Exception(msg)


def test_classify_invalid_url():
    _, kind = _classify_error(_e("is not a valid url"))
    assert kind == "invalid_url"


def test_classify_private():
    _, kind = _classify_error(_e("private video"))
    assert kind == "private"


def test_classify_network():
    _, kind = _classify_error(_e("urlopen error: timed out"))
    assert kind == "network_error"


def test_classify_unknown():
    _, kind = _classify_error(_e("some weird thing happened"))
    assert kind == "unknown"


def test_task_cleanup():
    task_id = "cleanup-test"
    TASKS[task_id] = {"status": "done"}
    t = threading.Timer(0.05, TASKS.pop, args=(task_id, None))
    t.start()
    t.join()
    assert task_id not in TASKS
