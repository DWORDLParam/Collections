
import os
import psycopg2 as pg
from psycopg2.extras import execute_values
import csv
import json
import pandas as pd
import numpy

from psycopg2.extensions import register_adapter, AsIs
def addapt_numpy_float64(numpy_float64):
    return AsIs(numpy_float64)
def addapt_numpy_int64(numpy_int64):
    return AsIs(numpy_int64)
def addapt_numpy_bool_(bool_):
    return AsIs(bool_)
def addapt_numpy_uint64(uint64):
    return AsIs(uint64)


pg.extensions.register_adapter(dict, pg.extras.Json)
register_adapter(numpy.float64, addapt_numpy_float64)
register_adapter(numpy.int64, addapt_numpy_int64)
register_adapter(numpy.bool_, addapt_numpy_bool_)
register_adapter(numpy.uint64, addapt_numpy_uint64)


folder_path = 'F:\\temp\\mvideo\\9'

NO_ACTION = 0
NEED_RECONNECT = -1
OPERATION_BREAK = -2
MAX_ROWS = 99999

def get_file_list(folder_name,extention,separator) -> list:
    result = []
    ic = 0
    for filename in os.listdir(folder_name):
        file_path = os.path.join(folder_name, filename)
        ic += 1
        if os.path.isfile(file_path) and (file_path[-4:] == extention):
            tab = filename[:-4].split(separator)
            tab.append(filename)
            tab.append(file_path)
            # <- признак ошибки (необходимость реконнекта, и т.д.)
            tab.append(NO_ACTION)
            # <- порядковый номер
            tab.append(ic)
            result.append(tab)

    return result

def fill_whole_table(tab_item, conn) -> bool:
    cur = conn.cursor()
    tab_full_name = tab_item[0] + '.' + tab_item[1]
    sql = f"SELECT * FROM public.truncate_if_exists('{tab_item[0]}','{tab_item[1]}');"

    try:
        cur.execute(sql)
        row = cur.fetchone()
        conn.commit()

        if row[0]:
            #sql = f"copy {tab_full_name} from stdin with csv;"
            sql = f'''copy {tab_full_name} from stdin with (FORMAT csv, DELIMITER ',', QUOTE '"', HEADER FALSE);'''

            with open(tab_item[3], 'r', encoding="utf-8") as f:
                next(f)
                #cur.copy_from(f, tab_full_name, sep=',', null='NULL')
                cur.copy_expert(sql, f)
        conn.commit()
        result = True

    except Exception as e:
        se = '>>> Error ' + tab_full_name
        print(f"{se}: {e}")
        result = False
    finally:
        cur.close()
    return result


def fill_table_row_by_row(tab_item, conn) -> int:
    result = 0
    buffer_size = 10
    cur_size = 0
    cur_pos = 0
    cur = conn.cursor()
    error_list = []
    error_counter = []
    tab_full_name = tab_item[0] + '.' + tab_item[1]
    lc = lines_count(tab_item[3])
    if buffer_size > lc:
        buffer_size = lc

    sql = f"SELECT * FROM public.count_rows_if_exists('{tab_item[0]}','{tab_item[1]}');"
    cur.execute(sql)
    row = cur.fetchone()
    if row[0] == lc:
        print(f"table {str(tab_item[5])}.{tab_full_name} skipped")
        cur.close()
        tab_item[4] = OPERATION_BREAK
        return row[0]
    elif row[0] == -1:
        print(f"table {str(tab_item[5])}.{tab_full_name} not found")
        cur.close()
        tab_item[4] = OPERATION_BREAK
        return result


    try:
        sql = f"SELECT * FROM public.truncate_if_exists('{tab_item[0]}','{tab_item[1]}');"
        cur.execute(sql)
        row = cur.fetchone()
        conn.commit()

        if row[0]:

            df = pd.read_csv(tab_item[3], low_memory=False)
            df = df.replace({numpy.NaN: None})
            fields = ''.join([fnc(f1)+', ' for f1 in df.columns.tolist()])[:-2]
            values = []
            val_line = []

            while cur_pos < len(df):
                val_line.clear()
                result += 1
                cur_size += 1

                for c1 in range(len(df.columns)):
                    x_val = df.iat[cur_pos, c1]
                    # <- обработка отдельных значений здесь
                    x_val = Json_correction(x_val)
                    x_val = Array_correction(x_val)
                    val_line.append(x_val)

                values.append(tuple(val_line))

                last_part = (lc - result) < buffer_size
                if (cur_size >= buffer_size) or last_part:
                    cur_size = 0
                    sql = f'INSERT INTO {tab_full_name} ({fields}) VALUES %s'

                    try:
                        execute_values(cur, sql, values)
                        conn.commit()
                        buffer_size *= 2
                    except Exception as e:
                        error_list.append(f"{str(tab_item[5])}.{tab_full_name} -> {e}")
                        cur.close()
                        conn = reconnect(conn)
                        cur = conn.cursor()
                        tab_item[4] = NEED_RECONNECT
                        error_counter.insert(0,result)
                        cur_pos = cur_pos - buffer_size if (cur_pos - buffer_size) > -1 else -1
                        result = result - buffer_size if (result - buffer_size) > 0 else 0
                        buffer_size = 1

                    values.clear()
                cur_pos += 1

                if len(error_counter) >= 3:
                    if error_counter[0] == error_counter[1] == error_counter[2]:
                        print(f"table {str(tab_item[5])}.{tab_full_name} too many errors")
                        break

        else:
            print(f"table {str(tab_item[5])}.{tab_full_name} not found")

    except Exception as e:
        se = '>>> Error ' + tab_full_name
        print(f"{se}: {e}")
        result = 0
    finally:
        cur.close()

        if len(error_list) > 0:
            efile = open(folder_path +'\\errors_'+tab_item[1]+'.txt','w')
            efile.write("\n".join(error_list))
            efile.close()

    return result


def reconnect(inConn):
    inConn.close()
    return pg.connect(dbname="db", user="user", password="pass", host="1.1.2.1", port="5432")


def lines_count(file_name) -> int:
    try:
        with open(file_name, 'r', encoding='utf-8') as f:
            reader = csv.reader(f)
            return sum(1 for row in reader)-1
    except:
        return MAX_ROWS


def Array_correction(in_value: any) -> any:
    if type(in_value) is str:
        if in_value[:1] == '[' and in_value[-1:] == ']':
            result = '{' + in_value[:-1][1:].replace('"', '').replace('{', '[').replace('}', ']') + '}'
        elif in_value[:2] == '"[' and in_value[-2:] == ']"':
            result = '{' + in_value[:-2][2:].replace('"', '').replace('{', '[').replace('}', ']') + '}'
        else:
            result = in_value
    else:
        result = in_value
    return result


def Json_correction(in_value: any) -> any:
    if type(in_value) is str:
        if in_value[:1] == '{' and in_value[-1:] == '}':
            if in_value.count('"') + in_value.count("'") > 1:
                try:
                    #s1 = in_value.replace('"', '')
                    result = json.loads(in_value.replace('\\', '').replace("'", '"'))
                except:
                    result = '{}'
            else:
                result = in_value
        else:
            result = in_value
    else:
        result = in_value
    return result


def fnc(f_name: str) -> str:
    if ' ' in f_name:
        result = '"'+f_name+'"'
    elif '.' in f_name:
        result = '"'+f_name+'"'
    elif any(c.isupper() for c in f_name):
        result = '"'+f_name+'"'
    elif f_name in ['user', 'date', 'time', 'group']:
        result = '"'+f_name+'"'
    else:
        result = f_name
    return result



file_list = get_file_list(folder_path,'.csv','_D_')
connection = pg.connect(dbname="db", user="user", password="pass", host="1.1.2.1", port="5432")
ii = 0
for itm in file_list:

    if itm[1] != 'extra_data':
        continue

    #if itm[5] <= 1500:
    #    continue

    rc = fill_table_row_by_row(itm, connection)

    if itm[4] == NEED_RECONNECT:
        connection = reconnect(connection)

    if itm[4] != OPERATION_BREAK:
        if rc > 0:
            print(f"table {str(itm[5])}.{itm[1]} saved ({rc} rows committed)")
        else:
            print(f"table {str(itm[5])}.{itm[1]} not saved")

    ii += 1
    if ii >= 2500:
        break

connection.close()

