import os
import time
import pytest
from app.services.memory_service import MemoryService


@pytest.fixture
def memory_service(tmp_path):
    db_file = str(tmp_path / "test_memory.db")
    return MemoryService(db_path=db_file)


def test_conversation_history(memory_service):
    user_id = 5556841083
    memory_service.add_message(user_id, "user", "Chào Airi")
    memory_service.add_message(user_id, "assistant", "Chào anh yêu!")

    history = memory_service.get_history(user_id)
    assert len(history) == 2
    assert history[0]["content"] == "Chào Airi"
    assert history[1]["content"] == "Chào anh yêu!"

    memory_service.clear_history(user_id)
    assert len(memory_service.get_history(user_id)) == 0


def test_user_facts(memory_service):
    user_id = 5556841083
    memory_service.save_fact(user_id, "tên_gọi", "anh yêu")
    memory_service.save_fact(user_id, "vai_trò", "chủ nhân")

    facts = memory_service.get_facts(user_id)
    assert facts["tên_gọi"] == "anh yêu"
    assert facts["vai_trò"] == "chủ nhân"

    summary = memory_service.get_facts_summary(user_id)
    assert "tên_gọi: anh yêu" in summary


def test_notes_management(memory_service):
    user_id = 5556841083
    note_id = memory_service.save_note(user_id, "Mua sắm", "Mua sữa và cà phê")
    assert note_id > 0

    notes = memory_service.get_notes(user_id)
    assert len(notes) == 1
    assert notes[0]["title"] == "Mua sắm"
    assert notes[0]["content"] == "Mua sữa và cà phê"

    deleted = memory_service.delete_note(user_id, note_id)
    assert deleted is True
    assert len(memory_service.get_notes(user_id)) == 0


def test_reminders_management(memory_service):
    user_id = 5556841083
    now = time.time()
    # Reminder due now
    r_id = memory_service.add_reminder(user_id, "Họp nhóm", now - 10)

    due = memory_service.get_due_reminders()
    assert len(due) == 1
    assert due[0]["id"] == r_id
    assert due[0]["reminder_text"] == "Họp nhóm"

    memory_service.mark_reminder_sent(r_id)
    assert len(memory_service.get_due_reminders()) == 0
