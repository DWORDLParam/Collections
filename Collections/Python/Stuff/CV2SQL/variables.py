
default_xsi = '{http://www.w3.org/2001/XMLSchema-instance}'

# Замены текста которые необходимо произвести в xml файле
replace_list = [['"SAPBWD".','"SAPBWP".'],['"SAPBWP".','SAPBWP.']]

# Режим формул  True - формула копируется как есть,  False - фурмула конвертируется согласно SQL стандартам
fstrict_mode = False

# Схема по умолчанию
default_schema = '"_SYS_BIC"'

# Схема которая будет использована в SQL скрипте (не редактируется)
active_schema = ''

# Максимальный размер xml файла
file_max_size = 10000000


def set_active_schema(in_schema: str):
    global active_schema
    active_schema = in_schema


def get_active_schema() -> str:
    return active_schema
