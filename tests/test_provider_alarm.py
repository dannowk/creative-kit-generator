"""Provider failures open a browser fix box: alarm record, local key save, retry handoff."""

import json
import os
import shutil
import tempfile
import unittest
import urllib.error
from unittest import mock

from PIL import Image

from kit import campaign, providers
from kit.providers.base import Provider
from kit.providers.http_api import HttpAPI


def _http_error(code):
    return urllib.error.HTTPError("http://x", code, "Invalid API key", {}, None)


class Boom(Provider):
    name = "boom"

    def generate(self, job):
        raise _http_error(401)


class Ok(Provider):
    name = "ok"

    def generate(self, job):
        os.makedirs(job["out_dir"], exist_ok=True)
        p = os.path.join(job["out_dir"], job["id"] + "_1.png")
        Image.new("RGB", (8, 8), (200, 30, 30)).save(p)
        return [p]


class ProviderAlarm(unittest.TestCase):
    def setUp(self):
        self.root = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.root)
        self.camp = {"_root": self.root,
                     "provider": {"name": "http", "api_key_env": "TEST_KEY"},
                     "asset_jobs": [{"id": "hero", "prompt": "a hero", "kind": "image"}]}

    def test_auth_failure_writes_alarm(self):
        with mock.patch.object(providers, "get_provider", return_value=Boom()):
            result = providers.run_assets(self.camp)
        self.assertEqual(result["generated"], [])
        self.assertEqual([f["id"] for f in result["failed"]], ["hero"])
        alarm = providers.read_alarm(self.root)
        self.assertIsNotNone(alarm)
        self.assertEqual(alarm["provider"], "boom")
        self.assertTrue(alarm["jobs"][0]["auth"])
        self.assertTrue(alarm["keyable"])
        self.assertIn("401", alarm["jobs"][0]["error"])

    def test_success_clears_alarm(self):
        with mock.patch.object(providers, "get_provider", return_value=Boom()):
            providers.run_assets(self.camp)
        self.assertIsNotNone(providers.read_alarm(self.root))
        with mock.patch.object(providers, "get_provider", return_value=Ok()):
            result = providers.run_assets(self.camp)
        self.assertEqual(result["failed"], [])
        self.assertIsNone(providers.read_alarm(self.root))

    def test_non_auth_failure_still_alarms(self):
        class Refused(Provider):
            name = "refused"

            def generate(self, job):
                raise urllib.error.URLError("connection refused")

        self.camp["provider"] = {"name": "http"}
        with mock.patch.object(providers, "get_provider", return_value=Refused()):
            providers.run_assets(self.camp)
        alarm = providers.read_alarm(self.root)
        self.assertFalse(alarm["jobs"][0]["auth"])
        self.assertFalse(alarm["keyable"])

    def test_restart_removes_alarm(self):
        with mock.patch.object(providers, "get_provider", return_value=Boom()):
            providers.run_assets(self.camp)
        campaign.restart(self.root)
        self.assertIsNone(providers.read_alarm(self.root))


class HttpApiKey(unittest.TestCase):
    def setUp(self):
        self.job = {"id": "hero", "prompt": "a hero", "out_dir": tempfile.mkdtemp()}
        self.addCleanup(shutil.rmtree, self.job["out_dir"])

    def test_file_key_wins_over_env(self):
        cfg = {"url": "http://x", "api_key": "file-key", "api_key_env": "TEST_KEY",
               "results_path": "data", "field": "url"}
        with mock.patch.dict(os.environ, {"TEST_KEY": "env-key"}), \
                mock.patch.object(HttpAPI, "_post", return_value={"data": []}) as post:
            HttpAPI(cfg).generate(self.job)
        headers = post.call_args[0][2]
        self.assertEqual(headers["Authorization"], "Bearer file-key")

    def test_missing_env_raises_friendly_keyerror(self):
        cfg = {"url": "http://x", "api_key_env": "TEST_KEY_MISSING"}
        env = {k: v for k, v in os.environ.items() if k != "TEST_KEY_MISSING"}
        with mock.patch.dict(os.environ, env, clear=True):
            with self.assertRaises(KeyError) as ctx:
                HttpAPI(cfg).generate(self.job)
        self.assertIn("fix box", str(ctx.exception))

    def test_key_saved_in_campaign_json_is_used(self):
        root = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, root)
        cpath = os.path.join(root, "campaign.json")
        with open(cpath, "w") as f:
            json.dump({"provider": {"name": "http", "url": "http://x",
                                    "api_key_env": "TEST_KEY_MISSING"}}, f)
        with open(cpath) as f:
            camp = json.load(f)
        camp["provider"]["api_key"] = "saved-key"
        with open(cpath, "w") as f:
            json.dump(camp, f)
        with mock.patch.object(HttpAPI, "_post", return_value={"data": []}) as post:
            HttpAPI(camp["provider"]).generate({**self.job, "out_dir": root})
        self.assertEqual(post.call_args[0][2]["Authorization"], "Bearer saved-key")


if __name__ == "__main__":
    unittest.main()