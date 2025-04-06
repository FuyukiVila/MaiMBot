import subprocess
import time
import sys

# 要监控的 Python 程序
TARGET_SCRIPT = "bot.py"

def start_process():
    """启动目标程序"""
    return subprocess.Popen([sys.executable, TARGET_SCRIPT])

def monitor():
    process = start_process()
    while True:
        # 检查进程是否仍在运行
        retcode = process.poll()
        if retcode is not None:  # 进程已退出
            print(f"Process crashed with exit code {retcode}. Restarting...")
            process = start_process()
        time.sleep(5)  # 每 5 秒检查一次

if __name__ == "__main__":
    monitor()