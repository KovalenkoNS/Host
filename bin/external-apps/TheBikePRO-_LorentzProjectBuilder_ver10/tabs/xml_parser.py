import os
import re
import tkinter as tk
from tkinter import ttk, filedialog, messagebox, scrolledtext
from utils.help_window import create_help_window


class XMLParserTab:
    """Вкладка для парсинга XML и извлечения тегов .xin и .OUT"""
    
    def __init__(self, parent, parent_tab=None):
        self.parent = parent
        self.parent_tab = parent_tab
        self.file_paths = []
        self.results = []
        self.file_results = {}
        self.create_widgets()
    
    def show_help(self):
        content = """
📌 НАЗНАЧЕНИЕ

Извлекает имена тегов из ST разделенных файлов для создания словарей.

🔍 ЧТО ИЩЕТСЯ
Теги извлекаются по шаблонам: Имя_тега.xin и Имя_тега.OUT
Поиск выполняется без учета регистра символов.

▶️ КАК ВЫБРАТЬ ФАЙЛЫ
   • "1 ФАЙЛ"          - выбрать один XML файл
   • "НЕСКОЛЬКО ФАЙЛОВ" - выбрать несколько файлов
   • "ПАПКА XML"        - выбрать папку со всеми XML файлами
   • "ПАПКА + МАСКА"    - выбрать папку и указать маску (например, *.xml)

💾 СОХРАНЕНИЕ РЕЗУЛЬТАТОВ
   • "СОХРАНИТЬ ВСЕ"        - все теги в один общий файл
   • "СОХРАНИТЬ ПО ФАЙЛАМ"  - отдельный файл для каждого исходного файла

Результаты сохраняются в папку "Собранные теги/"
"""
        create_help_window(self.parent, "🔍 Сбор тегов из ST", content)
    
    def create_widgets(self):
        # Основной фрейм с разделением на левую и правую часть
        main_paned = ttk.PanedWindow(self.parent, orient=tk.HORIZONTAL)
        main_paned.pack(fill=tk.BOTH, expand=True)
        
        # ============ ЛЕВАЯ ЧАСТЬ - Результаты ============
        left_frame = ttk.Frame(main_paned)
        main_paned.add(left_frame, weight=3)
        
        result_title = ttk.Label(left_frame, text="РЕЗУЛЬТАТЫ ПАРСИНГА", 
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
        
        btn1 = ttk.Button(file_frame, text="1 ФАЙЛ", command=self.select_single_file)
        btn1.pack(fill=tk.X, pady=(0, 5))
        
        btn2 = ttk.Button(file_frame, text="НЕСКОЛЬКО ФАЙЛОВ", command=self.select_multiple_files)
        btn2.pack(fill=tk.X, pady=(0, 5))
        
        btn3 = ttk.Button(file_frame, text="ПАПКА XML", command=self.select_folder)
        btn3.pack(fill=tk.X, pady=(0, 5))
        
        btn4 = ttk.Button(file_frame, text="ПАПКА + МАСКА", command=self.select_folder_with_mask)
        btn4.pack(fill=tk.X)
        
        self.file_count_label = ttk.Label(file_frame, text="Файлов: 0", foreground="gray")
        self.file_count_label.pack(anchor=tk.W, pady=(5, 0))
        
        # Список файлов
        listbox_frame = ttk.Frame(file_frame)
        listbox_frame.pack(fill=tk.BOTH, expand=True, pady=(5, 0))
        
        self.files_listbox = tk.Listbox(listbox_frame, height=4, font=("Courier", 8))
        self.files_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        scrollbar = ttk.Scrollbar(listbox_frame, orient=tk.VERTICAL, command=self.files_listbox.yview)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.files_listbox.config(yscrollcommand=scrollbar.set)
        
        # Кнопки действий
        action_frame = ttk.LabelFrame(right_frame, text="Действия", padding="10")
        action_frame.pack(fill=tk.X, pady=(0, 10))
        
        btn_parse = ttk.Button(action_frame, text="НАЙТИ .xin/.out", command=self.parse_files)
        btn_parse.pack(fill=tk.X, pady=(0, 5))
        
        btn_save = ttk.Button(action_frame, text="СОХРАНИТЬ ВСЕ", command=self.save_results)
        btn_save.pack(fill=tk.X, pady=(0, 5))
        
        btn_save_separate = ttk.Button(action_frame, text="СОХРАНИТЬ ПО ФАЙЛАМ", command=self.save_separate_results)
        btn_save_separate.pack(fill=tk.X, pady=(0, 5))
        
        btn_clear = ttk.Button(action_frame, text="ОЧИСТИТЬ", command=self.clear_all)
        btn_clear.pack(fill=tk.X)
        
        # Статус
        status_frame = ttk.LabelFrame(right_frame, text="Статус", padding="10")
        status_frame.pack(fill=tk.X)
        
        self.status_label = ttk.Label(status_frame, text="Готов к работе", foreground="gray", wraplength=450)
        self.status_label.pack(anchor=tk.W)
    
    def clear_all(self):
        self.file_paths = []
        self.results = []
        self.file_results = {}
        self.files_listbox.delete(0, tk.END)
        self.result_text.delete('1.0', tk.END)
        self.file_count_label.config(text="Файлов: 0")
        self.status_label.config(text="Очищено", foreground="gray")
    
    def update_files_list(self):
        self.files_listbox.delete(0, tk.END)
        for file_path in self.file_paths:
            self.files_listbox.insert(tk.END, os.path.basename(file_path))
        self.file_count_label.config(text=f"Файлов: {len(self.file_paths)}")
        self.status_label.config(text=f"Загружено файлов: {len(self.file_paths)}", foreground="green")
    
    def select_single_file(self):
        file_path = filedialog.askopenfilename(
            title="Выберите XML файл",
            filetypes=[
                ("Все файлы", "*.*"),
                ("XML файлы", "*.xml"),
                ("Текстовые файлы", "*.txt")
            ]
        )
        if file_path:
            self.file_paths = [file_path]
            self.update_files_list()
    
    def select_multiple_files(self):
        files = filedialog.askopenfilenames(
            title="Выберите XML файлы",
            filetypes=[
                ("Все файлы", "*.*"),
                ("XML файлы", "*.xml"),
                ("Текстовые файлы", "*.txt")
            ]
        )
        if files:
            self.file_paths = list(files)
            self.update_files_list()
    
    def select_folder(self):
        folder = filedialog.askdirectory(title="Выберите папку с XML файлами")
        if folder:
            xml_files = []
            for file in os.listdir(folder):
                if file.lower().endswith('.xml'):
                    xml_files.append(os.path.join(folder, file))
            if xml_files:
                self.file_paths = xml_files
                self.update_files_list()
            else:
                messagebox.showwarning("Предупреждение", "Нет XML файлов!")
    
    def select_folder_with_mask(self):
        mask_window = tk.Toplevel(self.parent)
        mask_window.title("Маска")
        mask_window.geometry("300x120")
        mask_window.resizable(False, False)
        
        ttk.Label(mask_window, text="Маска файлов:", font=("Arial", 10)).pack(pady=10)
        mask_entry = ttk.Entry(mask_window, width=30)
        mask_entry.pack(pady=5)
        mask_entry.insert(0, "*.xml")
        
        def apply_mask():
            mask = mask_entry.get().strip()
            if not mask:
                messagebox.showerror("Ошибка", "Введите маску!")
                return
            folder = filedialog.askdirectory(title="Выберите папку")
            if folder:
                mask_pattern = mask.replace('*', '.*').replace('?', '.')
                if not mask_pattern.endswith('$'):
                    mask_pattern += '$'
                files = []
                for file in os.listdir(folder):
                    if re.search(mask_pattern, file, re.IGNORECASE):
                        files.append(os.path.join(folder, file))
                if files:
                    self.file_paths = files
                    self.update_files_list()
                else:
                    messagebox.showwarning("Предупреждение", f"Файлы с маской '{mask}' не найдены!")
            mask_window.destroy()
        
        ttk.Button(mask_window, text="Выбрать", command=apply_mask).pack(pady=10)
    
    def center_window(self, window):
        window.update_idletasks()
        width = window.winfo_width()
        height = window.winfo_height()
        x = (window.winfo_screenwidth() // 2) - (width // 2)
        y = (window.winfo_screenheight() // 2) - (height // 2)
        window.geometry(f'{width}x{height}+{x}+{y}')
    
    def extract_names(self, xml_content):
        results = []
        pattern_xin = r'([a-zA-Z0-9_\-]+)\.xin'
        matches_xin = re.findall(pattern_xin, xml_content, re.IGNORECASE)
        results.extend(matches_xin)
        pattern_out = r'([a-zA-Z0-9_\-]+)\.OUT'
        matches_out = re.findall(pattern_out, xml_content, re.IGNORECASE)
        results.extend(matches_out)
        return results
    
    def parse_files(self):
        if not self.file_paths:
            messagebox.showwarning("Предупреждение", "Выберите файлы!")
            return
        
        self.results = []
        self.file_results = {}
        self.result_text.delete('1.0', tk.END)
        self.status_label.config(text="Поиск...")
        
        self.result_text.insert(tk.END, "РЕЗУЛЬТАТЫ ПОИСКА ЭЛЕМЕНТОВ\n", "header")
        self.result_text.insert(tk.END, "="*70 + "\n\n")
        
        all_found = []
        
        for idx, file_path in enumerate(self.file_paths, 1):
            try:
                with open(file_path, 'r', encoding='utf-8') as file:
                    content = file.read()
                names = self.extract_names(content)
                if names:
                    self.file_results[file_path] = names
                    all_found.extend(names)
                    self.result_text.insert(tk.END, f"📄 {os.path.basename(file_path)}\n", "header")
                    self.result_text.insert(tk.END, f"Найдено элементов: {len(names)}\n")
                    self.result_text.insert(tk.END, "-"*70 + "\n")
                    for name in names:
                        self.result_text.insert(tk.END, f"  • {name}\n")
                    self.result_text.insert(tk.END, "\n")
                else:
                    self.file_results[file_path] = []
                    self.result_text.insert(tk.END, f"📄 {os.path.basename(file_path)}\n", "header")
                    self.result_text.insert(tk.END, "Найдено элементов: 0\n")
                    self.result_text.insert(tk.END, "-"*70 + "\n")
                    self.result_text.insert(tk.END, "  (нет .xin/.OUT)\n\n")
            except Exception as e:
                self.result_text.insert(tk.END, f"❌ Ошибка: {os.path.basename(file_path)} - {str(e)}\n", "error")
        
        seen = set()
        for item in all_found:
            if item not in seen:
                seen.add(item)
                self.results.append(item)
        
        self.result_text.insert(tk.END, "="*70 + "\n")
        self.result_text.insert(tk.END, f"✅ Уникальных элементов: {len(self.results)}\n", "success")
        self.result_text.insert(tk.END, f"   Обработано файлов: {len(self.file_paths)}\n")
        self.result_text.insert(tk.END, "="*70 + "\n")
        
        self.status_label.config(text=f"Найдено: {len(self.results)} уникальных элементов", foreground="green")
        messagebox.showinfo("Успех", f"Найдено {len(self.results)} уникальных элементов")
    
    def save_separate_results_silent(self, base_folder):
        if not self.file_results:
            return
        output_folder = os.path.join(base_folder, "Собранные теги")
        try:
            os.makedirs(output_folder, exist_ok=True)
        except Exception as e:
            print(f"Ошибка создания папки: {e}")
            return
        try:
            saved_count = 0
            for file_path, names in self.file_results.items():
                original_filename = os.path.basename(file_path)
                base_name = os.path.splitext(original_filename)[0]
                output_filename = f"{base_name}.txt"
                output_file = os.path.join(output_folder, output_filename)
                
                unique_names = []
                seen = set()
                for name in names:
                    if name not in seen:
                        seen.add(name)
                        unique_names.append(name)
                
                with open(output_file, 'w', encoding='utf-8') as file:
                    for name in unique_names:
                        file.write(f"{name}\n")
                saved_count += 1
            self.status_label.config(text=f"Сохранено {saved_count} файлов в 'Собранные теги'", foreground="green")
        except Exception as e:
            print(f"Ошибка сохранения: {e}")
    
    def save_separate_results(self):
        if not self.file_results:
            messagebox.showwarning("Предупреждение", "Нет результатов для сохранения!")
            return
        base_folder = filedialog.askdirectory(title="Выберите папку для сохранения результатов")
        if not base_folder:
            return
        self.save_separate_results_silent(base_folder)
        messagebox.showinfo("Успех", f"Сохранено файлов в папке:\n{os.path.join(base_folder, 'Собранные теги')}")
    
    def save_results(self):
        if not self.results and not self.file_results:
            messagebox.showwarning("Предупреждение", "Нет результатов!")
            return
        file_path = filedialog.asksaveasfilename(
            title="Сохранить как",
            defaultextension=".txt",
            filetypes=[
                ("Текстовые файлы", "*.txt"),
                ("Все файлы", "*.*")
            ]
        )
        if file_path:
            try:
                with open(file_path, 'w', encoding='utf-8') as file:
                    file.write("РЕЗУЛЬТАТЫ ПОИСКА ЭЛЕМЕНТОВ\n")
                    file.write("="*70 + "\n\n")
                    for idx, (file_path, names) in enumerate(self.file_results.items(), 1):
                        file.write(f"📄 ФАЙЛ {idx}: {os.path.basename(file_path)}\n")
                        file.write("-"*70 + "\n")
                        if names:
                            unique_names = list(set(names))
                            for name in unique_names:
                                file.write(f"  {name}\n")
                        else:
                            file.write("  (нет .xin/.OUT)\n")
                        file.write("\n")
                    file.write("="*70 + "\n")
                    file.write(f"Уникальных элементов: {len(self.results)}\n")
                    file.write(f"Обработано файлов: {len(self.file_paths)}\n")
                    file.write("="*70 + "\n")
                messagebox.showinfo("Успех", f"Сохранено: {os.path.basename(file_path)}\nУникальных элементов: {len(self.results)}")
            except Exception as e:
                messagebox.showerror("Ошибка", str(e))