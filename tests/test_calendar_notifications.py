"""
Test script for the Jupiter Calendar Notification System

Usage:
  python test_calendar_notifications.py

This will create a test notification and display it using all available methods.
"""

import sys
import os
import time
import datetime
import tkinter as tk
import uuid

# Add parent directory to path to allow importing Jupiter modules
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Import calendar components
from utils.calendar.notification_manager import NotificationManager
from utils.calendar.gui_notifications import get_notification_handler as get_gui_handler
from utils.calendar.terminal_notifications import get_notification_handler as get_terminal_handler
from utils.calendar.voice_notifications import get_notification_handler as get_voice_handler

def create_test_notification():
    """Create a test notification"""
    # Generate unique ID
    notification_id = str(uuid.uuid4())
    
    # Create notification data
    notification = {
        'id': notification_id,
        'title': 'Test Calendar Reminder',
        'message': 'This is a test notification to verify that the Jupiter Calendar Notification System is working correctly.',
        'event_id': 'test-event-001',
        'user_id': 'test-user',
        'timestamp': datetime.datetime.now().timestamp()
    }
    
    return notification

def run_gui_test():
    """Run a test with the GUI notification handler"""
    print("Testing GUI notifications...")
    
    # Create a root window
    root = tk.Tk()
    root.title("Calendar Notification Test")
    root.geometry("300x200")
    
    # Create a simple UI
    label = tk.Label(root, text="Testing calendar notifications.\nA notification should appear shortly.")
    label.pack(pady=20)
    
    # Create notification manager
    notification_manager = NotificationManager()
    
    # Register GUI handler
    gui_method, gui_handler = get_gui_handler(root)
    notification_manager.register_delivery_method(gui_method, gui_handler)
    
    # Create a test notification
    notification = create_test_notification()
    
    # Create a button to trigger notification
    def send_notification():
        gui_handler(notification)
        
    button = tk.Button(root, text="Send Notification", command=send_notification)
    button.pack(pady=10)
    
    # Auto-send notification after 2 seconds
    root.after(2000, send_notification)
    
    # Add exit button
    exit_button = tk.Button(root, text="Exit", command=root.destroy)
    exit_button.pack(pady=10)
    
    # Start GUI loop
    root.mainloop()

def run_terminal_test():
    """Run a test with the terminal notification handler"""
    print("Testing terminal notifications...")
    
    # Create notification manager
    notification_manager = NotificationManager()
    
    # Register terminal handler
    term_method, term_handler = get_terminal_handler(None)
    notification_manager.register_delivery_method(term_method, term_handler)
    
    # Create a test notification
    notification = create_test_notification()
    
    # Send notification
    term_handler(notification)
    
    print("Terminal notification sent.")

def run_voice_test():
    """Run a test with the voice notification handler"""
    print("Testing voice notifications...")
    
    # Create notification manager
    notification_manager = NotificationManager()
    
    try:
        # Register voice handler
        voice_method, voice_handler = get_voice_handler()
        notification_manager.register_delivery_method(voice_method, voice_handler)
        
        # Create a test notification
        notification = create_test_notification()
        
        # Send notification
        voice_handler(notification)
        
        print("Voice notification sent.")
        
    except Exception as e:
        print(f"Error testing voice notifications: {e}")

def run_daemon_test():
    """Run a test with the notification daemon"""
    print("Testing notification daemon...")
    
    # Create notification manager
    notification_manager = NotificationManager(check_interval=5)
    
    # Register terminal handler
    term_method, term_handler = get_terminal_handler(None)
    notification_manager.register_delivery_method(term_method, term_handler)
    
    # Start daemon
    notification_manager.start()
    
    print("Notification daemon started.")
    print("Creating test notification for daemon to process...")
    
    # Create a test notification and add to queue
    notification = create_test_notification()
    notification_manager.notification_queue.put(notification)
    
    print("Notification added to queue. Waiting for processing...")
    time.sleep(10)
    
    # Stop daemon
    notification_manager.stop()
    print("Notification daemon stopped.")

def main():
    """Run all tests"""
    print("Jupiter Calendar Notification System Test")
    print("-" * 50)
    
    # Ask which test to run
    print("\nAvailable tests:")
    print("1. GUI Notification Test")
    print("2. Terminal Notification Test")
    print("3. Voice Notification Test")
    print("4. Notification Daemon Test")
    print("5. Run All Tests")
    
    try:
        choice = input("\nEnter your choice (1-5): ")
        
        if choice == '1':
            run_gui_test()
        elif choice == '2':
            run_terminal_test()
        elif choice == '3':
            run_voice_test()
        elif choice == '4':
            run_daemon_test()
        elif choice == '5':
            # Run terminal test first
            run_terminal_test()
            time.sleep(2)
            
            # Run voice test
            run_voice_test()
            time.sleep(2)
            
            # Run daemon test
            run_daemon_test()
            time.sleep(2)
            
            # Run GUI test last (blocks until window closed)
            run_gui_test()
        else:
            print("Invalid choice.")
            
    except KeyboardInterrupt:
        print("\nTest interrupted.")
    
    print("\nTest completed.")

if __name__ == "__main__":
    main()
