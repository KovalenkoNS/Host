import os
import re
import tkinter as tk
from tkinter import ttk, filedialog, messagebox, scrolledtext
from utils.help_window import create_help_window
from datetime import datetime


class ExcelXMLMatchTab:
    """Вкладка проверки соответствия Excel и XML файл (ST)"""
    
    def __init__(self, parent):
        self.parent = parent
        self.excel_file = ""
        self.xml_files = []
        self.excel_data = {}      # {tag: channel}
        self.xml_data = {}        # {file_name: {tag: channel}}
        self.mismatches = {}      # {file_name: {tag: (excel_channel, xml_channel)}}
        self.merged_xml_data = {} # {tag: channel} - объединенные данные из всех XML
        self.create_widgets()
    
    def show_help(self):
        content = """
📌 НАЗНАЧЕНИЕ

Проверяет соответствие каналов между Excel файлом и XML файл (ST).

🔍 ЧТО ПРОВЕРЯЕТСЯ

1. Извлекает теги из Excel (вида: _1110_FIA_10102.Xin := ...)
2. Извлекает теги из XML файл (ST) (аналогичного вида)
3. Сравнивает номера каналов для каждого тега

📊 РЕЗУЛЬТАТЫ

Показываются ТОЛЬКО несоответствия:
   ❌ Тег есть в Excel, но отсутствует в XML
   ❌ Тег есть в XML, но отсутствует в Excel
   ⚠️  Канал в Excel не совпадает с каналом в XML

📌 ОСОБЕННОСТИ

• Поддерживаются оба формата Excel и XML
• Регистр суффиксов не важен (.Xin = .xin, .Xs = .xs)
• Каналы определяются по шаблонам:
   - _IO_IU*A10-02*_0.ValueDINT → канал 0
   - _IO_I7_AI16H_0_VAL.Measurement → канал 0
   - _IO_I*А1-00*_0_VAL → канал 0 (без AI16H)
   - _IO_I*А1-00*_0_AI16H_0_VAL → канал 0 (с AI16H)
• XML файл (ST) загружаются через кнопку "Выбрать файлы POU"
• Игнорируются первые две строки в XML файл (ST)
• Игнорируются теги-заглушки _1000*, _2000*, _3000*
• Кнопка "Объединить XML" объединяет все XML файлы в один словарь
"""
        create_help_window(self.parent, "📊 Соответствие Excel и XML файл (ST)", content)
    
    def create_widgets(self):
        main_frame = ttk.Frame(self.parent, padding=10)
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Основной контейнер с разделением на левую и правую часть
        paned = ttk.PanedWindow(main_frame, orient=tk.HORIZONTAL)
        paned.pack(fill=tk.BOTH, expand=True)
        
        # ============ ЛЕВАЯ ЧАСТЬ - Результаты ============
        left_frame = ttk.Frame(paned)
        paned.add(left_frame, weight=2)
        
        result_title = ttk.Label(left_frame, text="РЕЗУЛЬТАТЫ ПРОВЕРКИ", 
                                font=('Arial', 12, 'bold'), foreground='blue')
        result_title.pack(pady=(0, 5))
        
        result_container = ttk.Frame(left_frame)
        result_container.pack(fill=tk.BOTH, expand=True)
        
        self.result_text = scrolledtext.ScrolledText(result_container, height=20, font=("Courier", 9))
        self.result_text.pack(fill=tk.BOTH, expand=True)
        
        self.result_text.tag_configure("header", foreground="blue", font=('Arial', 11, 'bold'))
        self.result_text.tag_configure("error", foreground="red", font=('Courier New', 9, 'bold'))
        self.result_text.tag_configure("success", foreground="green", font=('Arial', 10, 'bold'))
        self.result_text.tag_configure("warning", foreground="purple", font=('Courier New', 9, 'bold'))
        self.result_text.tag_configure("compare", foreground="blue", font=('Courier New', 9))
        
        # ============ ПРАВАЯ ЧАСТЬ - Настройки ============
        right_frame = ttk.Frame(paned, width=500)
        paned.add(right_frame, weight=1)
        
        settings_title = ttk.Label(right_frame, text="НАСТРОЙКИ ПРОВЕРКИ", 
                                  font=('Arial', 12, 'bold'), foreground='green')
        settings_title.pack(pady=(0, 15))
        
        # ============================================
        # ШАГ 1: Выбор Excel файла
        # ============================================
        step1_frame = ttk.LabelFrame(right_frame, text="Шаг 1: Выбор Excel файла", padding="10")
        step1_frame.pack(fill=tk.X, pady=(0, 10))
        
        file_row1 = ttk.Frame(step1_frame)
        file_row1.pack(fill=tk.X)
        
        self.excel_path_var = tk.StringVar(value="Файл не выбран")
        file_entry = ttk.Entry(file_row1, textvariable=self.excel_path_var, state='readonly')
        file_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 5))
        
        btn_excel = ttk.Button(file_row1, text="Выбрать Excel", 
                              command=self.select_excel_file)
        btn_excel.pack(side=tk.RIGHT)
        
        self.excel_status = ttk.Label(step1_frame, text="❌ Файл не загружен", foreground="red")
        self.excel_status.pack(anchor=tk.W, pady=(5, 0))
        
        # ============================================
        # ШАГ 2: Выбор XML файлов (ST)
        # ============================================
        step2_frame = ttk.LabelFrame(right_frame, text="Шаг 2: Выбор XML файлов (ST)", padding="10")
        step2_frame.pack(fill=tk.X, pady=(0, 10))
        
        file_row2 = ttk.Frame(step2_frame)
        file_row2.pack(fill=tk.X)
        
        self.xml_count_label = ttk.Label(file_row2, text="Файлов: 0", foreground="gray")
        self.xml_count_label.pack(side=tk.LEFT, padx=(0, 10))
        
        btn_xml = ttk.Button(file_row2, text="Выбрать файлы POU", 
                            command=self.select_xml_files)
        btn_xml.pack(side=tk.RIGHT)
        
        self.xml_status = ttk.Label(step2_frame, text="❌ Файлы не загружены", foreground="red")
        self.xml_status.pack(anchor=tk.W, pady=(5, 0))
        
        listbox_frame = ttk.Frame(step2_frame)
        listbox_frame.pack(fill=tk.X, pady=(5, 0))
        
        self.xml_files_listbox = tk.Listbox(listbox_frame, height=4, font=("Courier", 8), 
                                           selectmode=tk.EXTENDED)
        self.xml_files_listbox.pack(side=tk.LEFT, fill=tk.X, expand=True)
        
        scrollbar = ttk.Scrollbar(listbox_frame, orient=tk.VERTICAL, 
                                 command=self.xml_files_listbox.yview)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.xml_files_listbox.config(yscrollcommand=scrollbar.set)
        
        # ============================================
        # ШАГ 3: Объединение XML файлов
        # ============================================
        step3_frame = ttk.LabelFrame(right_frame, text="Шаг 3: Объединение XML файлов", padding="10")
        step3_frame.pack(fill=tk.X, pady=(0, 10))
        
        btn_row3 = ttk.Frame(step3_frame)
        btn_row3.pack(fill=tk.X)
        
        btn_merge = ttk.Button(btn_row3, text="📑 ОБЪЕДИНИТЬ XML", 
                              command=self.merge_xml_files)
        btn_merge.pack(side=tk.LEFT, padx=(0, 10))
        
        self.merge_status = ttk.Label(btn_row3, text="", foreground="gray")
        self.merge_status.pack(side=tk.LEFT)
        
        self.merge_info = ttk.Label(step3_frame, text="", foreground="gray")
        self.merge_info.pack(anchor=tk.W, pady=(5, 0))
        
        # ============================================
        # ШАГ 4: Проверка соответствия
        # ============================================
        step4_frame = ttk.LabelFrame(right_frame, text="Шаг 4: Проверка соответствия", padding="10")
        step4_frame.pack(fill=tk.X, pady=(0, 10))
        
        btn_row4 = ttk.Frame(step4_frame)
        btn_row4.pack(fill=tk.X)
        
        btn_check = ttk.Button(btn_row4, text="🔍 ПРОВЕРИТЬ СООТВЕТСТВИЕ", 
                              command=self.check_matches)
        btn_check.pack(side=tk.LEFT, padx=(0, 10))
        
        self.check_status = ttk.Label(btn_row4, text="", foreground="gray")
        self.check_status.pack(side=tk.LEFT)
        
        self.status_label = ttk.Label(step4_frame, text="Готов к работе", foreground="gray")
        self.status_label.pack(anchor=tk.W, pady=(5, 0))
        
        # ============================================
        # Дополнительные кнопки
        # ============================================
        action_frame = ttk.Frame(right_frame)
        action_frame.pack(fill=tk.X, pady=(5, 0))
        
        btn_save = ttk.Button(action_frame, text="💾 СОХРАНИТЬ ОТЧЕТ", 
                             command=self.save_report)
        btn_save.pack(side=tk.LEFT, padx=(0, 5), fill=tk.X, expand=True)
        
        btn_clear = ttk.Button(action_frame, text="🗑 ОЧИСТИТЬ ВСЁ", 
                              command=self.clear_all)
        btn_clear.pack(side=tk.LEFT, padx=(5, 0), fill=tk.X, expand=True)
    
    def center_window(self, window):
        window.update_idletasks()
        width = window.winfo_width()
        height = window.winfo_height()
        x = (window.winfo_screenwidth() // 2) - (width // 2)
        y = (window.winfo_screenheight() // 2) - (height // 2)
        window.geometry(f'{width}x{height}+{x}+{y}')
    
    # ====================================================================
    # НОРМАЛИЗАЦИЯ ТЕГОВ
    # ====================================================================
    def normalize_tag(self, tag):
        if not tag:
            return tag
        tag = re.sub(r'\.Xin\b', '.xin', tag, flags=re.IGNORECASE)
        tag = re.sub(r'\.Xs\b', '.xs', tag, flags=re.IGNORECASE)
        tag = re.sub(r'\.stat\b', '.xs', tag, flags=re.IGNORECASE)
        return tag
    
    def is_excluded_tag(self, tag):
        if not tag:
            return True
        excluded_prefixes = ['_1000', '_2000', '_3000']
        for prefix in excluded_prefixes:
            if tag.startswith(prefix):
                return True
        return False
    
    # ====================================================================
    # ИЗВЛЕЧЕНИЕ ТЕГОВ ИЗ EXCEL
    # ====================================================================
    def extract_excel_data(self, content):
        """
        Извлекает теги и каналы из Excel файла.
        """
        result = {}
        lines = content.split('\n')
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
            
            # Извлекаем тег - ищем _[имя].Xin или _[имя].Xs
            match = re.search(r'(_[a-zA-Z0-9_]+)\s*\.(Xin|Xs)\s*:=', line, re.IGNORECASE)
            if not match:
                continue
            
            tag_base = match.group(1)
            suffix = match.group(2)
            tag = f"{tag_base}.{suffix}"
            
            if self.is_excluded_tag(tag):
                continue
            
            normalized_tag = self.normalize_tag(tag)
            
            # Извлекаем канал
            channel = self.extract_channel_from_excel_line(line)
            
            if channel is not None:
                result[normalized_tag] = channel
            else:
                # Если канал не найден, пытаемся найти его в строке
                # Формат: _IO_I*А1-00*_0_VAL.Measurement
                match2 = re.search(r'_IO_I\*[^*]+\*_(\d+)_VAL\.', line, re.IGNORECASE)
                if match2:
                    channel = int(match2.group(1))
                    result[normalized_tag] = channel
                # Формат: _IO_I*А1-00*_0_AI16H_0_VAL
                else:
                    match3 = re.search(r'_IO_I\*[^*]+\*_(\d+)_AI16H_\d+_VAL\.', line, re.IGNORECASE)
                    if match3:
                        channel = int(match3.group(1))
                        result[normalized_tag] = channel
        
        return result
    
    def extract_channel_from_excel_line(self, line):
        """
        Извлекает номер канала из строки Excel.
        Поддерживает все форматы.
        """
        # --- ФОРМАТ 1: DCS AI ---
        # _IO_IU*A10-02*_0.ValueDINT
        match = re.search(r'_IO_IU\*[^*]+\*_(\d+)\.(?:ValueDINT|Status)', line)
        if match:
            return int(match.group(1))
        
        # --- ФОРМАТ 2: SCS AI с AI16H ---
        # _IO_I*A11-00*_AI16H_0_VAL.Measurement
        match = re.search(r'_IO_I\*[^*]+\*_AI16H_(\d+)_VAL\.(?:Measurement|Quality)', line)
        if match:
            return int(match.group(1))
        
        # --- ФОРМАТ 3: GDS AI с QUAL_STAT ---
        # QUAL_STAT(_IO_I*А1-00*_0_AI16H_0_VAL.Quality)
        match = re.search(r'_IO_I\*[^*]+\*_(\d+)_AI16H_\d+_VAL\.(?:Quality|Measurement)', line)
        if match:
            return int(match.group(1))
        
        # --- ФОРМАТ 4: GDS AI без AI16H (для .Xin) ---
        # _IO_I*А1-00*_0_VAL.Measurement
        match = re.search(r'_IO_I\*[^*]+\*_(\d+)_VAL\.(?:Measurement|Quality)', line)
        if match:
            return int(match.group(1))
        
        # --- ФОРМАТ 5: Простой DCS ---
        # _IO_IU0_0.ValueDINT
        match = re.search(r'_IO_IU\d+_(\d+)\.(?:ValueDINT|Status)', line)
        if match:
            return int(match.group(1))
        
        # --- ФОРМАТ 6: Простой SCS ---
        # _IO_I7_AI16H_0_VAL.Measurement
        match = re.search(r'_IO_I\d+_AI16H_(\d+)_VAL\.(?:Measurement|Quality)', line)
        if match:
            return int(match.group(1))
        
        # --- ФОРМАТ 7: Простой GDS без звездочек ---
        # _IO_I0_AI16H_0_VAL.Measurement
        match = re.search(r'_IO_I(\d+)_AI16H_(\d+)_VAL\.(?:Measurement|Quality)', line)
        if match:
            return int(match.group(2))
        
        return None
    
    def select_excel_file(self):
        file_path = filedialog.askopenfilename(
            title="Выберите Excel файл",
            filetypes=[("Все файлы", "*.*"), ("Текстовые файлы", "*.txt"), ("Excel файлы", "*.xlsx *.xls")]
        )
        
        if file_path:
            self.excel_file = file_path
            self.excel_path_var.set(os.path.basename(file_path))
            self.excel_status.config(text="✅ Файл загружен", foreground="green")
            self.status_label.config(text=f"Загружен Excel: {os.path.basename(file_path)}")
            self.load_excel_data()
    
    def load_excel_data(self):
        try:
            if self.excel_file.lower().endswith(('.xlsx', '.xls')):
                import pandas as pd
                df = pd.read_excel(self.excel_file)
                
                content = ""
                target_col = None
                
                keywords = ['GDS AI', 'SCS AI', 'DCS AI', 'GDS', 'SCS', 'DCS', 'AI']
                
                for col in df.columns:
                    col_str = str(col).strip()
                    for keyword in keywords:
                        if keyword in col_str:
                            target_col = col
                            break
                    if target_col is not None:
                        break
                
                if target_col is None:
                    for col in df.columns:
                        sample = df[col].astype(str).head(20)
                        if any('_IO_' in str(val) for val in sample):
                            target_col = col
                            break
                
                if target_col is None:
                    for col in df.columns:
                        if 'GDS' in str(col).upper():
                            target_col = col
                            break
                
                if target_col is None:
                    if len(df.columns) > 5:
                        target_col = df.columns[5]
                    else:
                        target_col = df.columns[-1]
                
                for val in df[target_col]:
                    if pd.notna(val) and '_' in str(val):
                        content += str(val) + "\n"
                
                if not content:
                    for col in df.columns:
                        for val in df[col]:
                            if pd.notna(val) and '_IO_' in str(val):
                                content += str(val) + "\n"
            else:
                with open(self.excel_file, 'r', encoding='utf-8') as file:
                    content = file.read()
            
            self.excel_data = self.extract_excel_data(content)
            
            info_text = f"Загружено {len(self.excel_data)} тегов"
            self.status_label.config(text=f"Excel: {info_text}")
            self.excel_status.config(text="✅ Файл загружен", foreground="green")
            
            if len(self.excel_data) == 0:
                messagebox.showwarning("Предупреждение", 
                    "Не найдено тегов в Excel файле.\n"
                    "Убедитесь, что файл содержит колонку с тегами (GDS AI, SCS AI, DCS AI).\n\n"
                    "Теги должны быть вида:\n"
                    "_1110_GEIA_1002_main.Xs := QUAL_STAT(_IO_I*А1-00*_0_AI16H_0_VAL.Quality);\n"
                    "_1110_GEIA_1002_main.Xin := _IO_I*А1-00*_0_VAL.Measurement;")
                self.excel_status.config(text="❌ Теги не найдены", foreground="red")
            
        except Exception as e:
            messagebox.showerror("Ошибка", f"Не удалось загрузить Excel файл:\n{str(e)}")
            self.excel_data = {}
            self.excel_status.config(text="❌ Ошибка загрузки", foreground="red")
    
    # ====================================================================
    # ИЗВЛЕЧЕНИЕ ТЕГОВ ИЗ XML
    # ====================================================================
    def select_xml_files(self):
        files = filedialog.askopenfilenames(
            title="Выберите XML файл (ST) для проверки",
            filetypes=[("Все файлы", "*.*"), ("Текстовые файлы", "*.txt"), ("XML файлы", "*.xml")]
        )
        
        if files:
            self.xml_files = list(files)
            self.update_xml_files_list()
            self.xml_status.config(text="✅ Файлы загружены", foreground="green")
            self.status_label.config(text=f"Загружено XML файлов: {len(self.xml_files)}")
            self.load_xml_data()
    
    def update_xml_files_list(self):
        self.xml_files_listbox.delete(0, tk.END)
        for file_path in self.xml_files:
            self.xml_files_listbox.insert(tk.END, os.path.basename(file_path))
        self.xml_count_label.config(text=f"Файлов: {len(self.xml_files)}")
    
    def extract_xml_data(self, content):
        result = {}
        lines = content.split('\n')
        
        start_idx = 0
        for i, line in enumerate(lines[:5]):
            if 'PROGRAM' in line:
                start_idx = i + 1
                break
        
        if start_idx == 0:
            start_idx = 3
        
        for line in lines[start_idx:]:
            line = line.strip()
            if not line:
                continue
            
            if line.startswith('(*') or line.startswith('//'):
                continue
            
            match = re.search(r'(_[a-zA-Z0-9_]+)\s*\.(xin|xs)\s*:=', line, re.IGNORECASE)
            if not match:
                continue
            
            tag_base = match.group(1)
            suffix = match.group(2)
            tag = f"{tag_base}.{suffix}"
            
            if self.is_excluded_tag(tag):
                continue
            
            normalized_tag = self.normalize_tag(tag)
            
            channel = self.extract_channel_from_xml_line(line)
            
            if channel is not None:
                if normalized_tag not in result:
                    result[normalized_tag] = channel
                elif result[normalized_tag] != channel:
                    print(f"Внимание: тег {normalized_tag} имеет разные каналы: {result[normalized_tag]} и {channel}")
        
        return result
    
    def extract_channel_from_xml_line(self, line):
        """
        Извлекает номер канала из строки XML.
        """
        # _IO_IU0_0.ValueDINT
        match = re.search(r'_IO_IU\d+_(\d+)\.(?:ValueDINT|Status)', line)
        if match:
            return int(match.group(1))
        
        # _IO_I7_AI16H_0_VAL.Measurement
        match = re.search(r'_IO_I\d+_AI16H_(\d+)_VAL\.(?:Measurement|Quality)', line)
        if match:
            return int(match.group(1))
        
        # _IO_IU*A10-02*_0.ValueDINT
        match = re.search(r'_IO_IU\*[^*]+\*_(\d+)\.(?:ValueDINT|Status)', line)
        if match:
            return int(match.group(1))
        
        # _IO_I*A11-00*_AI16H_0_VAL.Measurement
        match = re.search(r'_IO_I\*[^*]+\*_AI16H_(\d+)_VAL\.(?:Measurement|Quality)', line)
        if match:
            return int(match.group(1))
        
        # QUAL_STAT(_IO_I7_AI16H_0_VAL.Quality)
        match = re.search(r'_IO_I\d+_AI16H_(\d+)_VAL\.Quality', line)
        if match:
            return int(match.group(1))
        
        return None
    
    def load_xml_data(self):
        self.xml_data = {}
        
        for file_path in self.xml_files:
            try:
                with open(file_path, 'r', encoding='utf-8') as file:
                    content = file.read()
                
                file_name = os.path.basename(file_path)
                self.xml_data[file_name] = self.extract_xml_data(content)
                
            except Exception as e:
                print(f"Ошибка загрузки {file_path}: {e}")
        
        total_tags = sum(len(data) for data in self.xml_data.values())
        
        info_text = f"Загружено {len(self.xml_data)} файлов, {total_tags} тегов"
        self.status_label.config(text=f"XML: {info_text}")
        self.xml_status.config(text="✅ Файлы загружены", foreground="green")
        
        self.merged_xml_data = {}
        self.merge_info.config(text="", foreground="gray")
        self.merge_status.config(text="❌ XML не объединен", foreground="red")
        self.check_status.config(text="", foreground="gray")
    
    # ====================================================================
    # ОБЪЕДИНЕНИЕ XML
    # ====================================================================
    def merge_xml_files(self):
        if not self.xml_data:
            messagebox.showwarning("Предупреждение", "Сначала загрузите XML файлы!")
            return
        
        merged = {}
        conflicts = {}
        
        for file_name, tags in self.xml_data.items():
            for tag, channel in tags.items():
                if tag not in merged:
                    merged[tag] = channel
                else:
                    if merged[tag] != channel:
                        if tag not in conflicts:
                            conflicts[tag] = []
                        conflicts[tag].append({
                            'file': file_name,
                            'channel': channel,
                            'first_channel': merged[tag]
                        })
        
        self.merged_xml_data = merged
        
        info_text = f"Объединено {len(merged)} тегов"
        if conflicts:
            info_text += f" (⚠️ {len(conflicts)} конфликтов)"
            self.merge_info.config(text=f"⚠️ {info_text}", foreground="orange")
            self.merge_status.config(text="⚠️ Есть конфликты", foreground="orange")
        else:
            self.merge_info.config(text=f"✅ {info_text}", foreground="green")
            self.merge_status.config(text="✅ XML объединен", foreground="green")
        
        self.status_label.config(text=f"Объединено {len(merged)} тегов")
        
        self.result_text.delete('1.0', tk.END)
        self.result_text.insert(tk.END, "="*80 + "\n")
        self.result_text.insert(tk.END, "ОБЪЕДИНЕНИЕ XML ФАЙЛОВ\n")
        self.result_text.insert(tk.END, "="*80 + "\n\n")
        
        self.result_text.insert(tk.END, f"📊 Обработано файлов: {len(self.xml_data)}\n")
        self.result_text.insert(tk.END, f"📊 Всего тегов: {len(merged)}\n\n")
        
        if conflicts:
            self.result_text.insert(tk.END, "⚠️  ОБНАРУЖЕНЫ КОНФЛИКТЫ КАНАЛОВ:\n", "warning")
            self.result_text.insert(tk.END, "-"*80 + "\n")
            for tag, conflict_list in conflicts.items():
                self.result_text.insert(tk.END, f"  ⚠️  {tag}\n", "warning")
                self.result_text.insert(tk.END, f"     Первый канал: {conflict_list[0]['first_channel']}\n", "compare")
                for conflict in conflict_list:
                    self.result_text.insert(tk.END, f"     → {conflict['file']}: канал {conflict['channel']}\n", "compare")
                self.result_text.insert(tk.END, "-"*80 + "\n")
            self.result_text.insert(tk.END, "\n")
        else:
            self.result_text.insert(tk.END, "✅ КОНФЛИКТОВ НЕ ОБНАРУЖЕНО\n", "success")
        
        self.result_text.insert(tk.END, "\n" + "="*80 + "\n")
        
        self.check_status.config(text="", foreground="gray")
        
        if conflicts:
            messagebox.showwarning("Конфликты каналов", 
                f"⚠️  Обнаружены конфликты каналов в {len(conflicts)} тегах.\n\n"
                f"Использован первый найденный канал.\n"
                f"Подробности смотрите в окне результатов.")
        else:
            messagebox.showinfo("Успех", 
                f"✅ Объединено {len(merged)} тегов из {len(self.xml_data)} файлов.\n"
                f"Конфликтов не обнаружено.")
    
    # ====================================================================
    # ПРОВЕРКА СООТВЕТСТВИЯ
    # ====================================================================
    def check_matches(self):
        if not self.excel_data:
            messagebox.showwarning("Предупреждение", "Сначала загрузите Excel файл!")
            return
        
        if not self.xml_data:
            messagebox.showwarning("Предупреждение", "Сначала загрузите XML файл (ST)!")
            return
        
        if not self.merged_xml_data:
            self.merge_xml_files()
            if not self.merged_xml_data:
                return
        
        self.result_text.delete('1.0', tk.END)
        self.mismatches = {}
        
        total_errors = 0
        
        self.result_text.insert(tk.END, "="*80 + "\n")
        self.result_text.insert(tk.END, "РЕЗУЛЬТАТЫ ПРОВЕРКИ СООТВЕТСТВИЯ\n")
        self.result_text.insert(tk.END, "="*80 + "\n\n")
        
        merged_tags = self.merged_xml_data
        file_errors = {}
        
        # Проверяем теги из Excel
        for excel_tag, excel_channel in self.excel_data.items():
            clean_excel_tag = re.sub(r'\.Z\d+$', '', excel_tag)
            
            found = False
            xml_channel = None
            for xml_tag, xml_ch in merged_tags.items():
                clean_xml_tag = re.sub(r'\.Z\d+$', '', xml_tag)
                if clean_xml_tag.lower() == clean_excel_tag.lower():
                    found = True
                    xml_channel = xml_ch
                    break
            
            if found:
                if excel_channel != xml_channel:
                    file_errors[clean_excel_tag] = {
                        'excel_channel': excel_channel,
                        'xml_channel': xml_channel,
                        'type': 'mismatch'
                    }
            else:
                file_errors[excel_tag] = {
                    'excel_channel': excel_channel,
                    'xml_channel': None,
                    'type': 'missing_in_xml'
                }
        
        # Проверяем теги из XML
        for xml_tag, xml_channel in merged_tags.items():
            clean_xml_tag = re.sub(r'\.Z\d+$', '', xml_tag)
            found = False
            for excel_tag in self.excel_data.keys():
                clean_excel_tag = re.sub(r'\.Z\d+$', '', excel_tag)
                if clean_excel_tag.lower() == clean_xml_tag.lower():
                    found = True
                    break
            if not found:
                file_errors[clean_xml_tag] = {
                    'excel_channel': None,
                    'xml_channel': xml_channel,
                    'type': 'missing_in_excel'
                }
        
        if file_errors:
            total_errors = len(file_errors)
        
        if total_errors == 0:
            self.result_text.insert(tk.END, "🎉 ВСЕ ТЕГИ СОВПАДАЮТ! ОШИБОК НЕ НАЙДЕНО.\n", "success")
            self.result_text.insert(tk.END, "="*80 + "\n")
            self.status_label.config(text="✅ Все теги совпадают! Ошибок нет.")
            self.check_status.config(text="✅ Проверка пройдена", foreground="green")
            messagebox.showinfo("Успех", "Все теги совпадают! Ошибок не найдено.")
            return
        
        self.result_text.insert(tk.END, f"⚠️  НАЙДЕНО {total_errors} ОШИБОК(И)\n", "error")
        self.result_text.insert(tk.END, "="*80 + "\n\n")
        
        self.result_text.insert(tk.END, "📊 ОБЩАЯ СТАТИСТИКА:\n", "header")
        self.result_text.insert(tk.END, f"   Всего тегов в Excel: {len(self.excel_data)}\n")
        self.result_text.insert(tk.END, f"   Всего тегов в XML:   {len(merged_tags)}\n")
        self.result_text.insert(tk.END, f"   Найдено ошибок:      {total_errors}\n\n")
        
        self.result_text.insert(tk.END, "="*80 + "\n")
        self.result_text.insert(tk.END, "📄 ДЕТАЛИ ОШИБОК\n", "header")
        self.result_text.insert(tk.END, "="*80 + "\n\n")
        
        for tag, error in file_errors.items():
            if error['type'] == 'mismatch':
                self.result_text.insert(tk.END, f"  ⚠️  {tag}\n", "warning")
                self.result_text.insert(tk.END, f"     Excel: канал {error['excel_channel']}\n", "compare")
                self.result_text.insert(tk.END, f"     XML:   канал {error['xml_channel']}\n", "compare")
                self.result_text.insert(tk.END, "-"*80 + "\n")
                
            elif error['type'] == 'missing_in_xml':
                self.result_text.insert(tk.END, f"  ❌  {tag}\n", "error")
                self.result_text.insert(tk.END, f"     Excel: канал {error['excel_channel']}\n", "compare")
                self.result_text.insert(tk.END, f"     XML:   НЕ НАЙДЕН\n", "compare")
                self.result_text.insert(tk.END, "-"*80 + "\n")
                
            elif error['type'] == 'missing_in_excel':
                self.result_text.insert(tk.END, f"  ❌  {tag}\n", "error")
                self.result_text.insert(tk.END, f"     Excel: НЕ НАЙДЕН\n", "compare")
                self.result_text.insert(tk.END, f"     XML:   канал {error['xml_channel']}\n", "compare")
                self.result_text.insert(tk.END, "-"*80 + "\n")
        
        self.result_text.insert(tk.END, "\n")
        self.result_text.insert(tk.END, "="*80 + "\n")
        self.result_text.insert(tk.END, f"ИТОГО: {total_errors} ОШИБОК(И)\n", "error")
        self.result_text.insert(tk.END, "="*80 + "\n")
        
        self.status_label.config(text=f"⚠️ Найдено {total_errors} ошибок")
        self.check_status.config(text=f"⚠️ Найдено {total_errors} ошибок", foreground="red")
        
        messagebox.showwarning("Результаты проверки", 
            f"⚠️  НАЙДЕНО {total_errors} ОШИБОК(И)\n\n"
            f"📊 Статистика:\n"
            f"   Тегов в Excel: {len(self.excel_data)}\n"
            f"   Тегов в XML:   {len(merged_tags)}\n"
            f"   Ошибок:        {total_errors}")
    
    # ====================================================================
    # ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ
    # ====================================================================
    def clear_all(self):
        self.excel_file = ""
        self.xml_files = []
        self.excel_data = {}
        self.xml_data = {}
        self.mismatches = {}
        self.merged_xml_data = {}
        
        self.excel_path_var.set("Файл не выбран")
        self.xml_files_listbox.delete(0, tk.END)
        self.xml_count_label.config(text="Файлов: 0")
        self.result_text.delete('1.0', tk.END)
        
        self.excel_status.config(text="❌ Файл не загружен", foreground="red")
        self.xml_status.config(text="❌ Файлы не загружены", foreground="red")
        self.merge_status.config(text="", foreground="gray")
        self.merge_info.config(text="", foreground="gray")
        self.check_status.config(text="", foreground="gray")
        self.status_label.config(text="Очищено", foreground="gray")
    
    def save_report(self):
        content = self.result_text.get('1.0', tk.END).strip()
        if not content:
            messagebox.showwarning("Предупреждение", "Нет данных для сохранения!")
            return
        
        file_path = filedialog.asksaveasfilename(
            title="Сохранить отчет",
            defaultextension=".txt",
            filetypes=[("Все файлы", "*.*"), ("Текстовые файлы", "*.txt")]
        )
        
        if file_path:
            try:
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(content)
                
                self.status_label.config(text=f"Отчет сохранен: {os.path.basename(file_path)}")
                messagebox.showinfo("Успех", f"Отчет сохранен в:\n{file_path}")
                
            except Exception as e:
                messagebox.showerror("Ошибка", f"Не удалось сохранить отчет:\n{str(e)}")