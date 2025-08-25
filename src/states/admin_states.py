from aiogram.fsm.state import State, StatesGroup

class AdminStates(StatesGroup):
    WaitingUserLookup = State()
    WaitingQuotaNumber = State()
    WaitingRulesText = State()
    WaitingLangChoice = State()
