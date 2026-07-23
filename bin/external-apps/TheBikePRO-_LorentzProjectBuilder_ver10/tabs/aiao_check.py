import os
import tkinter as tk
from tkinter import ttk, scrolledtext, filedialog, messagebox
from tabs.file_splitter import FileSplitterTab
from tabs.xml_parser import XMLParserTab
from tabs.search_tags import SearchTab
from tabs.excel_xml_match import ExcelXMLMatchTab
from utils.help_window import create_help_window


class AIAO_CheckTab:
    """Объединённая вкладка для AI/AO"""
    
    def __init__(self, parent):
        self.parent = parent
        self.create_widgets()
    
    def show_help(self):
        content = """📌 НАЗНАЧЕНИЕ - Объединённый инструмент для работы с AI/AO.

📊 Вкладка "Соответствие Excel и XML файл (ST)": Сравнение каналов тегов между Excel и XML.
📊 Вкладка "Соответствие XML файл (ST) и FBD": 
   • Автообработка - полный цикл за один клик
   • Ручная обработка - разделение файлов, сбор тегов, поиск"""
        create_help_window(self.parent, "📊 Проверка AI/AO", content)
    
    def create_widgets(self):
        main_frame = ttk.Frame(self.parent, padding=4)
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Верхняя панель
        header_frame = ttk.Frame(main_frame)
        header_frame.pack(fill=tk.X, pady=(0, 4))
        
        title = ttk.Label(header_frame, text="ПРОВЕРКА AI/AO", font=("Arial", 12, "bold"))
        title.pack(side=tk.LEFT)
        
        btn_help = ttk.Button(header_frame, text="❓ Справка", command=self.show_help, width=10)
        btn_help.pack(side=tk.RIGHT)
        
        # Внутренний Notebook
        inner_notebook = ttk.Notebook(main_frame)
        inner_notebook.pack(fill=tk.BOTH, expand=True)
        
        # --- Вкладка 1: Соответствие Excel и XML файл (ST) ---
        self.tab_excel_xml = ttk.Frame(inner_notebook)
        inner_notebook.add(self.tab_excel_xml, text="📊 Соответствие Excel и XML файл (ST)")
        self.excel_xml_match = ExcelXMLMatchTab(self.tab_excel_xml)
        
        # --- Вкладка 2: Соответствие XML файл (ST) и FBD ---
        self.tab_xml_fbd = ttk.Frame(inner_notebook)
        inner_notebook.add(self.tab_xml_fbd, text="📊 Соответствие XML файл (ST) и FBD")
        
        # Подвкладки
        sub_notebook = ttk.Notebook(self.tab_xml_fbd)
        sub_notebook.pack(fill=tk.BOTH, expand=True, padx=3, pady=3)
        
        # Автообработка
        self.tab_auto = ttk.Frame(sub_notebook)
        sub_notebook.add(self.tab_auto, text="🤖 Автоматическая обработка")
        self.auto_tab = AutoProcessTab(self.tab_auto, parent_tab=self)
        
        # Ручная обработка
        self.tab_manual = ttk.Frame(sub_notebook)
        sub_notebook.add(self.tab_manual, text="🛠 Ручная обработка")
        
        manual_notebook = ttk.Notebook(self.tab_manual)
        manual_notebook.pack(fill=tk.BOTH, expand=True, padx=3, pady=3)
        
        self.tab_splitter = ttk.Frame(manual_notebook)
        manual_notebook.add(self.tab_splitter, text="📂 Разделить POU")
        self.splitter = FileSplitterTab(self.tab_splitter, parent_tab=self)
        
        self.tab_parser = ttk.Frame(manual_notebook)
        manual_notebook.add(self.tab_parser, text="🔍 Собрать теги")
        self.parser = XMLParserTab(self.tab_parser, parent_tab=self)
        
        self.tab_search = ttk.Frame(manual_notebook)
        manual_notebook.add(self.tab_search, text="🔎 Наличие тегов")
        self.search = SearchTab(self.tab_search, parent_tab=self)


class AutoProcessTab:
    """Автоматическая обработка - с двумя колонками в результатах"""
    
    EXCLUDED_TAGS = {
        'PROGRAM', 'in', 'sig', 'v2', 'HLB', 'ZH36',
        'A20_02', 'A20_03', 'A20_04', 'A20_05', 'A20_06', 'A20_07', 'A20_08', 'A20_09', 'A20_10',
        'A20_channels', 'A22_00', 'A22_01', 'A22_02', 'A22_03', 'A22_channels',
        'A23_00', 'A23_01', 'A23_02', 'A23_03', 'A23_channels'
    }
    
    EXCLUDED_SUFFIXES = (
        '_MOS', '_SRV', '_HLB', '_IO',
        '_SP_HH', '_SP_LL', '_SP_H', '_SP_L',
        '_HH', '_LL', '_H', '_L',
        '_ALARM', '_STATUS', '_STATE'
    )
    
    EXCLUDED_PATTERNS = ('_AI16H',)
    
    def __init__(self, parent, parent_tab=None):
        self.parent = parent
        self.parent_tab = parent_tab
        self.input_files = []
        self.last_results = None
        self.create_widgets()
    
    def show_help(self):
        content = """▶️ АВТОМАТИЧЕСКАЯ ОБРАБОТКА

1. Выберите файлы POU (кнопка "Выбрать файлы" или "Выбрать папку")
2. Выберите папку для результатов
3. Нажмите "🚀 АВТОМАТИЧЕСКАЯ ОБРАБОТКА"

Результаты сохраняются в папки:
   • FBD разделенный/
   • ST разделенный/
   • Собранные теги/"""
        create_help_window(self.parent, "🤖 Автоматическая обработка", content)
    
    def create_widgets(self):
        main_paned = ttk.PanedWindow(self.parent, orient=tk.HORIZONTAL)
        main_paned.pack(fill=tk.BOTH, expand=True)
        
        # Левая часть - результаты
        left_frame = ttk.Frame(main_paned)
        main_paned.add(left_frame, weight=3)
        
        result_title = ttk.Label(left_frame, text="РЕЗУЛЬТАТЫ АВТОМАТИЧЕСКОЙ ОБРАБОТКИ", 
                                 font=('Arial', 10, 'bold'), foreground='blue')
        result_title.pack(pady=(0, 4))
        
        self.result_text = scrolledtext.ScrolledText(left_frame, height=12, font=("Courier", 8))
        self.result_text.pack(fill=tk.BOTH, expand=True)
        
        # Стили
        self.result_text.tag_configure("header", foreground="blue", font=('Arial', 9, 'bold'))
        self.result_text.tag_configure("error", foreground="red", font=('Courier New', 8, 'bold'))
        self.result_text.tag_configure("success", foreground="green", font=('Arial', 9, 'bold'))
        self.result_text.tag_configure("warning", foreground="purple", font=('Courier New', 8, 'bold'))
        self.result_text.tag_configure("step", foreground="#0066cc", font=('Arial', 9, 'bold'))
        self.result_text.tag_configure("column_header", foreground="#2c3e50", font=('Arial', 9, 'bold'))
        self.result_text.tag_configure("file_header", foreground="#0066cc", font=('Arial', 9, 'bold'))
        self.result_text.tag_configure("stat", foreground="#2c3e50", font=('Arial', 9, 'bold'))
        
        # Правая часть - настройки
        right_frame = ttk.Frame(main_paned, width=350)
        main_paned.add(right_frame, weight=1)
        
        settings_title = ttk.Label(right_frame, text="НАСТРОЙКИ", 
                                   font=('Arial', 10, 'bold'), foreground='green')
        settings_title.pack(pady=(0, 4))
        
        # Выбор файлов
        file_frame = ttk.LabelFrame(right_frame, text="Выбор файлов POU", padding=4)
        file_frame.pack(fill=tk.X, pady=(0, 4))
        
        btn_row = ttk.Frame(file_frame)
        btn_row.pack(fill=tk.X, pady=2)
        
        ttk.Button(btn_row, text="Выбрать файлы", command=self.select_files).pack(side=tk.LEFT, padx=2, fill=tk.X, expand=True)
        ttk.Button(btn_row, text="Выбрать папку", command=self.select_folder).pack(side=tk.LEFT, padx=2, fill=tk.X, expand=True)
        ttk.Button(btn_row, text="✕ Очистить", command=self.clear_files, width=10).pack(side=tk.RIGHT, padx=2)
        
        self.file_count_label = ttk.Label(file_frame, text="Файлов: 0", foreground="gray")
        self.file_count_label.pack(anchor=tk.W, pady=2)
        
        # Список файлов (уменьшенный)
        self.files_listbox = tk.Listbox(file_frame, height=3, font=("Courier", 7))
        self.files_listbox.pack(fill=tk.X, pady=2)
        
        # Кнопки действий
        action_frame = ttk.LabelFrame(right_frame, text="Действия", padding=4)
        action_frame.pack(fill=tk.X, pady=4)
        
        self.auto_btn = ttk.Button(action_frame, text="🚀 АВТОМАТИЧЕСКАЯ ОБРАБОТКА", command=self.auto_process)
        self.auto_btn.pack(fill=tk.X, pady=2)
        
        self.save_btn = ttk.Button(action_frame, text="💾 СОХРАНИТЬ РЕЗУЛЬТАТЫ", command=self.save_results, state=tk.DISABLED)
        self.save_btn.pack(fill=tk.X, pady=2)
        
        ttk.Button(action_frame, text="ОЧИСТИТЬ РЕЗУЛЬТАТЫ", command=self.clear_results).pack(fill=tk.X, pady=2)
        
        # Прогресс
        progress_frame = ttk.LabelFrame(right_frame, text="Прогресс", padding=4)
        progress_frame.pack(fill=tk.X, pady=4)
        
        self.progress = ttk.Progressbar(progress_frame, mode='determinate', length=100)
        self.progress.pack(fill=tk.X)
        
        self.progress_label = ttk.Label(progress_frame, text="0%", foreground="gray")
        self.progress_label.pack(anchor=tk.W, pady=2)
        
        # Статус
        status_frame = ttk.LabelFrame(right_frame, text="Статус", padding=4)
        status_frame.pack(fill=tk.X)
        
        self.status_label = ttk.Label(status_frame, text="Готов к работе", foreground="gray", wraplength=330)
        self.status_label.pack(anchor=tk.W)
    
    def select_files(self):
        files = filedialog.askopenfilenames(
            title="Выберите файлы для обработки",
            filetypes=[("Все файлы", "*.*"), ("Текстовые", "*.txt"), ("XML", "*.xml")]
        )
        if files:
            self.input_files = list(files)
            self.update_files_list()
    
    def select_folder(self):
        folder = filedialog.askdirectory(title="Выберите папку с файлами")
        if folder:
            files = []
            for f in os.listdir(folder):
                if f.lower().endswith(('.txt', '.xml', '.log', '.csv')):
                    files.append(os.path.join(folder, f))
            if files:
                self.input_files = files
                self.update_files_list()
            else:
                messagebox.showwarning("Предупреждение", "Нет файлов для обработки в выбранной папке!")
    
    def update_files_list(self):
        self.files_listbox.delete(0, tk.END)
        for f in self.input_files:
            self.files_listbox.insert(tk.END, os.path.basename(f))
        self.file_count_label.config(text=f"Файлов: {len(self.input_files)}")
        self.status_label.config(text=f"Загружено файлов: {len(self.input_files)}", foreground="green")
    
    def clear_files(self):
        self.input_files = []
        self.files_listbox.delete(0, tk.END)
        self.file_count_label.config(text="Файлов: 0")
        self.status_label.config(text="Список файлов очищен", foreground="gray")
    
    def clear_results(self):
        self.result_text.delete('1.0', tk.END)
        self.progress['value'] = 0
        self.progress_label.config(text="0%")
        self.save_btn.config(state=tk.DISABLED)
        self.status_label.config(text="Результаты очищены", foreground="gray")
    
    def update_progress(self, value, message):
        self.progress['value'] = value
        self.progress_label.config(text=f"{int(value)}%")
        self.status_label.config(text=message, foreground="blue")
        self.parent.update_idletasks()
    
    def is_valid_tag(self, tag):
        if not tag:
            return False
        if tag in self.EXCLUDED_TAGS:
            return False
        for pattern in self.EXCLUDED_PATTERNS:
            if pattern in tag:
                return False
        for suffix in self.EXCLUDED_SUFFIXES:
            if tag.endswith(suffix):
                return False
        if tag.startswith('_'):
            if tag.startswith('_IO'):
                return False
            return True
        elif tag.startswith('B0'):
            return True
        return False
    
    def filter_tags(self, tags):
        return [tag for tag in tags if self.is_valid_tag(tag)]
    
    def collect_and_save_tags(self, st_folder, fbd_folder, output_dir):
        import re
        tags_folder = os.path.join(output_dir, "Собранные теги")
        os.makedirs(tags_folder, exist_ok=True)
        
        st_tags_by_file = {}
        for f in os.listdir(st_folder):
            if f.lower().endswith(('.txt', '.xml')):
                file_path = os.path.join(st_folder, f)
                base_name = os.path.splitext(f)[0]
                try:
                    with open(file_path, 'r', encoding='utf-8') as file:
                        content = file.read()
                    tags = []
                    matches = re.findall(r'([a-zA-Z0-9_\-]+)\.xin', content, re.IGNORECASE)
                    tags.extend(matches)
                    matches = re.findall(r'([a-zA-Z0-9_\-]+)\.OUT', content, re.IGNORECASE)
                    tags.extend(matches)
                    matches = re.findall(r'\b(_(?!IO)[a-zA-Z0-9_\-]+|B0[a-zA-Z0-9_\-]*)\b', content)
                    tags.extend(matches)
                    tags = list(set(tags))
                    valid_tags = self.filter_tags(tags)
                    if valid_tags:
                        normalized_tags = [tag.upper() for tag in valid_tags]
                        st_tags_by_file[base_name] = sorted(normalized_tags)
                        with open(os.path.join(tags_folder, f"{base_name}_ST.txt"), 'w', encoding='utf-8') as file:
                            file.write('\n'.join(normalized_tags))
                except Exception as e:
                    print(f"Ошибка чтения ST файла {f}: {e}")
        
        fbd_tags_by_file = {}
        for f in os.listdir(fbd_folder):
            if f.lower().endswith(('.txt', '.xml')):
                file_path = os.path.join(fbd_folder, f)
                base_name = os.path.splitext(f)[0]
                try:
                    with open(file_path, 'r', encoding='utf-8') as file:
                        content = file.read()
                    tags = re.findall(r'\b(_(?!IO)[a-zA-Z0-9_\-]+|B0[a-zA-Z0-9_\-]*)\b', content)
                    tags = list(set(tags))
                    valid_tags = self.filter_tags(tags)
                    if valid_tags:
                        normalized_tags = [tag.upper() for tag in valid_tags]
                        fbd_tags_by_file[base_name] = sorted(normalized_tags)
                        with open(os.path.join(tags_folder, f"{base_name}_FBD.txt"), 'w', encoding='utf-8') as file:
                            file.write('\n'.join(normalized_tags))
                except Exception as e:
                    print(f"Ошибка чтения FBD файла {f}: {e}")
        
        return st_tags_by_file, fbd_tags_by_file
    
    def load_tags_from_folder(self, folder_path):
        result = {}
        if not os.path.exists(folder_path):
            return result
        files_by_base = {}
        for f in os.listdir(folder_path):
            if not f.lower().endswith('.txt'):
                continue
            if f.endswith('_ST.txt'):
                base_name = f[:-7]
                ftype = 'ST'
            elif f.endswith('_FBD.txt'):
                base_name = f[:-8]
                ftype = 'FBD'
            else:
                continue
            if base_name not in files_by_base:
                files_by_base[base_name] = {}
            files_by_base[base_name][ftype] = f
        for base_name, file_dict in files_by_base.items():
            result[base_name] = {'ST': [], 'FBD': []}
            for ftype, fname in file_dict.items():
                try:
                    with open(os.path.join(folder_path, fname), 'r', encoding='utf-8') as file:
                        tags = [line.strip().upper() for line in file if line.strip()]
                    result[base_name][ftype] = sorted(tags)
                except Exception as e:
                    print(f"Ошибка чтения {fname}: {e}")
        return result
    
    def compare_tag_files(self, tags_data):
        st_not_in_fbd = {}
        fbd_not_in_st = {}
        for base_name, data in tags_data.items():
            st_tags = set(data.get('ST', []))
            fbd_tags = set(data.get('FBD', []))
            missing_in_fbd = st_tags - fbd_tags
            if missing_in_fbd:
                st_not_in_fbd[base_name] = sorted(missing_in_fbd)
            missing_in_st = fbd_tags - st_tags
            if missing_in_st:
                fbd_not_in_st[base_name] = sorted(missing_in_st)
        return st_not_in_fbd, fbd_not_in_st
    
    def display_results(self, st_not_in_fbd, fbd_not_in_st, output_dir):
        self.result_text.delete('1.0', tk.END)
        
        total_st_not_found = sum(len(tags) for tags in st_not_in_fbd.values())
        total_fbd_not_found = sum(len(tags) for tags in fbd_not_in_st.values())
        total_errors = total_st_not_found + total_fbd_not_found
        
        # Заголовок
        self.result_text.insert(tk.END, "="*90 + "\n")
        if total_errors == 0:
            self.result_text.insert(tk.END, "🎉 ВСЕ ТЕГИ СОВПАДАЮТ! ОШИБОК НЕ НАЙДЕНО.\n", "success")
        else:
            self.result_text.insert(tk.END, f"⚠️ НАЙДЕНО {total_errors} ОШИБОК(И)\n", "error")
        self.result_text.insert(tk.END, "="*90 + "\n\n")
        
        # Статистика по файлам
        self.result_text.insert(tk.END, "📊 СТАТИСТИКА ПО ФАЙЛАМ:\n", "stat")
        self.result_text.insert(tk.END, "-"*90 + "\n")
        
        all_files = set(st_not_in_fbd.keys()) | set(fbd_not_in_st.keys())
        for file_name in sorted(all_files):
            st_missing = len(st_not_in_fbd.get(file_name, []))
            fbd_missing = len(fbd_not_in_st.get(file_name, []))
            total = st_missing + fbd_missing
            status = "❌" if total > 0 else "✅"
            self.result_text.insert(tk.END, f"  {status} {file_name}: ST→FBD: {st_missing}, FBD→ST: {fbd_missing}\n")
        self.result_text.insert(tk.END, "\n")
        
        # Две колонки
        self.result_text.insert(tk.END, "="*90 + "\n")
        self.result_text.insert(tk.END, f"{'❌ ТЕГИ ИЗ ST, КОТОРЫХ НЕТ В FBD':<44} | {'❌ ТЕГИ ИЗ FBD, КОТОРЫХ НЕТ В ST':<44}\n", "column_header")
        self.result_text.insert(tk.END, "="*90 + "\n\n")
        
        all_files_display = sorted(set(st_not_in_fbd.keys()) | set(fbd_not_in_st.keys()))
        
        for file_name in all_files_display:
            st_tags = st_not_in_fbd.get(file_name, [])
            fbd_tags = fbd_not_in_st.get(file_name, [])
            
            if not st_tags and not fbd_tags:
                continue
            
            self.result_text.insert(tk.END, f"📄 {file_name}\n", "file_header")
            self.result_text.insert(tk.END, "-"*90 + "\n")
            
            max_lines = max(len(st_tags), len(fbd_tags))
            for i in range(max_lines):
                left_text = f"  • {st_tags[i]}" if i < len(st_tags) else ""
                right_text = f"  • {fbd_tags[i]}" if i < len(fbd_tags) else ""
                left_padded = left_text.ljust(44)
                self.result_text.insert(tk.END, f"{left_padded} | {right_text}\n")
            
            self.result_text.insert(tk.END, "-"*90 + "\n")
            self.result_text.insert(tk.END, f"  ST→FBD: {len(st_tags)} | FBD→ST: {len(fbd_tags)}\n")
            self.result_text.insert(tk.END, "\n")
        
        # Итоговая статистика
        self.result_text.insert(tk.END, "="*90 + "\n")
        self.result_text.insert(tk.END, "ИТОГОВАЯ СТАТИСТИКА:\n", "stat")
        self.result_text.insert(tk.END, "="*90 + "\n\n")
        self.result_text.insert(tk.END, f"📊 Всего ошибок: {total_errors}\n", "error")
        self.result_text.insert(tk.END, f"   ❌ ST→FBD: {total_st_not_found}\n", "error")
        self.result_text.insert(tk.END, f"   ❌ FBD→ST: {total_fbd_not_found}\n", "error")
        self.result_text.insert(tk.END, f"\n📁 Результаты сохранены в: {output_dir}\n")
        self.result_text.insert(tk.END, "="*90 + "\n")
    
    def save_results(self):
        content = self.result_text.get('1.0', tk.END).strip()
        if not content:
            messagebox.showwarning("Предупреждение", "Нет результатов для сохранения!")
            return
        file_path = filedialog.asksaveasfilename(
            title="Сохранить результаты",
            defaultextension=".txt",
            filetypes=[("Текстовые файлы", "*.txt"), ("Все файлы", "*.*")]
        )
        if file_path:
            try:
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(content)
                self.status_label.config(text=f"Результаты сохранены: {os.path.basename(file_path)}", foreground="green")
                messagebox.showinfo("Успех", f"Результаты сохранены в:\n{file_path}")
            except Exception as e:
                messagebox.showerror("Ошибка", f"Не удалось сохранить:\n{str(e)}")
    
    def auto_process(self):
        if not self.input_files:
            messagebox.showwarning("Предупреждение", "Сначала выберите файлы POU!")
            return
        
        output_dir = filedialog.askdirectory(title="Выберите папку для сохранения результатов")
        if not output_dir:
            return
        
        self.result_text.delete('1.0', tk.END)
        self.result_text.insert(tk.END, "🚀 ЗАПУСК АВТОМАТИЧЕСКОЙ ОБРАБОТКИ\n" + "="*90 + "\n\n")
        self.progress['value'] = 0
        self.auto_btn.config(state=tk.DISABLED)
        self.save_btn.config(state=tk.DISABLED)
        
        try:
            parent_tab = self.parent_tab
            
            # Шаг 1: Разделение
            self.result_text.insert(tk.END, "📌 ШАГ 1: РАЗДЕЛЕНИЕ ФАЙЛОВ\n", "step")
            self.result_text.insert(tk.END, "-"*90 + "\n")
            self.update_progress(5, "Разделение файлов...")
            
            splitter = parent_tab.splitter
            splitter.input_files = self.input_files.copy()
            splitter.update_files_list()
            split_result = splitter.split_files(output_dir, silent=True)
            
            if not split_result:
                self.result_text.insert(tk.END, "❌ Ошибка при разделении файлов\n\n", "error")
                return
            
            self.result_text.insert(tk.END, f"✅ Разделено {split_result['success_count']} файлов\n", "success")
            self.result_text.insert(tk.END, f"   📁 FBD: {split_result['fbd_folder']}\n")
            self.result_text.insert(tk.END, f"   📁 ST:  {split_result['st_folder']}\n\n")
            self.update_progress(30, "Разделение завершено")
            
            # Шаг 2: Сбор тегов
            self.result_text.insert(tk.END, "📌 ШАГ 2: СБОР ТЕГОВ\n", "step")
            self.result_text.insert(tk.END, "-"*90 + "\n")
            self.update_progress(40, "Сбор тегов из ST и FBD...")
            
            st_tags, fbd_tags = self.collect_and_save_tags(
                split_result['st_folder'],
                split_result['fbd_folder'],
                output_dir
            )
            
            total_st = sum(len(t) for t in st_tags.values())
            total_fbd = sum(len(t) for t in fbd_tags.values())
            self.result_text.insert(tk.END, f"✅ Собраны теги из ST: {len(st_tags)} файлов, {total_st} тегов\n", "success")
            self.result_text.insert(tk.END, f"✅ Собраны теги из FBD: {len(fbd_tags)} файлов, {total_fbd} тегов\n\n", "success")
            self.update_progress(70, "Сбор тегов завершён")
            
            # Шаг 3: Сравнение
            self.result_text.insert(tk.END, "📌 ШАГ 3: СРАВНЕНИЕ ТЕГОВ\n", "step")
            self.result_text.insert(tk.END, "-"*90 + "\n")
            self.update_progress(80, "Загрузка тегов из папки 'Собранные теги'...")
            
            tags_folder = os.path.join(output_dir, "Собранные теги")
            tags_data = self.load_tags_from_folder(tags_folder)
            
            if not tags_data:
                self.result_text.insert(tk.END, "❌ Не найдены файлы с тегами\n\n", "error")
                return
            
            self.result_text.insert(tk.END, f"✅ Загружены теги для {len(tags_data)} файлов\n", "success")
            self.update_progress(85, "Сравнение тегов...")
            
            st_not_in_fbd, fbd_not_in_st = self.compare_tag_files(tags_data)
            self.update_progress(95, "Формирование результатов...")
            self.display_results(st_not_in_fbd, fbd_not_in_st, output_dir)
            
            self.update_progress(100, "Обработка завершена!")
            self.result_text.insert(tk.END, "\n" + "="*90 + "\n")
            self.result_text.insert(tk.END, "🎉 АВТОМАТИЧЕСКАЯ ОБРАБОТКА ЗАВЕРШЕНА!\n", "success")
            self.result_text.insert(tk.END, "="*90 + "\n")
            
            self.status_label.config(text="✅ Автоматическая обработка завершена", foreground="green")
            
            if st_not_in_fbd or fbd_not_in_st:
                self.save_btn.config(state=tk.NORMAL)
            
            messagebox.showinfo("Успех", f"Автоматическая обработка завершена!\n\n"
                               f"📁 Результаты сохранены в:\n{output_dir}")
            
        except Exception as e:
            import traceback
            error_details = traceback.format_exc()
            self.result_text.insert(tk.END, f"\n❌ ОШИБКА: {str(e)}\n", "error")
            self.result_text.insert(tk.END, f"\n{error_details}\n")
            self.status_label.config(text=f"Ошибка: {str(e)}", foreground="red")
            messagebox.showerror("Ошибка", f"Произошла ошибка:\n{str(e)}\n\nПодробности в окне результатов.")
        finally:
            self.auto_btn.config(state=tk.NORMAL)