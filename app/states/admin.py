from aiogram.fsm.state import State, StatesGroup


class RejectReasonForm(StatesGroup):
    waiting_for_custom_reason = State()


class AdminMessageForm(StatesGroup):
    waiting_for_text = State()


class BroadcastForm(StatesGroup):
    waiting_for_text = State()
    confirm = State()


class SettingsForm(StatesGroup):
    waiting_for_value = State()
