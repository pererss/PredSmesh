from aiogram.fsm.state import State, StatesGroup


class IdeaForm(StatesGroup):
    waiting_for_text = State()
