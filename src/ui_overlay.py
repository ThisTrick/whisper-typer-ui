"""UI overlay module for Whisper Typer UI."""

import tkinter as tk
from pathlib import Path
from typing import Callable

from PIL import Image, ImageTk

from utils import IconType


class UIOverlay:
    """Circular overlay UI window."""
    
    def __init__(self, size: int = 80, margin: int = 20):
        """Initialize UI overlay window.
        
        Args:
            size: Diameter of circular overlay in pixels
            margin: Margin from screen edge in pixels
        """
        self.size = size
        self.margin = margin
        
        # Create root window
        self.window = tk.Tk()
        self.window.title("Whisper Typer")
        
        # Configure window properties
        self.window.attributes('-topmost', True)  # Always on top
        self.window.attributes('-alpha', 0.9)     # Semi-transparent
        self.window.overrideredirect(True)        # No window decorations
        
        # Position in bottom-right corner
        self._position_window()
        
        # Create canvas for drawing
        self.canvas = tk.Canvas(
            self.window,
            width=size,
            height=size,
            highlightthickness=0,
            bg='gray15'
        )
        self.canvas.pack()
        
        # Draw circle outline
        padding = 10
        self.circle_id = self.canvas.create_oval(
            padding, padding,
            size - padding, size - padding,
            outline='red',
            width=3
        )
        
        # Icon placeholder
        self.icon_id = None
        self.current_icon: IconType | None = None
        self._photo_image = None  # Keep reference to prevent garbage collection
        
        # Pulsation state
        self.pulsating = False
        self._pulsation_job = None
        
        # Click callback
        self.click_callback: Callable[[], None] | None = None
        self.canvas.bind('<Button-1>', self._on_click)
        
        # Start hidden
        self.window.withdraw()
    
    def _position_window(self) -> None:
        """Position window in bottom-right corner of screen."""
        self.window.update_idletasks()
        screen_width = self.window.winfo_screenwidth()
        screen_height = self.window.winfo_screenheight()
        
        x = screen_width - self.size - self.margin
        y = screen_height - self.size - self.margin
        
        self.window.geometry(f'{self.size}x{self.size}+{x}+{y}')
    
    def show(self) -> None:
        """Make window visible."""
        self.window.deiconify()
        self.window.lift()
    
    def hide(self) -> None:
        """Make window invisible."""
        self.window.withdraw()
    
    def set_icon(self, icon_type: IconType) -> None:
        """Change displayed icon.
        
        Args:
            icon_type: Icon to display
        """
        self.current_icon = icon_type
        
        # Load icon image
        icon_path = Path(icon_type.value)
        if not icon_path.exists():
            print(f"Warning: Icon file not found: {icon_path}")
            return
        
        try:
            image = Image.open(str(icon_path))  # Convert Path to string
            # Resize to fit inside circle
            icon_size = int(self.size * 0.5)
            image = image.resize((icon_size, icon_size), Image.Resampling.LANCZOS)
            self._photo_image = ImageTk.PhotoImage(image)
            
            # Remove old icon if exists
            if self.icon_id:
                self.canvas.delete(self.icon_id)
            
            # Create new icon in center
            center = self.size // 2
            self.icon_id = self.canvas.create_image(
                center, center,
                image=self._photo_image
            )
        except Exception as e:
            print(f"Error loading icon {icon_path}: {e}")
    
    def start_pulsation(self) -> None:
        """Begin pulsating border animation."""
        self.pulsating = True
        self._pulsate()
    
    def stop_pulsation(self) -> None:
        """Stop pulsating border animation."""
        self.pulsating = False
        if self._pulsation_job:
            self.window.after_cancel(self._pulsation_job)
            self._pulsation_job = None
        # Reset to default width
        self.canvas.itemconfig(self.circle_id, width=3)
    
    def _pulsate(self) -> None:
        """Pulsation animation step."""
        if not self.pulsating:
            return
        
        # Toggle between width 3 and 6
        current_width = float(self.canvas.itemcget(self.circle_id, 'width'))
        new_width = 6 if current_width == 3.0 else 3
        self.canvas.itemconfig(self.circle_id, width=new_width)
        
        # Schedule next pulsation (500ms = 2 Hz)
        self._pulsation_job = self.window.after(500, self._pulsate)
    
    def show_error(self, message: str, duration: float = 2.5) -> None:
        """Display error briefly.
        
        Args:
            message: Error message to display
            duration: Display duration in seconds
        """
        self.show()
        self.set_icon(IconType.ERROR)
        # TODO: Could add text display for message
        
        # Auto-dismiss after duration
        self.window.after(int(duration * 1000), self.hide)
    
    def set_click_callback(self, callback: Callable[[], None]) -> None:
        """Set callback for click events.
        
        Args:
            callback: Function to call when overlay is clicked
        """
        self.click_callback = callback
    
    def _on_click(self, event) -> None:
        """Handle click events."""
        if self.click_callback:
            self.click_callback()
    
    def run(self) -> None:
        """Start tkinter main loop (blocking)."""
        self.window.mainloop()
