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
        
        # Create canvas for drawing
        self.canvas = tk.Canvas(
            self.window,
            width=size,
            height=size,
            highlightthickness=0,
            bg='#1a1a1a'  # Dark gray background
        )
        self.canvas.pack()
        
        # Draw circle background (filled)
        padding = 30
        self.bg_circle_id = self.canvas.create_oval(
            padding, padding,
            size - padding, size - padding,
            fill='#2d2d2d',  # Slightly lighter gray for circle background
            outline=''
        )
        
        # Draw main circle outline (constant)
        self.circle_id = self.canvas.create_oval(
            padding, padding,
            size - padding, size - padding,
            outline='#ff4444',  # Brighter red
            width=6
        )
        
        # Draw glow circle outline (for pulsation effect)
        self.glow_circle_id = self.canvas.create_oval(
            padding - 3, padding - 3,
            size - padding + 3, size - padding + 3,
            outline='#ff4444',  # Same color as main circle
            width=3
        )
        # Hide glow initially
        self.canvas.itemconfig(self.glow_circle_id, state='hidden')
        
        # Icon placeholder
        self.icon_id = None
        self.current_icon: IconType | None = None
        self._photo_image = None  # Keep reference to prevent garbage collection
        self._original_image = None  # Keep original PIL image for rotation
        
        # Pulsation state
        self.pulsating = False
        self._pulsation_job = None
        self._current_border_color = '#ff4444'  # Store current border color for glow
        
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
            # Resize to fit inside circle - use smaller size for better proportions
            icon_size = int(self.size * 0.35)  # 35% of window size instead of 50%
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
        # Hide glow circle
        self.canvas.itemconfig(self.glow_circle_id, state='hidden')
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
        """Pulsation animation step with smooth color brightness pulsing."""
        if not self.pulsating:
            return
        
        # Use sine wave for smooth pulsation
        import math
        if not hasattr(self, '_pulsation_time'):
            self._pulsation_time = 0
        
        # Increment time
        self._pulsation_time += 0.12
        
        # Calculate brightness using sine wave (0.5 to 1.0)
        intensity = 0.5 + 0.5 * ((math.sin(self._pulsation_time) + 1) / 2)
        
        # Parse current color and apply brightness
        color = self._current_border_color
        if color.startswith('#') and len(color) == 7:
            # Extract RGB components
            r = int(color[1:3], 16)
            g = int(color[3:5], 16)
            b = int(color[5:7], 16)
            
            # Apply intensity to main circle
            pulse_r = int(r * intensity)
            pulse_g = int(g * intensity)
            pulse_b = int(b * intensity)
            pulse_color = f'#{pulse_r:02x}{pulse_g:02x}{pulse_b:02x}'
            
            # Update main circle with pulsing color (fixed width)
            self.canvas.itemconfig(self.circle_id, outline=pulse_color)
            
            # Glow circle with brighter color (also fixed width)
            glow_intensity = 0.7 + 0.3 * ((math.sin(self._pulsation_time) + 1) / 2)
            glow_r = min(255, int(r * glow_intensity))
            glow_g = min(255, int(g * glow_intensity))
            glow_b = min(255, int(b * glow_intensity))
            glow_color = f'#{glow_r:02x}{glow_g:02x}{glow_b:02x}'
            
            self.canvas.itemconfig(self.glow_circle_id, state='normal', outline=glow_color, width=6)
        
        # Schedule next pulsation (50ms = 20 FPS)
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
            color: Color hex code (e.g., '#ff4444', '#4488ff')
        """
        def _set_color():
            self._current_border_color = color
            self.canvas.itemconfig(self.circle_id, outline=color)
        
        self.window.after(0, _set_color)
    
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
