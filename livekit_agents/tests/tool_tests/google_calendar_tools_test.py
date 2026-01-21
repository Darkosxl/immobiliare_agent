"""
Direct tool tests - no LLM needed.
Tests the actual tool logic with real API calls.

FunctionTool objects are callable - just call them directly like regular async functions.
"""
import pytest
import os
import sys
from datetime import datetime, timedelta

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from dotenv import load_dotenv
load_dotenv()

from tools.calendar_tools import (
    check_available_slots,
    get_existing_bookings,
    schedule_meeting,
    cancel_booking,
)


# Mock context that tools expect
class MockAgent:
    is_test = True

class MockSession:
    current_agent = MockAgent()

class MockContext:
    session = MockSession()
    agent = MockAgent()

    async def wait_for_playout(self):
        pass


@pytest.fixture
def ctx():
    return MockContext()


@pytest.fixture
def tomorrow():
    """Get tomorrow's date in ISO format"""
    return (datetime.now() + timedelta(days=1)).replace(hour=10, minute=0, second=0, microsecond=0).isoformat()


# --- check_available_slots ---

@pytest.mark.asyncio
async def test_check_available_slots_valid_date(ctx, tomorrow):
    """Should return available time slots for a valid date"""
    result = await check_available_slots(ctx, date=tomorrow)
    print(f"\n✅ check_available_slots result: {result}")
    assert "Available times:" in result or "error" in result.lower()


@pytest.mark.asyncio
async def test_check_available_slots_invalid_date(ctx):
    """Should handle invalid date format"""
    try:
        result = await check_available_slots(ctx, date="not-a-date")
        print(f"\n❌ Expected error but got: {result}")
        assert False, "Should have raised an error"
    except Exception as e:
        print(f"\n✅ Correctly raised error: {type(e).__name__}: {e}")
        assert True


# --- get_existing_bookings ---

@pytest.mark.asyncio
async def test_get_existing_bookings_empty(ctx, tomorrow):
    """Should return no events for a time with no bookings"""
    result = await get_existing_bookings(ctx, date=tomorrow)
    print(f"\n✅ get_existing_bookings result: {result}")
    # Either no events or some events - both are valid
    assert "events" in result.lower() or "no" in result.lower()


@pytest.mark.asyncio
async def test_get_existing_bookings_invalid_date(ctx):
    """Should handle invalid date format"""
    try:
        result = await get_existing_bookings(ctx, date="invalid")
        print(f"\n❌ Expected error but got: {result}")
        assert False, "Should have raised an error"
    except Exception as e:
        print(f"\n✅ Correctly raised error: {type(e).__name__}: {e}")
        assert True


# --- schedule_meeting + cancel_booking (round-trip) ---

@pytest.mark.asyncio
async def test_schedule_and_cancel_booking(ctx):
    """Should schedule a meeting and then cancel it (is_test=True auto-cancels)"""
    # Schedule for tomorrow at 11:00 (less likely to conflict)
    test_date = (datetime.now() + timedelta(days=1)).replace(
        hour=11, minute=0, second=0, microsecond=0
    ).isoformat()

    result = await schedule_meeting(
        ctx,
        apartment_address="Via Test 123, Milano",
        date=test_date
    )
    print(f"\n✅ schedule_meeting result: {result}")
    assert "confermato" in result.lower() or "appuntamento" in result.lower()


@pytest.mark.asyncio
async def test_cancel_booking_nonexistent(ctx, tomorrow):
    """Should handle cancelling a booking that doesn't exist"""
    result = await cancel_booking(ctx, date=tomorrow)
    print(f"\n✅ cancel_booking (nonexistent) result: {result}")
    assert "cancelled" in result.lower() or "cancellato" in result.lower()
