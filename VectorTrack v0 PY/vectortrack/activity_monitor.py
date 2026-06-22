"""
Activity monitoring module for tracking user input and determining active status.
"""

from datetime import datetime, timedelta
from typing import Optional, Callable
from pynput import mouse, keyboard
import threading
from loguru import logger
import os

class ActivityMonitor:
    def __init__(self, idle_timeout_seconds: int = 300):
        self.idle_timeout = timedelta(seconds=idle_timeout_seconds)
        self.last_activity = datetime.now()
        self.is_monitoring = False
        self._mouse_listener: Optional[mouse.Listener] = None
        self._keyboard_listener: Optional[keyboard.Listener] = None
        self._activity_callbacks: list[Callable[[bool], None]] = []
        self._lock = threading.Lock()
        self._check_thread: Optional[threading.Thread] = None
        self._last_state = True  # Track last activity state
        self._last_debug_time = datetime.now()  # For throttling debug logs
        
    def start(self):
        """Start monitoring user activity."""
        if self.is_monitoring:
            logger.info("ActivityMonitor is already running.")
            return
            
        self.is_monitoring = True
        self.last_activity = datetime.now()
        
        try:
            if os.environ.get("VECTORTRACK_TESTING") == "1":
                logger.info("Test mode: Skipping input listeners but assigning dummy listeners.")
                DummyListener = type("DummyListener", (), {"stop": lambda self: None})
                self._mouse_listener = DummyListener()
                self._keyboard_listener = DummyListener()
            else:
                # Start input listeners
                self._mouse_listener = mouse.Listener(
                    on_move=self._on_activity,
                    on_click=self._on_activity,
                    on_scroll=self._on_activity
                )
                self._keyboard_listener = keyboard.Listener(
                    on_press=self._on_activity,
                    on_release=self._on_activity
                )

                self._mouse_listener.start()
                self._keyboard_listener.start()
            
            # Start the idle checker thread
            self._check_thread = threading.Thread(target=self._check_idle_loop, daemon=True)
            self._check_thread.start()
            
            logger.info("Activity monitoring started")
        except Exception as e:
            logger.error(f"Failed to start activity monitoring: {e}")
            self.is_monitoring = False
            raise
        
    def stop(self):
        """Stop monitoring user activity."""
        self.is_monitoring = False
        
        if self._mouse_listener:
            try:
                self._mouse_listener.stop()
            except Exception:
                pass
            self._mouse_listener = None
            
        if self._keyboard_listener:
            try:
                self._keyboard_listener.stop()
            except Exception:
                pass
            self._keyboard_listener = None
            
        if self._check_thread is not None:
            if self._check_thread.is_alive():
                self._check_thread.join(timeout=1)
            self._check_thread = None
        
        logger.info("Activity monitoring stopped")
        
    def _on_activity(self, *args):
        """Called when any input activity is detected."""
        with self._lock:
            current_time = datetime.now()
            was_idle = (current_time - self.last_activity) > self.idle_timeout
            self.last_activity = current_time
            
            # Only log debug messages every 5 seconds to reduce spam
            if current_time - self._last_debug_time > timedelta(seconds=5):
                logger.debug(f"Activity detected - Was idle: {was_idle}")
                self._last_debug_time = current_time
                
            if was_idle:
                self._notify_activity_change(True)
                
    def _check_idle_loop(self):
        """Background thread to check for idle state transitions."""
        while self.is_monitoring:
            current_time = datetime.now()
            with self._lock:
                time_since_activity = current_time - self.last_activity
                is_idle = time_since_activity > self.idle_timeout
                
                # Only notify if state changed
                if is_idle != self._last_state:
                    if is_idle:
                        logger.info(f"[STATUS] Idle timeout reached - No activity for {time_since_activity.total_seconds():.1f} seconds")
                    self._notify_activity_change(not is_idle)
                    self._last_state = is_idle
                    
            threading.Event().wait(1.0)  # Check every second
            
    def _notify_activity_change(self, is_active: bool):
        """Notify all registered callbacks of activity state change."""
        current_time = datetime.now()
        time_since_activity = current_time - self.last_activity
        
        if is_active:
            logger.info(f"[STATUS] Activity resumed after {time_since_activity.total_seconds():.1f} seconds of inactivity")
        else:
            logger.info(f"[STATUS] Entering idle state - Inactive for {time_since_activity.total_seconds():.1f} seconds")
            
        for callback in self._activity_callbacks:
            try:
                callback(is_active)
            except Exception as e:
                logger.error(f"Error in activity callback: {e}")
                
    def add_activity_callback(self, callback: Callable[[bool], None]):
        """Add a callback to be notified of activity state changes."""
        self._activity_callbacks.append(callback)
        logger.debug("Added activity callback")
        
    def remove_activity_callback(self, callback: Callable[[bool], None]):
        """Remove a previously registered callback."""
        if callback in self._activity_callbacks:
            self._activity_callbacks.remove(callback)
            logger.debug("Removed activity callback")
            
    def is_active(self) -> bool:
        """Check if the user is currently active."""
        is_active = (datetime.now() - self.last_activity) <= self.idle_timeout
        logger.debug(f"Checking active status: {is_active}")
        return is_active
        
    def set_idle_timeout(self, seconds: int):
        """Update the idle timeout duration."""
        self.idle_timeout = timedelta(seconds=seconds)
        logger.info(f"Idle timeout updated to {seconds} seconds") 