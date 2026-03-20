def parse_output(raw_output: str) -> list[dict]:
    entries = []
    for line in raw_output.splitlines():
        line = line.strip()
        if not line or line.startswith("----------"):
            break
        if ": " not in line:
            continue

        path, _, status_part = line.partition(": ")

        if status_part == "OK":
            entries.append({
                "scanned_path": path,
                "entry_status": "clean",
                "virus_name": None,
                "raw_line": line,
            })
        elif status_part.endswith(" FOUND"):
            virus_name = status_part[: -len(" FOUND")]
            entries.append({
                "scanned_path": path,
                "entry_status": "infected",
                "virus_name": virus_name,
                "raw_line": line,
            })
        elif (status_part.endswith(" ERROR") or status_part == "ERROR"
              or status_part == "Empty file" or status_part == "Symbolic link"):
            # ClamAV がファイルにアクセスできなかった（シンボリックリンク・空ファイル・権限不足）
            entries.append({
                "scanned_path": path,
                "entry_status": "clamav_error",
                "virus_name": None,
                "raw_line": line,
            })
        else:
            entries.append({
                "scanned_path": path,
                "entry_status": "error",
                "virus_name": None,
                "raw_line": line,
            })

    return entries
