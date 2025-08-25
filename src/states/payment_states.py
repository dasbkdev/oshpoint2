from aiogram.fsm.state import State, StatesGroup

class PaymentStates(StatesGroup):
    WaitingReceipt = State()


class AdminPaymentStates(StatesGroup):
    # Просмотр очереди заявок с пагинацией «« / »»
    Browsing = State()
    # Подтверждение отмены (ввод КАПСОМ "ПОДТВЕРДИТЬ")
    WaitingCancelConfirm = State()
