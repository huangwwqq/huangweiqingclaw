#!/usr/bin/env python3
import argparse
import inspect
import json
import os
import sys
from pathlib import Path


SCRIPT_DIR = Path(__file__).resolve().parent
RUNTIME_ROOT = SCRIPT_DIR / "runtime" / "spider_xhs_core"
ORIGINAL_CWD = Path.cwd()


def _read_json_arg(raw_params, raw_params_file):
    if raw_params and raw_params_file:
        raise ValueError("Use either --params or --params-file, not both.")
    if raw_params_file:
        path = Path(raw_params_file)
        if not path.is_absolute():
            path = ORIGINAL_CWD / path
        return json.loads(path.read_text(encoding="utf-8"))
    if raw_params:
        return json.loads(raw_params)
    return {}


def _runtime_error(exc):
    message = (
        "Failed to initialize the vendored XHS runtime. "
        "Install Python deps with 'pip install -r skills/xhs-apis/scripts/requirements.txt' "
        "and Node deps with 'cd skills/xhs-apis/scripts && npm install'. "
        f"Original error: {exc}"
    )
    raise RuntimeError(message) from exc


def _configure_runtime():
    node_modules = SCRIPT_DIR / "node_modules"
    existing_node_path = os.environ.get("NODE_PATH")
    if node_modules.exists():
        os.environ["NODE_PATH"] = str(node_modules)
        if existing_node_path:
            os.environ["NODE_PATH"] += os.pathsep + existing_node_path
    os.chdir(RUNTIME_ROOT)
    runtime_path = str(RUNTIME_ROOT)
    if runtime_path not in sys.path:
        sys.path.insert(0, runtime_path)


def _load_namespaces():
    _configure_runtime()
    try:
        from apis.xhs_creator_apis import XHS_Creator_Apis
        from apis.xhs_pc_apis import XHS_Apis
        from xhs_utils.cookie_util import trans_cookies
    except Exception as exc:
        _runtime_error(exc)
    return {
        "pc": {
            "class": XHS_Apis,
            "trans_cookies": trans_cookies,
        },
        "creator": {
            "class": XHS_Creator_Apis,
            "trans_cookies": trans_cookies,
        },
    }


def _format_signature(func):
    signature = inspect.signature(func)
    parameters = list(signature.parameters.values())
    if parameters and parameters[0].name == "self":
        parameters = parameters[1:]
    return "(" + ", ".join(str(parameter) for parameter in parameters) + ")"


def _list_methods(namespaces):
    result = {}
    for namespace, config in namespaces.items():
        cls = config["class"]
        methods = []
        for name, func in inspect.getmembers(cls, predicate=inspect.isfunction):
            if name.startswith("_") or name == "__init__":
                continue
            methods.append(
                {
                    "name": name,
                    "signature": _format_signature(func),
                }
            )
        result[namespace] = sorted(methods, key=lambda item: item["name"])
    return result


def _resolve_callable(namespaces, namespace, method):
    if namespace not in namespaces:
        raise KeyError(f"Unknown namespace: {namespace}")
    cls = namespaces[namespace]["class"]
    func = getattr(cls, method, None)
    if func is None or method.startswith("_"):
        raise KeyError(f"Unknown method: {namespace}.{method}")
    signature = inspect.signature(func)
    parameters = list(signature.parameters.values())
    if parameters and parameters[0].name == "self":
        target = getattr(cls(), method)
    else:
        target = func
    return target, signature


def _cookies_dict_to_string(cookies):
    return "; ".join(f"{key}={value}" for key, value in cookies.items())


def _resolve_input_path(value):
    path = Path(value)
    if not path.is_absolute():
        path = ORIGINAL_CWD / path
    return path


def _load_file_bytes(value):
    if isinstance(value, str):
        return _resolve_input_path(value).read_bytes()
    return value


def _normalize_creator_payload(method, payload):
    if method == "upload_media" and "path_or_file" in payload:
        payload["path_or_file"] = _load_file_bytes(payload["path_or_file"])
    if method == "get_file_info" and "file" in payload:
        payload["file"] = _load_file_bytes(payload["file"])
    if method == "post_note" and "noteInfo" in payload:
        note_info = dict(payload["noteInfo"])
        media_type = note_info.get("media_type")
        if media_type == "image":
            note_info["images"] = [_load_file_bytes(item) for item in note_info.get("images", [])]
        if media_type == "video" and "video" in note_info:
            note_info["video"] = _load_file_bytes(note_info["video"])
        payload["noteInfo"] = note_info
    return payload


def _normalize_payload(namespaces, namespace, method, signature, payload):
    if not isinstance(payload, dict):
        raise TypeError("Payload must be a JSON object.")

    payload = dict(payload)
    trans_cookies = namespaces[namespace]["trans_cookies"]
    parameter_names = list(signature.parameters.keys())
    if parameter_names and parameter_names[0] == "self":
        parameter_names = parameter_names[1:]

    expects_cookies = "cookies" in parameter_names
    expects_cookies_str = "cookies_str" in parameter_names

    if expects_cookies and "cookies" not in payload and isinstance(payload.get("cookies_str"), str):
        payload["cookies"] = trans_cookies(payload["cookies_str"])
    if expects_cookies and isinstance(payload.get("cookies"), str):
        payload["cookies"] = trans_cookies(payload["cookies"])
    if expects_cookies_str and "cookies_str" not in payload and isinstance(payload.get("cookies"), dict):
        payload["cookies_str"] = _cookies_dict_to_string(payload["cookies"])

    if namespace == "creator":
        payload = _normalize_creator_payload(method, payload)

    if "out" in payload and isinstance(payload["out"], str):
        payload["out"] = str(_resolve_input_path(payload["out"]))

    return payload


def _write_output(path_value, data):
    path = Path(path_value)
    if not path.is_absolute():
        path = ORIGINAL_CWD / path
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def main():
    parser = argparse.ArgumentParser(description="Call vendored XHS APIs from the xhs-apis skill.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    list_parser = subparsers.add_parser("list", help="List available namespaces and methods.")
    list_parser.add_argument("--out", help="Write the method list to a JSON file.")

    call_parser = subparsers.add_parser("call", help="Call a namespace method.")
    call_parser.add_argument("namespace", choices=["pc", "creator"])
    call_parser.add_argument("method")
    call_parser.add_argument("--params", help="Inline JSON payload.")
    call_parser.add_argument("--params-file", help="Path to a JSON payload file.")
    call_parser.add_argument("--out", help="Write the result to a JSON file.")

    args = parser.parse_args()
    try:
        namespaces = _load_namespaces()
    except Exception as exc:
        response = {
            "error": str(exc),
        }
        print(json.dumps(response, ensure_ascii=False, indent=2))
        raise SystemExit(1)

    if args.command == "list":
        result = _list_methods(namespaces)
        if args.out:
            _write_output(args.out, result)
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return

    try:
        payload = _read_json_arg(args.params, args.params_file)
        target, signature = _resolve_callable(namespaces, args.namespace, args.method)
        payload = _normalize_payload(namespaces, args.namespace, args.method, signature, payload)
        result = target(**payload)
        response = {
            "namespace": args.namespace,
            "method": args.method,
            "result": result,
        }
    except Exception as exc:
        response = {
            "namespace": args.namespace,
            "method": args.method,
            "error": str(exc),
        }
        print(json.dumps(response, ensure_ascii=False, indent=2))
        raise SystemExit(1)

    if args.out:
        _write_output(args.out, response)
    print(json.dumps(response, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
