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


def run_batch_scan(file_paths: list[str]) -> tuple[str, int, str]:
    """複数の file target をまとめて1回の clamscan で実行する。

    Returns:
        (stdout, exit_code, command_line)
    """
    if not file_paths:
        return "", 0, ""

    if shutil.which("clamscan") is None:
        raise RuntimeError("clamscan not found. Please install ClamAV.")

    cmd = ["clamscan", "--no-summary"] + file_paths
    command_line = " ".join(cmd)

    result = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        timeout=600,
    )
    return result.stdout, result.returncode, command_line
