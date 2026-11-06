"""Write docs/API_ENDPOINTS.md from the FastAPI OpenAPI schema.

Usage (from backend/):  python -m scripts.generate_api_docs
"""

from pathlib import Path

from main import app

OUTPUT = Path(__file__).resolve().parents[2] / "docs" / "API_ENDPOINTS.md"


def _schema_name(content: dict | None) -> str:
    if not content:
        return "—"
    schema = content.get("application/json", {}).get("schema", {})
    if "$ref" in schema:
        return schema["$ref"].split("/")[-1]
    if schema.get("type") == "array" and "$ref" in schema.get("items", {}):
        return f"list[{schema['items']['$ref'].split('/')[-1]}]"
    return schema.get("type", "—")


def main() -> None:
    spec = app.openapi()
    lines = [
        "# Prism Desk API endpoints",
        "",
        "Generated from the OpenAPI schema by `backend/scripts/generate_api_docs.py`.",
        "Interactive documentation: `/docs` (Swagger UI) and `/redoc`.",
        "Authorization rules per endpoint are described in `docs/API.md`.",
        "",
    ]

    by_tag: dict[str, list[str]] = {}
    for path, methods in spec["paths"].items():
        for method, operation in methods.items():
            tag = (operation.get("tags") or ["Other"])[0]
            params = ", ".join(
                f"`{p['name']}`" for p in operation.get("parameters", []) if p.get("in") == "query"
            ) or "—"
            request = _schema_name(operation.get("requestBody", {}).get("content"))
            responses = operation.get("responses", {})
            ok = next((code for code in responses if code.startswith("2")), "200")
            response = _schema_name(responses.get(ok, {}).get("content"))
            by_tag.setdefault(tag, []).append(
                f"| `{method.upper()}` | `{path}` | {operation.get('summary', '')} | {params} | {request} | {ok} {response} |"
            )

    for tag, rows in by_tag.items():
        lines += [
            f"## {tag}",
            "",
            "| Method | Path | Summary | Query parameters | Request body | Success response |",
            "|---|---|---|---|---|---|",
            *rows,
            "",
        ]

    OUTPUT.write_text("\n".join(lines))
    print(f"Wrote {OUTPUT} ({sum(len(r) for r in by_tag.values())} operations)")


if __name__ == "__main__":
    main()
