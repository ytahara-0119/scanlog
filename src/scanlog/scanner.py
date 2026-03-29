import shutil
import subprocess


def run_scan(target_path: str, scan_mode: str) -> tuple[str, int]:
    if shutil.which("clamscan") is None:
        raise RuntimeError("clamscan not found. Please install ClamAV.")

    if scan_mode == "recursive":
        cmd = ["clamscan", "-r", "--no-summary", target_path]
    else:
        cmd = ["clamscan", "--no-summary", target_path]

    result = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        timeout=300,
    )
    return result.stdout, result.returncode


_BATCH_CHUNK_SIZE = 500


def run_batch_scan(file_paths: list[str]) -> tuple[str, int, str]:
    """複数の file target をまとめて clamscan で実行する。

    ARG_MAX 超過を避けるため、_BATCH_CHUNK_SIZE ファイルずつ分割して実行する。

    Returns:
        (stdout, exit_code, command_line)
        exit_code は全チャンクの最大値（最も深刻な結果）を返す。
    """
    if not file_paths:
        return "", 0, ""

    if shutil.which("clamscan") is None:
        raise RuntimeError("clamscan not found. Please install ClamAV.")

    outputs: list[str] = []
    max_exit_code = 0
    base_cmd = ["clamscan", "--no-summary"]

    chunks = [
        file_paths[i:i + _BATCH_CHUNK_SIZE]
        for i in range(0, len(file_paths), _BATCH_CHUNK_SIZE)
    ]
    command_line = " ".join(base_cmd + [f"[{len(file_paths)} files in {len(chunks)} chunks]"])

    for chunk in chunks:
        cmd = base_cmd + chunk
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=600,
        )
        if result.stdout:
            outputs.append(result.stdout)
        if result.returncode > max_exit_code:
            max_exit_code = result.returncode

    return "\n".join(outputs), max_exit_code, command_line
