"""Leitura/escrita de JSON em disco para caches (só otimização: nunca levanta OSError)."""
import json
import os
import uuid
from pathlib import Path


def write_json_atomic(path: Path, obj: dict) -> None:
    tmp = path.with_name(f"{path.name}.{uuid.uuid4().hex}.tmp")
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp.write_text(json.dumps(obj), encoding="utf-8")
        os.replace(tmp, path)
    except OSError:
        pass  # cache é só otimização
    finally:
        try:
            tmp.unlink()
        except OSError:
            pass  # já movido ou nunca criado


def read_json(path: Path) -> dict | None:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None  # ausente ou corrompido
