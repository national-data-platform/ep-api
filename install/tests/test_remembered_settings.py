"""
Tests for the answers a Federation configuration remembers (issue #287).

The behaviour these protect is what makes the round trip safe to run: an
installation must not be stopped by a settings response it cannot read, and
nothing that is not an answer — a credential above all — must travel to a
service that has no use for it.
"""

import json
import shlex
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from remembered_settings import (  # noqa: E402
    REMEMBERED_KEYS,
    as_shell_assignments,
    from_payload,
    main,
    to_payload,
)

ANSWERS = {
    "backend": "ckan",
    "want_s3": "yes",
    "ep_api_port": "8002",
    "want_access_requests": "no",
}


class TestWhatTravels:
    """What is sent is answers, and only answers."""

    def test_the_answers_are_sent_under_settings(self):
        body = json.loads(to_payload(ANSWERS))

        assert body["settings"]["backend"] == "ckan"
        assert body["settings"]["ep_api_port"] == "8002"

    def test_a_credential_cannot_be_smuggled_in_by_name(self):
        """
        The guard that matters. The installer asks for CKAN and S3 keys in
        the same breath as these answers, and a stored credential would end
        up in a configuration document this Endpoint does not control.
        """
        body = json.loads(
            to_payload(
                {
                    "backend": "ckan",
                    "ckan_api_key": "secret",
                    "s3_secret_key": "secret",
                    "remember_token": "secret",
                }
            )
        )

        assert "secret" not in json.dumps(body)
        assert set(body["settings"]) == {"backend"}

    def test_no_credential_key_is_remembered(self):
        """Read as a list: nothing credential-shaped is in it."""
        for key in REMEMBERED_KEYS:
            assert "key" not in key
            assert "password" not in key
            assert "secret" not in key
            assert "token" not in key

    def test_an_unanswered_question_is_not_sent(self):
        body = json.loads(to_payload({"backend": "none", "want_s3": None}))

        assert "want_s3" not in body["settings"]

    def test_an_empty_answer_still_travels(self):
        """
        Stored as given: an answer cleared on purpose has to overwrite what
        was remembered, or clearing one would be impossible.
        """
        body = json.loads(to_payload({"backend": "none", "ckan_url": ""}))

        assert body["settings"]["ckan_url"] == ""

    def test_the_body_is_json(self):
        json.loads(to_payload(ANSWERS))


class TestWhatComesBack:
    """Reading remembered answers must never stop an installation."""

    def test_the_answers_are_read(self):
        assert from_payload(json.dumps({"settings": ANSWERS})) == ANSWERS

    def test_an_endpoint_that_stored_nothing_yields_nothing(self):
        assert from_payload(json.dumps({"settings": {}})) == {}

    @pytest.mark.parametrize(
        "body",
        [
            "",
            "not json at all",
            "null",
            "[]",
            '{"settings": null}',
            '{"settings": "a string"}',
            '{"settings": ["a", "list"]}',
            '{"detail": "Configuration not found"}',
            "<html>502 Bad Gateway</html>",
        ],
    )
    def test_a_body_that_cannot_be_read_yields_nothing(self, body):
        """
        None of these raise. A Federation that is misconfigured, down or
        behind a proxy that answers HTML must cost the operator their
        remembered answers, not their installation.
        """
        assert from_payload(body) == {}

    def test_a_stored_key_this_version_does_not_know_is_ignored(self):
        """
        Left alone rather than guessed at, so an Endpoint that stored more
        than this installer understands keeps it.
        """
        answers = from_payload(
            json.dumps({"settings": {"backend": "ckan", "from_the_future": "x"}})
        )

        assert answers == {"backend": "ckan"}

    def test_a_stored_empty_value_does_not_override_a_default(self):
        answers = from_payload(
            json.dumps({"settings": {"backend": "", "want_s3": "no"}})
        )

        assert "backend" not in answers
        assert answers["want_s3"] == "no"

    def test_a_round_trip_keeps_the_answers(self):
        assert from_payload(to_payload(ANSWERS)) == ANSWERS


class TestTheShellReadsThemSafely:
    """The installer evals this, so quoting is not cosmetic."""

    def test_each_answer_is_one_assignment(self):
        rendered = as_shell_assignments({"backend": "ckan", "want_s3": "yes"})

        assert "backend='ckan'" in rendered
        assert "want_s3='yes'" in rendered

    def test_a_value_with_a_space_stays_one_word(self):
        rendered = as_shell_assignments({"auth_api_url": "http://host/a b"})

        assert rendered == "auth_api_url='http://host/a b'"

    def test_a_value_cannot_close_its_quote_and_run_a_command(self):
        """
        A stored value reaches this from a remote service, so it is treated
        as hostile input rather than as something this installer wrote.

        Checked by parsing it the way a shell parses it: the result has to be
        one word whose value is the literal that was stored, not two words
        with a command in the second.
        """
        hostile = "x'; touch /tmp/pwned; '"

        rendered = as_shell_assignments({"backend": hostile})

        assert shlex.split(rendered) == ["backend=" + hostile]

    def test_nothing_remembered_renders_nothing(self):
        assert as_shell_assignments({}) == ""


class TestTheCommandLine:
    """How install.sh calls it."""

    def test_load_prints_assignments(self, capsys):
        code = main(["x", "load", json.dumps({"settings": {"backend": "ckan"}})])

        assert code == 0
        assert "backend='ckan'" in capsys.readouterr().out

    def test_load_without_a_body_prints_nothing_and_succeeds(self, capsys):
        code = main(["x", "load"])

        assert code == 0
        assert capsys.readouterr().out.strip() == ""

    def test_save_prints_a_body(self, capsys):
        code = main(["x", "save", "backend=ckan", "ep_api_port=8002"])

        assert code == 0
        body = json.loads(capsys.readouterr().out)
        assert body["settings"]["backend"] == "ckan"

    def test_save_handles_a_value_containing_an_equals_sign(self):
        """``key=value`` splits once: a URL with a query string survives."""
        body = json.loads(to_payload({"auth_api_url": "http://h/a?b=c"}))

        assert body["settings"]["auth_api_url"] == "http://h/a?b=c"

    def test_an_unknown_action_fails(self, capsys):
        assert main(["x", "frobnicate"]) == 2

    def test_no_action_fails(self, capsys):
        assert main(["x"]) == 2
