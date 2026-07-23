import os
import re
import tkinter as tk
from tkinter import ttk, filedialog, messagebox, scrolledtext
from pathlib import Path
from utils.help_window import create_help_window


class FileSplitterTab:
    """Вкладка разделения файлов POU на FBD и ST части"""
    
    def __init__(self, parent, parent_tab=None):
        self.parent = parent
        self.parent_tab = parent_tab
        self.input_files = []
        self.output_dir = ""
        self.create_widgets()
    
    def show_help(self):
        content = """
📌 НАЗНАЧЕНИЕ

Разделяет файлы POU (Program Organization Unit) на две части для дальнейшего анализа.

📁 FBD РАЗДЕЛЕННЫЙ
• Содержит строки БЕЗ ключевых слов: .Xin, .Xs, .OUT, 0.0
• Используется для проверки наличия тегов в FBD логике

📁 ST РАЗДЕЛЕННЫЙ
• Содержит ТОЛЬКО строки с ключевыми словами: .Xin, .Xs, .OUT, 0.0
• Используется для сбора тегов

▶️ КАК РАБОТАТЬ
1. Нажмите "ВЫБРАТЬ ФАЙЛЫ POU" или "ВЫБРАТЬ ПАПКУ"
2. Выберите исходные файлы для разделения
3. Нажмите "РАЗДЕЛИТЬ ВСЕ ФАЙЛЫ"

📁 РЕЗУЛЬТАТЫ
Результаты сохраняются в выбранную папку:
   📁 FBD разделенный/
   📁 ST разделенный/

📄 ПОДДЕРЖИВАЕМЫЕ ФОРМАТЫ: .txt, .xml, .log, .csv
"""
        create_help_window(self.parent, "📂 Разделитель файлов", content)
    
    def create_widgets(self):
        # Основной фрейм с разделением на левую и правую часть
        main_paned = ttk.PanedWindow(self.parent, orient=tk.HORIZONTAL)
        main_paned.pack(fill=tk.BOTH, expand=True)
        
        # ============ ЛЕВАЯ ЧАСТЬ - Результаты ============
        left_frame = ttk.Frame(main_paned)
        main_paned.add(left_frame, weight=3)
        
        result_title = ttk.Label(left_frame, text="РЕЗУЛЬТАТЫ РАЗДЕЛЕНИЯ", 
                                 font=('Arial', 12, 'bold'), foreground='blue')
        result_title.pack(pady=(0, 5))
        
        self.result_text = scrolledtext.ScrolledText(left_frame, height=20, font=("Courier", 9))
        self.result_text.pack(fill=tk.BOTH, expand=True)
        
        # Настройка стилей
        self.result_text.tag_configure("header", foreground="blue", font=('Arial', 11, 'bold'))
        self.result_text.tag_configure("success", foreground="green", font=('Arial', 10, 'bold'))
        self.result_text.tag_configure("error", foreground="red", font=('Courier New', 9, 'bold'))
        
        # ============ ПРАВАЯ ЧАСТЬ - Настройки ============
        right_frame = ttk.Frame(main_paned, width=500)
        main_paned.add(right_frame, weight=1)
        
        settings_title = ttk.Label(right_frame, text="НАСТРОЙКИ", 
                                   font=('Arial', 12, 'bold'), foreground='green')
        settings_title.pack(pady=(0, 10))
        
        # Блок выбора файлов
        file_frame = ttk.LabelFrame(right_frame, text="Выбор файлов", padding="10")
        file_frame.pack(fill=tk.X, pady=(0, 10))
        
        btn_select = ttk.Button(file_frame, text="ВЫБРАТЬ ФАЙЛЫ POU", command=self.select_files)
        btn_select.pack(fill=tk.X, pady=(0, 5))
        
        btn_select_folder = ttk.Button(file_frame, text="ВЫБРАТЬ ПАПКУ", command=self.select_folder)
        btn_select_folder.pack(fill=tk.X, pady=(0, 5))
        
        self.file_count_label = ttk.Label(file_frame, text="Файлов: 0", foreground="gray")
        self.file_count_label.pack(anchor=tk.W, pady=(5, 0))
        
        # Список файлов
        listbox_frame = ttk.Frame(file_frame)
        listbox_frame.pack(fill=tk.BOTH, expand=True, pady=(5, 0))
        
        self.files_listbox = tk.Listbox(listbox_frame, height=6, font=("Courier", 8))
        self.files_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        scrollbar = ttk.Scrollbar(listbox_frame, orient=tk.VERTICAL, command=self.files_listbox.yview)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.files_listbox.config(yscrollcommand=scrollbar.set)
        
        # Кнопки действий
        action_frame = ttk.LabelFrame(right_frame, text="Действия", padding="10")
        action_frame.pack(fill=tk.X, pady=(0, 10))
        
        btn_split = ttk.Button(action_frame, text="РАЗДЕЛИТЬ ВСЕ ФАЙЛЫ", command=self.split_files)
        btn_split.pack(fill=tk.X, pady=(0, 5))
        
        btn_clear = ttk.Button(action_frame, text="ОЧИСТИТЬ", command=self.clear_all)
        btn_clear.pack(fill=tk.X)
        
        # Статус
        status_frame = ttk.LabelFrame(right_frame, text="Статус", padding="10")
        status_frame.pack(fill=tk.X)
        
        self.status_label = ttk.Label(status_frame, text="Готов к работе", foreground="gray", wraplength=450)
        self.status_label.pack(anchor=tk.W)
    
    def clear_all(self):
        self.input_files = []
        self.files_listbox.delete(0, tk.END)
        self.result_text.delete('1.0', tk.END)
        self.file_count_label.config(text="Файлов: 0")
        self.status_label.config(text="Очищено", foreground="gray")
    
    def select_files(self):
        files = filedialog.askopenfilenames(
            title="Выберите файлы для разделения",
            filetypes=[
                ("Все файлы", "*.*"),
                ("Текстовые файлы", "*.txt"),
                ("XML файлы", "*.xml"),
                ("LOG файлы", "*.log"),
                ("CSV файлы", "*.csv")
            ]
        )
        if files:
            self.input_files = list(files)
            self.update_files_list()
            self.status_label.config(text=f"Загружено файлов: {len(self.input_files)}", foreground="green")
            return self.input_files
        return []
    
    def select_folder(self):
        folder = filedialog.askdirectory(title="Выберите папку с файлами")
        if folder:
            files = []
            for file in os.listdir(folder):
                if file.lower().endswith(('.txt', '.xml', '.log', '.csv')):
                    files.append(os.path.join(folder, file))
            if files:
                self.input_files = files
                self.update_files_list()
                self.status_label.config(text=f"Загружено файлов из папки: {len(self.input_files)}", foreground="green")
                return self.input_files
            else:
                messagebox.showwarning("Предупреждение", "Нет файлов для обработки в выбранной папке!")
        return []
    
    def update_files_list(self):
        self.files_listbox.delete(0, tk.END)
        for file_path in self.input_files:
            self.files_listbox.insert(tk.END, os.path.basename(file_path))
        self.file_count_label.config(text=f"Файлов: {len(self.input_files)}")
    
    def contains_keyword(self, line):
        cleaned_line = line.strip()
        if not cleaned_line:
            return False
        patterns = [r'\.Xin', r'\.Xs', r'\.OUT, 0.0,']
        for pattern in patterns:
            if re.search(pattern, cleaned_line, re.IGNORECASE):
                return True
        return False
    
    def split_file(self, file_path, output_dir):
        try:
            fbd_folder = os.path.join(output_dir, "FBD разделенный")
            st_folder = os.path.join(output_dir, "ST разделенный")
            os.makedirs(fbd_folder, exist_ok=True)
            os.makedirs(st_folder, exist_ok=True)
            
            base_name = os.path.splitext(os.path.basename(file_path))[0]
            ext = os.path.splitext(file_path)[1]
            
            fbd_file = os.path.join(fbd_folder, f"{base_name}{ext}")
            st_file = os.path.join(st_folder, f"{base_name}{ext}")
            
            with open(file_path, 'r', encoding='utf-8') as file:
                lines = file.readlines()
            
            lines_without_keywords = []
            lines_with_keywords = []
            
            for line in lines:
                if self.contains_keyword(line):
                    lines_with_keywords.append(line)
                else:
                    lines_without_keywords.append(line)
            
            while lines_with_keywords and lines_with_keywords[-1].strip() == '':
                lines_with_keywords.pop()
            
            with open(fbd_file, 'w', encoding='utf-8') as file:
                file.writelines(lines_without_keywords)
            
            with open(st_file, 'w', encoding='utf-8') as file:
                file.writelines(lines_with_keywords)
            
            return {
                'filename': os.path.basename(file_path),
                'fbd_lines': len(lines_without_keywords),
                'st_lines': len(lines_with_keywords),
                'total_lines': len(lines),
                'fbd_folder': fbd_folder,
                'st_folder': st_folder,
                'success': True
            }
        except Exception as e:
            return {
                'filename': os.path.basename(file_path),
                'error': str(e),
                'success': False
            }
    
    def split_files(self, output_dir=None, silent=False):
        if not self.input_files:
            if not silent:
                messagebox.showwarning("Предупреждение", "Выберите файлы для обработки!")
            return None
        
        if not output_dir:
            output_dir = filedialog.askdirectory(title="Выберите папку для сохранения результатов")
            if not output_dir:
                return None
        
        self.status_label.config(text="Разделение файлов...")
        if not silent:
            self.result_text.delete('1.0', tk.END)
            self.result_text.insert(tk.END, "РАЗДЕЛЕНИЕ ФАЙЛОВ\n", "header")
            self.result_text.insert(tk.END, "="*70 + "\n\n")
        
        results = []
        success_count = 0
        
        for file_path in self.input_files:
            result = self.split_file(file_path, output_dir)
            results.append(result)
            if result['success']:
                success_count += 1
                if not silent:
                    self.result_text.insert(tk.END, f"✅ {result['filename']}\n", "success")
            else:
                if not silent:
                    self.result_text.insert(tk.END, f"❌ {result['filename']} - {result['error']}\n", "error")
        
        if not silent:
            self.result_text.insert(tk.END, "\n" + "="*70 + "\n")
            self.result_text.insert(tk.END, f"✅ Успешно: {success_count} файлов\n", "success")
            if len(self.input_files) - success_count > 0:
                self.result_text.insert(tk.END, f"❌ С ошибками: {len(self.input_files) - success_count}\n", "error")
            self.result_text.insert(tk.END, f"📁 FBD: {os.path.join(output_dir, 'FBD разделенный')}\n")
            self.result_text.insert(tk.END, f"📁 ST: {os.path.join(output_dir, 'ST разделенный')}\n")
        
        self.status_label.config(text=f"Разделено {success_count} файлов", foreground="green")
        
        return {
            'output_dir': output_dir,
            'fbd_folder': os.path.join(output_dir, "FBD разделенный"),
            'st_folder': os.path.join(output_dir, "ST разделенный"),
            'results': results,
            'success_count': success_count
        }