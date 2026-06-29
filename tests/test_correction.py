from __future__ import annotations

from pathlib import Path

from raprom.correction import CorrectorFile


def raw_block(timestamp: str) -> list[str]:
    values = " ".join(str(index + 1) for index in range(32))
    return [
        f"MRR {timestamp} UTC-05 DVS 6.10 DSN 0509106128 BW 37305 CC 1769675 MDQ 100 57 57 TYP RAW",
        f"H {values}",
        f"TF {' '.join('1.0' for _ in range(32))}",
        *[f"F{index:02d} {values}" for index in range(64)],
    ]


def write_raw(path: Path, lines: list[str]) -> None:
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def test_corrector_removes_repeated_mrr_header(tmp_path):
    raw_path = tmp_path / "repeated.raw"
    lines = [
        *raw_block("250101000000"),
        raw_block("250101000010")[0],
        *raw_block("250101000020"),
    ]
    write_raw(raw_path, lines)

    corrected_path = Path(CorrectorFile(str(raw_path)))

    assert corrected_path.name == "repeated-corrected.raw"
    assert corrected_path.parent == tmp_path / "CorrectedRaw"
    corrected_lines = corrected_path.read_text(encoding="utf-8").splitlines()
    assert corrected_lines.count(raw_block("250101000010")[0]) == 0
    assert corrected_lines.count(raw_block("250101000020")[0]) == 1
    assert raw_path.exists()
    assert not (tmp_path / "Moved").exists()


def test_corrector_drops_malformed_record(tmp_path):
    raw_path = tmp_path / "malformed.raw"
    lines = [
        *raw_block("250101000000"),
        *raw_block("250101000010")[:20],
        "BROKEN LINE WITHOUT A RAW RECORD PREFIX",
        *raw_block("250101000010")[20:],
        *raw_block("250101000020"),
    ]
    write_raw(raw_path, lines)

    corrected_path = Path(CorrectorFile(str(raw_path)))

    text = corrected_path.read_text(encoding="utf-8")
    assert corrected_path.name == "malformed-corrected.raw"
    assert corrected_path.parent == tmp_path / "CorrectedRaw"
    assert "BROKEN LINE" not in text
    assert "MRR 250101000000" in text
    assert "MRR 250101000010" in text
    assert raw_path.exists()
    assert not (tmp_path / "Moved").exists()


def test_corrector_drops_backward_time_jump(tmp_path):
    raw_path = tmp_path / "jump.raw"
    write_raw(
        raw_path,
        [
            *raw_block("250101000030"),
            *raw_block("250101000020"),
            *raw_block("250101000040"),
        ],
    )

    corrected_path = Path(CorrectorFile(str(raw_path)))

    text = corrected_path.read_text(encoding="utf-8")
    assert corrected_path.name == "jump-corrected.raw"
    assert corrected_path.parent == tmp_path / "CorrectedRaw"
    assert "MRR 250101000030" in text
    assert "MRR 250101000020" not in text
    assert raw_path.exists()
    assert not (tmp_path / "Moved").exists()
