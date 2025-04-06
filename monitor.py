import subprocess
import time
import sys
import signal
import threading
try:
    import keyboard  # 需要安装：pip install keyboard
except ImportError:
    print("'keyboard' 模块未安装，快捷键功能不可用。请运行：pip install keyboard")
    keyboard = None

# 要监控的 Python 程序
TARGET_SCRIPT = "bot.py"

class ProcessMonitor:
    def __init__(self):
        self.process = None
        self.should_exit = False

        # 监听 Ctrl+C
        signal.signal(signal.SIGINT, self.handle_exit)
        signal.signal(signal.SIGTERM, self.handle_exit)

        # 启动键盘监听（如果可用）
        if keyboard:
            threading.Thread(target=self.listen_keyboard, daemon=True).start()

    def handle_exit(self, signum, frame):
        """处理 Ctrl+C 退出信号"""
        print("\nReceived exit signal. Stopping monitor and child process...")
        self.should_exit = True
        if self.process and self.process.poll() is None:
            self.process.terminate()  # 终止子进程

    def start_process(self):
        """启动目标程序"""
        return subprocess.Popen([sys.executable, TARGET_SCRIPT])

    def restart_process(self):
        """手动重启子进程"""
        if self.process and self.process.poll() is None:
            self.process.terminate()
        self.process = self.start_process()
        print("手动重启目标程序")

    def listen_keyboard(self):
        """监听键盘输入（R键重启）"""
        print("按 [R] 键手动重启目标程序，按 [Ctrl+C] 退出监控...")
        while not self.should_exit:
            if keyboard.is_pressed('r'):  # 检测 R 键
                self.restart_process()
                time.sleep(0.5)  # 防抖
            time.sleep(0.1)

    def monitor(self):
        """监控目标程序，崩溃时自动重启"""
        self.process = self.start_process()
        while not self.should_exit:
            retcode = self.process.poll()
            if retcode is not None:  # 进程已退出
                print(f"进程崩溃，退出码: {retcode}. 正在重启...")
                self.process = self.start_process()
            time.sleep(5)  # 每 5 秒检查一次

        # 确保子进程终止
        if self.process and self.process.poll() is None:
            self.process.terminate()
        print("监控已停止")

if __name__ == "__main__":
    monitor = ProcessMonitor()
    monitor.monitor()