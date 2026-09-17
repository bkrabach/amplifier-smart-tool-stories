"""Owned authenticated loopback service. Content runs in an opaque sandbox, without credentials."""

import hmac
import json
import os
import secrets
import subprocess
import sys
import threading
import time
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from importlib.resources import files
from pathlib import Path
from urllib.parse import urlparse

from .errors import StoriesError, require
from .store import identity


class Dashboard:
    def __init__(self, api, story_id, revision_id=None, token=None):
        self.api, self.story_id, self.revision_id = api, story_id, revision_id
        self.token = token or secrets.token_urlsafe(32)
        owner = self
        self.operations = set()
        self.provider_lock = threading.RLock()
        self.provider_stop = threading.Event()
        self.provider_thread = None
        self.provider_job = {"status": "idle", "messages": []}

        class Handler(BaseHTTPRequestHandler):
            def log_message(self, *args):
                pass  # Access logs must not collect bearer credentials or material.

            def send(self, status, payload, mime="application/json", attachment=False):
                raw = (
                    payload
                    if isinstance(payload, bytes)
                    else payload.encode()
                    if isinstance(payload, str)
                    else json.dumps(payload).encode()
                )
                self.send_response(status)
                self.send_header("Content-Type", mime + "; charset=utf-8")
                self.send_header("Content-Length", str(len(raw)))
                self.send_header("Cache-Control", "no-store")
                self.send_header("X-Content-Type-Options", "nosniff")
                self.send_header("Referrer-Policy", "no-referrer")
                self.send_header(
                    "Content-Security-Policy",
                    "default-src 'none'; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline'; connect-src 'self'; frame-src 'self' about:; img-src data:; frame-ancestors 'none'",
                )
                if attachment:
                    extension = (
                        "pdf"
                        if mime == "application/pdf"
                        else "docx"
                        if "wordprocessingml" in mime
                        else "html"
                    )
                    self.send_header("Content-Disposition", f'attachment; filename="story.{extension}"')
                self.end_headers()
                self.wfile.write(raw)

            def allowed(self):
                origin = f"http://127.0.0.1:{owner.server.server_port}"
                return (
                    self.headers.get("Host") == origin.removeprefix("http://")
                    and self.headers.get("Origin", origin) == origin
                    and hmac.compare_digest(self.headers.get("Authorization", ""), "Bearer " + owner.token)
                )

            def do_GET(self):
                path = urlparse(self.path).path
                assets = {
                    "/": ("dashboard.html", "text/html"),
                    "/app.js": ("dashboard.js", "text/javascript"),
                    "/style.css": ("dashboard.css", "text/css"),
                    "/document-view.js": ("document-view.js", "text/javascript"),
                    "/provider-settings.js": ("provider-settings.js", "text/javascript"),
                    "/bridge.js": ("bridge.js", "text/plain"),
                }
                if path in assets:
                    name, mime = assets[path]
                    self.send(
                        200,
                        files("amplifier_smart_tool_stories").joinpath("resources", name).read_text(),
                        mime,
                    )
                else:
                    self.send(404, {"error": "not_found"})

            def do_POST(self):
                if not self.allowed():
                    self.send(403, {"error": "unauthorized"})
                    return
                try:
                    length = int(self.headers.get("Content-Length", "0"))
                    require(0 < length <= 200_000, "Request too large or empty.")
                    data = json.loads(self.rfile.read(length))
                    require(isinstance(data, dict), "Request must be an object.")
                    path = urlparse(self.path).path
                    if path == "/api/bootstrap":
                        result = {
                            "story": owner.api.get_story(owner.story_id),
                            "revision_id": owner.revision_id,
                        }
                    elif path == "/api/provider-settings":
                        result = {**owner.api.provider_settings(), "model_access": owner.api.model_env}
                    elif path == "/api/configure-provider":
                        with owner.provider_lock:
                            require(
                                owner.provider_job["status"] != "running",
                                "Wait for provider setup to finish.",
                                "provider_busy",
                            )
                            require(set(data) <= {"provider", "model"}, "Unknown setting.")
                            result = owner.api.configure_provider(**data)
                    elif path == "/api/provider-job":
                        with owner.provider_lock:
                            result = json.loads(json.dumps(owner.provider_job))
                    elif path == "/api/start-provider-job":
                        result = owner.start_provider_job(data)
                    elif path == "/api/stop":
                        owner.provider_stop.set()
                        for operation_id in list(owner.operations):
                            owner.api.cancel_operation(operation_id)
                        self.send(200, {"status": "stopped"})
                        threading.Thread(target=owner.server.shutdown, daemon=True).start()
                        return
                    elif path == "/api/download":
                        import base64

                        result = owner.api.get_export(
                            owner.story_id, data["revision_id"], data.get("format", "html")
                        )
                        self.send(
                            200, base64.b64decode(result["data_base64"]), result["mime_type"], attachment=True
                        )
                        return
                    else:
                        name = path.removeprefix("/api/").replace("-", "_")
                        require(
                            name
                            in {
                                "get_story",
                                "get_preview",
                                "select_revision",
                                "accept_revision",
                                "add_comment",
                                "respond",
                                "save_draft",
                                "get_operation",
                                "read_changes",
                            },
                            "Unknown route.",
                        )
                        if name == "get_operation":
                            op = owner.api.get_operation(data["operation_id"])
                            require(op["story_id"] == owner.story_id, "Wrong story.")
                            result = op
                        else:
                            data["story_id"] = owner.story_id
                            if name == "add_comment":
                                data["author"] = "user"
                            if name in {"add_comment", "respond"}:
                                with owner.provider_lock:
                                    require(
                                        owner.provider_job["status"] != "running",
                                        "Provider setup is in progress. Your draft is saved; send it when setup finishes.",
                                        "provider_busy",
                                    )
                                    result = getattr(owner.api, name)(**data)
                            else:
                                result = getattr(owner.api, name)(**data)
                        if isinstance(result, dict) and result.get("operation_id"):
                            owner.operations.add(result["operation_id"])
                    self.send(200, result)
                except StoriesError as exc:
                    self.send(400, exc.public())
                except (ValueError, KeyError, TypeError):
                    self.send(400, {"error": {"code": "invalid_input", "message": "Malformed request."}})

        self.server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        self.server.daemon_threads = True

    def start_provider_job(self, data):
        from .lib import Stories

        require(set(data) <= {"kind", "provider", "model"}, "Unknown provider action field.")
        kind = data.get("kind")
        require(kind in {"prepare", "test", "models", "login"}, "Unknown provider action.")
        require(
            self.api.model_env,
            "This viewer has no provider access. Reopen it with model_env enabled.",
            "model_access_required",
        )
        with self.provider_lock:
            require(
                self.provider_job["status"] != "running",
                "Another provider action is running.",
                "provider_busy",
            )
            story = self.api.get_story(self.story_id)
            ids = self.operations | {n["operation_id"] for n in story["annotations"] if n.get("operation_id")}
            require(
                not any(self.api.get_operation(i)["state"] in {"queued", "running"} for i in ids),
                "Wait for current story work to finish before testing or signing in.",
                "provider_busy",
            )
            target = Stories(self.api.store.path, model_env=True)
            target.configure_provider(data.get("provider"), data.get("model"))
            job = {"status": "running", "kind": kind, "provider": target.config.provider, "messages": []}
            self.provider_job = job

            def progress(text):
                with self.provider_lock:
                    job["messages"] = (job["messages"] + [str(text)[:2000]])[-30:]

            def run():
                from .providers import _job_context

                _job_context.cancel = self.provider_stop
                try:
                    if kind == "login":
                        result = target.provider_login(on_progress=progress)
                    elif kind == "models":
                        result = target.provider_models()
                    elif kind == "prepare":
                        result = target.prepare_runtime()
                    else:
                        result = target.test_provider()
                    with self.provider_lock:
                        job.update(status="succeeded", result=result)
                except StoriesError as exc:
                    with self.provider_lock:
                        job.update(status="failed", error=exc.public()["error"])
                except Exception:
                    with self.provider_lock:
                        job.update(
                            status="failed",
                            error={
                                "message": "Provider action failed.",
                                "remedy": "Check provider setup and retry.",
                            },
                        )

            self.provider_thread = threading.Thread(target=run, daemon=True)
            self.provider_thread.start()
            return {"status": "running", "provider": target.config.provider, "kind": kind}

    def serve(self):
        try:
            self.server.serve_forever(poll_interval=0.1)
        finally:
            self.provider_stop.set()
            if self.provider_thread:
                self.provider_thread.join(timeout=5)
            self.server.server_close()


def start(api, story_id, revision_id):
    service_id = identity("viewer")
    config_path = api.store.path / (service_id + ".json")
    config = {
        "service_id": service_id,
        "story_id": story_id,
        "revision_id": revision_id,
        "token": secrets.token_urlsafe(32),
        "model_env": api.model_env,
        "provider": api.config.public(),
        "feedback_provider_override": api._feedback_provider_override,
        "status": "starting",
    }
    fd = os.open(config_path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    with os.fdopen(fd, "w") as file:
        json.dump(config, file)
    proc = subprocess.Popen(
        [sys.executable, "-m", "amplifier_smart_tool_stories.dashboard", str(api.store.path), service_id],
        stdin=subprocess.DEVNULL,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        start_new_session=True,
    )
    for _ in range(150):
        if proc.poll() is not None:
            raise StoriesError("viewer_failed", "Viewer process could not start.")
        try:
            value = json.loads(config_path.read_text())
        except ValueError:
            value = {}
        if value.get("status") == "ready":
            return {
                "status": "ready",
                "service_id": service_id,
                "story_id": story_id,
                "url": value["url"] + "#" + value["token"],
            }
        time.sleep(0.1)
    proc.terminate()
    proc.wait(timeout=5)
    raise StoriesError("viewer_failed", "Viewer startup timed out.")


def stop(api, service_id):
    require(
        isinstance(service_id, str) and service_id.startswith("viewer_") and service_id[7:].isalnum(),
        "Invalid service identity.",
    )
    path = api.store.path / (service_id + ".json")
    require(path.exists(), "No owned viewer with that identity.")
    value = json.loads(path.read_text())
    if value.get("status") == "stopped":
        return {"status": "stopped"}
    request = urllib.request.Request(
        value["url"] + "/api/stop",
        data=b"{}",
        headers={"Authorization": "Bearer " + value["token"], "Content-Type": "application/json"},
    )
    try:
        with urllib.request.urlopen(request, timeout=5) as response:
            return json.load(response)
    except OSError:
        raise StoriesError(
            "viewer_unreachable", "The owned viewer is no longer reachable; retained work is safe."
        ) from None


if __name__ == "__main__":
    from .lib import Stories

    root, service_id = sys.argv[1:3]
    path = Path(root) / (service_id + ".json")
    config = json.loads(path.read_text())
    api = Stories(root, model_env=config["model_env"], execution="background", **config["provider"])
    api._feedback_provider_override = config.get("feedback_provider_override", False)
    dashboard = Dashboard(api, config["story_id"], config["revision_id"], config["token"])
    config.update(status="ready", url=f"http://127.0.0.1:{dashboard.server.server_port}", pid=os.getpid())
    path.write_text(json.dumps(config))
    try:
        dashboard.serve()
    finally:
        config["status"] = "stopped"
        path.write_text(json.dumps(config))
