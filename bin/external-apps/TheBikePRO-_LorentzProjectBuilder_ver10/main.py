import tkinter as tk
from tkinter import ttk
from tabs import (
    AIAO_CheckTab,
    DI_DOCheckTab,
    DO_CheckTab,
    XMLGeneratorTab
)

class MainApp:
    """Главное приложение с вкладками"""
    
    def __init__(self, root):
        self.root = root
        self.root.title("Полный инструментарий - XML/текстовые файлы + DDR")
        self.root.geometry("1000x680")
        self.root.minsize(850, 550)
        
        # Компактный стиль
        style = ttk.Style()
        style.configure("TNotebook.Tab", padding=[6, 2], font=('Arial', 9))
        style.configure("TButton", padding=3, font=('Arial', 8))
        style.configure("TLabelframe.Label", font=('Arial', 9, 'bold'))
        style.configure("TLabelframe", padding=4)
        
        self.notebook = ttk.Notebook(root)
        self.notebook.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Вкладки с полными названиями
        self.tab_combined = ttk.Frame(self.notebook)
        self.notebook.add(self.tab_combined, text="📊 Проверка AI/AO")
        self.combined = AIAO_CheckTab(self.tab_combined)
        
        self.tab_di = ttk.Frame(self.notebook)
        self.notebook.add(self.tab_di, text="✅ Проверка DI")
        self.di_check = DI_DOCheckTab(self.tab_di)
        
        self.tab_do = ttk.Frame(self.notebook)
        self.notebook.add(self.tab_do, text="✅ Проверка DO")
        self.do_check = DO_CheckTab(self.tab_do)
        
        self.tab_ddr = ttk.Frame(self.notebook)
        self.notebook.add(self.tab_ddr, text="📄 Генератор DDR")
        self.ddr_gen = XMLGeneratorTab(self.tab_ddr)


if __name__ == "__main__":
    try:
        import pandas as pd
    except ImportError:
        print("ОШИБКА: Установите pandas:")
        print("  pip install pandas openpyxl")
        exit()
    
    root = tk.Tk()
    app = MainApp(root)
    root.mainloop()