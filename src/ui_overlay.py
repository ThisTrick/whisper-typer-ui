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
        self.window.overrideredirect(True)        # No window decorations
        
        # Try to make background transparent (platform-specific)
        try:
            # Windows
            self.window.attributes('-transparentcolor', '#1a1a1a')
            self.window.attributes('-alpha', 1.0)
        except:
            # Linux/Mac - use alpha for semi-transparency
            self.window.attributes('-alpha', 0.95)
        
        # Position in bottom-right corner
        self._position_window()
        
        # Create canvas for drawing - minimal size
        canvas_size = size - 40  # Smaller canvas, just for the circle
        self.canvas = tk.Canvas(
            self.window,
            width=canvas_size,
            height=canvas_size,
            highlightthickness=0,
            bg='#1a1a1a'  # Dark gray background
        )
        self.canvas.place(x=20, y=20)  # Center the canvas
        
        # Draw circle background (filled)
        padding = 10
        self.bg_circle_id = self.canvas.create_oval(
            padding, padding,
            canvas_size - padding, canvas_size - padding,
            fill='#2d2d2d',  # Slightly lighter gray for circle background
            outline=''
        )
        
        # Draw circle outline
        self.circle_id = self.canvas.create_oval(
            padding, padding,
            canvas_size - padding, canvas_size - padding,
            outline='#ff4444',  # Brighter red
            width=9
        )
        
        # Icon placeholder
        self.icon_id = None
        self.current_icon: IconType | None = None
        self._photo_image = None  # Keep reference to prevent garbage collection
        self._original_image = None  # Keep original PIL image for rotation
        
        # Pulsation state
        self.pulsating = False
        self._pulsation_job = None
        
        # Rotation state (for processing animation)
        self.rotating = False
        self._rotation_job = None
        self._rotation_angle = 0
        
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
            
            # Store original image for rotation
            self._original_image = image.copy()
            
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
        # Reset to default width
        self.canvas.itemconfig(self.circle_id, width=9)
        # Reset pulsation time
        if hasattr(self, '_pulsation_time'):
            delattr(self, '_pulsation_time')
    
    def start_rotation(self) -> None:
        """Begin rotating icon animation (for processing state)."""
        self.window.after(0, self._do_start_rotation)
    
    def _do_start_rotation(self) -> None:
        """Actually start rotation (called in main thread)."""
        self.rotating = True
        self._rotation_angle = 0
        self._rotate()
    
    def stop_rotation(self) -> None:
        """Stop rotating icon animation."""
        self.window.after(0, self._do_stop_rotation)
    
    def _do_stop_rotation(self) -> None:
        """Actually stop rotation (called in main thread)."""
        self.rotating = False
        if self._rotation_job:
            self.window.after_cancel(self._rotation_job)
            self._rotation_job = None
        self._rotation_angle = 0
    
    def _rotate(self) -> None:
        """Rotation animation step."""
        if not self.rotating or not self.icon_id:
            return
        
        # Rotate icon
        self._rotation_angle = (self._rotation_angle + 10) % 360
        
        # Re-create icon with rotation
        if self.current_icon and self._original_image:
            try:
                # Rotate image
                rotated = self._original_image.rotate(-self._rotation_angle, expand=False)
                
                # Convert to PNG in memory
                import io
                buffer = io.BytesIO()
                rotated.save(buffer, format='PNG')
                buffer.seek(0)
                
                # Update PhotoImage
                self._photo_image = tk.PhotoImage(data=buffer.getvalue())
                
                # Update canvas
                if self.icon_id:
                    self.canvas.itemconfig(self.icon_id, image=self._photo_image)
            except Exception as e:
                print(f"Error rotating icon: {e}")
        
        # Schedule next rotation (30ms = ~33 FPS for smooth rotation)
        self._rotation_job = self.window.after(30, self._rotate)
    
    def _pulsate(self) -> None:
        """Pulsation animation step."""
        if not self.pulsating:
            return
        
        # Use sine wave for smooth pulsation
        import math
        if not hasattr(self, '_pulsation_time'):
            self._pulsation_time = 0
        
        # Increment time
        self._pulsation_time += 0.1
        
        # Calculate width using sine wave (range 6-12 for smooth effect)
        min_width = 6
        max_width = 12
        amplitude = (max_width - min_width) / 2
        offset = (max_width + min_width) / 2
        new_width = offset + amplitude * math.sin(self._pulsation_time)
        
        self.canvas.itemconfig(self.circle_id, width=int(new_width))
        
        # Schedule next pulsation (50ms = 20 FPS for very smooth animation)
        self._pulsation_job = self.window.after(50, self._pulsate)
    
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
