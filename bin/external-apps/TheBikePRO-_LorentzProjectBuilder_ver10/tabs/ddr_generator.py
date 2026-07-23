import os  # Импорт модуля для работы с операционной системой (пути, файлы)
import re  # Импорт модуля для работы с регулярными выражениями
import tkinter as tk  # Импорт основного модуля tkinter для создания GUI
from tkinter import ttk, filedialog, messagebox, scrolledtext  # Импорт виджетов: вкладки, диалоги, сообщения, прокручиваемый текст
import pandas as pd  # Импорт библиотеки pandas для работы с Excel-файлами
from datetime import datetime  # Импорт для работы с датой и временем
from utils.help_window import create_help_window  # Импорт функции создания окна справки
from templates.xml_templates import TEMPLATE_XML_NORMAL, TEMPLATE_XML_VAL  # Импорт шаблонов XML для NORMAL и VAL

class XMLGeneratorTab:  # Определение класса вкладки генератора XML
    """Вкладка генератора XML для DDR"""  # Документация класса
    
    def __init__(self, parent):  # Конструктор класса, принимает родительский виджет
        self.parent = parent  # Сохраняем ссылку на родительский виджет
        self.df_data = None  # Переменная для хранения данных из Excel (DataFrame)
        self.column_mapping = {}  # Словарь для хранения соответствия столбцов (устройство, тег, и т.д.)
        self.generated_results = {}  # Словарь для хранения сгенерированных XML по тегам
        self.last_copied_tag = None  # Переменная для хранения последнего скопированного тега
        self.tag_frames = {}  # Словарь для хранения фреймов тегов (для подсветки)
        self.copy_buttons = {}  # Словарь для хранения кнопок копирования по тегам
        self.template_xml_normal = TEMPLATE_XML_NORMAL  # Шаблон XML для NORMAL (CPU715)
        self.template_xml_val = TEMPLATE_XML_VAL  # Шаблон XML для VAL (CPU850)
        self.create_widgets()  # Вызов метода создания интерфейсных элементов
    
    def show_help(self):  # Метод отображения справочной информации
        content = """  # Многострочная строка с содержимым справки
📌 НАЗНАЧЕНИЕ

Генерация XML-файлов для DDR на основе Excel-данных.

▶️ КАК РАБОТАТЬ

1. Загрузите Excel файл (автоматическое определение столбцов)
2. Введите теги для генерации (вручную или извлеките из XML)
3. Нажмите "СГЕНЕРИРОВАТЬ XML ДЛЯ ВСЕХ ТЕГОВ"

📊 РЕЗУЛЬТАТЫ

• XML для каждого тега с подстановкой устройств
• Копирование в буфер обмена одним кликом
• Сохранение всех XML в один файл

📌 ОСОБЕННОСТИ

• Поддержка двух шаблонов: NORMAL (CPU715) и VAL (CPU850)
• Автоматическое определение типа шаблона по суффиксу _VAL
• Извлечение тегов из существующего XML
"""
        create_help_window(self.parent, "📄 Генератор XML для DDR", content)  # Вызов функции создания окна справки
    
    def create_widgets(self):  # Метод создания графических элементов интерфейса
        main_frame = ttk.Frame(self.parent, padding=10)  # Создание основного фрейма с отступами
        main_frame.pack(fill=tk.BOTH, expand=True)  # Размещение фрейма с расширением по всем направлениям
        
        # Заголовок
        header_frame = ttk.Frame(main_frame)  # Создание фрейма для заголовка
        header_frame.pack(fill=tk.X, pady=(0, 10))  # Размещение по горизонтали с вертикальным отступом
        title = ttk.Label(header_frame, text="ГЕНЕРАТОР XML ДЛЯ DDR", font=("Arial", 14, "bold"))  # Создание заголовка жирным шрифтом
        title.pack(side=tk.LEFT)  # Размещение заголовка слева
        btn_help = ttk.Button(header_frame, text="❓ Справка", command=self.show_help, width=12)  # Создание кнопки справки
        btn_help.pack(side=tk.RIGHT)  # Размещение кнопки справа
        
        # Основной фрейм с разделением на левую и правую часть
        main_paned = ttk.PanedWindow(main_frame, orient=tk.HORIZONTAL)  # Создание разделительной панели (горизонтальная)
        main_paned.pack(fill=tk.BOTH, expand=True)  # Размещение с расширением
        
        # ============ ЛЕВАЯ ЧАСТЬ - Результаты ============
        left_frame = ttk.Frame(main_paned)  # Создание фрейма для левой части
        main_paned.add(left_frame, weight=1)  # Добавление левой панели с весом 1 (занимает пропорционально больше места)
        
        result_title = ttk.Label(left_frame, text="РЕЗУЛЬТАТЫ ГЕНЕРАЦИИ",   # Создание заголовка результатов
                                 font=('Arial', 12, 'bold'), foreground='blue')  # Синий цвет, жирный шрифт
        result_title.pack(pady=(0, 5))  # Размещение с нижним отступом
        
        result_container = ttk.Frame(left_frame)  # Создание контейнера для результатов
        result_container.pack(fill=tk.BOTH, expand=True)  # Размещение с расширением
        
        self.result_canvas = tk.Canvas(result_container, bg='white')  # Создание холста с белым фоном
        self.result_canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)  # Размещение холста слева с расширением
        
        scrollbar = ttk.Scrollbar(result_container, orient=tk.VERTICAL, command=self.result_canvas.yview)  # Создание вертикальной полосы прокрутки
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)  # Размещение полосы прокрутки справа
        self.result_canvas.configure(yscrollcommand=scrollbar.set)  # Привязка полосы прокрутки к холсту
        
        self.result_inner = ttk.Frame(self.result_canvas)  # Создание внутреннего фрейма для размещения результатов
        self.result_canvas.create_window((0, 0), window=self.result_inner, anchor="nw")  # Размещение фрейма на холсте
        self.result_inner.bind("<Configure>", lambda e: self.result_canvas.configure(scrollregion=self.result_canvas.bbox("all")))  # Обновление области прокрутки при изменении размера
        
        # ============ ПРАВАЯ ЧАСТЬ - Настройки ============
        right_frame = ttk.Frame(main_paned, width=600)  # Создание фрейма для правой части с фиксированной шириной
        main_paned.add(right_frame, weight=0)  # Добавление правой панели с весом 0 (фиксированный размер)
        
        settings_title = ttk.Label(right_frame, text="НАСТРОЙКИ ГЕНЕРАЦИИ",   # Создание заголовка настроек
                                   font=('Arial', 12, 'bold'), foreground='green')  # Зеленый цвет, жирный шрифт
        settings_title.pack(pady=(0, 10))  # Размещение с нижним отступом
        
        # Шаг 1: Загрузка Excel
        file_frame = ttk.LabelFrame(right_frame, text="Шаг 1: Загрузка Excel файла", padding="10")  # Создание группы с рамкой для загрузки файла
        file_frame.pack(fill=tk.X, pady=(0, 10))  # Размещение по горизонтали с отступами
        
        file_row = ttk.Frame(file_frame)  # Создание строки для поля ввода и кнопки
        file_row.pack(fill=tk.X)  # Размещение по горизонтали
        self.file_path_var = tk.StringVar()  # Строковая переменная для хранения пути к файлу
        file_entry = ttk.Entry(file_row, textvariable=self.file_path_var)  # Поле ввода пути к файлу
        file_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 5))  # Размещение слева с расширением
        load_btn = ttk.Button(file_row, text="Выбрать", command=self.load_excel)  # Кнопка выбора файла
        load_btn.pack(side=tk.RIGHT)  # Размещение справа
        self.file_status_label = ttk.Label(file_frame, text="Файл не загружен", foreground="gray")  # Метка статуса файла
        self.file_status_label.pack(anchor=tk.W, pady=(5, 0))  # Размещение по левому краю
        
        # Шаг 2: Информация
        info_frame = ttk.LabelFrame(right_frame, text="Шаг 2: Информация о данных", padding="10")  # Группа для информации о данных
        info_frame.pack(fill=tk.X, pady=(0, 10))  # Размещение по горизонтали с отступами
        self.info_text = scrolledtext.ScrolledText(info_frame, height=4, font=('Courier', 8))  # Поле для вывода информации (с прокруткой)
        self.info_text.pack(fill=tk.X)  # Размещение по горизонтали
        
        # Шаг 3: Ввод тегов
        tags_frame = ttk.LabelFrame(right_frame, text="Шаг 3: Ввод тегов", padding="10")  # Группа для ввода тегов
        tags_frame.pack(fill=tk.X, pady=(0, 10))  # Размещение по горизонтали с отступами
        
        ttk.Label(tags_frame, text="Способ 1 - Вручную (каждый с новой строки):",   # Метка для ручного ввода
                  font=('Arial', 9)).pack(anchor=tk.W)  # Размещение по левому краю
        self.tags_text = scrolledtext.ScrolledText(tags_frame, height=4, font=('Courier', 9))  # Поле для ручного ввода тегов (с прокруткой)
        self.tags_text.pack(fill=tk.X, pady=(5, 10))  # Размещение по горизонтали с отступами
        
        ttk.Label(tags_frame, text="Способ 2 - Извлечь из XML (вставьте XML текст):",   # Метка для извлечения из XML
                  font=('Arial', 9)).pack(anchor=tk.W)  # Размещение по левому краю
        self.xml_text = scrolledtext.ScrolledText(tags_frame, height=4, font=('Courier', 9))  # Поле для вставки XML (с прокруткой)
        self.xml_text.pack(fill=tk.X, pady=(5, 5))  # Размещение по горизонтали с отступами
        
        extract_row = ttk.Frame(tags_frame)  # Строка для кнопки извлечения и статуса
        extract_row.pack(fill=tk.X)  # Размещение по горизонтали
        extract_btn = ttk.Button(extract_row, text="Извлечь теги из XML", command=self.extract_tags_from_xml)  # Кнопка извлечения тегов
        extract_btn.pack(side=tk.LEFT, padx=(0, 10))  # Размещение слева с отступом
        self.extract_status = ttk.Label(extract_row, text="", foreground="green")  # Метка статуса извлечения
        self.extract_status.pack(side=tk.LEFT)  # Размещение слева
        
        # Кнопки
        btn_frame = ttk.Frame(right_frame)  # Фрейм для кнопок управления
        btn_frame.pack(fill=tk.X, pady=(0, 10))  # Размещение по горизонтали с отступами
        generate_btn = ttk.Button(btn_frame, text="СГЕНЕРИРОВАТЬ XML ДЛЯ ВСЕХ ТЕГОВ", command=self.generate_all_xml)  # Кнопка генерации XML
        generate_btn.pack(fill=tk.X, pady=(0, 5))  # Размещение по горизонтали с отступом
        self.status_label = ttk.Label(btn_frame, text="", foreground="green")  # Метка общего статуса
        self.status_label.pack()  # Размещение
        self.last_copy_label = ttk.Label(btn_frame, text="", foreground="blue", font=('Arial', 9, 'bold'))  # Метка последнего скопированного тега
        self.last_copy_label.pack(pady=(5, 0))  # Размещение с отступом
        
        action_frame = ttk.Frame(right_frame)  # Фрейм для дополнительных действий
        action_frame.pack(fill=tk.X)  # Размещение по горизонтали
        self.save_all_btn = ttk.Button(action_frame, text="Сохранить все XML в файл",   # Кнопка сохранения всех XML
                                      command=self.save_all_xml, state=tk.DISABLED)  # Изначально отключена
        self.save_all_btn.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 5))  # Размещение слева с расширением
        clear_btn = ttk.Button(action_frame, text="Очистить всё", command=self.clear_all)  # Кнопка очистки
        clear_btn.pack(side=tk.LEFT, fill=tk.X, expand=True)  # Размещение слева с расширением
    
    def extract_tags_from_xml(self):  # Метод извлечения тегов из XML
        xml_text = self.xml_text.get(1.0, tk.END).strip()  # Получение текста из поля XML
        if not xml_text:  # Проверка, что текст не пустой
            self.extract_status.config(text="❌ Вставьте XML текст!", foreground="red")  # Обновление статуса с ошибкой
            return  # Выход из метода
        try:  # Блок try для обработки ошибок
            start_marker = '<ISACARDSINFO>'  # Маркер начала блока с тегами
            end_marker = '</ISACARDSINFO>'  # Маркер конца блока с тегами
            start_pos = xml_text.find(start_marker)  # Поиск позиции начала маркера
            if start_pos == -1:  # Если маркер не найден
                self.extract_status.config(text="❌ Не найден тег <ISACARDSINFO>", foreground="red")  # Статус с ошибкой
                return  # Выход из метода
            end_pos = xml_text.find(end_marker, start_pos)  # Поиск позиции конца маркера
            if end_pos == -1:  # Если маркер не найден
                self.extract_status.config(text="❌ Не найден тег </ISACARDSINFO>", foreground="red")  # Статус с ошибкой
                return  # Выход из метода
            content = xml_text[start_pos + len(start_marker):end_pos]  # Извлечение содержимого между маркерами
            pattern = r'Info="([^"]*)"'  # Регулярное выражение для поиска атрибута Info
            matches = re.findall(pattern, content)  # Поиск всех совпадений
            tags = []  # Список для найденных тегов
            for tag in matches:  # Перебор всех найденных тегов
                if '_MOS' not in tag and tag.strip():  # Исключение тегов с _MOS и пустых
                    tags.append(tag.strip())  # Добавление тега в список
            if not tags:  # Если теги не найдены
                self.extract_status.config(text="❌ Теги не найдены", foreground="red")  # Статус с ошибкой
                return  # Выход из метода
            unique_tags = []  # Список для уникальных тегов
            seen = set()  # Множество для отслеживания уже добавленных тегов
            for tag in tags:  # Перебор всех тегов
                if tag not in seen:  # Если тег еще не добавлен
                    unique_tags.append(tag)  # Добавление в список уникальных
                    seen.add(tag)  # Добавление в множество просмотренных
            self.tags_text.delete(1.0, tk.END)  # Очистка поля для ввода тегов
            self.tags_text.insert(1.0, '\n'.join(unique_tags))  # Вставка уникальных тегов (каждый с новой строки)
            self.extract_status.config(text=f"✅ Извлечено {len(unique_tags)} тегов", foreground="green")  # Статус успеха
        except Exception as e:  # Обработка исключений
            self.extract_status.config(text=f"❌ Ошибка: {str(e)}", foreground="red")  # Статус с ошибкой
    
    def find_columns(self, df):  # Метод автоматического определения столбцов в Excel
        column_mapping = {}  # Словарь для хранения соответствий
        search_patterns = {  # Шаблоны поиска для разных полей
            'device': ['устройство', 'device', 'устр', 'модуль', 'module', 'канал', 'channel'],  # Для устройств
            'tag': ['тег', 'tag', 'тэг', 'имя', 'name'],  # Для тегов
            'controller_id': ['controllerid', 'controller id', 'id контроллера', 'контроллер id'],  # Для ID контроллера
            'resuorce_id': ['resuorceid', 'resuorce id', 'id ресурса', 'ресурс id'],  # Для ID ресурса
            'template_type': ['тип', 'type', 'template', 'шаблон']  # Для типа шаблона
        }
        for col in df.columns:  # Перебор всех столбцов DataFrame
            col_lower = str(col).lower().strip()  # Приведение к нижнему регистру и удаление пробелов
            col_clean = re.sub(r'[^a-zа-я0-9]', '', col_lower)  # Удаление всех символов кроме букв и цифр
            for key, patterns in search_patterns.items():  # Перебор всех шаблонов
                if key not in column_mapping:  # Если ключ еще не найден
                    for pattern in patterns:  # Перебор шаблонов для текущего ключа
                        pattern_clean = re.sub(r'[^a-zа-я0-9]', '', pattern.lower())  # Очистка шаблона
                        if pattern_clean in col_clean or pattern in col_lower:  # Проверка совпадения
                            column_mapping[key] = col  # Сохранение соответствия
                            break  # Выход из внутреннего цикла
        # Дополнительные проверки для автоматического определения
        if 'device' not in column_mapping and len(df.columns) >= 1:  # Если устройство не найдено и есть хотя бы один столбец
            sample = str(df.iloc[0, 0])  # Значение из первой ячейки первого столбца
            if 'IO_IU' in sample or '_' in sample:  # Проверка характерного формата
                column_mapping['device'] = df.columns[0]  # Назначение первого столбца как устройство
        if 'tag' not in column_mapping and len(df.columns) >= 5:  # Если тег не найден и есть минимум 5 столбцов
            sample = str(df.iloc[0, 4])  # Значение из первой ячейки пятого столбца
            if '_1110_' in sample or '_' in sample:  # Проверка характерного формата
                column_mapping['tag'] = df.columns[4]  # Назначение пятого столбца как тег
        if 'controller_id' not in column_mapping and len(df.columns) >= 2:  # Если ID контроллера не найден
            sample = str(df.iloc[0, 1])  # Значение из второй ячейки
            if sample.isdigit() or '189' in sample:  # Проверка на цифры или характерное значение
                column_mapping['controller_id'] = df.columns[1]  # Назначение второго столбца
        if 'resuorce_id' not in column_mapping and len(df.columns) >= 3:  # Если ID ресурса не найден
            sample = str(df.iloc[0, 2])  # Значение из третьей ячейки
            if sample.isdigit() or '62' in sample:  # Проверка на цифры или характерное значение
                column_mapping['resuorce_id'] = df.columns[2]  # Назначение третьего столбца
        return column_mapping  # Возврат словаря соответствий
    
    def load_excel(self):  # Метод загрузки Excel-файла
        file_path = filedialog.askopenfilename(  # Открытие диалога выбора файла
            title="Выберите Excel файл",  # Заголовок окна
            filetypes=[("Excel files", "*.xlsx *.xls"), ("All files", "*.*")]  # Фильтр типов файлов
        )
        if not file_path:  # Если файл не выбран
            return  # Выход из метода
        try:  # Блок try для обработки ошибок
            df = pd.read_excel(file_path)  # Чтение Excel-файла в DataFrame
            column_mapping = self.find_columns(df)  # Автоматическое определение столбцов
            if len(column_mapping) < 4:  # Если найдено менее 4 столбцов
                df = pd.read_excel(file_path, header=None)  # Повторное чтение без заголовков
                column_mapping = self.find_columns(df)  # Повторное определение столбцов
            self.df_data = df  # Сохранение данных в атрибут
            self.column_mapping = column_mapping  # Сохранение соответствий
            required = ['device', 'tag', 'controller_id', 'resuorce_id']  # Список обязательных полей
            missing = [r for r in required if r not in column_mapping]  # Определение отсутствующих полей
            self.info_text.delete(1.0, tk.END)  # Очистка поля информации
            self.info_text.insert(1.0, f"Загружено строк: {len(df)}\n")  # Вывод количества строк
            self.info_text.insert(tk.END, f"Столбцов: {len(df.columns)}\n\n")  # Вывод количества столбцов
            self.info_text.insert(tk.END, "Найденные столбцы:\n")  # Заголовок найденных столбцов
            for key, col in column_mapping.items():  # Перебор найденных соответствий
                self.info_text.insert(tk.END, f"  {key}: {col}\n")  # Вывод соответствия
            if missing:  # Если есть пропущенные поля
                self.info_text.insert(tk.END, f"\n⚠️ Не найдены: {', '.join(missing)}\n")  # Предупреждение
            if 'template_type' in column_mapping:  # Если найден тип шаблона
                self.info_text.insert(tk.END, f"\n✅ Столбец типа шаблона: {column_mapping['template_type']}")  # Подтверждение
            self.file_path_var.set(file_path)  # Установка пути в поле ввода
            self.file_status_label.config(text=f"✅ Загружено {len(df)} строк", foreground="green")  # Обновление статуса
            self.status_label.config(text="", foreground="green")  # Сброс статуса
        except Exception as e:  # Обработка исключений
            messagebox.showerror("Ошибка", f"Не удалось загрузить файл:\n{str(e)}")  # Вывод сообщения об ошибке
    
    def extract_devices(self, device_val):  # Метод извлечения устройств из строки
        if not device_val or device_val == 'nan':  # Если значение пустое или NaN
            return []  # Возврат пустого списка
        devices = re.split(r'[,\s;]+', device_val)  # Разделение строки по запятым, пробелам, точкам с запятой
        devices = [d.strip() for d in devices if d.strip() and d.strip() != 'nan']  # Очистка и фильтрация
        return devices  # Возврат списка устройств
    
    def find_two_different_devices(self, devices):  # Метод поиска двух различных устройств
        if not devices:  # Если список устройств пуст
            return None, None  # Возврат None, None
        unique_devices = []  # Список уникальных устройств
        seen = set()  # Множество для отслеживания добавленных
        for device in devices:  # Перебор всех устройств
            if device not in seen:  # Если устройство еще не добавлено
                unique_devices.append(device)  # Добавление в список
                seen.add(device)  # Добавление в множество
        if len(unique_devices) >= 2:  # Если найдено 2 и более уникальных устройств
            return unique_devices[0], unique_devices[1]  # Возврат первых двух
        elif len(unique_devices) == 1:  # Если найдено только одно уникальное устройство
            return unique_devices[0], unique_devices[0]  # Возврат одного и того же устройства
        else:  # Если устройств нет
            return None, None  # Возврат None, None
    
    def get_template_type_for_tag(self, tag_name):  # Метод определения типа шаблона для тега
        if 'template_type' in self.column_mapping:  # Если есть столбец с типом шаблона
            for idx, row in self.df_data.iterrows():  # Перебор всех строк DataFrame
                tag = str(row[self.column_mapping['tag']]).strip()  # Получение значения тега
                if tag == tag_name:  # Если тег совпадает с искомым
                    template_val = str(row[self.column_mapping['template_type']]).strip().upper()  # Получение типа шаблона
                    if template_val and template_val != 'nan':  # Если значение не пустое
                        if 'VAL' in template_val:  # Если в значении есть 'VAL'
                            return 'VAL'  # Возврат 'VAL'
                        elif 'NORMAL' in template_val or 'NORM' in template_val:  # Если в значении есть 'NORMAL' или 'NORM'
                            return 'NORMAL'  # Возврат 'NORMAL'
        # Дополнительная проверка по устройствам
        matching_rows = []  # Список для строк с совпадающими тегами
        for idx, row in self.df_data.iterrows():  # Перебор всех строк
            tag = str(row[self.column_mapping['tag']]).strip()  # Получение значения тега
            if tag == tag_name:  # Если тег совпадает
                matching_rows.append(row)  # Добавление строки в список
        all_devices = []  # Список всех устройств для этого тега
        for row in matching_rows:  # Перебор найденных строк
            device_val = str(row[self.column_mapping['device']]).strip()  # Получение значения устройства
            devices = self.extract_devices(device_val)  # Извлечение устройств
            all_devices.extend(devices)  # Добавление в общий список
        for device in all_devices:  # Перебор всех устройств
            if device.endswith('_VAL'):  # Если устройство заканчивается на _VAL
                return 'VAL'  # Возврат 'VAL'
        return 'NORMAL'  # По умолчанию возврат 'NORMAL'
    
    def generate_single_xml(self, tag_name):  # Метод генерации XML для одного тега
        if self.df_data is None:  # Если данные не загружены
            return None, "Excel файл не загружен"  # Возврат ошибки
        if 'device' not in self.column_mapping or 'tag' not in self.column_mapping:  # Если необходимые столбцы не найдены
            return None, "Не найдены столбцы 'Устройство' и 'Тег'"  # Возврат ошибки
        matching_rows = []  # Список строк с совпадающим тегом
        for idx, row in self.df_data.iterrows():  # Перебор всех строк
            tag = str(row[self.column_mapping['tag']]).strip()  # Получение значения тега
            if tag == tag_name:  # Если тег совпадает
                matching_rows.append(row)  # Добавление строки
        if not matching_rows:  # Если строки не найдены
            return None, f"Тег не найден"  # Возврат ошибки
        all_devices = []  # Список всех устройств
        for row in matching_rows:  # Перебор найденных строк
            device_val = str(row[self.column_mapping['device']]).strip()  # Получение устройства
            devices = self.extract_devices(device_val)  # Извлечение устройств
            all_devices.extend(devices)  # Добавление в общий список
        device_1, device_2 = self.find_two_different_devices(all_devices)  # Поиск двух устройств
        if not device_1:  # Если устройство не найдено
            return None, f"Устройства не найдены"  # Возврат ошибки
        if not device_2:  # Если второе устройство не найдено
            device_2 = device_1  # Использование первого как второго
        first_row = matching_rows[0]  # Берем первую найденную строку
        controller_id = "189285"  # Значение по умолчанию для ID контроллера
        if 'controller_id' in self.column_mapping:  # Если столбец с ID контроллера найден
            controller_val = str(first_row[self.column_mapping['controller_id']]).strip()  # Получение значения
            if controller_val and controller_val != 'nan':  # Если значение не пустое
                controller_id = controller_val  # Использование значения из файла
        resuorce_id = "627"  # Значение по умолчанию для ID ресурса
        if 'resuorce_id' in self.column_mapping:  # Если столбец с ID ресурса найден
            resuorce_val = str(first_row[self.column_mapping['resuorce_id']]).strip()  # Получение значения
            if resuorce_val and resuorce_val != 'nan':  # Если значение не пустое
                resuorce_id = resuorce_val  # Использование значения из файла
        template_type = self.get_template_type_for_tag(tag_name)  # Определение типа шаблона
        if template_type == 'VAL':  # Если тип VAL
            template = self.template_xml_val  # Использование шаблона VAL
            template_type_display = "VAL"  # Отображаемое название
        else:  # Если тип NORMAL
            template = self.template_xml_normal  # Использование шаблона NORMAL
            template_type_display = "NORMAL"  # Отображаемое название
        lines = template.split('\n')  # Разбиение шаблона на строки
        if len(lines) > 2:  # Если в шаблоне больше 2 строк
            common_line = lines[2]  # Берем третью строку (индекс 2)
            common_line = re.sub(r'ControllerID="[^"]*"', f'ControllerID="{controller_id}"', common_line)  # Замена ID контроллера
            common_line = re.sub(r'ResuorceID="[^"]*"', f'ResuorceID="{resuorce_id}"', common_line)  # Замена ID ресурса
            lines[2] = common_line  # Обновление строки
        isacardsinfo_start = -1  # Индекс начала блока ISACARDSINFO
        isacardsinfo_end = -1  # Индекс конца блока ISACARDSINFO
        for i, line in enumerate(lines):  # Перебор всех строк с индексами
            if '<ISACARDSINFO>' in line:  # Если найдено начало блока
                isacardsinfo_start = i  # Сохранение индекса
            elif '</ISACARDSINFO>' in line:  # Если найден конец блока
                isacardsinfo_end = i  # Сохранение индекса
                break  # Выход из цикла
        if isacardsinfo_start != -1 and isacardsinfo_end != -1:  # Если найдены начало и конец
            rec_indices = []  # Список индексов строк с <rec>
            for i in range(isacardsinfo_start + 1, isacardsinfo_end):  # Перебор строк внутри блока
                if '<rec' in lines[i]:  # Если строка содержит <rec
                    rec_indices.append(i)  # Добавление индекса
            if len(rec_indices) >= 3:  # Если найдено минимум 3 записи
                line_idx = rec_indices[0]  # Первая запись
                lines[line_idx] = re.sub(r'Info="[^"]*"', f'Info="{device_1}"', lines[line_idx])  # Подстановка первого устройства                line_idx = rec_indices[1]  # Вторая запись
                lines[line_idx] = re.sub(r'Info="[^"]*"', f'Info="{device_2}"', lines[line_idx])  # Подстановка второго устройства
                line_idx = rec_indices[2]  # Третья запись
                lines[line_idx] = re.sub(r'Info="[^"]*"', f'Info="{tag_name}"', lines[line_idx])  # Подстановка тега
        new_xml = '\n'.join(lines)  # Объединение строк обратно в XML
        info = f"OK [{template_type_display}]: device1={device_1}, device2={device_2}"  # Информация о результате
        if device_1 == device_2:  # Если устройства одинаковые
            info += " (одно устройство)"  # Добавление пояснения
        return new_xml, info  # Возврат XML и информации
    
    def copy_to_clipboard(self, text):  # Метод копирования в буфер обмена
        self.parent.clipboard_clear()  # Очистка буфера обмена
        self.parent.clipboard_append(text)  # Добавление текста в буфер
        self.parent.update()  # Обновление окна
    
    def reset_highlight(self):  # Метод сброса подсветки
        if self.last_copied_tag and self.last_copied_tag in self.tag_frames:  # Если есть последний скопированный тег
            self.tag_frames[self.last_copied_tag].configure(style='TFrame')  # Сброс стиля фрейма
            if self.last_copied_tag in self.copy_buttons:  # Если есть кнопка для этого тега
                self.copy_buttons[self.last_copied_tag].configure(style='TButton')  # Сброс стиля кнопки
    
    def on_copy_click(self, tag):  # Обработчик нажатия кнопки копирования
        if tag in self.generated_results:  # Если тег есть в результатах
            self.reset_highlight()  # Сброс предыдущей подсветки
            self.copy_to_clipboard(self.generated_results[tag])  # Копирование XML в буфер
            self.last_copied_tag = tag  # Сохранение последнего скопированного тега
            if tag in self.tag_frames:  # Если есть фрейм для тега
                self.tag_frames[tag].configure(style='Highlight.TFrame')  # Подсветка фрейма
            if tag in self.copy_buttons:  # Если есть кнопка для тега
                self.copy_buttons[tag].configure(style='Highlight.TButton')  # Подсветка кнопки
            self.status_label.config(text=f"✅ XML для '{tag}' скопирован!", foreground="green")  # Обновление статуса
            self.last_copy_label.config(text=f"📋 Последний: {tag}", foreground="blue")  # Обновление метки последнего
            self.parent.after(3000, lambda: self.status_label.config(text="", foreground="green"))  # Сброс статуса через 3 секунды
        else:  # Если тег не найден в результатах
            self.status_label.config(text=f"❌ XML для '{tag}' не найден!", foreground="red")  # Обновление статуса с ошибкой
    
    def generate_all_xml(self):  # Метод генерации XML для всех тегов
        if self.df_data is None:  # Если данные не загружены
            messagebox.showerror("Ошибка", "Сначала загрузите Excel файл!")  # Вывод сообщения об ошибке
            return  # Выход из метода
        tags_text = self.tags_text.get(1.0, tk.END).strip()  # Получение текста с тегами
        if not tags_text:  # Если текст пустой
            messagebox.showerror("Ошибка", "Введите теги для генерации!")  # Вывод сообщения об ошибке
            return  # Выход из метода
        tags = [t.strip() for t in tags_text.split('\n') if t.strip()]  # Разбиение на список тегов
        if not tags:  # Если список пуст
            messagebox.showerror("Ошибка", "Не найдено ни одного тега!")  # Вывод сообщения об ошибке
            return  # Выход из метода
        for widget in self.result_inner.winfo_children():  # Очистка результатов
            widget.destroy()  # Удаление всех виджетов
        self.generated_results = {}  # Очистка словаря результатов
        self.tag_frames = {}  # Очистка словаря фреймов
        self.copy_buttons = {}  # Очистка словаря кнопок
        self.last_copied_tag = None  # Сброс последнего скопированного тега
        self.last_copy_label.config(text="")  # Очистка метки последнего
        success_count = 0  # Счетчик успешных генераций
        fail_count = 0  # Счетчик ошибок
        failed_tags = []  # Список тегов с ошибками
        val_count = 0  # Счетчик шаблонов VAL
        normal_count = 0  # Счетчик шаблонов NORMAL
        style = ttk.Style()  # Создание объекта стиля
        style.configure('Highlight.TFrame', background='#c7e5ff', relief='groove', borderwidth=2)  # Стиль подсветки фрейма
        style.configure('Highlight.TButton', background='#4a90d9')  # Стиль подсветки кнопки
        header = ttk.Label(self.result_inner, text=f"Результаты генерации ({len(tags)} тегов)", font=('Arial', 10, 'bold'))  # Заголовок результатов
        header.grid(row=0, column=0, columnspan=4, pady=(0, 10), sticky=tk.W)  # Размещение заголовка
        row = 1  # Начальная строка для размещения результатов
        for tag in tags:  # Перебор всех тегов
            xml_content, info = self.generate_single_xml(tag)  # Генерация XML для тега
            frame = ttk.Frame(self.result_inner, relief=tk.GROOVE, padding=5)  # Создание фрейма для результата
            frame.grid(row=row, column=0, columnspan=4, sticky=(tk.W, tk.E), pady=2)  # Размещение фрейма
            self.tag_frames[tag] = frame  # Сохранение фрейма в словарь
            if xml_content:  # Если XML успешно сгенерирован
                self.generated_results[tag] = xml_content  # Сохранение в словарь результатов
                success_count += 1  # Увеличение счетчика успешных
                if 'VAL' in info:  # Если тип шаблона VAL
                    val_count += 1  # Увеличение счетчика VAL
                    template_type = "VAL"  # Тип для отображения
                else:  # Иначе NORMAL
                    normal_count += 1  # Увеличение счетчика NORMAL
                    template_type = "NORMAL"  # Тип для отображения
                status = "✅"  # Статус успеха
                status_color = "green"  # Цвет статуса
                info_text = info  # Информация о результате
                copy_btn = ttk.Button(frame, text="📋 Копировать", command=lambda t=tag: self.on_copy_click(t), width=12)  # Кнопка копирования
                copy_btn.grid(row=0, column=0, padx=(0, 5), sticky=tk.W)  # Размещение кнопки
                self.copy_buttons[tag] = copy_btn  # Сохранение кнопки в словарь
            else:  # Если генерация не удалась
                fail_count += 1  # Увеличение счетчика ошибок
                failed_tags.append(tag)  # Добавление тега в список ошибок
                status = "❌"  # Статус ошибки
                status_color = "red"  # Цвет статуса
                info_text = info  # Информация об ошибке
                template_type = "-"  # Тип не определен
            tag_label = ttk.Label(frame, text=f"{status} {tag}", foreground=status_color, font=('Courier', 9, 'bold'))  # Метка с тегом и статусом
            tag_label.grid(row=0, column=1, padx=(0, 10), sticky=tk.W)  # Размещение метки
            type_label = ttk.Label(frame, text=f"[{template_type}]", font=('Courier', 8), foreground="blue")  # Метка типа шаблона
            type_label.grid(row=0, column=2, padx=(0, 10), sticky=tk.W)  # Размещение метки
            info_label = ttk.Label(frame, text=info_text, font=('Courier', 8), foreground="gray")  # Метка с дополнительной информацией
            info_label.grid(row=0, column=3, padx=(0, 10), sticky=tk.W)  # Размещение метки
            row += 1  # Переход к следующей строке
        summary_color = "green" if fail_count == 0 else ("orange" if success_count > 0 else "red")  # Определение цвета итогов
        summary_text = f"ИТОГ: Успешно: {success_count}, Ошибок: {fail_count}"  # Текст итогов
        if success_count > 0:  # Если есть успешные генерации
            summary_text += f" (NORMAL: {normal_count}, VAL: {val_count})"  # Добавление статистики по типам
        if failed_tags:  # Если есть теги с ошибками
            summary_text += f"\nНе найдены: {', '.join(failed_tags)}"  # Добавление списка ошибок
        summary_label = ttk.Label(self.result_inner, text=summary_text, foreground=summary_color, font=('Arial', 10, 'bold'))  # Метка с итогами
        summary_label.grid(row=row, column=0, columnspan=4, pady=(10, 0), sticky=tk.W)  # Размещение итогов
        self.result_canvas.configure(scrollregion=self.result_canvas.bbox("all"))  # Обновление области прокрутки
        if fail_count == 0:  # Если все успешно
            self.status_label.config(text=f"✅ Все {success_count} тегов сгенерированы!", foreground="green")  # Статус успеха
        elif success_count == 0:  # Если все с ошибкой
            self.status_label.config(text=f"❌ Все теги не найдены!", foreground="red")  # Статус ошибки
        else:  # Если частичный успех
            self.status_label.config(text=f"⚠️ Сгенерировано: {success_count}, ошибок: {fail_count}", foreground="orange")  # Предупреждение
        self.save_all_btn.config(state=tk.NORMAL)  # Активация кнопки сохранения
    
    def save_all_xml(self):  # Метод сохранения всех XML в один файл
        if not hasattr(self, 'generated_results') or not self.generated_results:  # Если нет сгенерированных результатов
            messagebox.showerror("Ошибка", "Нет сгенерированных XML файлов!")  # Вывод сообщения об ошибке
            return  # Выход из метода
        file_path = filedialog.asksaveasfilename(  # Открытие диалога сохранения файла
            title="Сохранить все XML в один файл",  # Заголовок окна
            defaultextension=".txt",  # Расширение по умолчанию
            filetypes=[("Text files", "*.txt"), ("All files", "*.*")]  # Фильтр типов файлов
        )
        if not file_path:  # Если путь не выбран
            return  # Выход из метода
        try:  # Блок try для обработки ошибок
            with open(file_path, 'w', encoding='utf-8') as f:  # Открытие файла для записи
                f.write("=" * 80 + "\n")  # Разделительная линия
                f.write(f"СГЕНЕРИРОВАННЫЕ XML ДЛЯ BUFSCADA\n")  # Заголовок
                f.write(f"Дата: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")  # Дата и время
                f.write(f"Всего тегов: {len(self.generated_results)}\n")  # Количество тегов
                f.write("=" * 80 + "\n\n")  # Разделительная линия
                for i, (tag, xml) in enumerate(self.generated_results.items(), 1):  # Перебор всех результатов
                    f.write(f"\n{'='*80}\n")  # Разделитель
                    f.write(f"ТЕГ #{i}: {tag}\n")  # Номер и имя тега
                    f.write(f"{'='*80}\n\n")  # Разделитель
                    f.write(xml)  # Запись XML
                    f.write("\n\n")  # Пустая строка
                f.write("\n" + "=" * 80 + "\n")  # Завершающая линия
                f.write("КОНЕЦ ФАЙЛА\n")  # Завершающая надпись
                f.write("=" * 80 + "\n")  # Завершающая линия
            messagebox.showinfo("Успех", f"Все XML сохранены в файл:\n{file_path}\n\nВсего: {len(self.generated_results)} тегов")  # Сообщение об успехе
        except Exception as e:  # Обработка исключений
            messagebox.showerror("Ошибка", f"Не удалось сохранить файл:\n{str(e)}")  # Вывод сообщения об ошибке
    
    def clear_all(self):  # Метод очистки всех данных
        self.df_data = None  # Сброс данных
        self.column_mapping = {}  # Сброс соответствий
        self.file_path_var.set("")  # Очистка пути к файлу
        self.file_status_label.config(text="Файл не загружен", foreground="gray")  # Сброс статуса файла
        self.info_text.delete(1.0, tk.END)  # Очистка поля информации
        self.tags_text.delete(1.0, tk.END)  # Очистка поля тегов
        self.xml_text.delete(1.0, tk.END)  # Очистка поля XML
        self.extract_status.config(text="", foreground="green")  # Сброс статуса извлечения
        for widget in self.result_inner.winfo_children():  # Очистка результатов
            widget.destroy()  # Удаление всех виджетов
        self.generated_results = {}  # Сброс результатов
        self.tag_frames = {}  # Сброс фреймов
        self.copy_buttons = {}  # Сброс кнопок
        self.last_copied_tag = None  # Сброс последнего скопированного тега
        self.status_label.config(text="", foreground="green")  # Сброс статуса
        self.last_copy_label.config(text="")  # Сброс метки последнего
        self.save_all_btn.config(state=tk.DISABLED)  # Отключение кнопки сохранения