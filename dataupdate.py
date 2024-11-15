import tkinter as tk
from tkinter import ttk
import random, time

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
        self.chunk_list = tk.Listbox(self)
        self.chunk_list.pack(pady=10)

        self.action_button = ttk.Button(self, text="Generate Chunk", command=self.generate_chunk)
        self.action_button.pack(pady=10)

    def display_chunks(self):
        # Logic to display existing chunks
        pass

    def generate_chunk(self):
        chunk_id = random.randint(1, 100)
        self.chunk_list.insert(tk.END, f"Chunk {chunk_id}: Some generated data")
        print(f"Chunk generated: {chunk_id}")

class AnalyticsFrame(ttk.Frame):

    def __init__(self, parent):
        super().__init__(parent, padding=20)
        self.label = ttk.Label(self, text="Analytics", font=("Helvetica", 16))
        self.label.pack(pady=20)
        self.analytics_display = tk.Text(self, height=15, width=50)
        self.analytics_display.pack(pady=10)

        self.load_button = ttk.Button(self, text="Load Analytics", command=self.load_analytics)
        self.load_button.pack(pady=10)

    def load_analytics(self):
        # This would load analytics data
        self.analytics_display.insert(tk.END, "Loaded analytics data...\n")
        print("Analytics loaded.")

if __name__ == "__main__":
    app = App()
    app.mainloop()