"""Text insertion module using keyboard emulation."""

from pynput.keyboard import Controller


class TextInserter:
    """Inserts text via keyboard emulation."""
    
    def __init__(self, typing_speed: int = 100):
        """Initialize text inserter.
        
        Args:
            typing_speed: Characters per second (default 100)
        """
        self.typing_speed = typing_speed
        self.controller = Controller()
    
    def type_text(self, text: str) -> None:
        """Type text into currently focused application.
        
        Args:
            text: Text to type
        """
        if not text:
            return
        
        print(f"Typing {len(text)} characters...")
        
        # Use pynput's type method which handles special characters
        self.controller.type(text)
        
        print("Text insertion complete")
