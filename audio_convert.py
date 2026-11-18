#!/usr/bin/env python3
"""Inspect audio content and create real MP3 files using only ffprobe/ffmpeg.

Requires Python 3.10+ and ffmpeg/ffprobe in PATH or alongside the script. No pip dependencies.

Examples:
    python audio_convert.py inspect "C:\\Music\\track.mp3"
    python audio_convert.py inspect "C:\\Music"
    python audio_convert.py verify  "C:\\Music\\track.mp3"
    python audio_convert.py convert "C:\\Music\\track.mp3"
    python audio_convert.py convert "C:\\Music" --out "C:\\SpotifyReady"
    python audio_convert.py convert "C:\\Music" --reencode-mp3
"""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
from pathlib import Path

# Direct file arguments are always inspected, irrespective of their extension.
# Folder scans include audio and common audiovisual containers.
AUDIO_SUFFIXES = {
    ".mp3", ".mp2", ".m4a", ".m4b", ".mp4", ".ogg", ".oga", ".opus",
    ".aac", ".flac", ".wav", ".wave", ".wma", ".webm", ".mka",
    ".mkv", ".aif", ".aiff", ".caf", ".3gp", ".amr", ".ape",
}


def executable(name: str) -> str | None:
    # Allows ffmpeg.exe and ffprobe.exe to live next to a PyInstaller .exe too.
    directory = (Path(sys.executable).resolve().parent if getattr(sys, "frozen", False)
                 else Path(__file__).resolve().parent)
    local = directory / (name + (".exe" if sys.platform == "win32" else ""))
    return str(local) if local.is_file() else shutil.which(name)


def run(command: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run([executable(command[0]) or command[0], *command[1:]],
                          capture_output=True, text=True, encoding="utf-8",
                          errors="replace", check=False)


def probe(path: Path) -> tuple[dict, dict]:
    result = run(["ffprobe", "-v", "error", "-show_format", "-show_streams",
                  "-of", "json", str(path)])
    if result.returncode != 0:
        raise RuntimeError(result.stderr.strip() or "ffprobe failed")
    try:
        info = json.loads(result.stdout)
    except json.JSONDecodeError as exc:
        raise RuntimeError("ffprobe returned invalid JSON") from exc

    audio = next((s for s in info.get("streams", [])
                  if s.get("codec_type") == "audio"), None)
    if audio is None:
        raise RuntimeError("No audio stream found")
    return info.get("format", {}), audio


def file_list(source: Path, excluded: Path | None = None) -> list[Path]:
    if source.is_file():
        return [source]
    if not source.is_dir():
        raise FileNotFoundError(f"Source not found: {source}")
    files = sorted(p for p in source.rglob("*") if p.is_file()
                   and p.suffix.lower() in AUDIO_SUFFIXES)
    if excluded is not None:
        files = [p for p in files if not p.is_relative_to(excluded)]
    return files


def print_info(path: Path, fmt: dict, audio: dict) -> None:
    bit_rate = audio.get("bit_rate") or fmt.get("bit_rate")
    try:
        kbps = f"{int(bit_rate) / 1000:g} kb/s" if bit_rate else "unknown"
    except (ValueError, TypeError):
        kbps = "unknown"
    print(f"\n{path}")
    print(f"  Filename suffix: {path.suffix.lower() or '(none)'}")
    print(f"  Container:       {fmt.get('format_name', 'unknown')}")
    print(f"  Audio codec:     {audio.get('codec_name', 'unknown')}")
    print(f"  Sample rate:     {audio.get('sample_rate', 'unknown')} Hz")
    print(f"  Channels:        {audio.get('channels', 'unknown')}")
    print(f"  Bit rate:        {kbps} (reported)")
    if audio.get("codec_name") == "mp3":
        print("  MP3 codec:       YES")
    else:
        print("  MP3 codec:       NO")


def check_decoding(path: Path) -> None:
    result = run(["ffmpeg", "-v", "error", "-i", str(path),
                  "-map", "0:a:0", "-f", "null", "-"])
    if result.returncode != 0 or result.stderr.strip():
        raise RuntimeError(result.stderr.strip() or "Audio decoding failed")


def convert_file(source: Path, dest: Path, codec: str,
                 reencode_mp3: bool, overwrite: bool) -> str:
    if source.resolve() == dest.resolve():
        raise RuntimeError("Output path would overwrite the original")
    if dest.exists() and not overwrite:
        return "SKIP: output already exists (use --overwrite)"

    dest.parent.mkdir(parents=True, exist_ok=True)
    # Output is first written to a temporary file and only then moved in place.
    temporary = dest.with_name(dest.stem + ".partial.mp3")
    if temporary.exists():
        raise RuntimeError(f"Temporary output already exists: {temporary}")

    use_copy = codec == "mp3" and not reencode_mp3
    mode = "LOSSLESS STREAM COPY" if use_copy else "RE-ENCODE TO MP3 (VBR V0)"
    command = ["ffmpeg", "-hide_banner", "-nostdin", "-loglevel", "error",
               "-i", str(source), "-map", "0:a:0", "-map_metadata", "0",
               "-vn", "-sn", "-dn"]
    if use_copy:
        command += ["-c:a", "copy"]
    else:
        command += ["-c:a", "libmp3lame", "-q:a", "0"]
    command += ["-id3v2_version", "3", "-f", "mp3", str(temporary)]

    try:
        result = run(command)
        if result.returncode != 0:
            raise RuntimeError(result.stderr.strip() or "ffmpeg conversion failed")
        _, final_audio = probe(temporary)
        if final_audio.get("codec_name") != "mp3":
            raise RuntimeError("Output validation failed: codec is not MP3")
        temporary.replace(dest)
    except Exception:
        temporary.unlink(missing_ok=True)
        raise
    return mode


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("mode", choices=("inspect", "verify", "convert"))
    parser.add_argument("path", type=Path, help="Audio file or directory")
    parser.add_argument("--out", type=Path,
                        help="Output directory (default: sibling <source-folder>_converted)")
    parser.add_argument("--reencode-mp3", action="store_true",
                        help="Re-encode even existing MP3 audio (lossy; only if needed)")
    parser.add_argument("--overwrite", action="store_true",
                        help="Replace existing output files, never source files")
    args = parser.parse_args()

    needed = ["ffprobe"] if args.mode == "inspect" else ["ffprobe", "ffmpeg"]
    missing = [exe for exe in needed if not executable(exe)]
    if missing:
        parser.error("Not found in PATH: " + ", ".join(missing))

    source = args.path.expanduser().resolve()
    source_folder = source if source.is_dir() else source.parent
    out_dir = (args.out.expanduser().resolve() if args.out
               else source_folder.with_name(source_folder.name + "_converted"))
    if args.mode == "convert" and source.is_dir() and source == out_dir:
        parser.error("Output directory must be different from the input directory")

    try:
        files = file_list(source, out_dir if args.mode == "convert" else None)
    except (OSError, ValueError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    if not files:
        print("No supported files found")
        return 1

    errors = 0
    done = 0
    for path in files:
        try:
            fmt, audio = probe(path)
            if args.mode == "inspect":
                print_info(path, fmt, audio)
            elif args.mode == "verify":
                check_decoding(path)
                print(f"OK: fully decoded: {path}")
            else:
                relative = path.relative_to(source) if source.is_dir() else Path(path.name)
                # Preserve source suffix for non-.mp3 files to avoid collisions:
                # song.ogg -> song.ogg.mp3, song.mp3 -> song.mp3.
                output_rel = (relative.with_suffix(".mp3")
                              if relative.suffix.lower() == ".mp3"
                              else relative.with_name(relative.name + ".mp3"))
                dest = out_dir / output_rel
                result = convert_file(path, dest, audio.get("codec_name", ""),
                                      args.reencode_mp3, args.overwrite)
                print(f"{result}: {path}\n  -> {dest}")
            done += 1
        except (OSError, RuntimeError, ValueError) as exc:
            errors += 1
            print(f"ERROR: {path}: {exc}", file=sys.stderr)

    print(f"\nProcessed: {done}; errors: {errors}")
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
