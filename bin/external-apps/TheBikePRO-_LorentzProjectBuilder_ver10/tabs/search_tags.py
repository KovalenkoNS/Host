import os
import re
import tkinter as tk
from tkinter import ttk, filedialog, messagebox, scrolledtext
from collections import defaultdict
from pathlib import Path
from utils.help_window import create_help_window


class SearchTab:
    """Вкладка поиска тегов из словарей в FBD файлах"""
    
    def __init__(self, parent, parent_tab=None):
        self.parent = parent
        self.parent_tab = parent_tab
        self.files = []
        self.words_by_file = {}
        self.input_method = tk.StringVar(value="manual")
        self.search_mode = tk.StringVar(value="whole")
        self.file_display_list = []
        self.last_results = None
        self.create_widgets()
    
    def show_help(self):
        content = """
📌 НАЗНАЧЕНИЕ

Проверяет наличие тегов (собранных из ST) в FBD файлах.
Выводит ТОЛЬКО те теги, которые НЕ БЫЛИ НАЙДЕНЫ.

▶️ КАК РАБОТАТЬ

1. ВЫБЕРИТЕ FBD ФАЙЛЫ
   • "Один файл"         - выбрать один XML файл
   • "Несколько файлов"  - выбрать несколько файлов
   • "Папка"             - выбрать папку со всеми XML файлами

2. ЗАГРУЗИТЕ СЛОВА ДЛЯ ПОИСКА
   • "Загрузить общие слова (для всех)"  - один словарь для всех файлов
   • "Загрузить слова по файлам"         - отдельные словари по имени файла

3. ВЫБЕРИТЕ РЕЖИМ ПОИСКА
   • "Целое слово"  - ищет точное совпадение
   • "Подстрока"    - ищет вхождение слова

4. Нажмите "НАЧАТЬ ПОИСК"

📊 РЕЗУЛЬТАТЫ

Результаты показывают ТОЛЬКО теги, которые НЕ найдены в FBD файлах.
"""
        create_help_window(self.parent, "🔎 Поиск тегов в FBD", content)
    
    def create_widgets(self):
        # Основной фрейм с разделением на левую и правую часть
        main_paned = ttk.PanedWindow(self.parent, orient=tk.HORIZONTAL)
        main_paned.pack(fill=tk.BOTH, expand=True)
        
        # ============ ЛЕВАЯ ЧАСТЬ - Результаты ============
        left_frame = ttk.Frame(main_paned)
        main_paned.add(left_frame, weight=3)
        
        result_title = ttk.Label(left_frame, text="РЕЗУЛЬТАТЫ ПОИСКА", 
                                 font=('Arial', 12, 'bold'), foreground='blue')
        result_title.pack(pady=(0, 5))
        
        self.result_text = scrolledtext.ScrolledText(left_frame, height=20, font=("Courier", 9))
        self.result_text.pack(fill=tk.BOTH, expand=True)
        
        # Настройка стилей
        self.result_text.tag_configure("header", foreground="blue", font=('Arial', 11, 'bold'))
        self.result_text.tag_configure("error", foreground="red", font=('Courier New', 9, 'bold'))
        self.result_text.tag_configure("success", foreground="green", font=('Arial', 10, 'bold'))
        self.result_text.tag_configure("file_name", foreground="#0066cc", font=('Arial', 10, 'bold'))
        self.result_text.tag_configure("stats", foreground="#2c3e50", font=('Arial', 9, 'italic'))
        
        # ============ ПРАВАЯ ЧАСТЬ - Настройки ============
        right_frame = ttk.Frame(main_paned, width=500)
        main_paned.add(right_frame, weight=1)
        
        settings_title = ttk.Label(right_frame, text="НАСТРОЙКИ", 
                                   font=('Arial', 12, 'bold'), foreground='green')
        settings_title.pack(pady=(0, 10))
        
        # Блок выбора файлов
        file_frame = ttk.LabelFrame(right_frame, text="Выбор FBD файлов", padding="10")
        file_frame.pack(fill=tk.X, pady=(0, 10))
        
        self.file_mode = tk.StringVar(value="files")
        mode_frame = ttk.Frame(file_frame)
        mode_frame.pack(fill=tk.X, pady=(0, 5))
        
        ttk.Radiobutton(mode_frame, text="Один", variable=self.file_mode, value="single").pack(side=tk.LEFT, padx=2)
        ttk.Radiobutton(mode_frame, text="Несколько", variable=self.file_mode, value="files").pack(side=tk.LEFT, padx=2)
        ttk.Radiobutton(mode_frame, text="Папка", variable=self.file_mode, value="folder").pack(side=tk.LEFT, padx=2)
        
        btn_select = ttk.Button(file_frame, text="ВЫБРАТЬ FBD ФАЙЛЫ", command=self.select_files)
        btn_select.pack(fill=tk.X, pady=(0, 5))
        
        btn_clear_files = ttk.Button(file_frame, text="ОЧИСТИТЬ СПИСОК", command=self.clear_files)
        btn_clear_files.pack(fill=tk.X)
        
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
        
        # Блок загрузки слов
        words_frame = ttk.LabelFrame(right_frame, text="Загрузка словарей", padding="10")
        words_frame.pack(fill=tk.X, pady=(0, 10))
        
        btn_common = ttk.Button(words_frame, text="ЗАГРУЗИТЬ ОБЩИЕ СЛОВА", command=self.load_common_words)
        btn_common.pack(fill=tk.X, pady=(0, 5))
        
        btn_per_file = ttk.Button(words_frame, text="ЗАГРУЗИТЬ СЛОВА ПО ФАЙЛАМ", command=self.load_words_per_file)
        btn_per_file.pack(fill=tk.X)
        
        self.words_info = tk.StringVar(value="Слова не заданы")
        ttk.Label(words_frame, textvariable=self.words_info, foreground="gray").pack(anchor=tk.W, pady=(5, 0))
        
        # Блок режима поиска
        search_mode_frame = ttk.LabelFrame(right_frame, text="Режим поиска", padding="10")
        search_mode_frame.pack(fill=tk.X, pady=(0, 10))
        
        ttk.Radiobutton(search_mode_frame, text="Целое слово", variable=self.search_mode, value="whole").pack(anchor=tk.W)
        ttk.Radiobutton(search_mode_frame, text="Подстрока", variable=self.search_mode, value="substring").pack(anchor=tk.W)
        
        # Кнопки действий
        action_frame = ttk.LabelFrame(right_frame, text="Действия", padding="10")
        action_frame.pack(fill=tk.X, pady=(0, 10))
        
        self.search_btn = ttk.Button(action_frame, text="НАЧАТЬ ПОИСК", command=self.start_search)
        self.search_btn.pack(fill=tk.X, pady=(0, 5))
        
        self.save_btn = ttk.Button(action_frame, text="СОХРАНИТЬ РЕЗУЛЬТАТЫ", 
                                  command=self.save_results, state=tk.DISABLED)
        self.save_btn.pack(fill=tk.X, pady=(0, 5))
        
        btn_clear = ttk.Button(action_frame, text="ОЧИСТИТЬ ВСЁ", command=self.clear_all)
        btn_clear.pack(fill=tk.X)
        
        # Прогресс
        progress_frame = ttk.LabelFrame(right_frame, text="Прогресс", padding="10")
        progress_frame.pack(fill=tk.X, pady=(0, 10))
        
        self.progress = ttk.Progressbar(progress_frame, mode='determinate')
        self.progress.pack(fill=tk.X)
        
        self.progress_label = ttk.Label(progress_frame, text="0%", foreground="gray")
        self.progress_label.pack(anchor=tk.W, pady=(5, 0))
        
        # Статус
        status_frame = ttk.LabelFrame(right_frame, text="Статус", padding="10")
        status_frame.pack(fill=tk.X)
        
        self.status_label = ttk.Label(status_frame, text="Готов к работе", foreground="gray", wraplength=450)
        self.status_label.pack(anchor=tk.W)
    
    def center_window(self, window):
        window.update_idletasks()
        width = window.winfo_width()
        height = window.winfo_height()
        x = (window.winfo_screenwidth() // 2) - (width // 2)
        y = (window.winfo_screenheight() // 2) - (height // 2)
        window.geometry(f'{width}x{height}+{x}+{y}')
    
    def load_common_words(self):
        file_path = filedialog.askopenfilename(
            title="Выберите файл со словами для ВСЕХ файлов",
            filetypes=[
                ("Все файлы", "*.*"),
                ("Text files", "*.txt"),
                ("Dictionary files", "*.dict")
            ]
        )
        if not file_path:
            return
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                words = [line.strip() for line in f if line.strip()]
            if not words:
                messagebox.showwarning("Внимание", "Файл пуст или не содержит слов")
                return
            for file_path in self.files:
                self.words_by_file[file_path] = words.copy()
            self.update_files_list()
            mode = "целых слов" if self.search_mode.get() == "whole" else "подстрок"
            self.status_label.config(text=f"Загружено {len(words)} общих {mode} для {len(self.files)} файлов", foreground="green")
            messagebox.showinfo("Успех", f"Загружено {len(words)} общих слов для {len(self.files)} файлов")
        except Exception as e:
            messagebox.showerror("Ошибка", f"Не удалось прочитать файл: {e}")
    
    def load_words_per_file(self):
        if not self.files:
            messagebox.showwarning("Внимание", "Сначала выберите файлы для поиска")
            return
        folder = filedialog.askdirectory(title="Выберите папку с файлами словарей")
        if not folder:
            return
        dict_files = {}
        for file in os.listdir(folder):
            if file.lower().endswith(('.txt', '.words', '.dict')):
                base_name = os.path.splitext(file)[0].lower()
                dict_files[base_name] = os.path.join(folder, file)
        if not dict_files:
            messagebox.showwarning("Внимание", f"В папке '{folder}' не найдено файлов словарей")
            return
        loaded_count = 0
        matched_files = []
        not_matched_files = []
        for file_path in self.files:
            file_name = os.path.splitext(os.path.basename(file_path))[0].lower()
            if file_name in dict_files:
                try:
                    with open(dict_files[file_name], 'r', encoding='utf-8') as f:
                        words = [line.strip() for line in f if line.strip()]
                    if words:
                        self.words_by_file[file_path] = words
                        loaded_count += 1
                        matched_files.append(os.path.basename(file_path))
                except Exception as e:
                    print(f"Ошибка чтения {dict_files[file_name]}: {e}")
            else:
                not_matched_files.append(os.path.basename(file_path))
        self.update_files_list()
        result_msg = f"Загружены слова для {loaded_count} из {len(self.files)} файлов"
        if loaded_count > 0:
            result_msg += f"\n\n✅ Сопоставлено:\n" + "\n".join(f"  • {f}" for f in matched_files[:10])
            if len(matched_files) > 10:
                result_msg += f"\n  ... и еще {len(matched_files) - 10} файлов"
        if not_matched_files:
            result_msg += f"\n\n❌ Не найдены словари для:\n" + "\n".join(f"  • {f}" for f in not_matched_files[:10])
            if len(not_matched_files) > 10:
                result_msg += f"\n  ... и еще {len(not_matched_files) - 10} файлов"
        self.status_label.config(text=result_msg.split('\n')[0], foreground="green")
        messagebox.showinfo("Результат загрузки", result_msg)
    
    def select_files(self):
        mode = self.file_mode.get()
        if mode == "single":
            file_path = filedialog.askopenfilename(
                title="Выберите FBD файл",
                filetypes=[
                    ("Все файлы", "*.*"),
                    ("XML files", "*.xml"),
                    ("Text files", "*.txt")
                ]
            )
            if file_path:
                self.files = [Path(file_path)]
                self.update_files_list()
        elif mode == "files":
            file_paths = filedialog.askopenfilenames(
                title="Выберите FBD файлы",
                filetypes=[
                    ("Все файлы", "*.*"),
                    ("XML files", "*.xml"),
                    ("Text files", "*.txt")
                ]
            )
            if file_paths:
                self.files = [Path(p) for p in file_paths]
                self.update_files_list()
        elif mode == "folder":
            folder = filedialog.askdirectory(title="Выберите папку")
            if folder:
                self.files = self.get_files_from_directory(folder, "*.xml")
                self.update_files_list()
    
    def get_files_from_directory(self, directory, pattern="*.xml"):
        directory = Path(directory)
        if not directory.exists():
            return []
        files = list(directory.glob(pattern))
        files.extend(list(directory.glob(pattern.upper())))
        files = list(set(files))
        return sorted(files)
    
    def update_files_list(self):
        self.files_listbox.delete(0, tk.END)
        self.file_display_list = []
        for file_path in self.files:
            file_name = os.path.basename(file_path)
            word_count = len(self.words_by_file.get(file_path, []))
            if word_count > 0:
                display_text = f"{file_name}  [{word_count} слов]"
            else:
                display_text = f"{file_name}  [нет слов]"
            self.files_listbox.insert(tk.END, display_text)
            self.file_display_list.append(file_path)
        self.file_count_label.config(text=f"Файлов: {len(self.files)}")
        if self.files:
            self.status_label.config(text=f"Выбрано файлов: {len(self.files)}", foreground="green")
        else:
            self.status_label.config(text="Файлы не выбраны", foreground="gray")
        self.update_words_info()
    
    def clear_files(self):
        self.files = []
        self.file_display_list = []
        self.files_listbox.delete(0, tk.END)
        self.words_by_file = {}
        self.words_info.set("Слова не заданы ни для одного файла")
        self.file_count_label.config(text="Файлов: 0")
        self.status_label.config(text="Список файлов очищен", foreground="gray")
        self.save_btn.config(state=tk.DISABLED)
        self.last_results = None
        self.progress['value'] = 0
        self.progress_label.config(text="0%")
    
    def clear_all_words(self):
        self.words_by_file = {}
        self.update_files_list()
        self.words_info.set("Слова не заданы ни для одного файла")
        self.save_btn.config(state=tk.DISABLED)
        self.last_results = None
        self.status_label.config(text="Все слова очищены", foreground="gray")
    
    def update_words_info(self):
        total_words = sum(len(words) for words in self.words_by_file.values())
        files_with_words = len([w for w in self.words_by_file.values() if w])
        if files_with_words > 0:
            mode = "целых слов" if self.search_mode.get() == "whole" else "подстрок"
            info = f"Задано {total_words} {mode} для {files_with_words} файлов"
            self.words_info.set(info)
        else:
            self.words_info.set("Слова не заданы ни для одного файла")
    
    def update_progress(self, current, total, file_name):
        progress_value = (current / total) * 100
        self.progress['value'] = progress_value
        self.progress_label.config(text=f"{int(progress_value)}%")
        self.status_label.config(text=f"Обработка {current}/{total}: {file_name}", foreground="blue")
        self.parent.update_idletasks()
    
    def search_in_single_xml(self, xml_file_path, search_words, whole_word=True):
        word_counts = defaultdict(int)
        if not search_words:
            return word_counts
        
        if whole_word:
            escaped_words = [r'\b' + re.escape(word) + r'\b' for word in search_words]
        else:
            escaped_words = [re.escape(word) for word in search_words]
        
        pattern = re.compile('(' + '|'.join(escaped_words) + ')', re.IGNORECASE | re.UNICODE)
        
        try:
            with open(xml_file_path, 'r', encoding='utf-8', errors='ignore') as file:
                content = file.read()
                matches = pattern.findall(content)
                for match in matches:
                    word_counts[match] += 1
        except FileNotFoundError:
            return None
        except Exception as e:
            print(f"Ошибка при чтении файла {xml_file_path}: {e}")
            return None
        return word_counts
    
    def search_in_multiple_xml(self, files_list, words_by_file, whole_word=True, progress_callback=None):
        results = {}
        total_by_word = defaultdict(int)
        files_with_matches = set()
        files_without_matches = set()
        not_found_in_files = {}
        total_files = len(files_list)
        
        for i, file_path in enumerate(files_list, 1):
            file_name = os.path.basename(file_path)
            if progress_callback:
                progress_callback(i, total_files, file_name)
            
            search_words = words_by_file.get(file_path, [])
            if not search_words:
                files_without_matches.add(file_path)
                not_found_in_files[file_path] = set()
                continue
            
            file_results = self.search_in_single_xml(file_path, search_words, whole_word)
            if file_results is None:
                files_without_matches.add(file_path)
                not_found_in_files[file_path] = set(search_words)
                continue
            
            if file_results:
                results[file_path] = file_results
                files_with_matches.add(file_path)
                for word, count in file_results.items():
                    total_by_word[word] += count
                
                found_words_lower = set([w.lower() for w in file_results.keys()])
                all_words_lower = set([w.lower() for w in search_words])
                not_found_lower = all_words_lower - found_words_lower
                not_found_original = [w for w in search_words if w.lower() in not_found_lower]
                if not_found_original:
                    not_found_in_files[file_path] = set(not_found_original)
                else:
                    not_found_in_files[file_path] = set()
            else:
                files_without_matches.add(file_path)
                not_found_in_files[file_path] = set(search_words)
        
        return results, total_by_word, files_with_matches, files_without_matches, not_found_in_files
    
    def start_search_silent(self):
        if not self.files:
            return
        has_words = False
        for words in self.words_by_file.values():
            if words:
                has_words = True
                break
        if not has_words:
            return
        
        self.result_text.delete('1.0', tk.END)
        self.result_text.insert('1.0', "Запуск поиска...\n\n")
        self.search_btn.config(state=tk.DISABLED)
        self.save_btn.config(state=tk.DISABLED)
        self.progress['value'] = 0
        self.progress_label.config(text="0%")
        
        try:
            whole_word = (self.search_mode.get() == "whole")
            results, total_by_word, files_with_matches, files_without_matches, not_found_in_files = \
                self.search_in_multiple_xml(self.files, self.words_by_file, whole_word, self.update_progress)
            
            self.last_results = (not_found_in_files, self.words_by_file)
            self.display_results(not_found_in_files, self.words_by_file, results)
            
            has_not_found = any(words for words in not_found_in_files.values() if words)
            if has_not_found or results:
                self.save_btn.config(state=tk.NORMAL)
            else:
                self.save_btn.config(state=tk.DISABLED)
            self.status_label.config(text="Поиск завершен", foreground="green")
        except Exception as e:
            self.status_label.config(text=f"Ошибка: {e}", foreground="red")
        finally:
            self.search_btn.config(state=tk.NORMAL)
            self.progress['value'] = 100
            self.progress_label.config(text="100%")
    
    def start_search(self):
        if not self.files:
            messagebox.showwarning("Внимание", "Не выбрано ни одного файла")
            return
        has_words = False
        for words in self.words_by_file.values():
            if words:
                has_words = True
                break
        if not has_words:
            messagebox.showwarning("Внимание", "Не заданы слова для поиска.\nИспользуйте:\n"
                                   "• 'Загрузить общие слова (для всех)' - один файл для всех\n"
                                   "• 'Загрузить слова по файлам' - отдельные словари")
            return
        self.start_search_silent()
    
    def display_results(self, not_found_in_files, words_by_file, results):
        self.result_text.delete('1.0', tk.END)
        has_not_found = any(words for words in not_found_in_files.values() if words)
        
        self.result_text.insert('1.0', "="*70 + "\n")
        if has_not_found:
            self.result_text.insert('1.0', "РЕЗУЛЬТАТЫ ПОИСКА - НАЙДЕНЫ НЕ ВСЕ ТЕГИ!\n", "error")
        else:
            self.result_text.insert('1.0', "РЕЗУЛЬТАТЫ ПОИСКА - ВСЕ ТЕГИ НАЙДЕНЫ!\n", "success")
        self.result_text.insert('1.0', "="*70 + "\n\n")
        
        if has_not_found:
            self.result_text.insert('1.0', "⚠️  ТЕГИ, КОТОРЫЕ НЕ БЫЛИ НАЙДЕНЫ:\n", "error")
            self.result_text.insert('1.0', "━"*70 + "\n")
            for file_path, not_found_words in sorted(not_found_in_files.items()):
                if not not_found_words:
                    continue
                file_name = os.path.basename(file_path)
                search_words = words_by_file.get(file_path, [])
                self.result_text.insert('1.0', f"\n📄 {file_name}\n", "file_name")
                self.result_text.insert('1.0', f"   Искали: {', '.join(search_words)}\n")
                self.result_text.insert('1.0', f"   ❌ НЕ НАЙДЕНЫ ({len(not_found_words)} слов):\n")
                for word in sorted(not_found_words):
                    self.result_text.insert('1.0', f"      • {word}\n", "error")
                self.result_text.insert('1.0', "\n")
            self.result_text.insert('1.0', "━"*70 + "\n\n")
        
        if results:
            self.result_text.insert('1.0', "📊 СТАТИСТИКА НАЙДЕННЫХ ТЕГОВ:\n", "stats")
            self.result_text.insert('1.0', "─"*70 + "\n")
            total_found = sum(len(r) for r in results.values())
            self.result_text.insert('1.0', f"\n  Всего найдено уникальных тегов: {total_found}\n")
            self.result_text.insert('1.0', f"  Всего найдено вхождений: {sum(sum(r.values()) for r in results.values())}\n")
            
            for file_path, file_results in results.items():
                file_name = os.path.basename(file_path)
                total_matches = sum(file_results.values())
                self.result_text.insert('1.0', f"\n  📄 {file_name}:\n")
                self.result_text.insert('1.0', f"     Уникальных тегов: {len(file_results)}\n")
                self.result_text.insert('1.0', f"     Всего вхождений: {total_matches}\n")
                if file_results:
                    words_found = sorted(file_results.items(), key=lambda x: x[1], reverse=True)[:5]
                    self.result_text.insert('1.0', f"     Топ-5 найденных слов:\n")
                    for word, count in words_found:
                        self.result_text.insert('1.0', f"        ✓ '{word}' - {count} раз\n")
                self.result_text.insert('1.0', "\n")
        
        if not has_not_found and results:
            self.result_text.insert('1.0', "✅ ВСЕ ТЕГИ УСПЕШНО НАЙДЕНЫ ВО ВСЕХ ФАЙЛАХ!\n", "success")
        self.result_text.insert('1.0', "\n" + "="*70 + "\n")
    
    def save_results(self):
        if not self.last_results:
            messagebox.showwarning("Внимание", "Нет результатов для сохранения")
            return
        
        not_found_in_files, words_by_file = self.last_results
        file_path = filedialog.asksaveasfilename(
            title="Сохранить результаты",
            defaultextension=".txt",
            filetypes=[
                ("Текстовые файлы", "*.txt"),
                ("Все файлы", "*.*")
            ]
        )
        if file_path:
            try:
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write("="*70 + "\n")
                    f.write("РЕЗУЛЬТАТЫ ПОИСКА\n")
                    f.write("="*70 + "\n\n")
                    mode = "целых слов" if self.search_mode.get() == "whole" else "подстрок"
                    f.write(f"Режим поиска: {mode}\n\n")
                    
                    has_not_found = any(words for words in not_found_in_files.values() if words)
                    if not has_not_found:
                        f.write("ВСЕ ТЕГИ НАЙДЕНЫ ВО ВСЕХ ФАЙЛАХ!\n")
                    else:
                        f.write("⚠️  СЛОВА, КОТОРЫЕ НЕ БЫЛИ НАЙДЕНЫ:\n")
                        f.write("━"*70 + "\n")
                        for file_path, not_found_words in sorted(not_found_in_files.items()):
                            if not not_found_words:
                                continue
                            file_name = os.path.basename(file_path)
                            search_words = words_by_file.get(file_path, [])
                            f.write(f"\n📄 {file_name}:\n")
                            f.write(f"   Искали: {', '.join(search_words)}\n")
                            f.write(f"   ❌ НЕ НАЙДЕНЫ ({len(not_found_words)} слов):\n")
                            for word in sorted(not_found_words):
                                f.write(f"      • '{word}'\n")
                            f.write("\n")
                self.status_label.config(text=f"Результаты сохранены в файл: {os.path.basename(file_path)}", foreground="green")
                messagebox.showinfo("Успех", f"Результаты сохранены в:\n{file_path}")
            except Exception as e:
                messagebox.showerror("Ошибка", f"Не удалось сохранить файл: {e}")
    
    def clear_all(self):
        self.files = []
        self.words_by_file = {}
        self.file_display_list = []
        self.files_listbox.delete(0, tk.END)
        self.result_text.delete('1.0', tk.END)
        self.file_count_label.config(text="Файлов: 0")
        self.words_info.set("Слова не заданы ни для одного файла")
        self.status_label.config(text="Очищено", foreground="gray")
        self.save_btn.config(state=tk.DISABLED)
        self.last_results = None
        self.progress['value'] = 0
        self.progress_label.config(text="0%")