"""Shared helpers for talking to the YouCam API: loading the feature contract, finding the
API key, and checking account balance/costs.

None of the calls in this file cost any credits. The calls that actually run a feature
(upload, create_task, poll, run) live in youcam_tasks.py.
"""

import json
import os
import sys
from typing import Any, Optional

from constants import (
    DEFAULT_API_BALANCE_PATH,
    DEFAULT_API_FEAT_COST_PATH,
    CREDENTIALS_FILE,
    API_FALLBACK_DOC,
    _REQUEST_TIMEOUT,
)
from youcam_init import requests, yaml


# ---------- Contract: offline fallback and default ----------
def load_contract(feature: Optional[str] = None) -> dict[str, Any]:
    """Load the offline API contract (api-fallback.yaml) describing base URL, billing, and features.

    Only the requested feature's block is parsed in full, since feature blocks can be large.
    Other features are skipped for speed, not omitted from the file.

    Args:
        feature: Which feature's config to load, e.g. "skin-analysis". If omitted, the
            returned "features" dict is empty.

    Returns:
        dict[str, Any]: {"base_url": str, "credit": dict, "features": {feature: dict} or {}}.
    """
    with open(API_FALLBACK_DOC, "r", encoding="utf-8") as fh:
        loader = yaml.SafeLoader(fh)
        try:
            root = loader.get_single_node()
            contract: dict[str, Any] = {"features": {}}
            for key_node, val_node in root.value:
                key = loader.construct_object(key_node)
                if key != "features":
                    contract[key] = loader.construct_object(val_node, deep=True)
                    continue
                if feature is None:
                    continue
                names, found = [], None
                for fkey_node, fval_node in val_node.value:
                    name = loader.construct_object(fkey_node)
                    names.append(name)
                    if name == feature:
                        found = fval_node
                if found is None:
                    raise ValueError(f"unknown feature '{feature}'. features: {sorted(names)}")
                contract["features"][feature] = loader.construct_object(found, deep=True)
        finally:
            loader.dispose()
    return contract


def feature_cfg(contract: dict[str, Any], feature: str, version: Optional[str] = None) -> dict[str, Any]:
    """Resolve one feature's config from the contract, with an optional version override applied
    to task_path.

    api-fallback.yaml stores task_path with the feature's version already baked in as plain text
    (e.g. "/s2s/v2.0/task/cloth-v4"), not as a "{version}" placeholder, so an override is applied
    by replacing that known, already-baked-in version substring with the requested one.

    Args:
        contract: The loaded contract (from load_contract), containing the feature's config.
        feature: Which feature to resolve, e.g. "skin-analysis".
        version: Which version of the feature to use. Defaults to the feature's version
            as recorded in the contract if not given.

    Returns:
        dict[str, Any]: A copy of the feature's config with "_task_path" and "_version"
        resolved for the chosen version.
    """
    feats = contract.get("features", {})
    if feature not in feats:
        raise ValueError(f"Unknown feature '{feature}'. known: {sorted(feats)}")
    cfg = dict(feats[feature])
    default_ver = cfg["version"]
    ver = version or default_ver  # lets the LLM override the version from the live doc
    cfg["_task_path"] = cfg["task_path"].replace(default_ver, ver, 1)
    cfg["_version"] = ver
    return cfg


# ---------- API key ----------
def get_key() -> Optional[str]:
    """Resolve the API key from the YOUCAM_API_KEY env var or credentials.json.

    Returns:
        Optional[str]: The resolved API key, or None if none is configured.
    """
    env = os.environ.get("YOUCAM_API_KEY")
    if env:
        return env

    example = os.path.join(os.path.dirname(CREDENTIALS_FILE), "credentials.example.json")
    if not os.path.isfile(CREDENTIALS_FILE):
        hint = f'Set the YOUCAM_API_KEY env var, or create {CREDENTIALS_FILE} with {{"api_key": "..."}}'
        if os.path.isfile(example):
            hint += f" (see {example} for the expected format)."
        print(
            json.dumps(
                {
                    "error": "No API key configured.",
                    "hint": hint,
                    "details": "Neither YOUCAM_API_KEY nor credentials.json was found.",
                },
                ensure_ascii=False,
            ),
            file=sys.stderr,
        )
        return None

    hint = f"Set the YOUCAM_API_KEY env var, or fix {CREDENTIALS_FILE}"
    if os.path.isfile(example):
        hint += f" (see {example} for the expected format)."
    try:
        with open(CREDENTIALS_FILE, encoding="utf-8") as fh:
            data = json.load(fh)
    except (OSError, json.JSONDecodeError) as exc:
        print(
            json.dumps(
                {"error": "Could not read api_key.", "hint": hint, "details": f"{CREDENTIALS_FILE}: {exc}"},
                ensure_ascii=False,
            ),
            file=sys.stderr,
        )
        return None
    key = data.get("api_key")
    if not key:
        print(
            json.dumps(
                {
                    "error": "Could not read api_key.",
                    "hint": hint,
                    "details": f'{CREDENTIALS_FILE} has no "api_key" field.',
                },
                ensure_ascii=False,
            ),
            file=sys.stderr,
        )
    return key


def _headers(key: str) -> dict[str, str]:
    """Build the standard Authorization/Content-Type headers for an API request.

    Args:
        key: The API key to authenticate with.

    Returns:
        dict[str, str]: Request headers.
    """
    return {"Authorization": f"Bearer {key}", "Content-Type": "application/json"}


# ---------- Billing ----------
def get_credits(key: str) -> dict[str, Any]:
    """Fetch the account's credit balance, split into spendable units and totals by type.

    Args:
        key: The API key to authenticate with.

    Returns:
        dict[str, Any]: {"api_spendable_units": int, "by_type": dict}.
    """
    contract = load_contract()
    cr = contract.get("credit", {})
    base = contract["base_url"]
    prefix = cr.get("api_spendable_prefix", "Api")
    r = requests.get(
        f"{base}{cr.get('balance_path', DEFAULT_API_BALANCE_PATH)}",
        headers=_headers(key),
        timeout=_REQUEST_TIMEOUT,
    )
    r.raise_for_status()
    batches = r.json().get("results", []) or []
    spendable = sum(b.get("amount", 0) for b in batches if str(b.get("type", "")).startswith(prefix))
    by_type = {}
    for b in batches:
        by_type[b.get("type", "?")] = by_type.get(b.get("type", "?"), 0) + b.get("amount", 0)
    return {"api_spendable_units": spendable, "by_type": by_type}


def get_feature_cost(key: str, feature: Optional[str] = None) -> list[dict[str, Any]]:
    """Fetch per-call credit costs for one feature, or all features if none is given.

    Args:
        key: The API key to authenticate with.
        feature: Which feature to filter costs for. If not given, returns costs for all features.

    Returns:
        list[dict[str, Any]]: One entry per SKU with "description", "amount", "unit", "proc_unit", and "feature".
    """
    contract = load_contract()
    path = contract.get("credit", {}).get("feature_cost_path", DEFAULT_API_FEAT_COST_PATH)
    base = contract["base_url"]
    skus, token = [], None
    while True:
        params = {"page_size": 20}
        if token:
            params["starting_token"] = token
        r = requests.get(f"{base}{path}", headers=_headers(key), params=params, timeout=_REQUEST_TIMEOUT)
        r.raise_for_status()
        res = r.json().get("result", {}) or {}
        skus += res.get("skus", []) or []
        token = res.get("next_token")
        if not token:
            break

    def slug_of(u: str) -> str:
        return u.rstrip("/").split("/task/")[-1] if u and "/task/" in u else "(other)"

    if feature:
        skus = [s for s in skus if slug_of(s.get("run_task_url", "")) == feature]
    return [
        {
            "description": s.get("description"),
            "amount": s.get("amount"),
            "unit": s.get("unit"),
            "proc_unit": s.get("proc_unit"),
            "feature": slug_of(s.get("run_task_url", "")),
        }
        for s in skus
    ]
