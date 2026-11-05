"""Provider HTTP genérico (fal, Replicate, OpenAI images, Stability...) via urllib.

Config declarativa no campaign.json: url, headers, corpo-template e onde ler a imagem
na resposta (url ou base64), com polling opcional para APIs assíncronas.
"""

import base64
import json
import os
import time
import urllib.request

from .base import Provider


def _dig(obj, path):
    cur = obj
    for part in path.split("."):
        cur = cur[int(part)] if isinstance(cur, list) else cur[part]
    return cur


class HttpAPI(Provider):
    name = "http"

    def __init__(self, cfg):
        self.cfg = cfg
        self.name = cfg.get("name", "http")
        self.credits_per_image = cfg.get("credits_per_image", 0.0)
        self.credits_per_video = cfg.get("credits_per_video", 0.0)

    def note(self):
        return self.cfg.get("note", self.cfg.get("url", ""))

    def _post(self, url, payload, headers):
        req = urllib.request.Request(url, data=json.dumps(payload).encode(),
                                     headers={"Content-Type": "application/json", **headers},
                                     method="POST")
        with urllib.request.urlopen(req, timeout=self.cfg.get("timeout", 120)) as r:
            return json.load(r)

    def _get(self, url, headers):
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req, timeout=self.cfg.get("timeout", 60)) as r:
            return json.load(r)

    def generate(self, job):
        cfg = self.cfg
        body = json.loads(json.dumps(cfg.get("body", {}))
                          .replace("{prompt}", json.dumps(job["prompt"])[1:-1])
                          .replace("{n}", str(job.get("n", 1)))
                          .replace("{aspect}", job.get("aspect", "1:1"))
                          .replace("{duration}", str(job.get("duration", 5))))
        headers = dict(cfg.get("headers", {}))
        if cfg.get("api_key_env"):
            headers.setdefault("Authorization", "Bearer " + os.environ[cfg["api_key_env"]])
        resp = self._post(cfg["url"], body, headers)

        poll = cfg.get("poll")
        if poll:
            url = poll["url"].format(id=_dig(resp, poll.get("id_path", "id")))
            deadline = time.time() + poll.get("max_wait", 300)
            while time.time() < deadline:
                resp = self._get(url, headers)
                if _dig(resp, poll["status_path"]) in poll.get("done_values", ["succeeded", "completed"]):
                    break
                time.sleep(poll.get("interval", 3))
            else:
                raise TimeoutError(f"Provider {self.name} não terminou o job {job['id']}.")

        out = []
        results = _dig(resp, cfg.get("results_path", "data"))
        results = results if isinstance(results, list) else [results]
        for i, item in enumerate(results[:job.get("n", 1)]):
            ext = ".mp4" if job.get("kind") == "video" else ".png"
            dest = os.path.join(job["out_dir"], f"{job['id']}_{i + 1}{ext}")
            os.makedirs(job["out_dir"], exist_ok=True)
            if cfg.get("result") == "b64":
                with open(dest, "wb") as f:
                    f.write(base64.b64decode(_dig(item, cfg.get("field", "b64_json"))))
            else:
                url = _dig(item, cfg.get("field", "url")) if isinstance(item, dict) else item
                urllib.request.urlretrieve(url, dest)
            out.append(dest)
        return out