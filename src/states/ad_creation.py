from aiogram.fsm.state import State, StatesGroup

class AdCreation(StatesGroup):
    Type = State()
    Category = State()
    Subcategory = State()
    Name = State()
    ShortDesc = State()
    Condition = State()
    DetailDesc = State()
    Price = State()
    Delivery = State()   # <--- новый шаг
    City = State()
    Photos = State()
    Preview = State()
