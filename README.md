# File Read & Write Challenge — with Error Handling

## Overview
This project contains a Python script (`index.py`) that:
- Reads a text file supplied by the user.
- Applies a chosen modification (line numbers, uppercase, lowercase, remove blank lines, text replacement, reverse lines, or copy as-is).
- Writes the modified content to a new file safely (uses a temporary file and atomic replace).
- Robustly handles errors like missing files, permission issues, and encoding problems.

## Features
- Interactive prompts for input filename, transformation choice, and output filename.
- Encoding detection attempts: tries `utf-8`, then `cp1252`, then `latin-1` before reporting decode issues.
- Safe write: writes to a temporary file in the same directory and then atomically replaces the target output file (reduces risk of corrupted output).
- Clear error messages & retry options.

## Files
- `index.py` — main Python script (executable).
- `README.md` — this documentation.

## How to run
1. Make sure you have **Python 3.6+** installed.
2. Save `index.py` in a folder.
3. Open a terminal and run:
   ```bash
   python index.py
