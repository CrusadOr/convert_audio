# audio_convert: Fix Telegram `.mp3` files that won't play in Spotify Local Files

**Spotify local files greyed out? Downloaded an MP3 from Telegram, but Spotify says the audio is unavailable or refuses to play it?** The file may **end in `.mp3` without actually containing MP3-encoded audio**.

`audio_convert` is a free command-line utility for Windows that detects the **real audio codec and container** with FFprobe, then uses FFmpeg to produce an actual MP3 file. You can run the Python script directly or **build your own Windows `.exe` from the Python source** using PyInstaller. The generated executable does not require Python on the computer where it runs.

> **In short:** inspect suspicious audio files, convert them to real MP3, and add the converted files to Spotify's local-files library. The original files are preserved, and the output folder is created *next to*, not inside, the source folder.

## The problem: Telegram audio appears to be MP3 but Spotify can't play it

I downloaded music tracks from Telegram to my Windows computer. The filenames ended with `.mp3`, and Windows **Properties** also identified them as MP3 files. I added the folder to **Spotify → Local Files**, but the tracks appeared **greyed out / unavailable** and would not play.

The surprising part was that the `.mp3` extension did not reliably describe the actual audio format. A file can be named `song.mp3` while containing, for example, **Opus audio in an Ogg container**, AAC audio, or another codec. Renaming the extension does not convert the audio. Windows may identify the *file type* from its extension, while players can reject the contents or behave inconsistently.

I had previously solved the issue using scripts and FFmpeg, but lost the original scripts. This project recreates that workflow and makes it reusable for anyone experiencing the same problem.

**Other search terms this guide may help with:**

- Spotify local files greyed out / grayed out on Windows
- Spotify local files not playing, song unavailable or audio unavailable
- Telegram downloaded MP3 doesn't work in Spotify
- MP3 file has the wrong codec or wrong extension
- How to find the real audio format of a `.mp3` file
- How to convert Opus or Ogg to MP3 with FFmpeg
- Convert mislabeled audio files to Spotify-compatible MP3 without unnecessary quality loss

**Important:** A mismatched codec is *one possible cause*, not the explanation for every greyed-out Spotify track. Check the actual codec first. Other Spotify settings, file-access issues, or unsupported/corrupted files may cause similar symptoms.

## How it fixes the problem

1. **Inspect:** FFprobe examines the file itself, not just its extension, and reports its container and audio codec.
2. **Convert:** If the audio is not MP3, FFmpeg encodes it as MP3 with `libmp3lame -q:a 0` (high-quality VBR V0).
3. **Avoid unnecessary quality loss:** If the audio is already MP3, FFmpeg uses `-c:a copy` instead of re-encoding it.
4. **Validate:** The program checks that the output contains an MP3 audio stream. A separate `verify` mode checks full audio decoding.
5. **Keep originals:** Files are written to a separate sibling directory. The originals remain untouched.

### Example: a fake `.mp3`

```text
Filename:        song.mp3
Windows file type: MP3 File

Actual file contents (hypothetical example):
Container:       ogg
Audio codec:     opus
MP3 codec:       NO
```

After conversion:

```text
Filename:        song.mp3
Container:       mp3
Audio codec:     mp3
MP3 codec:       YES
```

The example illustrates a possible mismatch; it does **not** claim that every Telegram download uses Opus or Ogg.

## Quick start (Windows 10/11, x64)

### 1. Get the files

Download or clone this repository. Its source files are:

| File | Purpose |
| --- | --- |
| `audio_convert.py` | **Single source of truth:** Python implementation of the audio inspector and converter. |
| `build_exe.bat` | Windows build script that installs PyInstaller if needed and compiles `audio_convert.py` into `dist\audio_convert.exe`. |
| `README.md` | Usage, troubleshooting, security notes, and EXE build instructions. |
| `LICENSE` | MIT license for the Python code, build script, and documentation. |
| `.gitignore` | Excludes Python caches and generated build artifacts. |

The `.exe` is **not committed to the source repository**. Build it on Windows using the instructions below, or download a Python-built executable from GitHub Releases if one is published. No Go source or Go-built executable is part of this version.

### 2. Install FFmpeg and FFprobe

Both `ffmpeg.exe` and `ffprobe.exe` are **required**. They are **not bundled** inside the PyInstaller-generated `audio_convert.exe` or this repository.

1. Download a Windows FFmpeg build from the links at <https://ffmpeg.org/download.html> (for example, a Windows *essentials* build containing both tools).
2. Extract `ffmpeg.exe` and `ffprobe.exe` from its `bin` directory.
3. Place both alongside the generated `dist\audio_convert.exe`, or add their `bin` directory to your Windows `PATH`.

Example:

```text
C:\Tools\audio_convert\
    audio_convert.py
    build_exe.bat
    README.md
    dist\
        audio_convert.exe
        ffmpeg.exe
        ffprobe.exe
```

The Python script can also find the FFmpeg tools beside `audio_convert.py` or through `PATH`. Both the script and the generated EXE use FFmpeg as an external dependency.

### 3. Convert a folder

First, [build the executable](#building-the-windows-executable-from-source). Then open PowerShell in the `dist` directory (which contains the generated EXE) and run:

```powershell
.\audio_convert.exe convert "C:\Music"
```

The converted music is created in **`C:\Music_converted`**, beside the original `C:\Music` folder.

```text
C:\
├── Music\
│   ├── song.mp3
│   └── subfolder\other.ogg
└── Music_converted\
    ├── song.mp3
    └── subfolder\other.ogg.mp3
```

For a **single file** such as `C:\Music\song.mp3`, the default output is `C:\Music_converted\song.mp3`. Subfolders are preserved; a file like `other.ogg` becomes `other.ogg.mp3` to reduce name collisions. Existing output files are skipped unless `--overwrite` is supplied.

### 4. Add the converted folder to Spotify

In Spotify for Windows, open **Settings → Library → Show Local Files**, then add or enable the new folder (for example, `C:\Music_converted`) as a local-files source. If an existing playlist still contains unavailable references to the original files, remove those entries and add the converted tracks. Restarting Spotify may help it refresh the local-files library.

Official Spotify guidance: <https://support.spotify.com/article/local-files/>

**Note:** Creating a valid MP3 fixes a format mismatch, but cannot guarantee Spotify will play every file in every situation.

## Inspect the true audio format (without converting)

Inspect one suspicious file:

```powershell
.\audio_convert.exe inspect "C:\Music\song.mp3"
```

Inspect a whole folder recursively:

```powershell
.\audio_convert.exe inspect "C:\Music"
```

Typical output for a mislabeled file might look like this:

```text
Filename suffix: .mp3
Container:       ogg
Audio codec:     opus
Sample rate:     48000 Hz
Channels:        2
MP3 codec:       NO
```

You can also diagnose the file directly with FFprobe, without using this utility:

```powershell
.\ffprobe.exe -hide_banner "C:\Music\song.mp3"
```

For machine-readable information:

```powershell
.\ffprobe.exe -v error -show_format -show_streams -of json "C:\Music\song.mp3"
```

The **audio codec** is the important property to check. A filename extension and Windows Properties alone do not prove that the content is MP3 audio.

## All commands

Run these in PowerShell from the directory containing the executable:

```powershell
# Show the real container, audio codec, and other technical details
.\audio_convert.exe inspect "C:\Music\song.mp3"

# Inspect all supported files within a folder
.\audio_convert.exe inspect "C:\Music"

# Convert one file or a whole folder
.\audio_convert.exe convert "C:\Music\song.mp3"
.\audio_convert.exe convert "C:\Music"

# Choose a custom destination instead of the sibling _converted folder
.\audio_convert.exe convert "C:\Music" --out "D:\SpotifyReady"

# Check that the files can be fully decoded by FFmpeg
.\audio_convert.exe verify "C:\Music_converted"

# Last resort: re-encode even when the input already uses MP3
.\audio_convert.exe convert "C:\Music" --reencode-mp3 --overwrite
```

**Note:** The Python-built executable is a **command-line program**. It expects a mode (`inspect`, `convert`, or `verify`) and a path. Double-clicking it or dragging a file onto it does not start a conversion by itself. Open PowerShell and use the commands above. Python is not required to *run* the compiled EXE.

### Run the Python version instead

Install **Python 3.10+** and use:

```powershell
python .\audio_convert.py inspect "C:\Music\song.mp3"
python .\audio_convert.py convert "C:\Music"
python .\audio_convert.py verify "C:\Music_converted"
```

There are **no third-party Python package dependencies** for normal execution. FFmpeg and FFprobe are still required. Depending on your Windows setup, `py -3` can replace `python`.

## Audio quality: will converting damage the music?

The program tries to avoid **additional** quality loss:

| Actual input audio | Method | Additional quality loss? |
| --- | --- | --- |
| MP3 | Stream copy (`-c:a copy`) | **No** re-encoding; compressed audio frames are copied. |
| Opus or AAC | Re-encode to MP3 (`libmp3lame -q:a 0`) | **Yes**, because MP3 is lossy. |
| FLAC or WAV | Re-encode to MP3 (`libmp3lame -q:a 0`) | **Yes**, because MP3 is lossy. |

If audio was originally compressed with Opus or AAC, converting it to a high-bitrate MP3 **cannot restore sound information already discarded** by the first encoding. The goal is a playable MP3 with minimal *new* loss, not a magically improved source.

By default, already-valid MP3 audio is copied without re-encoding. If an MP3 still causes problems, the optional `--reencode-mp3` flag forces a fresh encoding, which **can introduce further loss** and should generally be a last resort.

**Metadata:** Supported metadata is copied where possible, but cover artwork is not preserved because only the first audio stream is mapped. If the source contains multiple audio streams, only the first is processed.

## Troubleshooting

| Issue | What to try |
| --- | --- |
| Spotify local files are greyed out / unavailable | Inspect the original: `audio_convert.exe inspect "C:\Music\song.mp3"`. If the codec is not `mp3`, convert the file and add the new output folder to Spotify. |
| Spotify still won't play the newly converted MP3 | Run `verify` on the new file. Check Spotify's local-files settings and the actual playlist file references. Try `--reencode-mp3 --overwrite` only if necessary. |
| `ffmpeg` or `ffprobe` cannot be found | Put both executables beside the generated `dist\audio_convert.exe`, or configure `PATH`. |
| `SKIP: output already exists` | The tool deliberately avoids overwriting previous outputs. Use `--overwrite` to regenerate them. |
| A file does not appear during folder inspection | Folder scanning is restricted to common audio/media filename suffixes. Passing that file directly may still allow FFprobe to inspect it. |
| The converted file has no cover art | The conversion maps the first audio stream only; embedded artwork is not copied. |
| Windows SmartScreen warns about the EXE | The binary is not code-signed. You can inspect the source, build it independently, and apply your normal security checks. |

For more general Spotify local-files troubleshooting, see <https://support.spotify.com/article/local-files/>.

## Building the Windows executable from source

The Windows executable is built **from `audio_convert.py`** using [PyInstaller](https://pyinstaller.org/). There is only **one application implementation (Python)**. `build_exe.bat` is just a small Windows Command Prompt script that automates the build; it is not a second implementation of the converter.

### Prerequisites for building (Windows 10/11)

1. Install **Python 3.10+ for Windows** from <https://www.python.org/downloads/windows/>. Ensure that the **Python launcher (`py`)** and **pip** are installed.
2. Place `audio_convert.py` and `build_exe.bat` in the **same folder**.
3. The batch file ensures PyInstaller **6.22.1 or newer** is available (installing or upgrading it with `pip` if needed). Internet access may be required when installing/updating it. This minimum addresses a documented security advisory affecting older one-file executables.

To check Python and pip, open PowerShell and run:

```powershell
py -3 --version
py -3 -m pip --version
```

### Build the EXE

**Method A: Double-click `build_exe.bat`** in File Explorer. A Command Prompt window will display the build progress. It pauses at the end so you can read any success or error message.

**Method B: Use PowerShell** from the folder containing the two source files:

```powershell
.\build_exe.bat
```

The batch file:

1. Changes the working directory to its own folder using `cd /d "%~dp0"`. Here, `%~dp0` is a built-in batch parameter meaning the drive and folder containing `build_exe.bat`; it is **not** a typo.
2. Checks that `audio_convert.py` and Python 3 are available.
3. Ensures that PyInstaller **6.22.1 or newer** is installed, upgrading older installations if necessary.
4. Builds a single-file Windows executable (`--onefile --console`).
5. Reports the location of the generated executable, or displays an error.

After a successful build, the structure will look like this:

```text
AudioConvert/
├── audio_convert.py
├── build_exe.bat
├── README.md
├── build/                       # PyInstaller temporary build files
├── audio_convert.spec            # Generated PyInstaller configuration
└── dist/
    └── audio_convert.exe        # The Windows executable to distribute
```

The output is **`dist\audio_convert.exe`**, not an EXE in the source-code folder. PyInstaller bundles the necessary Python runtime, so people who run this EXE do **not** need to install Python. It does **not** bundle FFmpeg or FFprobe.

To run the newly built EXE, open PowerShell in the `dist` directory:

```powershell
.\audio_convert.exe inspect "C:\Music\song.mp3"
.\audio_convert.exe convert "C:\Music"
.\audio_convert.exe verify "C:\Music_converted"
```

For distribution, provide `audio_convert.exe` and explain that `ffmpeg.exe` and `ffprobe.exe` must be placed beside it or be accessible through `PATH`.

### Should build outputs be committed to Git?

Commit **`audio_convert.py`, `build_exe.bat`, `README.md`, `LICENSE`, and `.gitignore`**. Do not commit the generated `build/`, `dist/`, `.spec`, or `.exe` files. Publish a Windows EXE via **GitHub Releases** instead, if you want to offer a ready-to-download binary. Build the Windows EXE **on Windows**, not on Linux or macOS, because PyInstaller is not a cross-compiler.

The included `.gitignore` excludes generated files. Before releasing an executable to other people, test it on a Windows machine using a file with mislabeled audio as well as a genuine MP3.

## Security and privacy

- **No telemetry in the Python application:** The source code does not implement analytics, send personal data to an application server, or upload audio files. It invokes FFprobe and FFmpeg as external processes on paths supplied by the user. The Windows build script uses `pip` to install or update **PyInstaller**, which may access the internet. Some FFmpeg-supported media formats can refer to external resources, so do not assume that processing arbitrary untrusted media can never cause network access.
- **Use trustworthy executables:** Download FFmpeg and FFprobe from the official FFmpeg download page or trusted distribution sources. The program intentionally uses `ffmpeg.exe` and `ffprobe.exe` next to the script/EXE in preference to programs on `PATH`; a malicious replacement in that location would run with the same privileges as the converter.
- **Keep dependencies current:** Security fixes are released for FFmpeg and PyInstaller. See [FFmpeg security information](https://ffmpeg.org/security.html) and [PyInstaller security advisories](https://github.com/pyinstaller/pyinstaller/security/advisories). The build script requires PyInstaller 6.22.1 or newer because [older one-file builds are affected by a published security advisory](https://github.com/pyinstaller/pyinstaller/security/advisories/GHSA-9fxf-4qw3-ghmr).
- **Treat media as untrusted input:** Malformed multimedia files may trigger vulnerabilities in outdated versions of FFmpeg. Do not run the converter as administrator, and avoid processing suspicious media from unknown sources.
- **Be careful with output paths:** The `--overwrite` flag permits replacing files in the destination folder. Check any custom `--out` directory carefully, especially if it is shared or contains symbolic links. The converter normally preserves input files, but it is not designed as a security boundary against hostile filesystem modifications.
- **Metadata and privacy:** Converted MP3 files may retain artist, album, comments, and other metadata from the originals. Review metadata before sharing the generated files publicly. Diagnostic output may include local file paths, so redact personal information from bug reports.
- **Operational limits:** No subprocess timeout or resource quota is currently enforced; large or malformed files can take a long time or consume substantial memory and disk space. Success means the output contains an MP3 stream, not that every possible player will accept it.

## License

This project is released under the **MIT License**. See [LICENSE](LICENSE) for the full terms. It allows reuse, modification, and redistribution, including commercial use, subject to preserving the license notice. The software is supplied without warranty.

FFmpeg and FFprobe are **external dependencies and are not included** in this repository or its PyInstaller-built EXE. They are distributed under their own licenses, which may vary by build and enabled components. If you redistribute those binaries yourself, you must comply with the applicable licensing terms. See [FFmpeg's legal information](https://ffmpeg.org/legal.html).

## Contributing and reporting issues

Bug reports and improvements are welcome through GitHub Issues and pull requests. When reporting a problem, include the Windows and Python versions (if relevant), the FFmpeg and FFprobe versions, the command used, and a short description of the expected and actual results. **Do not publish private file paths, personal metadata, or copyrighted audio samples without permission.** Small self-generated test samples are preferable.

This is an independent community utility and is **not affiliated with, endorsed by, or maintained by Spotify, Telegram, or FFmpeg**. Only convert and share files when you have the right to do so.

## Declaration: generated with ChatGPT

**AI disclosure:** This solution, including the Python program, the Windows build script, and the documentation, was generated with the assistance of **ChatGPT by OpenAI**, based on my problem description, requirements, and feedback. I am publishing it on GitHub so others encountering the same Telegram audio / Spotify Local Files compatibility issue can inspect, reuse, and improve the solution. The output should be independently reviewed and tested; neither ChatGPT nor OpenAI provides a warranty or official endorsement of this project.
