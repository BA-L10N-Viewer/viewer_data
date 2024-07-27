import os
import logging

logging.basicConfig(level=logging.DEBUG)
REPO_BASEPATH = os.path.split(os.path.split(os.path.split(__file__)[0])[0])[0]


def get_path_based_on_repopath(target_path, base_path=REPO_BASEPATH):
    return os.path.join(base_path, target_path)


def repeat_until_its_ok(func, *args, **kwargs):
    while True:
        try:
            return func(*args, **kwargs)
        except Exception as e:
            logging.error(f"[Func: {func.__name__}]: {e}")
