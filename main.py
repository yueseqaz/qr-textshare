import tkinter as tk
from tkinter import ttk
import pyperclip
import qrcode
from PIL import Image, ImageTk
import threading
import time
import sys
import os
import math
import json
import winreg
import ctypes

LANGUAGES = {
    "中文": {
        "title": "跨设备文本分享工具",
        "header": "跨设备文本分享",
        "tips": "复制文本后自动生成二维码\n长文本会自动分页显示",
        "waiting": "等待生成二维码...",
        "generated": "二维码已生成，请用手机扫描查看内容",
        "long_text": "文本较长，已分为{}页，使用翻页按钮查看全部内容",
        "prev": "上一页",
        "next": "下一页",
        "exit": "退出程序",
        "settings": "设置",
        "about": "关于",
        "autostart": "开机自动启动",
        "language": "语言选择",
        "save": "保存设置",
        "about_text": """跨设备文本分享工具 v1.0

作者: Sakura
博客：sakurablogs.top
版权所有 Sakura科技工作室

这是一个便捷的跨设备文本分享工具，支持：
• 自动监控剪贴板
• 长文本分页显示
• 多语言支持
• 开机自启动

使用方法：
1. 复制需要分享的文本
2. 使用手机扫描生成的二维码
3. 对于长文本，使用翻页按钮浏览所有内容
4.文本过长 生成的二维码无法解析 故设置为每页1024字符
""",
        "error_qr": "生成二维码时出错: {}",
        "error_clipboard": "监控剪贴板时出错: {}"
    },
    "English": {
        "title": "Cross-device Text Sharing Tool",
        "header": "Cross-device Text Sharing",
        "tips": "QR code will be generated automatically after copying text\nLong text will be paginated",
        "waiting": "Waiting for text to generate QR code...",
        "generated": "QR code generated, please scan with your phone",
        "long_text": "Text is split into {} pages, use navigation buttons to view all",
        "prev": "Previous",
        "next": "Next",
        "exit": "Exit",
        "settings": "Settings",
        "about": "About",
        "autostart": "Start with Windows",
        "language": "Language",
        "save": "Save Settings",
        "about_text": """Cross-device Text Sharing Tool v1.0

Author: Sakura
blog：sakurablogs.top
Copyright Sakura-tech-studio

A convenient tool for sharing text across devices, featuring:
• Automatic clipboard monitoring
• Long text pagination
• Multi-language support
• Auto-start with Windows

How to use:
1. Copy the text you want to share
2. Scan the generated QR code with your phone
3. For long text, use navigation buttons to view all pages
4.The text is too long to be translated into a QR code. To ensure proper parsing, it has been set to 1024 characters per page.
""",
        "error_qr": "Error generating QR code: {}",
        "error_clipboard": "Error monitoring clipboard: {}"
    }
}


class Settings:
    def __init__(self):
        self.config_file = os.path.join(os.path.expanduser("~"), "qrcode_app_config.json")
        self.load_settings()

    def load_settings(self):

        try:
            with open(self.config_file, 'r', encoding='utf-8') as f:
                self.settings = json.load(f)
        except:
            self.settings = {
                "language": "中文",
                "autostart": False
            }
            self.save_settings()

    def save_settings(self):

        with open(self.config_file, 'w', encoding='utf-8') as f:
            json.dump(self.settings, f)

    def set_autostart(self, enable):

        key = winreg.OpenKey(
            winreg.HKEY_CURRENT_USER,
            r"Software\Microsoft\Windows\CurrentVersion\Run",
            0,
            winreg.KEY_ALL_ACCESS
        )

        app_path = sys.executable
        try:
            if enable:
                winreg.SetValueEx(key, "QRCodeTextShare", 0, winreg.REG_SZ, f'"{app_path}"')
            else:
                try:
                    winreg.DeleteValue(key, "QRCodeTextShare")
                except:
                    pass
        finally:
            winreg.CloseKey(key)


class QRCodeApp:
    def __init__(self, root):
        self.settings = Settings()
        self.setup_window(root)
        self.current_page = 0
        self.total_pages = 0
        self.qr_data_list = []
        self.create_widgets()
        self.setup_monitoring()

    def setup_window(self, root):

        self.root = root
        self.root.title(LANGUAGES[self.settings.settings["language"]]["title"])
        self.root.geometry("400x580")
        self.root.resizable(False, False)

    def create_widgets(self):

        self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(expand=True, fill='both')


        self.main_frame = tk.Frame(self.notebook)
        self.notebook.add(self.main_frame, text="QR Code")


        self.settings_frame = tk.Frame(self.notebook)
        self.notebook.add(self.settings_frame, text=LANGUAGES[self.settings.settings["language"]]["settings"])


        self.about_frame = tk.Frame(self.notebook)
        self.notebook.add(self.about_frame, text=LANGUAGES[self.settings.settings["language"]]["about"])

        self.create_main_page()
        self.create_settings_page()
        self.create_about_page()

    def create_main_page(self):

        lang = LANGUAGES[self.settings.settings["language"]]

        main_frame = tk.Frame(self.main_frame)
        main_frame.pack(expand=True, fill='both', padx=20, pady=10)


        tk.Label(
            main_frame,
            text=lang["header"],
            font=("Microsoft YaHei UI", 18, "bold")
        ).pack(pady=10)


        tk.Label(
            main_frame,
            text=lang["tips"],
            font=("Microsoft YaHei UI", 10),
            fg="#666666"
        ).pack(pady=5)


        self.status_label = tk.Label(
            main_frame,
            text=lang["waiting"],
            font=("Microsoft YaHei UI", 10),
            fg="#333333",
            wraplength=350
        )
        self.status_label.pack(pady=10)

        self.qr_frame = tk.Frame(main_frame, bg="#f0f0f0", width=250, height=250)
        self.qr_frame.pack(pady=10)
        self.qr_frame.pack_propagate(False)

        self.image_label = tk.Label(self.qr_frame, bg="#f0f0f0")
        self.image_label.pack(expand=True)

        # 分页控制区域
        self.page_frame = tk.Frame(main_frame)
        self.page_frame.pack(pady=5)

        self.prev_button = tk.Button(
            self.page_frame,
            text=lang["prev"],
            command=self.prev_page,
            state=tk.DISABLED,
            font=("Microsoft YaHei UI", 9)
        )
        self.prev_button.pack(side=tk.LEFT, padx=5)

        self.page_label = tk.Label(
            self.page_frame,
            text="0/0",
            font=("Microsoft YaHei UI", 9)
        )
        self.page_label.pack(side=tk.LEFT, padx=10)

        self.next_button = tk.Button(
            self.page_frame,
            text=lang["next"],
            command=self.next_page,
            state=tk.DISABLED,
            font=("Microsoft YaHei UI", 9)
        )
        self.next_button.pack(side=tk.LEFT, padx=5)

    def create_settings_page(self):

        lang = LANGUAGES[self.settings.settings["language"]]

        settings_frame = tk.Frame(self.settings_frame)
        settings_frame.pack(expand=True, fill='both', padx=20, pady=10)


        autostart_frame = tk.Frame(settings_frame)
        autostart_frame.pack(fill='x', pady=10)

        self.autostart_var = tk.BooleanVar(value=self.settings.settings["autostart"])
        autostart_cb = ttk.Checkbutton(
            autostart_frame,
            text=lang["autostart"],
            variable=self.autostart_var
        )
        autostart_cb.pack(side='left')


        language_frame = tk.Frame(settings_frame)
        language_frame.pack(fill='x', pady=10)

        tk.Label(
            language_frame,
            text=lang["language"] + ":",
            font=("Microsoft YaHei UI", 10)
        ).pack(side='left', padx=(0, 10))

        self.language_var = tk.StringVar(value=self.settings.settings["language"])
        language_cb = ttk.Combobox(
            language_frame,
            textvariable=self.language_var,
            values=list(LANGUAGES.keys()),
            state="readonly",
            width=15
        )
        language_cb.pack(side='left')


        save_button = ttk.Button(
            settings_frame,
            text=lang["save"],
            command=self.save_settings
        )
        save_button.pack(pady=20)

    def create_about_page(self):

        lang = LANGUAGES[self.settings.settings["language"]]

        about_frame = tk.Frame(self.about_frame)
        about_frame.pack(expand=True, fill='both', padx=20, pady=10)

        about_text = tk.Text(
            about_frame,
            wrap=tk.WORD,
            font=("Microsoft YaHei UI", 10),
            height=20,
            width=40
        )
        about_text.pack(expand=True, fill='both')
        about_text.insert('1.0', lang["about_text"])
        about_text.config(state='disabled')

    def save_settings(self):
        lang = LANGUAGES[self.settings.settings["language"]]
        new_language = self.language_var.get()
        new_autostart = self.autostart_var.get()

        # 更新设置
        self.settings.settings["language"] = new_language
        self.settings.settings["autostart"] = new_autostart

        # 保存设置到文件
        self.settings.save_settings()

        # 设置自启动
        self.settings.set_autostart(new_autostart)

        # 更新界面语言
        if new_language != self.settings.settings["language"]:
            self.root.title(LANGUAGES[new_language]["title"])
            self.notebook.tab(1, text=LANGUAGES[new_language]["settings"])
            self.notebook.tab(2, text=LANGUAGES[new_language]["about"])
            # 刷新所有页面
            self.create_main_page()
            self.create_settings_page()
            self.create_about_page()

    def split_text(self, text, max_length=1024):
        chunks = []
        total_chunks = math.ceil(len(text) / max_length)

        for i in range(0, len(text), max_length):
            chunk = text[i:i + max_length]

            chunk_data = f"[第{(i // max_length) + 1}页/共{total_chunks}页]\n{chunk}"
            chunks.append(chunk_data)

        return chunks

    def generate_qr(self, content):

        try:
            qr = qrcode.QRCode(
                version=None,  # 自动选择合适的版本
                error_correction=qrcode.constants.ERROR_CORRECT_L,
                box_size=10,
                border=4,
            )
            qr.add_data(content)
            qr.make(fit=True)

            img = qr.make_image(fill_color="black", back_color="white")
            img = img.resize((230, 230), Image.Resampling.LANCZOS)

            self.tk_image = ImageTk.PhotoImage(img)
            self.image_label.config(image=self.tk_image)

        except Exception as e:
            self.status_label.config(
                text=f"生成二维码时出错: {str(e)}",
                fg="#dc3545"
            )

    def process_text(self, text):
        self.qr_data_list = self.split_text(text)
        if len(self.qr_data_list) > 1:
            self.status_label.config(
                text=f"文本较长，已分为{len(self.qr_data_list)}页，使用翻页按钮查看全部内容",
                fg="#28a745"
            )
        else:
            self.status_label.config(
                text="二维码已生成，请用手机扫描查看内容",
                fg="#28a745"
            )

        self.total_pages = len(self.qr_data_list)
        self.current_page = 0
        self.update_page_display()

    def update_page_display(self):

        if self.qr_data_list:
            self.generate_qr(self.qr_data_list[self.current_page])
            if self.total_pages > 1:
                self.page_label.config(text=f"{self.current_page + 1}/{self.total_pages}")

            # 更新按钮状态
            self.prev_button.config(state=tk.NORMAL if self.current_page > 0 else tk.DISABLED)
            self.next_button.config(state=tk.NORMAL if self.current_page < self.total_pages - 1 else tk.DISABLED)

    def next_page(self):

        if self.current_page < self.total_pages - 1:
            self.current_page += 1
            self.update_page_display()

    def prev_page(self):

        if self.current_page > 0:
            self.current_page -= 1
            self.update_page_display()

    def monitor_clipboard(self):

        while self.monitoring:
            try:
                content = pyperclip.paste()
                if content != self.last_content and content.strip():
                    self.last_content = content
                    self.root.after(0, self.process_text, content)
            except Exception as e:
                self.status_label.config(
                    text=f"监控剪贴板时出错: {str(e)}",
                    fg="#dc3545"
                )
            time.sleep(1)

    def setup_monitoring(self):

        self.monitoring = True
        self.last_content = None
        threading.Thread(target=self.monitor_clipboard, daemon=True).start()

    def stop_monitoring(self):

        self.monitoring = False
        self.root.destroy()


def hide_console():
    if sys.platform.startswith('win'):
        whnd = ctypes.windll.kernel32.GetConsoleWindow()
        if whnd != 0:
            ctypes.windll.user32.ShowWindow(whnd, 0)


def main():
    hide_console()
    root = tk.Tk()
    app = QRCodeApp(root)
    try:
        root.iconbitmap("qrshare.ico")  # 尝试加载图标文件
    except:
        pass  # 如果图标文件不存在，继续运行程序
    root.mainloop()


if __name__ == "__main__":
    main()