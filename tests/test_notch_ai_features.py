# tests/test_notch_ai_features.py
import sys
import os
from PySide6.QtWidgets import QApplication
from PySide6.QtCore import Qt, QPoint, QRect

# Ensure project root is on sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

def run_tests():
    app = QApplication.instance() or QApplication(sys.argv)

    from widgets.notch_widget import NotchWidget
    from widgets.notch_ai_chat import NotchMiniAIChat, NotchChatBubble, COPY_SVG, CHECK_SVG
    from utils import config

    print("--- 1. Testing NotchChatBubble copy button ---")
    bubble_user = NotchChatBubble("User question", is_user=True)
    assert not hasattr(bubble_user, "btn_copy"), "User bubble should not have a copy button"

    bubble_ai = NotchChatBubble("Hello! Here is the AI response.", is_user=False)
    assert hasattr(bubble_ai, "btn_copy"), "AI bubble must have a copy button"
    assert bubble_ai.btn_copy is not None, "AI copy button must exist"
    assert bubble_ai.raw_text == "Hello! Here is the AI response."

    # Test copy action
    bubble_ai._copy_message()
    clipboard_text = QApplication.clipboard().text()
    assert clipboard_text == "Hello! Here is the AI response.", f"Expected clipboard text, got: {clipboard_text}"
    assert bubble_ai.btn_copy.svg_template == CHECK_SVG, "Button icon should change to checkmark after copying"
    print("[OK] Copy button copies text to clipboard and shows checkmark successfully!")

    print("--- 2. Testing Notch AI Chat Header & Elements ---")
    notch = NotchWidget()
    notch.show()
    notch.show_ai_chat_in_notch()

    assert notch.ai_chat_in_notch is True, "Notch should be in AI chat mode"
    assert notch.ai_chat_widget.isVisible(), "AI chat widget should be visible"

    # Verify task checkbox rect is registered when painted
    notch.repaint()
    assert hasattr(notch, "notch_ai_close_rect"), "Close rect should exist"
    assert hasattr(notch, "notch_ai_task_cb_rect"), "Task checkbox rect should exist"
    print(f"[OK] AI chat close rect: {notch.notch_ai_close_rect}, task cb rect: {notch.notch_ai_task_cb_rect}")

    print("--- 3. Testing Eye Expressions ---")
    notch.set_ai_thinking_state(True)
    assert notch.ai_is_thinking is True
    assert notch.override_pupil is True
    assert notch.override_pupil_y < 0, "Thinking eyes should look upwards"
    print("[OK] Thinking eyes expression verified!")

    notch.set_ai_thinking_state(False)
    assert notch.ai_is_thinking is False
    assert notch.override_pupil is False

    notch.trigger_ai_response_expression(success=True)
    assert notch.target_half_closed > 0.5, "Response expression should have happy half-closed/smiling eyes"
    print("[OK] Response eyes expression verified!")

    print("--- 4. Testing Glitch-Free Mode Transitions ---")
    # From AI Chat -> Timer
    print("Transitioning from AI Chat to Timer...")
    notch.toggle_notch_timer_standalone()
    assert notch.ai_chat_in_notch is False, "AI chat mode must be False after switching to Timer"
    assert not notch.ai_chat_widget.isVisible(), "AI chat widget must be hidden in Timer mode"
    assert notch.timer_in_notch is True, "Timer mode must be active"
    print("[OK] AI Chat -> Timer transition clean!")

    # From Timer -> AI Chat
    print("Transitioning from Timer to AI Chat...")
    notch.show_ai_chat_in_notch()
    assert notch.ai_chat_in_notch is True
    assert notch.timer_in_notch is False, "Timer mode must be cleared when opening AI chat"
    assert notch.ai_chat_widget.isVisible()
    print("[OK] Timer -> AI Chat transition clean!")

    # From AI Chat -> Notes
    print("Transitioning from AI Chat to Notes...")
    notch.show_notes_in_notch()
    assert notch.ai_chat_in_notch is False, "AI chat mode must be False after switching to Notes"
    assert not notch.ai_chat_widget.isVisible(), "AI chat widget must be hidden in Notes mode"
    assert notch.notes_in_notch is True, "Notes mode must be active"
    print("[OK] AI Chat -> Notes transition clean!")

    # Clean up
    notch.collapse_to_idle(force=True)
    notch.close()
    print("\nALL VERIFICATION TESTS PASSED SUCCESSFULLY!")
    os._exit(0)

if __name__ == "__main__":
    run_tests()
