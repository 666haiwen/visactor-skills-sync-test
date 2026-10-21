#!/usr/bin/env python3
"""Normalize a supplied transparent portrait, or remove its background locally."""

import argparse
import hashlib
import json
import os
from pathlib import Path

from collage import validate_cutout
from PIL import Image, ImageOps

MODEL_MD5 = {
    "u2netp": "8e83ca70e441ab06c318d82300c84806",
    "u2net": "60024c5c889badc19c04ad937298a77b",
    "u2net_human_seg": "c09ddc2e0104f800e3e1bb4652583d1f",
}


def prepare(
    input_path,
    output_path,
    backend="alpha",
    model="u2netp",
    model_dir=None,
    allow_download=False,
    provider=None,
):
    src, dst = Path(input_path).resolve(), Path(output_path).resolve()
    if src == dst:
        raise ValueError("Keep the source photo; choose a different output path")
    if dst.suffix.lower() != ".png":
        raise ValueError("Cutout output must be a transparent .png")
    with Image.open(src) as original:
        result = ImageOps.exif_transpose(original).convert("RGBA")
    if backend == "rembg":
        if model not in {"u2netp", "u2net", "u2net_human_seg"}:
            raise ValueError("Choose u2netp, u2net or u2net_human_seg")
        if model_dir is None:
            raise ValueError("Set --model-dir to an explicit local model cache")
        model_dir = Path(model_dir).resolve()
        if not allow_download and not (model_dir / f"{model}.onnx").is_file():
            raise ValueError(
                "Model is not cached; provide it or explicitly use --allow-model-download"
            )
        if (
            not allow_download
            and hashlib.md5((model_dir / f"{model}.onnx").read_bytes()).hexdigest()
            != MODEL_MD5[model]
        ):
            raise ValueError(
                "Cached model checksum differs; replace it or explicitly allow re-download"
            )
        model_dir.mkdir(parents=True, exist_ok=True)
        # Keep optional library caches under the explicitly selected cache root.
        old = {k: os.environ.get(k) for k in ("U2NET_HOME", "NUMBA_CACHE_DIR")}
        os.environ["U2NET_HOME"] = str(model_dir)
        os.environ["NUMBA_CACHE_DIR"] = str(model_dir / "numba")
        try:
            from rembg import new_session, remove

            session = new_session(model, providers=["CPUExecutionProvider"])
            result = remove(result, session=session).convert("RGBA")
        except ImportError as error:
            raise ValueError(
                "Local cutout needs optional requirements-cutout.txt; alpha/MediaKit normalization needs only Pillow"
            ) from error
        finally:
            for key, value in old.items():
                if value is None:
                    os.environ.pop(key, None)
                else:
                    os.environ[key] = value
    elif backend != "alpha":
        raise ValueError("backend must be alpha or rembg")
    validate_cutout(result)
    bounds = result.getchannel("A").point(lambda a: 255 if a >= 16 else 0).getbbox()
    # A small transparent inset preserves a clear asset boundary after trimming.
    result = ImageOps.expand(result.crop(bounds), border=4, fill=(0, 0, 0, 0))
    dst.parent.mkdir(parents=True, exist_ok=True)
    result.save(dst)
    report = {
        "backend": backend,
        "provider": provider or backend,
        "input": str(src),
        "inputSha256": hashlib.sha256(src.read_bytes()).hexdigest(),
        "output": str(dst),
        "outputSha256": hashlib.sha256(dst.read_bytes()).hexdigest(),
        "mode": result.mode,
        "size": list(result.size),
        "model": model if backend == "rembg" else None,
        "review": "Check face, hair, hands and silhouette visually before composing the poster",
    }
    dst.with_suffix(".processing.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n"
    )
    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--backend", choices=["alpha", "rembg"], default="alpha")
    parser.add_argument("--model", choices=["u2netp", "u2net", "u2net_human_seg"], default="u2netp")
    parser.add_argument("--model-dir", type=Path)
    parser.add_argument("--allow-model-download", action="store_true")
    parser.add_argument(
        "--provider", help="Provenance label, e.g. byted-mediakit-image; does not invoke a tool"
    )
    args = parser.parse_args()
    try:
        print(
            json.dumps(
                prepare(
                    args.input,
                    args.output,
                    args.backend,
                    args.model,
                    args.model_dir,
                    args.allow_model_download,
                    args.provider,
                ),
                ensure_ascii=False,
                indent=2,
            )
        )
    except (ValueError, OSError, RuntimeError) as error:
        parser.error(str(error))
