#!/usr/bin/env python3
"""
index.py

File Read & Write Challenge + Error Handling Lab

- Prompts the user for an input filename and validates it (exists, readable).
- Lets the user choose a transformation to apply.
- Writes the modified content to a new file (safe atomic replace via temp file).
- Handles FileNotFoundError, PermissionError, UnicodeDecodeError, IsADirectoryError, etc.
"""

import os
import sys
import tempfile
import shutil

# ---------- Helpers ----------

def choose_encoding_try(filename, encodings=("utf-8", "cp1252", "latin-1")):
    """
    Try to open the file using a list of encodings.
    Returns the encoding that worked, or raises UnicodeDecodeError if none worked.
    """
    for enc in encodings:
        try:
            with open(filename, "r", encoding=enc) as f:
                # Try to read a small chunk to validate decoding
                f.readline()
            return enc
        except UnicodeDecodeError:
            continue
        except Exception:
            # For other exceptions (permission, isdir), re-raise so caller handles them
            raise
    # if none succeeded
    raise UnicodeDecodeError("unknown", b"", 0, 1, "Unable to decode using tried encodings")


def prompt_input_file():
    """
    Prompt the user for an input filename. Validate errors and allow retry.
    Returns (filename, encoding) if success, or exits if user chooses to quit.
    """
    while True:
        inp = input("Enter the path to the input file (or 'q' to quit): ").strip()
        if inp.lower() == "q":
            print("Exiting.")
            sys.exit(0)

        # Expand user tilde and variables
        fname = os.path.expanduser(os.path.expandvars(inp))

        # Basic existence checks
        if not os.path.exists(fname):
            print("Error: file not found. Please check the path and try again.")
            continue
        if os.path.isdir(fname):
            print("Error: the path is a directory, not a file. Please provide a file.")
            continue

        # Try opening and detect encoding
        try:
            enc = choose_encoding_try(fname)
            return fname, enc
        except UnicodeDecodeError:
            print("Error: Could not decode file with standard encodings.")
            # allow retry
            r = input("Try again with a different file? (Y/n): ").strip().lower()
            if r == "n":
                sys.exit(1)
            continue
        except PermissionError:
            print("Error: Permission denied when attempting to read the file.")
            r = input("Choose another file? (Y/n): ").strip().lower()
            if r == "n":
                sys.exit(1)
            continue
        except IsADirectoryError:
            print("Error: This is a directory, not a file.")
            continue
        except Exception as e:
            # Catch-all for unexpected errors (report and offer retry)
            print(f"Unexpected error while checking file: {e}")
            r = input("Try again? (Y/n): ").strip().lower()
            if r == "n":
                sys.exit(1)
            continue


def prompt_transformation():
    """
    Present transformation options and return a dict describing user's choice.
    """
    print("\nChoose a transformation to apply to the file (enter number):")
    print("  1) Add line numbers (prefix each line with '0001: ')")
    print("  2) Convert to UPPERCASE")
    print("  3) Convert to lowercase")
    print("  4) Remove blank lines")
    print("  5) Replace text (provide target and replacement)")
    print("  6) Reverse lines (write lines in reverse order)  -- NOTE: may load file into memory")
    print("  7) No modification (copy as-is)")

    choice = input("Choice [1-7]: ").strip()
    if choice not in set(str(i) for i in range(1, 8)):
        print("Invalid choice, defaulting to No modification (7).")
        choice = "7"

    opt = {"choice": choice}
    if choice == "5":
        target = input("Enter the text to replace (target): ")
        replacement = input("Enter the replacement text: ")
        opt["target"] = target
        opt["replacement"] = replacement
    return opt


def make_output_filename(input_path):
    """
    Suggest an output filename based on the input.
    E.g., if input is /path/file.txt => suggests /path/file_modified.txt
    If file already exists, will prompt for action later.
    """
    folder, fname = os.path.split(input_path)
    base, ext = os.path.splitext(fname)
    if ext == "":
        ext = ".txt"
    suggested = os.path.join(folder, f"{base}_modified{ext}")
    return suggested


def transform_line_core(core_text, idx, opt):
    """
    Apply transformation to a single line core (without trailing newline).
    idx is 0-based line index for numbering.
    Return the transformed core (string) or None if line should be skipped (e.g., remove blank).
    """
    choice = opt["choice"]
    if choice == "1":
        # line numbers (padded)
        return f"{idx+1:04d}: {core_text}"
    if choice == "2":
        return core_text.upper()
    if choice == "3":
        return core_text.lower()
    if choice == "4":
        # remove blank lines
        if core_text.strip() == "":
            return None
        return core_text
    if choice == "5":
        return core_text.replace(opt.get("target", ""), opt.get("replacement", ""))
    if choice == "6":
        # reverse lines handled at write time (not here)
        return core_text
    if choice == "7":
        return core_text
    return core_text


def process_streaming(input_path, encoding, opt, output_path):
    """
    Process file line-by-line and write to a temporary file, then atomically move to output_path.
    Returns tuple (lines_read, lines_written, output_path).
    """
    lines_read = 0
    lines_written = 0

    # Use temporary file in same directory (safer for atomic replace across filesystems)
    out_dir = os.path.dirname(output_path) or "."
    with tempfile.NamedTemporaryFile(mode="w", delete=False, dir=out_dir, encoding=encoding) as tmp:
        tmp_name = tmp.name
        try:
            with open(input_path, "r", encoding=encoding) as src:
                for idx, raw_line in enumerate(src):
                    lines_read += 1
                    # Preserve trailing newline if present
                    has_nl = raw_line.endswith("\n")
                    core = raw_line.rstrip("\r\n")
                    transformed = transform_line_core(core, idx, opt)
                    if transformed is None:
                        # e.g., blank-line removal
                        continue
                    out_line = transformed + ("\n" if has_nl else "")
                    tmp.write(out_line)
                    lines_written += 1
        except Exception:
            # Clean up temporary file on unexpected failure
            try:
                tmp.close()
                os.remove(tmp_name)
            except Exception:
                pass
            raise

    # If output exists and is same path as tmp_name, handle overwrite; else replace
    try:
        # If output already exists, ask user whether to overwrite
        if os.path.exists(output_path):
            resp = input(f"Output file '{output_path}' already exists. Overwrite? (y/N): ").strip().lower()
            if resp != "y":
                # ask for new name
                new_name = input("Enter a new output filename (or 'q' to cancel): ").strip()
                if new_name.lower() == "q":
                    os.remove(tmp_name)
                    print("Operation cancelled. Temporary file removed.")
                    return lines_read, 0, None
                output_path = os.path.expanduser(new_name)

        # atomic replace
        os.replace(tmp_name, output_path)
    except Exception as e:
        # Cleanup temp file if replace failed
        try:
            os.remove(tmp_name)
        except Exception:
            pass
        raise e

    return lines_read, lines_written, output_path


def process_reverse(input_path, encoding, opt, output_path):
    """
    Reverse lines transformation requires loading lines in memory. Warn user.
    """
    print("Warning: 'Reverse lines' will load the entire file into memory. Continue? (Y/n): ", end="")
    c = input().strip().lower()
    if c == "n":
        print("Operation cancelled by user.")
        return 0, 0, None

    with open(input_path, "r", encoding=encoding) as src:
        lines = src.readlines()

    transformed_lines = []
    for idx, raw_line in enumerate(lines):
        core = raw_line.rstrip("\r\n")
        has_nl = raw_line.endswith("\n")
        t = transform_line_core(core, idx, opt)
        if t is None:
            continue
        transformed_lines.append(t + ("\n" if has_nl else ""))

    # write to temp file and replace
    out_dir = os.path.dirname(output_path) or "."
    with tempfile.NamedTemporaryFile(mode="w", delete=False, dir=out_dir, encoding=encoding) as tmp:
        tmp_name = tmp.name
        tmp.writelines(reversed(transformed_lines))

    try:
        if os.path.exists(output_path):
            resp = input(f"Output file '{output_path}' already exists. Overwrite? (y/N): ").strip().lower()
            if resp != "y":
                new_name = input("Enter a new output filename (or 'q' to cancel): ").strip()
                if new_name.lower() == "q":
                    os.remove(tmp_name)
                    print("Operation cancelled. Temporary file removed.")
                    return 0, 0, None
                output_path = os.path.expanduser(new_name)
        os.replace(tmp_name, output_path)
    except Exception:
        try:
            os.remove(tmp_name)
        except Exception:
            pass
        raise

    return len(lines), len(transformed_lines), output_path


# ---------- Main ----------

def main():
    print("File Read & Write Challenge + Error Handling Lab")
    print("This program reads a file, applies a chosen modification, and writes a modified copy.\n")

    # 1) Ask user for input file with validation
    input_path, encoding = prompt_input_file()
    print(f"Detected/selected encoding: {encoding}")

    # 2) Ask user for transformation
    opt = prompt_transformation()

    # 3) Suggest output filename and confirm
    suggested_output = make_output_filename(input_path)
    print(f"Suggested output filename: {suggested_output}")
    out = input(f"Press Enter to accept or type a new output path: ").strip()
    output_path = suggested_output if out == "" else os.path.expanduser(out)

    # 4) Perform processing (choose streaming or reverse)
    try:
        if opt["choice"] == "6":  # reverse
            lines_read, lines_written, written_path = process_reverse(input_path, encoding, opt, output_path)
        else:
            lines_read, lines_written, written_path = process_streaming(input_path, encoding, opt, output_path)

        if written_path is None:
            print("No output written (operation cancelled).")
        else:
            print("\nDone.")
            print(f"Input file: {input_path}")
            print(f"Output file: {written_path}")
            print(f"Lines read: {lines_read}")
            print(f"Lines written: {lines_written}")

    except FileNotFoundError:
        print("Error: input file disappeared during processing.")
    except PermissionError:
        print("Error: Permission denied while reading/writing files. Check file permissions.")
    except UnicodeDecodeError:
        print("Error: File encoding not supported or file is binary. Try a different encoding or file.")
    except Exception as e:
        print(f"An unexpected error occurred: {e}")


if __name__ == "__main__":
    main()
