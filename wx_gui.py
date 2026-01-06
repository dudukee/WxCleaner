import tkinter as tk
from tkinter import filedialog, messagebox
import ttkbootstrap as ttk
from ttkbootstrap.constants import *
import threading
import os
import time
from send2trash import send2trash # 恢复使用 send2trash
from scanner import find_duplicates

class WxCleanerApp:
    def __init__(self, root):
        self.root = root
        self.root.title("WxCleaner - 微信重复文件清理工具")
        self.root.geometry("1100x800")
        
        # 设置窗口图标 (运行时)
        try:
            icon_path = "icon.ico" # 使用生成的 icon.ico
            if os.path.exists(icon_path):
                self.root.iconbitmap(icon_path)
        except Exception as e:
            print(f"图标加载失败: {e}")
        
        # 设置全局字体大小
        self.root = root
        self.root.title("微信重复文件清理工具")
        self.root.geometry("1100x800")
        
        # 设置全局字体大小
        default_font = ("Microsoft YaHei", 10)
        self.root.option_add("*Font", default_font)
        
        # 针对特定的 Treeview 设置更大字体
        style = ttk.Style()
        style.configure("Treeview", font=("Microsoft YaHei", 10), rowheight=30)
        style.configure("Treeview.Heading", font=("Microsoft YaHei", 11, "bold"))
        
        self.scan_path = tk.StringVar()
        self.duplicates = {} # {hash: [paths]}
        
        self.setup_ui()

    def setup_ui(self):
        # 主容器
        main_frame = ttk.Frame(self.root, padding="15")
        main_frame.pack(fill=BOTH, expand=YES)
        
        # --- 顶部工具栏 ---
        top_frame = ttk.Labelframe(main_frame, text="扫描设置", padding="10")
        top_frame.pack(fill=X, pady=(0, 10))
        
        ttk.Label(top_frame, text="扫描路径:", font=("Microsoft YaHei", 10, "bold")).pack(side=LEFT)
        self.entry = ttk.Entry(top_frame, textvariable=self.scan_path, font=("Microsoft YaHei", 10))
        self.entry.pack(side=LEFT, fill=X, expand=YES, padx=10)
        
        ttk.Button(top_frame, text="浏览", command=self.browse_folder, bootstyle="outline-primary").pack(side=LEFT, padx=5)
        ttk.Button(top_frame, text="开始扫描", command=self.start_scan_thread, bootstyle="primary").pack(side=LEFT, padx=5)
        
        # --- 中间列表区域 ---
        list_frame = ttk.Labelframe(main_frame, text="重复文件列表 (红色标记为建议清理项)", padding="10")
        list_frame.pack(fill=BOTH, expand=YES)
        
        # 滚动条容器
        tree_scroll = ttk.Scrollbar(list_frame, bootstyle="round")
        tree_scroll.pack(side=RIGHT, fill=Y)
        
        # 列定义
        columns = ("num", "path", "size", "mtime", "status")
        self.tree = ttk.Treeview(
            list_frame, 
            columns=columns, 
            show="headings", 
            selectmode="extended",
            bootstyle="info",
            yscrollcommand=tree_scroll.set
        )
        tree_scroll.config(command=self.tree.yview)
        
        # 列标题设置
        self.tree.heading("num", text="序号", anchor=CENTER, command=lambda: self.sort_column("num", False))
        self.tree.heading("path", text="文件路径", command=lambda: self.sort_column("path", False))
        self.tree.heading("size", text="大小", command=lambda: self.sort_column("size", False))
        self.tree.heading("mtime", text="修改时间", command=lambda: self.sort_column("mtime", False))
        self.tree.heading("status", text="状态", command=lambda: self.sort_column("status", False))
        
        # 列宽设置
        self.tree.column("num", width=70, anchor=CENTER, stretch=False)
        self.tree.column("path", width=500, anchor=W)
        self.tree.column("size", width=120, anchor=E)
        self.tree.column("mtime", width=180, anchor=CENTER)
        self.tree.column("status", width=100, anchor=CENTER)
        
        self.tree.pack(fill=BOTH, expand=YES)
        
        # 绑定选择事件
        self.tree.bind("<<TreeviewSelect>>", self.on_tree_select)
        
        # 右键菜单
        self.menu = tk.Menu(self.root, tearoff=0)
        self.menu.add_command(label="打开文件位置", command=self.open_file_location)
        self.menu.add_separator()
        self.menu.add_command(label="保留此文件 (设为绿色)", command=self.unmark_item)
        self.menu.add_command(label="标记为删除 (设为红色)", command=self.mark_item)
        self.tree.bind("<Button-3>", self.show_menu)
        
        # --- 底部操作栏 ---
        bottom_frame = ttk.Frame(main_frame, padding="10")
        bottom_frame.pack(fill=X, pady=(10, 0))
        
        # 进度条
        self.progress = ttk.Progressbar(bottom_frame, orient=HORIZONTAL, mode='determinate', bootstyle="success-striped")
        self.progress.pack(fill=X, pady=(0, 10))
        
        # 状态与统计信息栏
        info_frame = ttk.Frame(bottom_frame)
        info_frame.pack(fill=X)
        
        self.status_label = ttk.Label(info_frame, text="准备就绪", bootstyle="secondary", font=("Microsoft YaHei", 10))
        self.status_label.pack(side=LEFT)
        
        self.selection_label = ttk.Label(info_frame, text="", bootstyle="danger", font=("Microsoft YaHei", 10, "bold"))
        self.selection_label.pack(side=LEFT, padx=20)
        
        # 按钮
        btn_frame = ttk.Frame(info_frame)
        btn_frame.pack(side=RIGHT)
        
        ttk.Button(btn_frame, text="全选重复项", command=self.select_all_duplicates, bootstyle="warning-outline").pack(side=LEFT, padx=5)
        ttk.Button(btn_frame, text="移至回收站", command=self.delete_selected, bootstyle="danger").pack(side=LEFT, padx=5)

    def browse_folder(self):
        path = filedialog.askdirectory()
        if path:
            self.scan_path.set(path)

    def start_scan_thread(self):
        path = self.scan_path.get()
        if not path or not os.path.exists(path):
            messagebox.showwarning("警告", "请选择有效的文件夹")
            return
        
        self.status_label.config(text="正在初始化...", bootstyle="info")
        self.progress['value'] = 0
        # 清空列表
        for item in self.tree.get_children():
            self.tree.delete(item)
        self.selection_label.config(text="")
            
        threading.Thread(target=self.run_scan, args=(path,), daemon=True).start()

    def run_scan(self, path):
        def progress_callback(current, total, status_text):
            def _update():
                self.status_label.config(text=status_text)
                if total > 0:
                    if "统计" in status_text:
                        self.progress['mode'] = 'indeterminate'
                        self.progress.start(10)
                    else:
                        self.progress.stop()
                        self.progress['mode'] = 'determinate'
                        if "筛选" in status_text:
                            pct = (current / total) * 50
                        else:
                            pct = (current / total) * 100
                        self.progress['value'] = pct
            self.root.after(0, _update)

        try:
            self.duplicates = find_duplicates(path, progress_callback=progress_callback)
            self.root.after(0, self.update_results)
        except Exception as e:
            def _error():
                messagebox.showerror("错误", f"扫描出错: {e}")
                self.status_label.config(text="扫描失败", bootstyle="danger")
            self.root.after(0, _error)

    def update_results(self):
        self.progress['value'] = 100
        # 配置 Tag 样式
        self.tree.tag_configure("duplicate", foreground="#e74c3c") # 浅红色
        self.tree.tag_configure("original", foreground="#27ae60")  # 浅绿色
        
        total_groups = len(self.duplicates)
        total_files = sum(len(p) for p in self.duplicates.values())
        
        def format_size(size):
            for unit in ['B', 'KB', 'MB', 'GB']:
                if size < 1024: return f"{size:.2f} {unit}"
                size /= 1024
            return f"{size:.2f} TB"

        count = 1
        for h, paths in self.duplicates.items():
            # 策略：保留路径最短的文件
            paths.sort(key=lambda x: len(x))
            
            for i, p in enumerate(paths):
                try:
                    stat = os.stat(p)
                    size = stat.st_size
                    size_str = format_size(size)
                    mtime_str = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(stat.st_mtime))
                except:
                    size_str = "未知"
                    mtime_str = "未知"
                
                status = "保留" if i == 0 else "重复"
                tags = ("original",) if i == 0 else ("duplicate",)
                
                self.tree.insert("", tk.END, values=(count, p, size_str, mtime_str, status), tags=tags)
                count += 1
        
        self.status_label.config(text=f"完成！找到 {total_groups} 组重复，共 {total_files} 个文件", bootstyle="success")

    def on_tree_select(self, event):
        selected_items = self.tree.selection()
        count = len(selected_items)
        total_size = 0.0
        
        for item in selected_items:
            try:
                size_str = self.tree.item(item)['values'][2]
                parts = size_str.split()
                if len(parts) == 2:
                    val = float(parts[0])
                    unit = parts[1]
                    multipliers = {'B': 1, 'KB': 1024, 'MB': 1024**2, 'GB': 1024**3, 'TB': 1024**4}
                    total_size += val * multipliers.get(unit, 0)
            except:
                pass
        
        size_disp = f"{total_size:.2f} B"
        for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
            if total_size < 1024:
                size_disp = f"{total_size:.2f} {unit}"
                break
            total_size /= 1024
            
        self.selection_label.config(text=f"已选中: {count} 个文件 ({size_disp})")

    def show_menu(self, event):
        item = self.tree.identify_row(event.y)
        if item:
            if item not in self.tree.selection():
                self.tree.selection_set(item)
            self.menu.post(event.x_root, event.y_root)

    def open_file_location(self):
        selected = self.tree.selection()
        if not selected: return
        path = self.tree.item(selected[0])['values'][1]
        try:
            folder = os.path.dirname(path)
            os.startfile(folder)
        except Exception as e:
            messagebox.showerror("错误", f"无法打开文件夹: {e}")

    def unmark_item(self):
        for item in self.tree.selection():
            vals = list(self.tree.item(item)['values'])
            vals[4] = "保留"
            self.tree.item(item, values=vals, tags=("original",))
        self.on_tree_select(None)

    def mark_item(self):
        for item in self.tree.selection():
            vals = list(self.tree.item(item)['values'])
            vals[4] = "重复"
            self.tree.item(item, values=vals, tags=("duplicate",))
        self.on_tree_select(None)

    def select_all_duplicates(self):
        self.tree.selection_remove(self.tree.selection())
        items_to_select = []
        for item in self.tree.get_children():
            if self.tree.item(item)['values'][4] == "重复":
                items_to_select.append(item)
        if items_to_select:
            self.tree.selection_add(items_to_select)
        self.on_tree_select(None)

import subprocess

# ... (Previous imports)
