import os
import tempfile
from unittest.mock import patch

from api.config.swagger_settings import Settings


def test_a_local_env_file_does_not_decide_these_answers():
    """
    Every settings class declares ``env_file=".env"``, so clearing
    ``os.environ`` is not enough to isolate a test: the file is read as well,
    and a development ``.env`` normally carries ``IS_PUBLIC=False``. That is
    what made the default test below fail on a maintainer's machine while
    passing in CI, where there is no ``.env`` (issue #283).
    """
    with tempfile.TemporaryDirectory() as directory:
        env_file = os.path.join(directory, ".env")
        with open(env_file, "w", encoding="utf-8") as handle:
            handle.write("IS_PUBLIC=False\n")

        previous = os.getcwd()
        os.chdir(directory)
        try:
            with patch.dict(os.environ, {}, clear=True):
                # What the file says, when it is allowed to speak.
                assert Settings().is_public is False
                # What these tests are actually about: the code default.
                assert Settings(_env_file=None).is_public is True
        finally:
            os.chdir(previous)


def test_public_variable_default():
    """
    Test that the default value of 'is_public' is True
    when the 'IS_PUBLIC' environment variable is not set.

    ``_env_file=None`` is what "not set" has to mean here; without it this
    reads whatever ``.env`` is in the working directory (issue #283).
    """
    with patch.dict(os.environ, {}, clear=True):
        settings = Settings(_env_file=None)
        assert settings.is_public is True


def test_public_variable_true():
    """
    Test that 'is_public' is True when the 'IS_PUBLIC' environment
    variable is set to 'True'.
    """
    with patch.dict(os.environ, {"IS_PUBLIC": "True"}):
        settings = Settings(_env_file=None)
        assert settings.is_public is True


def test_public_variable_false():
    """
    Test that 'is_public' is False when the 'IS_PUBLIC' environment
    variable is set to 'False'.
    """
    with patch.dict(os.environ, {"IS_PUBLIC": "False"}):
        settings = Settings(_env_file=None)
        assert settings.is_public is False
