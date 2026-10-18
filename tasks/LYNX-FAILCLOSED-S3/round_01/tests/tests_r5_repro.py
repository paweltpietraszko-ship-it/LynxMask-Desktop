"""Narrow re-check of retained F1/F2 on r3, without modifying earlier evidence."""
from pathlib import Path


def main():
    p = Path(__file__).with_name("tests_r4_repro.py")
    s = p.read_text(encoding="utf-8").replace("9bf6131732087a183db45bc0bcb3dc799c365096",
                                            "25ed265a687dee673edd2cbfc3d90203e229fb47")
    s = s.replace('assert owner.called and response.status_code == 200 and data["blocked"] is True',
                  'assert owner.called and response.status_code == 500 and data["blocked"] is True')
    s = s.replace('assert any("GUARD_ERROR" in reason for reason in data["guard_reasons"])',
                  'assert data == api.S3_FAILURE')
    s = s.replace('assert data["error"] is None', 'assert data["error"]')
    s = s.replace('assert "44051401359" in data["original_text"]',
                  'assert "44051401359" not in response.text')
    s = s.replace('assert any(t["original"] == "44051401359" for t in data["tokens"])',
                  'assert not ({"original_text", "tokens", "anonymized_preview"} & data.keys())')
    s = s.replace('assert "anonymized_preview" in data', 'assert set(data) == {"error", "blocked"}')
    s = s.replace('Guard failure: HTTP 200, original text and token map returned',
                  'closed: controlled Guard failure gives HTTP 500, safe JSON only')
    exec(compile(s, str(p), "exec"), {"__file__": str(p), "__name__": "__main__"})


if __name__ == "__main__":
    main()
