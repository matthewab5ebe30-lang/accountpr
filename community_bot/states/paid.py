from aiogram.fsm.state import State, StatesGroup


class PaidAnnouncementState(StatesGroup):
    choose_chat = State()
    waiting_text = State()
    waiting_payment = State()
