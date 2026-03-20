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
