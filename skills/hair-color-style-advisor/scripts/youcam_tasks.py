"""Wraps the YouCam AI REST API for uploading files, creating tasks, and polling results.

`run()` drives one feature end to end: it uploads the input file(s) if needed, creates
the processing task, and polls until it finishes (or polling runs out), then returns the
result.
`upload()`, `create_task()`, and `poll()` are also available on their own for
callers that want to manage each step individually.
"""

import json
import os
import tempfile
import time
from typing import Any, Optional
from urllib.parse import urlparse

from constants import (
    DEFAULT_UPLOAD_PATH,
    SUPPORT_FILE_TYPES,
    TASK_STATUS,
    _DEFAULT_MAX_POLLS,
    _DEFAULT_POLL_INTERVAL,
    _REQUEST_TIMEOUT,
    _UPLOAD_TIMEOUT,
)
from youcam_api import _headers, feature_cfg, load_contract
from youcam_init import requests


class UploadBatchError(RuntimeError):
    """Raised when resolving a mixed group of local paths and URLs has any failures.

    Carries the structured per-item results so callers can see exactly which sources
    uploaded successfully and which failed (and why), instead of just the first error.
    """

    def __init__(self, uploaded: list[dict[str, str]], failed: list[dict[str, str]]):
        self.uploaded = uploaded
        self.failed = failed
        super().__init__(
            f"{len(failed)} of {len(uploaded) + len(failed)} upload(s) failed: "
            + "; ".join(f"{f['source']}: {f['error']}" for f in failed)
        )


def upload(
    contract: dict[str, Any], feature: str, file_path: str, key: str, version: Optional[str] = None
) -> str:
    """Upload a local file for a feature and return its file_id.

    Uploads always go through the single generic upload endpoint (contract["file_path"],
    falling back to DEFAULT_UPLOAD_PATH), which every feature shares.

    Args:
        contract: The feature's loaded API contract, e.g. from load_contract().
        feature: Which YouCam feature this upload is for, e.g. "skin-analysis".
        file_path: Path to the local file to upload. Must be jpg, jpeg, png, or mp4.
        key: The API key to authenticate the request with.
        version: Which version of the feature to call. Defaults to the standard version.

    Returns:
        str: The uploaded file's file_id.

    Raises:
        FileNotFoundError: file_path doesn't point to an existing local file.
        ValueError: The file's extension isn't a supported type.
    """
    if not os.path.isfile(file_path):
        raise FileNotFoundError(file_path)
    base = contract["base_url"]
    ext = os.path.splitext(file_path)[1].lower()
    ct = SUPPORT_FILE_TYPES.get(ext)

    if not ct:
        raise ValueError(
            f"[Upload File] Unsupported extension {ext}. this engine does not convert files, "
            "provide jpg, jpeg, or png, or mp4 for video"
        )
    meta = requests.post(
        f"{base}{contract.get('file_path', DEFAULT_UPLOAD_PATH)}",
        headers=_headers(key),
        json={
            "files": [
                {
                    "content_type": ct,
                    "file_name": os.path.basename(file_path),
                    "file_size": os.path.getsize(file_path),
                }
            ]
        },
        timeout=_REQUEST_TIMEOUT,
    )
    meta.raise_for_status()
    info = meta.json()["data"]["files"][0]
    put_req = info["requests"][0]
    with open(file_path, "rb") as fh:
        requests.put(
            put_req["url"],
            headers=put_req.get("headers", {"Content-Type": ct}),
            data=fh,
            timeout=_UPLOAD_TIMEOUT,
        ).raise_for_status()
    return info["file_id"]


def _download_to_temp(url: str) -> str:
    """Download a URL to a local temp file so it can go through the normal upload flow.

    Args:
        url: The web URL to download.

    Returns:
        str: Path to the downloaded temp file. Caller is responsible for removing it.

    Raises:
        requests.HTTPError: The download request failed.
    """
    ext = os.path.splitext(urlparse(url).path)[1].lower()
    r = requests.get(url, timeout=_UPLOAD_TIMEOUT, stream=True)
    r.raise_for_status()
    fd, tmp_path = tempfile.mkstemp(suffix=ext)
    try:
        with os.fdopen(fd, "wb") as fh:
            for chunk in r.iter_content(chunk_size=1 << 16):
                fh.write(chunk)
    except Exception:
        os.remove(tmp_path)
        raise
    return tmp_path


def upload_url(
    contract: dict[str, Any], feature: str, url: str, key: str, version: Optional[str] = None
) -> str:
    """Download a web URL and upload it, returning its file_id.

    Used when a src/ref group mixes local paths and URLs: the upload endpoint only
    registers local file bytes, so a URL has to be fetched client-side first to get a
    file_id that can sit alongside the local files' file_ids in the same list.

    Args:
        contract: The feature's loaded API contract, e.g. from load_contract().
        feature: Which YouCam feature this upload is for, e.g. "skin-analysis".
        url: The web URL to download and upload.
        key: The API key to authenticate the request with.
        version: Which version of the feature to call. Defaults to the standard version.

    Returns:
        str: The uploaded file's file_id.
    """
    tmp_path = _download_to_temp(url)
    try:
        return upload(contract, feature, tmp_path, key, version)
    finally:
        os.remove(tmp_path)


def create_task(
    contract: dict[str, Any], feature: str, body: dict[str, Any], key: str, version: Optional[str] = None
) -> str:
    """Create a processing task for a feature and return its task_id.

    Args:
        contract: The feature's loaded API contract, e.g. from load_contract().
        feature: Which YouCam feature to create a task for, e.g. "skin-analysis".
        body: The request payload, e.g. file_id(s)/url(s) and any feature-specific params.
        key: The API key to authenticate the request with.
        version: Which version of the feature to call. Defaults to the standard version.

    Returns:
        str: The created task's task_id.
    """
    base, cfg = contract["base_url"], feature_cfg(contract, feature, version)
    r = requests.post(
        f"{base}{cfg['_task_path']}", headers=_headers(key), json=body, timeout=_REQUEST_TIMEOUT
    )
    r.raise_for_status()
    return r.json()["data"]["task_id"]


def poll(
    contract: dict[str, Any],
    feature: str,
    task_id: str,
    key: str,
    version: Optional[str] = None,
    interval: float = _DEFAULT_POLL_INTERVAL,
    max_polls: int = _DEFAULT_MAX_POLLS,
) -> dict[str, Any]:
    """Poll a task up to max_polls times, interval seconds apart.

    Running out of polls isn't a failure: the task may just still be processing, so this
    returns normally with whatever status was last observed (typically still "running").
    The caller can decide whether to poll again later with the same task_id.

    Args:
        contract: The feature's loaded API contract, e.g. from load_contract().
        feature: Which YouCam feature this task belongs to, e.g. "skin-analysis".
        task_id: The task to poll, as returned by create_task().
        key: The API key to authenticate the request with.
        version: Which version of the feature to call. Defaults to the standard version.
        interval: How many seconds to wait between checks while the job is processing.
        max_polls: How many times to check on the job before giving up and returning
            whatever status was last seen.

    Returns:
        dict[str, Any]: The task's most recent "data" payload, plus "task_id".
    """
    base, cfg = contract["base_url"], feature_cfg(contract, feature, version)
    url = f"{base}{cfg['_task_path']}/{task_id}"
    data = {}
    for _ in range(max_polls):
        r = requests.get(url, headers=_headers(key), timeout=_REQUEST_TIMEOUT)
        r.raise_for_status()
        data = r.json().get("data", {})
        if data.get("task_status") in TASK_STATUS:
            break
        time.sleep(interval)
    return {**data, "task_id": task_id}


def _as_list(value: Optional[str] | list[str]) -> list[str]:
    if not value:
        return []
    return [value] if isinstance(value, str) else list(value)


def _is_url(value: str) -> bool:
    return value.startswith(("http://", "https://"))


def _resolve_group(
    contract: dict[str, Any], feature: str, key: str, version: Optional[str], values: list[str], kind: str
) -> dict[str, Any]:
    """Resolve one src/ref group into the single body field it maps to.

    A pure list of URLs is passed through as-is. Any group containing at least one
    local path needs uploads to get ids for a single homogeneous field, so every item
    is uploaded (paths directly, URLs downloaded client-side first); a failure on any
    item still preserves the file_ids already obtained for the others.

    Args:
        contract: The feature's loaded API contract, e.g. from load_contract().
        feature: Which YouCam feature this group is for, e.g. "skin-analysis".
        key: The API key to authenticate any uploads with.
        version: Which version of the feature to call. Defaults to the standard version.
        values: The local file paths and/or web URLs for this group.
        kind: Which group this is, "src" or "ref"; used to name the returned field.

    Returns:
        dict[str, Any]: A single-key dict for the body, e.g. {"src_file_ids": [...]}.

    Raises:
        UploadBatchError: One or more values failed to upload while resolving a group
            containing local paths.
    """
    urls = [v for v in values if _is_url(v)]
    paths = [v for v in values if not _is_url(v)]

    if paths:
        uploaded, failed = [], []
        for v in values:
            try:
                fid = (
                    upload_url(contract, feature, v, key, version)
                    if _is_url(v)
                    else upload(contract, feature, v, key, version)
                )
                uploaded.append({"source": v, "file_id": fid})
            except Exception as exc:
                failed.append({"source": v, "error": str(exc)})
        if failed:
            raise UploadBatchError(uploaded, failed)
        ids = [u["file_id"] for u in uploaded]
        return {f"{kind}_file_id" if len(ids) == 1 else f"{kind}_file_ids": ids[0] if len(ids) == 1 else ids}
    if urls:
        return {
            f"{kind}_file_url" if len(urls) == 1 else f"{kind}_file_urls": urls[0] if len(urls) == 1 else urls
        }
    return {}


def run(
    feature: str,
    src_file: Optional[str] | list[str] = None,
    ref_file: Optional[str] | list[str] = None,
    params: Optional[dict[str, Any]] = None,
    key: Optional[str] = None,
    version: Optional[str] = None,
    interval: float = _DEFAULT_POLL_INTERVAL,
    max_polls: int = _DEFAULT_MAX_POLLS,
    contract: Optional[dict[str, Any]] = None,
) -> dict[str, Any]:
    """Runs one YouCam AI feature on a photo or video and returns the result.

    Uploads the input file(s) if needed, starts the processing job, and waits for it
    to finish before returning.

    Args:
        feature: Which YouCam feature to run, e.g. "skin-analysis".
        src_file: The main input photo or video. Give one local file path or web URL,
            or a list of several (some features need multiple photos, e.g. three
            angles of a face). Local paths and web URLs can be mixed in the same list.
            When mixed, every URL is also uploaded (fetched client-side) to get a
            file_id, since the API needs one homogeneous field.
        ref_file: A second input some features need for reference, such as a
            hairstyle photo for a hair transfer or a garment photo for a virtual
            try-on. Follows the same rules as src_file. Not every feature needs this.
        params: Extra options to send along with the request.
        key: The API key to use. Required; the caller (e.g. youcam_core.py's CLI) is
            expected to resolve it from YOUCAM_API_KEY or credentials.json beforehand.
        version: Which version of the feature to call. Defaults to the standard version.
        interval: How many seconds to wait between checks while the job is processing.
        max_polls: How many times to check on the job before giving up and returning
            whatever status was last seen.
        contract: An already-loaded feature contract to reuse instead of loading it again.

    Returns:
        dict[str, Any]: The job's latest result, plus its "task_id".

    Raises:
        ValueError: No API key is available, or no input file/URL/ID was given.
        UploadBatchError: One or more values failed to upload while resolving a mixed
            src_file/ref_file list of local paths and URLs.
    """
    contract = contract or load_contract(feature)
    if not key:
        raise ValueError(
            "missing API key. set the YOUCAM_API_KEY env var, or create credentials.json "
            "(see credentials.example.json for the format)"
        )
    body = dict(params or {})

    src_values = _as_list(src_file)
    if src_values:
        body.update(_resolve_group(contract, feature, key, version, src_values, "src"))
    elif not any(k in body for k in ("src_file_id", "src_file_url", "src_file_ids", "src_file_urls")):
        raise ValueError("provide src_file, or one of src_file_id/src_file_url/src_file_ids/src_file_urls")

    ref_values = _as_list(ref_file)
    if ref_values:  # needed by features like hair transfer or clothes try-on
        body.update(_resolve_group(contract, feature, key, version, ref_values, "ref"))

    tid = create_task(contract, feature, body, key, version)
    return poll(contract, feature, tid, key, version, interval, max_polls)


def _parse_params(pairs: Optional[list[str]]) -> dict[str, Any]:
    """Parse CLI-style key=value strings into a dict, used by youcam_core.py's --param flag.

    Each value is JSON-decoded when possible, so numbers, booleans, and lists (e.g.
    'count=3' or 'tags=["a","b"]') come through as real Python types; anything that
    doesn't parse as JSON is kept as the raw string.

    Args:
        pairs: A list of "key=value" strings, or None.

    Returns:
        dict[str, Any]: The parsed key/value pairs.
    """
    out = {}
    for p in pairs or []:
        k, v = p.split("=", 1)
        try:
            out[k] = json.loads(v)
        except json.JSONDecodeError:
            out[k] = v
    return out
