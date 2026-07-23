import tkinter as tk
from tkinter import ttk, scrolledtext

def create_help_window(parent, title, content, width=550, height=400):
    """Создает компактное окно справки"""
    help_window = tk.Toplevel(parent)
    help_window.title(title)
    help_window.geometry(f"{width}x{height}")
    help_window.transient(parent)
    help_window.grab_set()
    help_window.resizable(False, False)
    
    # Центрирование
    help_window.update_idletasks()
    x = (help_window.winfo_screenwidth() // 2) - (width // 2)
    y = (help_window.winfo_screenheight() // 2) - (height // 2)
    help_window.geometry(f'{width}x{height}+{x}+{y}')
    
    main_frame = ttk.Frame(help_window, padding=12)
    main_frame.pack(fill=tk.BOTH, expand=True)
    
    # Заголовок
    title_label = ttk.Label(main_frame, text=title, font=("Arial", 12, "bold"), foreground="#2c3e50")
    title_label.pack(anchor=tk.W, pady=(0, 8))
    
    ttk.Separator(main_frame, orient='horizontal').pack(fill=tk.X, pady=(0, 8))
    
    # Текст
    text_widget = scrolledtext.ScrolledText(
        main_frame, wrap=tk.WORD, font=("Segoe UI", 9),
        bg="#f8f9fa", fg="#2c3e50", relief=tk.FLAT, borderwidth=0,
        padx=10, pady=10
    )
    text_widget.pack(fill=tk.BOTH, expand=True, pady=(0, 8))
    
    # Стили
    text_widget.tag_configure("header1", font=("Segoe UI", 11, "bold"), foreground="#2980b9")
    text_widget.tag_configure("header2", font=("Segoe UI", 10, "bold"), foreground="#27ae60")
    text_widget.tag_configure("bold", font=("Segoe UI", 9, "bold"))
    text_widget.tag_configure("code", font=("Consolas", 8), background="#e9ecef", foreground="#d63384")
    
    text_widget.insert('1.0', content)
    text_widget.config(state=tk.DISABLED)
    
    # Кнопка закрытия
    ttk.Button(main_frame, text="✕ ЗАКРЫТЬ", command=help_window.destroy, width=15).pack()
    
    return help_window