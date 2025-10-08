"""UI overlay module for Whisper Typer UI."""

import tkinter as tk
from pathlib import Path
from typing import Callable

from PIL import Image

from utils import IconType


class UIOverlay:
    """Circular overlay UI window."""
    
    def __init__(self, size: int = 240, margin: int = 20):
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
        padding = 30  # Increased for larger UI
        self.circle_id = self.canvas.create_oval(
            padding, padding,
            size - padding, size - padding,
            outline='red',
            width=9  # Increased from 3 to 9 (3x)
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
        # Schedule in tkinter's main thread
        self.window.after(0, self._do_show)
    
    def _do_show(self) -> None:
        """Actually show the window (called in main thread)."""
        self.window.deiconify()
        self.window.lift()
        # Update position after showing (window needs to be visible to get correct screen dimensions)
        self._position_window()
        self.window.update_idletasks()
    
    def hide(self) -> None:
        """Make window invisible."""
        # Schedule in tkinter's main thread
        self.window.after(0, self._do_hide)
    
    def _do_hide(self) -> None:
        """Actually hide the window (called in main thread)."""
        self.window.withdraw()
    
    def set_icon(self, icon_type: IconType) -> None:
        """Change displayed icon.
        
        Args:
            icon_type: Icon to display
        """
        # Schedule in tkinter's main thread
        self.window.after(0, lambda: self._do_set_icon(icon_type))
    
    def _do_set_icon(self, icon_type: IconType) -> None:
        """Actually set the icon (called in main thread)."""
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
            # Use LANCZOS for high-quality resampling (fallback to BICUBIC if not available)
            try:
                resample_method = Image.Resampling.LANCZOS
            except AttributeError:
                resample_method = Image.LANCZOS
            image = image.resize((icon_size, icon_size), resample_method)
            
            # Convert to PNG in memory and use tkinter's PhotoImage
            # This avoids PIL ImageTk threading issues
            import io
            buffer = io.BytesIO()
            image.save(buffer, format='PNG')
            buffer.seek(0)
            
            self._photo_image = tk.PhotoImage(data=buffer.getvalue())
            
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
            import traceback
            traceback.print_exc()
    
    def start_pulsation(self) -> None:
        """Begin pulsating border animation."""
        # Schedule in tkinter's main thread
        self.window.after(0, self._do_start_pulsation)
    
    def _do_start_pulsation(self) -> None:
        """Actually start pulsation (called in main thread)."""
        self.pulsating = True
        self._pulsate()
    
    def stop_pulsation(self) -> None:
        """Stop pulsating border animation."""
        # Schedule in tkinter's main thread
        self.window.after(0, self._do_stop_pulsation)
    
    def _do_stop_pulsation(self) -> None:
        """Actually stop pulsation (called in main thread)."""
        self.pulsating = False
        if self._pulsation_job:
            self.window.after_cancel(self._pulsation_job)
            self._pulsation_job = None
        # Reset to default width (3x larger)
        self.canvas.itemconfig(self.circle_id, width=9)
        # Reset pulsation direction
        if hasattr(self, '_pulsation_direction'):
            delattr(self, '_pulsation_direction')
    
    def _pulsate(self) -> None:
        """Pulsation animation step."""
        if not self.pulsating:
            return
        
        # Smooth pulsation between width 6 and 15 (3x larger)
        current_width = float(self.canvas.itemcget(self.circle_id, 'width'))
        
        # Toggle between widths for smooth pulsation
        if not hasattr(self, '_pulsation_direction'):
            self._pulsation_direction = 1  # 1 = growing, -1 = shrinking
        
        # Increment/decrement width
        if current_width >= 15:
            self._pulsation_direction = -1
        elif current_width <= 6:
            self._pulsation_direction = 1
        
        new_width = current_width + (1.5 * self._pulsation_direction)  # 3x step size
        self.canvas.itemconfig(self.circle_id, width=new_width)
        
        # Schedule next pulsation (100ms = 10 FPS for smoother animation)
        self._pulsation_job = self.window.after(100, self._pulsate)
    
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
    
    def set_border_color(self, color: str) -> None:
        """Set the border color.
        
        Args:
            color: Color name (e.g., 'red', 'blue', 'green')
        """
        self.window.after(0, lambda: self.canvas.itemconfig(self.circle_id, outline=color))
    
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
