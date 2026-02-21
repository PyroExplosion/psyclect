import tkinter as tk
from tkinter import ttk
import random, time
import json
import sqlite3
import os
import re

def _safe_tk_color(color, fallback='#f0f0f0'):
    """Return fallback color if the value is a CSS gradient or otherwise invalid for Tkinter."""
    if isinstance(color, str) and ('gradient' in color or color.startswith('url(')):
        return fallback
    return color if color else fallback


def _transform_chunk_text(chunk_type, raw_text):
    """Validate and transform chunk text according to per-type rules.
    Returns (transformed_text, log_list)."""
    text = raw_text.strip() if raw_text else ''
    log = []

    if chunk_type == 'background_color':
        if 'gradient' in text:
            match = re.search(r'#[0-9a-fA-F]{3,6}', text)
            if match:
                text = match.group(0)
                log.append(f'gradient → extracted first hex: {text}')
            else:
                text = '#1a1a2e'
                log.append('gradient with no hex → fallback #1a1a2e')
        elif re.match(r'^#[0-9a-fA-F]{3,6}$', text):
            log.append(f'valid hex: {text}')
        elif text.lower() in ('white', 'black', 'red', 'blue', 'green', 'gray', 'grey'):
            log.append(f'named color: {text}')
        else:
            text = '#1a1a2e'
            log.append(f'invalid color "{raw_text}" → fallback #1a1a2e')

    elif chunk_type == 'preformatted':
        original = text
        text = text.replace(' then on a new line ', '\n')
        text = text.replace(' then new line ', '\n')
        text = text.replace('then on a new line', '\n')
        text = text.replace('then new line', '\n')
        if text != original:
            log.append('replaced newline placeholders → actual \\n')
        else:
            log.append('no newline placeholders — whitespace preserved as-is')

    elif chunk_type == 'navbar':
        if '|' in text:
            items = [i.strip() for i in text.split('|') if i.strip()]
            log.append(f'delimiter: | → {len(items)} items')
        else:
            items = [i.strip() for i in text.split(',') if i.strip()]
            log.append(f'delimiter: , → {len(items)} items')
        text = '|'.join(items)

    elif chunk_type == 'column':
        if '\n' in text:
            items = [i.strip() for i in text.split('\n') if i.strip()]
            log.append(f'delimiter: \\n → {len(items)} items')
        else:
            items = [i.strip() for i in text.split(',') if i.strip()]
            log.append(f'delimiter: , → {len(items)} items')
        text = '\n'.join(items)

    elif chunk_type == 'datalist':
        items = [i.strip() for i in text.split(',') if i.strip()]
        log.append(f'split on , → {len(items)} options: {items}')
        text = ', '.join(items)

    elif chunk_type == 'metadata':
        pairs = {}
        for part in text.split(','):
            part = part.strip()
            if ':' in part:
                k, v = part.split(':', 1)
                pairs[k.strip()] = v.strip()
        log.append(f'parsed {len(pairs)} key:value pairs → {list(pairs.keys())}')

    elif chunk_type == 'fenced_frame':
        cleaned = re.sub(r'<[^>]+>', '', text)
        if cleaned != text:
            log.append('stripped HTML tags from input')
            text = cleaned
        else:
            log.append('no HTML tags — passthrough')

    else:
        log.append(f'passthrough ({chunk_type})')

    return text, log


def _detect_code_type(code_str):
    """Detect whether a code string is HTML, CSS, Python, or plain text.
    Returns one of: 'html', 'css', 'python', 'text'"""
    s = code_str.strip()
    if not s:
        return 'text'
    # HTML: contains tags like <nav>, <div>, <ul>, <li>
    if re.search(r'<\s*[a-zA-Z][^>]*>', s):
        return 'html'
    # CSS: has selector { property: value; } patterns
    if re.search(r'[\w.#:\-]+\s*\{[^}]*:[^}]*\}', s, re.DOTALL):
        return 'css'
    # Python: def/class/import/print keywords
    if re.search(r'^\s*(def |class |import |from |print\()', s, re.MULTILINE):
        return 'python'
    return 'text'


class App(tk.Tk):

    def __init__(self):
        super().__init__()
        self.title("Modular Event Tracker")
        self.geometry("800x600")
        self.style = ttk.Style(self)
        self.style.configure("TFrame", background="#2B2B2B")
        self.style.configure("TButton", padding=10)
        
        self.notebook = ttk.Notebook(self)
        self.notebook.pack(expand=True, fill='both')

        self.home_frame = HomeFrame(self.notebook)
        self.chunk_view_frame = ChunkView(self.notebook)
        self.analytics_frame = AnalyticsFrame(self.notebook)

        self.notebook.add(self.home_frame, text="Home")
        self.notebook.add(self.chunk_view_frame, text="Chunk View")
        self.notebook.add(self.analytics_frame, text="Analytics")

        self.notebook.bind("<<NotebookTabChanged>>", self.on_tab_change)

        # Track button clicks and interactions
        self.interaction_data = []
        self.windows_created = []
        self.chunks_generated = []

    def on_tab_change(self, event):
        selected_tab = self.notebook.tab(self.notebook.select(), "text")
        if selected_tab == "Chunk View":
            self.chunk_view_frame.display_chunks()  # Populate chunk data
        print(f"Switched to {selected_tab}")

class HomeFrame(ttk.Frame):
    
    def __init__(self, parent):
        super().__init__(parent, padding=20)
        self.label = ttk.Label(self, text="Welcome to the Modular Event Tracker", font=("Helvetica", 16))
        self.label.pack(pady=20)
        self.start_button = ttk.Button(self, text="Start Tracking", command=self.start_tracking)
        self.start_button.pack(pady=20)

    def start_tracking(self):
        print("Tracking started...")

class ChunkView(ttk.Frame):

    def __init__(self, parent):
        super().__init__(parent, padding=20)
        self.label = ttk.Label(self, text="View your data chunks here", font=("Helvetica", 16))
        self.label.pack(pady=20)
        self.chunk_list = tk.Listbox(self, selectmode=tk.MULTIPLE)
        self.chunk_list.pack(pady=10, fill=tk.BOTH, expand=True)

        self.action_button = ttk.Button(self, text="Generate Chunk", command=self.generate_chunk)
        self.action_button.pack(pady=10)

        self.create_window_button = ttk.Button(self, text="Create New Window from Selected Chunks", command=self.create_new_window)
        self.create_window_button.pack(pady=10)

        self.chunks = []  # Store chunk data as dicts

    def display_chunks(self):
        # Logic to display existing chunks
        self.chunk_list.delete(0, tk.END)
        for idx, chunk in enumerate(self.chunks):
            metadata = chunk.get('metadata', {})
            display_text = f"Chunk {idx+1}: {chunk.get('content', 'No content')} | Type: {chunk.get('type', 'N/A')} | Version: {metadata.get('version', 'N/A')}"
            self.chunk_list.insert(tk.END, display_text)

    def generate_chunk(self):
        chunk_id = random.randint(1, 100)
        chunk_type = random.choice(['label', 'button', 'text', 'card', 'paragraph', 'video', 'image_placeholder', 'hero_title', 'navbar', 'banner', 'background_color', 'bidirectional_text', 'code', 'kbd', 'fenced_frame', 'column', 'datalist', 'fieldset', 'preformatted', 'metadata'])
        # Create a richer chunk dictionary
        if chunk_type == 'code':
            text = "def hello_world():\n    print('Hello, World!')"
            code_example = "def create_code_block(code: str) -> None:\n    print(f'Code block: {code}')"
        elif chunk_type == 'kbd':
            text = "Press Ctrl+C to copy"
            code_example = "def handle_kbd_input(key: str) -> None:\n    print(f'Key pressed: {key}')"
        elif chunk_type == 'bidirectional_text':
            text = "Isolated text: Hello"
            code_example = "def isolate_text(text: str) -> str:\n    return f'<bdi>{text}</bdi>'"
        elif chunk_type == 'fenced_frame':
            text = "Fenced content placeholder"
            code_example = "def create_fenced_frame(content: str) -> None:\n    print(f'Fenced frame: {content}')"
        elif chunk_type == 'column':
            text = "Item 1\nItem 2\nItem 3"
            code_example = "def create_column(items: list) -> None:\n    for item in items:\n        print(item)"
        elif chunk_type == 'datalist':
            text = "Option 1, Option 2, Option 3"
            code_example = "def create_datalist(options: list) -> None:\n    print(f'Datalist options: {options}')"
        elif chunk_type == 'fieldset':
            text = "Fieldset label"
            code_example = "def create_fieldset(label: str, content: str) -> None:\n    print(f'Fieldset: {label} - {content}')"
        elif chunk_type == 'preformatted':
            text = "Preformatted\ntext\nhere"
            code_example = "def create_preformatted(text: str) -> None:\n    print(f'<pre>{text}</pre>')"
        elif chunk_type == 'metadata':
            text = "Metadata: Version 1.0"
            code_example = "def add_metadata(version: str) -> None:\n    print(f'Metadata version: {version}')"
        else:
            text = f"Chunk {chunk_id} content: {random.choice(['Welcome message', 'Interactive button', 'Detailed paragraph with markup', 'Video embed placeholder'])}"
            code_example = f"def create_{chunk_type}(text: str) -> None:\n    print(f'Creating {chunk_type}: {{text}}')"

        chunk = {
            'id': chunk_id,
            'type': chunk_type,
            'content': f"Generated data {chunk_id}",
            'text': text,
            'style': {
                'background': random.choice(['#f0f0f0', 'linear-gradient(to right, #ff7e5f, #feb47b)', '#2B2B2B']),
                'color': random.choice(['black', 'white', '#007bff']),
                'font': ('Helvetica', random.randint(10, 16)),
                'border': random.choice([None, '2px solid #007bff'])
            },
            'events': {
                'hover': random.choice([None, 'highlight_border', 'change_color'])
            },
            'hyperlinks': [
                {'text': 'Example Link', 'url': 'https://example.com'} if random.random() > 0.5 else {}
            ],
            'analytics': {
                'visits': random.randint(0, 1000),
                'pages_visited': random.sample(['Home', 'Chunk View', 'Analytics'], random.randint(1, 3)),
                'user': f"User{random.randint(1, 10)}",
                'runtime_data': f"{random.randint(1, 60)}s",
                'last_run': time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(time.time() - random.randint(0, 86400)))
            },
            'parameters': {
                'label': random.choice(['Send Request', 'Submit Complaint', 'Interactive Element']),
                'action': random.choice(['send_request', 'submit_complaint', 'toggle_visibility'])
            },
            'annotations': f"str: {chunk_type} content, int: id={chunk_id}",
            'code_example': code_example,
            'metadata': {
                'version': '1.0',
                'created_at': time.strftime('%Y-%m-%d %H:%M:%S'),
                'author': 'System'
            }
        }
        self.chunks.append(chunk)
        self.chunk_list.insert(tk.END, f"Chunk {len(self.chunks)}: {chunk['content']} ({chunk['type']})")
        app = self.winfo_toplevel()
        app.chunks_generated.append(f"generated: {len(self.chunks)} [{chunk['type']}, {chunk['content']}, {chunk['text']}]")
        app.interaction_data.append(f"Button pressed: Generate Chunk at {time.strftime('%H:%M:%S')}")
        print(f"Chunk generated: {chunk_id}")

    def create_new_window(self):
        selected_indices = self.chunk_list.curselection()
        if not selected_indices:
            print("No chunks selected to create window.")
            return
        new_window = tk.Toplevel(self)
        new_window.title("New Window from Chunks")
        new_window.geometry("600x400")

        # Make it scrollable
        canvas = tk.Canvas(new_window)
        scrollbar = ttk.Scrollbar(new_window, orient="vertical", command=canvas.yview)
        scrollable_frame = ttk.Frame(canvas)

        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )

        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)

        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        # Add export button at the bottom
        export_button = ttk.Button(scrollable_frame, text="Export This Window to HTML", command=lambda: self.export_window_to_html(selected_indices))
        export_button.pack(pady=10)

        for idx in selected_indices:
            chunk = self.chunks[idx]
            widget_type = chunk.get('type')
            text = chunk.get('text', '')
            style = chunk.get('style', {})
            events = chunk.get('events', {})
            hyperlinks = chunk.get('hyperlinks', [])
            analytics = chunk.get('analytics', {})
            parameters = chunk.get('parameters', {})
            annotations = chunk.get('annotations', '')
            code_example = chunk.get('code_example', '')

            # Create widget based on type
            if widget_type == 'label':
                lbl = ttk.Label(scrollable_frame, text=text, font=style.get('font', ('Helvetica', 12)), foreground=style.get('color', 'black'))
                lbl.pack(pady=5, fill='x')
                if events.get('hover') == 'highlight_border':
                    lbl.bind("<Enter>", lambda e, l=lbl: l.config(relief='solid', borderwidth=2))
                    lbl.bind("<Leave>", lambda e, l=lbl: l.config(relief='flat', borderwidth=0))
            elif widget_type == 'button':
                btn = ttk.Button(scrollable_frame, text=parameters.get('label', text), command=lambda t=text, a=parameters.get('action'): print(f"Action: {a}, Text: {t}"))
                btn.pack(pady=5)
                if events.get('hover') == 'change_color':
                    btn.bind("<Enter>", lambda e, b=btn: b.config(style='Hover.TButton'))
                    btn.bind("<Leave>", lambda e, b=btn: b.config(style='TButton'))
            elif widget_type == 'text':
                txt = tk.Text(scrollable_frame, height=3, width=50, font=style.get('font', ('Helvetica', 12)), bg=_safe_tk_color(style.get('background'), 'white'), fg=style.get('color', 'black'))
                txt.insert(tk.END, text)
                txt.pack(pady=5, fill='x')
            elif widget_type == 'card':
                card_frame = ttk.Frame(scrollable_frame, relief='raised', borderwidth=2)
                card_frame.pack(pady=5, fill='x', padx=10)
                card_label = ttk.Label(card_frame, text=text, font=style.get('font', ('Helvetica', 14, 'bold')), foreground=style.get('color', 'black'))
                card_label.pack(pady=5)
                # Add analytics
                analytics_label = ttk.Label(card_frame, text=f"Visits: {analytics.get('visits', 0)}, User: {analytics.get('user', 'Unknown')}")
                analytics_label.pack()
            elif widget_type == 'paragraph':
                para_frame = ttk.Frame(scrollable_frame)
                para_frame.pack(pady=5, fill='x')
                para_text = tk.Text(para_frame, height=5, width=50, font=style.get('font', ('Helvetica', 12)), wrap='word')
                para_text.insert(tk.END, text)
                para_text.pack(fill='x')
                # Add hyperlinks
                for link in hyperlinks:
                    if link:
                        link_label = ttk.Label(para_frame, text=link['text'], foreground='blue', cursor='hand2')
                        link_label.pack()
                        link_label.bind("<Button-1>", lambda e, u=link['url']: print(f"Open URL: {u}"))
            elif widget_type == 'video':
                video_label = ttk.Label(scrollable_frame, text=f"Video: {text} (URL placeholder)", font=style.get('font', ('Helvetica', 12)))
                video_label.pack(pady=5)
            elif widget_type == 'image_placeholder':
                img_label = ttk.Label(scrollable_frame, text="[Image Placeholder]", font=style.get('font', ('Helvetica', 12)))
                img_label.pack(pady=5)
            elif widget_type == 'hero_title':
                hero_label = ttk.Label(scrollable_frame, text=text, font=('Helvetica', 24, 'bold'), foreground=style.get('color', 'black'))
                hero_label.pack(pady=5)
            elif widget_type == 'navbar':
                nav_label = ttk.Label(scrollable_frame, text="Navbar: Home | About | Contact", font=style.get('font', ('Helvetica', 12)), foreground=style.get('color', 'black'))
                nav_label.pack(pady=5)
            elif widget_type == 'banner':
                banner_label = ttk.Label(scrollable_frame, text=text, font=('Helvetica', 18, 'bold'), foreground=style.get('color', 'black'), background=_safe_tk_color(style.get('background'), '#f0f0f0'))
                banner_label.pack(pady=5, fill='x')
            elif widget_type == 'background_color':
                bg_label = ttk.Label(scrollable_frame, text=f"Background Color: {style.get('background', '#ffffff')}", font=style.get('font', ('Helvetica', 12)))
                bg_label.pack(pady=5)
            elif widget_type == 'bidirectional_text':
                bdi_label = ttk.Label(scrollable_frame, text=text, font=style.get('font', ('Helvetica', 12)), foreground=style.get('color', 'black'))
                bdi_label.pack(pady=5, fill='x')
            elif widget_type == 'code':
                code_text = tk.Text(scrollable_frame, height=5, width=50, font=('Courier', 12), bg=_safe_tk_color(style.get('background'), 'white'), fg=style.get('color', 'black'))
                code_text.insert(tk.END, text)
                code_text.pack(pady=5, fill='x')
            elif widget_type == 'kbd':
                kbd_label = ttk.Label(scrollable_frame, text=text, font=style.get('font', ('Helvetica', 12)), foreground=style.get('color', 'black'), relief='raised', borderwidth=1)
                kbd_label.pack(pady=5)
            elif widget_type == 'fenced_frame':
                fenced_label = ttk.Label(scrollable_frame, text=text, font=style.get('font', ('Helvetica', 12)), foreground=style.get('color', 'black'), relief='solid', borderwidth=2)
                fenced_label.pack(pady=5, fill='x')
            elif widget_type == 'column':
                column_list = tk.Listbox(scrollable_frame, height=5)
                for item in text.split('\n'):
                    column_list.insert(tk.END, item)
                column_list.pack(pady=5, fill='x')
            elif widget_type == 'datalist':
                datalist_combo = ttk.Combobox(scrollable_frame, values=text.split(', '))
                datalist_combo.set("Select option")
                datalist_combo.pack(pady=5, fill='x')
            elif widget_type == 'fieldset':
                fieldset_frame = ttk.Frame(scrollable_frame, relief='ridge', borderwidth=2)
                fieldset_frame.pack(pady=5, fill='x')
                fieldset_label = ttk.Label(fieldset_frame, text=text, font=style.get('font', ('Helvetica', 12, 'bold')))
                fieldset_label.pack(anchor='w')
                fieldset_entry = ttk.Entry(fieldset_frame)
                fieldset_entry.pack(fill='x')
            elif widget_type == 'preformatted':
                pre_text = tk.Text(scrollable_frame, height=5, width=50, font=('Courier', 12), bg=_safe_tk_color(style.get('background'), 'white'), fg=style.get('color', 'black'))
                pre_text.insert(tk.END, text)
                pre_text.pack(pady=5, fill='x')
            elif widget_type == 'metadata':
                metadata = chunk.get('metadata', {})
                meta_label = ttk.Label(scrollable_frame, text=f"Version: {metadata.get('version', 'N/A')}, Created: {metadata.get('created_at', 'N/A')}, Author: {metadata.get('author', 'N/A')}", font=('Helvetica', 10))
                meta_label.pack(pady=5)
            else:
                lbl = ttk.Label(scrollable_frame, text=f"Unknown chunk type: {widget_type}")
                lbl.pack(pady=5)

            # Display annotations and code example
            if annotations:
                anno_label = ttk.Label(scrollable_frame, text=f"Annotations: {annotations}", font=('Helvetica', 10, 'italic'))
                anno_label.pack(pady=2)
            if code_example:
                code_text = tk.Text(scrollable_frame, height=4, width=50, font=('Courier', 10))
                code_text.insert(tk.END, code_example)
                code_text.pack(pady=2)

        app = self.winfo_toplevel()
        app.windows_created.append(f"Window created with chunks: {[self.chunks[idx]['type'] for idx in selected_indices]} at {time.strftime('%H:%M:%S')}")
        app.interaction_data.append(f"Button pressed: Create New Window at {time.strftime('%H:%M:%S')}")
        print(f"New window created with {len(selected_indices)} chunks.")

    def export_window_to_html(self, selected_indices):
        self.open_custom_input_window(selected_indices)

    def open_custom_input_window(self, selected_indices):
        input_window = tk.Toplevel(self)
        input_window.title("Customize Chunks for HTML Export")
        input_window.geometry("500x400")

        canvas = tk.Canvas(input_window)
        scrollbar = ttk.Scrollbar(input_window, orient="vertical", command=canvas.yview)
        scrollable_frame = ttk.Frame(canvas)

        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )

        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)

        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        custom_entries = {}
        code_entries = {}
        for idx in selected_indices:
            chunk = self.chunks[idx]
            frame = ttk.Frame(scrollable_frame)
            frame.pack(pady=5, fill='x')
            ttk.Label(frame, text=f"Customize {chunk['type'].capitalize()}:").pack(anchor='w')
            entry = ttk.Entry(frame)
            entry.insert(0, chunk['text'])
            entry.pack(fill='x')
            custom_entries[idx] = entry
            # Editable code_example / dev note
            if chunk.get('code_example'):
                ttk.Label(frame, text="  Dev note (code example):", font=('Helvetica', 8, 'italic')).pack(anchor='w')
                code_entry = tk.Text(frame, height=3, width=50, font=('Courier', 8))
                code_entry.insert(tk.END, chunk['code_example'])
                code_entry.pack(fill='x', pady=2)
                code_entries[idx] = code_entry

        def submit():
            custom_data = {idx: entry.get() for idx, entry in custom_entries.items()}
            self.generate_html_with_custom(selected_indices, custom_data)
            input_window.destroy()

        def submit_structured():
            custom_data = {idx: entry.get() for idx, entry in custom_entries.items()}
            code_custom = {idx: widget.get('1.0', tk.END).strip() for idx, widget in code_entries.items()}
            self.build_structured_page(selected_indices, custom_data, code_custom)
            input_window.destroy()

        ttk.Button(scrollable_frame, text="Generate HTML", command=submit).pack(pady=10)
        ttk.Button(scrollable_frame, text="Build Structured Page", command=submit_structured).pack(pady=5)

    def generate_html_with_custom(self, selected_indices, custom_data):
        html_content = """
        <!DOCTYPE html>
        <html lang="en">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>Custom Window Chunks Report</title>
            <style>
                body { font-family: Arial, sans-serif; margin: 20px; }
                .chunk { margin: 10px 0; padding: 5px; border-left: 3px solid #007bff; }
                h1 { color: #333; }
            </style>
        </head>
        <body>
            <h1>Custom Window Chunks</h1>
        """
        for idx in selected_indices:
            chunk = self.chunks[idx]
            custom_text = custom_data.get(idx, chunk['text'])
            chunk_type = chunk['type']
            if chunk_type == 'code':
                html_content += f"<div class='chunk'><strong>{chunk_type.capitalize()}:</strong> <code>{custom_text}</code></div>"
            elif chunk_type == 'kbd':
                html_content += f"<div class='chunk'><strong>{chunk_type.capitalize()}:</strong> <kbd>{custom_text}</kbd></div>"
            elif chunk_type == 'preformatted':
                html_content += f"<div class='chunk'><strong>{chunk_type.capitalize()}:</strong> <pre>{custom_text}</pre></div>"
            elif chunk_type == 'column':
                items = custom_text.split('\n')
                html_content += f"<div class='chunk'><strong>{chunk_type.capitalize()}:</strong> <ul>"
                for item in items:
                    html_content += f"<li>{item}</li>"
                html_content += "</ul></div>"
            elif chunk_type == 'datalist':
                options = custom_text.split(', ')
                html_content += f"<div class='chunk'><strong>{chunk_type.capitalize()}:</strong> <datalist id='datalist-{idx}'>"
                for option in options:
                    html_content += f"<option value='{option}'>"
                html_content += "</datalist></div>"
            elif chunk_type == 'fieldset':
                html_content += f"<div class='chunk'><fieldset><legend>{custom_text}</legend><input type='text' /></fieldset></div>"
            elif chunk_type == 'metadata':
                metadata = chunk.get('metadata', {})
                html_content += f"<div class='chunk'><meta name='version' content='{metadata.get('version', 'N/A')}' /><meta name='author' content='{metadata.get('author', 'N/A')}' /><strong>{chunk_type.capitalize()}:</strong> {custom_text}</div>"
            elif chunk_type == 'bidirectional_text':
                html_content += f"<div class='chunk'><strong>{chunk_type.capitalize()}:</strong> <bdi>{custom_text}</bdi></div>"
            elif chunk_type == 'fenced_frame':
                html_content += f"<div class='chunk'><strong>{chunk_type.capitalize()}:</strong> <div style='border: 2px solid #000; padding: 10px;'>{custom_text}</div></div>"
            else:
                html_content += f"<div class='chunk'><strong>{chunk_type.capitalize()}:</strong> {custom_text}</div>"
        # Append developer notes (annotations + code_example) as a comment block
        html_content += '\n<!-- DEVELOPER NOTES\n'
        for idx in selected_indices:
            chunk = self.chunks[idx]
            html_content += f'[{chunk["type"]} id={chunk["id"]}]\n'
            if chunk.get('annotations'):
                html_content += f'  annotations: {chunk["annotations"]}\n'
            if chunk.get('code_example'):
                html_content += f'  code:\n{chunk["code_example"]}\n'
            html_content += '\n'
        html_content += '-->\n'
        html_content += "</body></html>"
        with open("custom_window_chunks.html", 'w', encoding='utf-8') as f:
            f.write(html_content)
        print("Exported custom window chunks to custom_window_chunks.html")

    def build_structured_page(self, selected_indices, custom_data, code_custom=None):
        """Apply per-type transformers to selected chunks and assemble a structured HTML page."""
        if code_custom is None:
            code_custom = {}
        slots = {
            'bg_color': '#1a1a2e',
            'navbar_items': [],
            'banner': None,
            'hero_title': None,
            'paragraphs': [],
            'button': None,
            'image_placeholder': None,
            'cards': [],
            'fenced_frames': [],
            'bdi_texts': [],
            'preformatted': None,
            'labels': [],
            'texts': [],
            'kbd_items': [],
            'column_items': [],
            'datalist_options': [],
            'metadata_pairs': {},
            'dev_notes': [],
            'code_overrides': {},
        }
        transform_log = []

        for idx in selected_indices:
            chunk = self.chunks[idx]
            chunk_type = chunk['type']
            raw_text = custom_data.get(idx, chunk['text'])
            transformed, log = _transform_chunk_text(chunk_type, raw_text)

            transform_log.append({
                'type': chunk_type, 'id': chunk['id'],
                'raw': raw_text, 'result': transformed, 'log': log
            })

            if chunk.get('annotations') or chunk.get('code_example'):
                raw_code = code_custom.get(idx, chunk.get('code_example', ''))
                code_lang = _detect_code_type(raw_code)
                slots['dev_notes'].append({
                    'type': chunk_type,
                    'id': chunk['id'],
                    'annotations': chunk.get('annotations', ''),
                    'code_example': raw_code,
                    'lang': code_lang,
                })
                # If user typed actual HTML/CSS, store it as a page override for this type
                if code_lang in ('html', 'css'):
                    slots['code_overrides'][chunk_type] = {
                        'lang': code_lang,
                        'code': raw_code,
                    }

            if chunk_type == 'background_color':
                slots['bg_color'] = transformed
            elif chunk_type == 'navbar':
                slots['navbar_items'] = [i.strip() for i in transformed.split('|') if i.strip()]
            elif chunk_type == 'banner':
                slots['banner'] = transformed
            elif chunk_type == 'hero_title':
                slots['hero_title'] = transformed
            elif chunk_type == 'paragraph':
                slots['paragraphs'].append(transformed)
            elif chunk_type == 'button':
                slots['button'] = transformed
            elif chunk_type == 'image_placeholder':
                slots['image_placeholder'] = transformed
            elif chunk_type == 'card':
                slots['cards'].append(transformed)
            elif chunk_type == 'fenced_frame':
                slots['fenced_frames'].append(transformed)
            elif chunk_type == 'bidirectional_text':
                slots['bdi_texts'].append(transformed)
            elif chunk_type == 'preformatted':
                slots['preformatted'] = transformed
            elif chunk_type == 'label':
                slots['labels'].append(transformed)
            elif chunk_type == 'text':
                slots['texts'].append(transformed)
            elif chunk_type == 'kbd':
                slots['kbd_items'].append(transformed)
            elif chunk_type == 'column':
                slots['column_items'] = [i.strip() for i in transformed.split('\n') if i.strip()]
            elif chunk_type == 'datalist':
                slots['datalist_options'] = [i.strip() for i in transformed.split(',') if i.strip()]
            elif chunk_type == 'metadata':
                for part in transformed.split(','):
                    if ':'  in part:
                        k, v = part.split(':', 1)
                        slots['metadata_pairs'][k.strip()] = v.strip()

        # ── Transform log as HTML comment ──────────────────────────────
        log_comment = '<!--\nTRANSFORM LOG\n'
        for entry in transform_log:
            log_comment += f'  [{entry["type"]} id={entry["id"]}]\n'
            log_comment += f'    raw:    {str(entry["raw"])[:80]}\n'
            log_comment += f'    result: {str(entry["result"])[:80]}\n'
            for note in entry['log']:
                log_comment += f'    rule:   {note}\n'
        log_comment += '-->\n'

        # ── Build HTML sections ────────────────────────────────────────
        bg = slots['bg_color']
        meta_tags = ''.join(
            f'    <meta name="{k.lower()}" content="{v}">\n'
            for k, v in slots['metadata_pairs'].items()
        )
        nav_override = slots['code_overrides'].get('navbar')
        if nav_override and nav_override['lang'] == 'html':
            # User supplied raw HTML — inject it directly, stripping outer <nav> if present
            nav_inner = nav_override['code']
            nav_section = f'    <!-- navbar: user-supplied HTML -->\n    {nav_inner}'
        else:
            nav_links = '\n'.join(
                f'            <li><a href="#">{item}</a></li>'
                for item in (slots['navbar_items'] or ['Home', 'About', 'Contact'])
            )
            nav_section = f'''    <nav>\n        <span class="brand">Psyclect</span>\n        <ul>\n{nav_links}\n        </ul>\n    </nav>'''
        col_items_html = '\n'.join(
            f'                <li class="{"active" if i == 0 else ""}">  {item}</li>'
            for i, item in enumerate(slots['column_items'])
        ) if slots['column_items'] else '                <li class="active">Dashboard</li>'
        dl_options_html = '\n'.join(
            f'                    <option value="{o}">{o}</option>'
            for o in slots['datalist_options']
        )
        cards_html = ''.join(
            f'\n            <div class="card">\n                <div class="card-body"><h2>{c}</h2></div>\n                <span class="card-badge">chunk</span>\n            </div>'
            for c in slots['cards']
        )
        texts_html = ''.join(
            f'            <div class="text-block"><p>{t}</p></div>\n'
            for t in slots['texts']
        )
        kbd_html = ''.join(
            f'            <div class="kbd-block"><kbd>{k}</kbd></div>\n'
            for k in slots['kbd_items']
        )
        fenced_html = ''.join(
            f'\n            <div class="fenced-frame" data-sandbox="{i+1}">\n                <span class="fenced-label">{"PRIMARY" if i == 0 else f"SANDBOX {i+1}"}</span>\n                <p>{ff}</p>\n            </div>'
            for i, ff in enumerate(slots['fenced_frames'])
        )
        bdi_html = ''.join(
            f'            <div class="bdi-notice">&#127760;&nbsp;<bdi>{t}</bdi></div>\n'
            for t in slots['bdi_texts']
        )
        pre_html = (
            f'            <div class="pre-block"><pre>{slots["preformatted"]}</pre></div>'
            if slots['preformatted'] else ''
        )
        labels_html = ''.join(
            f'            <p class="label-tag">{lbl}</p>\n'
            for lbl in slots['labels']
        )
        para_html = '<br>'.join(slots['paragraphs']) if slots['paragraphs'] else 'Explore the platform below.'
        hero_title = slots['hero_title'] or 'Welcome'
        btn_text = slots['button'] or 'Get Started'
        img_text = slots['image_placeholder'] or 'Hero banner &mdash; 1200&times;400px recommended'
        banner_html = f'    <div class="banner">{slots["banner"]}</div>' if slots['banner'] else ''

        # Collect any CSS overrides the user typed into dev note fields
        extra_css = ''
        for ctype, ov in slots['code_overrides'].items():
            if ov['lang'] == 'css':
                extra_css += f'\n        /* user override: {ctype} */\n'
                # indent each line to match the style block
                for line in ov['code'].splitlines():
                    extra_css += f'        {line}\n'
        dev_notes_html = ''
        if slots['dev_notes']:
            lang_colors = {'html': '#e34c26', 'css': '#563d7c', 'python': '#3572A5', 'text': '#555577'}
            notes_inner = ''.join(
                f'\n            <div class="dev-note">\n'
                f'                <span class="dev-type">{n["type"]}</span>'
                f'<span class="dev-lang" style="background:{lang_colors.get(n["lang"],"#555577")}">{n["lang"].upper()}</span>\n'
                f'                <p class="dev-annotation">{n["annotations"]}</p>\n'
                f'                <pre class="dev-code">{n["code_example"]}</pre>\n'
                f'            </div>'
                for n in slots['dev_notes']
            )
            dev_notes_html = f'    <section class="dev-notes"><h2>Developer Notes</h2>{notes_inner}\n    </section>'

        page = f'''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{hero_title}</title>
{meta_tags}    <style>
        *, *::before, *::after {{ box-sizing: border-box; margin: 0; padding: 0; }}
        body {{ font-family: \'Segoe UI\', Arial, sans-serif; background-color: {bg}; color: #e0e0e0; min-height: 100vh; }}
        nav {{ background: #12122a; border-bottom: 2px solid #007bff; padding: 0 40px; display: flex; align-items: center; justify-content: space-between; height: 60px; position: sticky; top: 0; z-index: 100; }}
        nav .brand {{ font-size: 1.2rem; font-weight: 700; color: #007bff; letter-spacing: 1px; }}
        nav ul {{ list-style: none; display: flex; gap: 32px; }}
        nav ul li a {{ color: #cdd6f4; text-decoration: none; font-size: 0.95rem; transition: color 0.2s; }}
        nav ul li a:hover {{ color: #007bff; }}
        .banner {{ background: linear-gradient(135deg, #007bff 0%, #6610f2 100%); text-align: center; padding: 14px 20px; font-size: 1rem; font-weight: 500; color: #fff; }}
        .hero {{ text-align: center; padding: 80px 20px 50px; }}
        .hero h1 {{ font-size: 3rem; font-weight: 800; color: #fff; margin-bottom: 20px; }}
        .hero p {{ font-size: 1.15rem; color: #a6adc8; max-width: 600px; margin: 0 auto 32px; line-height: 1.75; }}
        .btn-primary {{ background: #007bff; color: #fff; border: none; padding: 14px 36px; font-size: 1rem; font-weight: 600; border-radius: 6px; cursor: pointer; text-decoration: none; display: inline-block; transition: background 0.2s; }}
        .btn-primary:hover {{ background: #0056b3; }}
        .image-placeholder {{ margin: 0 40px 50px; height: 220px; background: #252545; border: 2px dashed #444466; border-radius: 10px; display: flex; align-items: center; justify-content: center; color: #555577; font-size: 0.95rem; }}
        .layout {{ display: flex; gap: 30px; padding: 0 40px 60px; max-width: 1200px; margin: 0 auto; }}
        .sidebar {{ width: 220px; flex-shrink: 0; }}
        .sidebar h3 {{ font-size: 0.75rem; text-transform: uppercase; letter-spacing: 1.5px; color: #555577; margin-bottom: 12px; }}
        .sidebar ul {{ list-style: none; }}
        .sidebar ul li {{ padding: 10px 14px; border-radius: 6px; color: #a6adc8; font-size: 0.9rem; cursor: pointer; margin-bottom: 4px; transition: background 0.15s; }}
        .sidebar ul li:hover, .sidebar ul li.active {{ background: #252545; color: #007bff; }}
        .sidebar ul li.active {{ font-weight: 600; }}
        .nav-select-wrap {{ margin-top: 24px; }}
        .nav-select-wrap label {{ display: block; font-size: 0.75rem; text-transform: uppercase; letter-spacing: 1px; color: #555577; margin-bottom: 8px; }}
        .nav-select-wrap select {{ width: 100%; padding: 8px 10px; background: #252545; border: 1px solid #444466; border-radius: 6px; color: #e0e0e0; font-size: 0.9rem; }}
        .content {{ flex: 1; min-width: 0; }}
        .label-tag {{ color: #a6adc8; font-size: 0.9rem; margin-bottom: 8px; font-style: italic; }}
        .card {{ background: #252545; border: 1px solid #333355; border-radius: 10px; padding: 28px 30px; margin-bottom: 24px; display: flex; align-items: flex-start; justify-content: space-between; gap: 20px; }}
        .card-body h2 {{ font-size: 1.3rem; color: #fff; margin-bottom: 8px; }}
        .card-badge {{ background: #007bff22; color: #007bff; border: 1px solid #007bff55; border-radius: 20px; padding: 4px 14px; font-size: 0.8rem; white-space: nowrap; font-weight: 600; }}
        .fenced-frame {{ border: 2px solid #444466; border-radius: 10px; padding: 28px 24px 20px; background: #1e1e38; margin-bottom: 24px; position: relative; }}
        .fenced-label {{ position: absolute; top: -10px; left: 16px; background: {bg}; padding: 0 8px; font-size: 0.7rem; letter-spacing: 2px; color: #555577; }}
        .fenced-frame p {{ color: #a6adc8; font-size: 0.95rem; line-height: 1.6; }}
        .bdi-notice {{ background: #252545; border-left: 4px solid #6610f2; border-radius: 0 8px 8px 0; padding: 12px 18px; margin-bottom: 24px; font-size: 0.9rem; color: #a6adc8; }}
        .bdi-notice bdi {{ color: #cdd6f4; font-style: italic; }}
        .pre-block {{ background: #0d0d1a; border: 1px solid #333355; border-radius: 8px; padding: 20px 24px; margin-bottom: 24px; }}
        .pre-block pre {{ font-family: \'Courier New\', monospace; font-size: 0.9rem; color: #a6f0a6; line-height: 1.8; white-space: pre; }}
        .dev-notes {{ margin: 0 40px 40px; border-top: 1px solid #252545; padding-top: 30px; }}
        .dev-notes h2 {{ color: #555577; font-size: 0.75rem; text-transform: uppercase; letter-spacing: 2px; margin-bottom: 20px; }}
        .dev-note {{ background: #0d0d1a; border: 1px solid #333355; border-radius: 8px; padding: 16px 20px; margin-bottom: 16px; }}
        .dev-type {{ background: #252545; color: #007bff; font-size: 0.75rem; padding: 2px 10px; border-radius: 10px; font-weight: 600; display: inline-block; margin-bottom: 8px; }}
        .dev-annotation {{ color: #555577; font-size: 0.8rem; font-style: italic; margin: 6px 0; }}
        .dev-code {{ font-family: \'Courier New\', monospace; font-size: 0.8rem; color: #a6f0a6; white-space: pre; margin-top: 8px; }}
        .dev-lang {{ font-size: 0.7rem; padding: 2px 8px; border-radius: 10px; color: #fff; font-weight: 600; display: inline-block; margin-left: 6px; margin-bottom: 8px; vertical-align: middle; }}
        .text-block {{ background: #252545; border-radius: 8px; padding: 16px 20px; margin-bottom: 16px; color: #cdd6f4; font-size: 0.95rem; line-height: 1.7; }}
        .kbd-block {{ margin-bottom: 12px; }}
        kbd {{ background: #12122a; border: 1px solid #444466; border-bottom: 3px solid #333355; border-radius: 5px; padding: 4px 10px; font-family: \'Courier New\', monospace; font-size: 0.85rem; color: #cdd6f4; }}
        footer {{ text-align: center; padding: 24px; border-top: 1px solid #252545; color: #555577; font-size: 0.8rem; }}{extra_css}
    </style>
</head>
<body>
{log_comment}
{nav_section}

{banner_html}

    <section class="hero">
        <h1>{hero_title}</h1>
        <p>{para_html}</p>
        <a href="#" class="btn-primary">{btn_text}</a>
    </section>

    <div class="image-placeholder">&#128444;&nbsp; {img_text}</div>

    <div class="layout">
        <aside class="sidebar">
            <h3>Navigate</h3>
            <ul>
{col_items_html}
            </ul>
            <div class="nav-select-wrap">
                <label for="section-select">Jump to section</label>
                <select id="section-select">
{dl_options_html}
                </select>
            </div>
        </aside>
        <main class="content">
{labels_html}{cards_html}
{texts_html}
{kbd_html}
{fenced_html}
{bdi_html}
{pre_html}
        </main>
    </div>

{dev_notes_html}

    <footer>&copy; 2026 Psyclect &mdash; Built with the Chunk Builder</footer>
</body>
</html>'''

        with open('custom_window_page.html', 'w', encoding='utf-8') as f:
            f.write(page)
        print('Built structured page → custom_window_page.html')

class AnalyticsFrame(ttk.Frame):

    def __init__(self, parent):
        super().__init__(parent, padding=20)
        self.label = ttk.Label(self, text="Analytics", font=("Helvetica", 16))
        self.label.pack(pady=20)
        self.analytics_display = tk.Text(self, height=15, width=50)
        self.analytics_display.pack(pady=10)

        self.format_label = ttk.Label(self, text="Save/Load Format:")
        self.format_label.pack(pady=5)
        self.format_combo = ttk.Combobox(self, values=['.json', '.txt', '.db'], state='readonly')
        self.format_combo.set('.json')
        self.format_combo.pack(pady=5)

        self.save_button = ttk.Button(self, text="Save Analytics", command=self.save_analytics)
        self.save_button.pack(pady=10)

        self.load_button = ttk.Button(self, text="Load Analytics", command=self.load_analytics)
        self.load_button.pack(pady=10)

        self.export_html_button = ttk.Button(self, text="Export to HTML", command=self.export_to_html)
        self.export_html_button.pack(pady=10)

        self.analytics_data = {}

    def collect_session_data(self):
        # Collect data from the app
        app = self.winfo_toplevel()
        data = {
            'chunks_generated': app.chunks_generated,
            'windows_created': app.windows_created,
            'interactions': app.interaction_data,
            'chunks': app.chunk_view_frame.chunks,
            'developer_notes': "Session upgrades: Enhanced chunk dictionaries with styling, analytics, hyperlinks, parameters, annotations, and code examples. Added scrollable new window creation with hover effects and interactive elements. New chunk types: bidirectional_text, code, kbd, fenced_frame, column, datalist, fieldset, preformatted, metadata."
        }
        return data

    def save_analytics(self):
        format_type = self.format_combo.get()
        data = self.collect_session_data()
        filename = f"analytics{format_type}"
        if format_type == '.json':
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=4)
        elif format_type == '.txt':
            with open(filename, 'w', encoding='utf-8') as f:
                f.write(str(data))
        elif format_type == '.db':
            conn = sqlite3.connect(filename)
            c = conn.cursor()
            c.execute('''CREATE TABLE IF NOT EXISTS analytics (key TEXT, value TEXT)''')
            for key, value in data.items():
                c.execute("INSERT INTO analytics VALUES (?, ?)", (key, str(value)))
            conn.commit()
            conn.close()
        print(f"Analytics saved to {filename}")

    def load_analytics(self):
        # Display current session data instead of loading from file
        data = self.collect_session_data()
        self.analytics_display.delete(1.0, tk.END)
        self.analytics_display.insert(tk.END, json.dumps(data, indent=4))
        print("Current session analytics displayed.")

    def export_to_html(self):
        app = self.winfo_toplevel()
        html_content = """
        <!DOCTYPE html>
        <html lang="en">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>Windows Report</title>
            <style>
                body { font-family: Arial, sans-serif; margin: 20px; }
                .window { border: 1px solid #ccc; margin: 20px 0; padding: 10px; }
                .chunk { margin: 10px 0; padding: 5px; border-left: 3px solid #007bff; }
                h1 { color: #333; }
                h2 { color: #555; }
            </style>
        </head>
        <body>
            <h1>Generated Windows Report</h1>
        """
        for window_info in app.windows_created:
            html_content += f"<div class='window'><h2>{window_info}</h2>"
            # Extract chunk types from window_info
            import re
            chunk_types = re.findall(r"'(\w+)'", window_info)
            for chunk_type in chunk_types:
                # Find matching chunks
                for chunk in app.chunk_view_frame.chunks:
                    if chunk['type'] == chunk_type:
                        html_content += f"<div class='chunk'><strong>{chunk['type'].capitalize()}:</strong> {chunk['text']}</div>"
                        break
            html_content += "</div>"
        html_content += "</body></html>"
        with open("windows_report.html", 'w', encoding='utf-8') as f:
            f.write(html_content)
        print("Exported windows to windows_report.html")

if __name__ == "__main__":
    app = App()
    app.mainloop()