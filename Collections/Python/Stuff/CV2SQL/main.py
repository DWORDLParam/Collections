
import xml.etree.ElementTree as ET
import os
import sys
from string import ascii_letters, whitespace, digits, punctuation
from stuff import (
    find_xsi,
    check_replacement,
    get_schema,
    get_parameters,
    make_new_element,
    ifnone_to_str,
    remove_prefix,
    make_new_rest_element,
    make_alias,
    make_new_input,
    pull_parameter_value,
    stage_formula,
    format_filter
)
from produser import produce_query, DataBlock, Rank
from converters import format_formula
from variables import fstrict_mode, set_active_schema, file_max_size

"""
Данная утилита предназначена для конвертации xml файла содержащего метаданные CV (calculation view) БД HANA в формат SQL 
"""

def get_file_list(folder_name, extention) -> list:
    result = []
    for filename in os.listdir(folder_name):
        file_path = os.path.join(folder_name, filename)
        if os.path.isfile(file_path) and (file_path[-4:] == extention):
            result.append([file_path, filename])
    return result


def parse_str(root, xsi) -> str:
    nodes = []
    params = []
    get_parameters(root, params)

    for rl in root:
        if rl.tag == 'viewNode':

            db1 = DataBlock()
            db1.name = rl.get('name')
            db1.type = rl.get(xsi + 'type')
            for sr in rl:
                elem = make_new_element()

                if sr.tag == 'element':
                    elem['name'] = sr.get('name')
                    elem['agg'] = sr.get('aggregationBehavior')
                    elem['atype'] = sr.get('engineAggregation')
                    rsf = ifnone_to_str(sr.get('restricted'), '')

                    typ = sr.find('inlineType')
                    if typ is not None:
                        elem['ctype'] = typ.get('primitiveType')

                    clc = sr.find('calculationDefinition')
                    if clc is not None:
                        fml = clc.find('formula')
                        elem['formula'] = format_formula(fml.text.replace('\r\n', ' '), fstrict_mode)

                    eas = sr.find('exceptionAggregationStep')
                    if eas is not None:
                        elem['exagg'] = eas.get('exceptionAggregationBehavior')
                        for reasl in eas:
                            elem['reelm'].append(remove_prefix(reasl.text, '', db1.name + '/'))

                    if rsf == 'true':
                        for rse in sr:
                            if rse.tag == 'restriction':
                                rest = make_new_rest_element()
                                rest['restelm'] = remove_prefix(rse.get('element'), '', db1.name + '/')
                                for rvl in rse:
                                    if rvl.tag == 'valueFilter':
                                        rest['restvalue'].append([rvl.get('including') == 'true', rvl.get('value')])
                                elem['rest'].append(rest)

                    if elem.get('name') != '':
                        db1.elements.append(elem)

                if sr.tag == 'input':
                    ph = remove_prefix(sr.find('entity').text) if sr.find('entity') is not None else ''
                    bn = remove_prefix(sr.find('viewNode').text) if sr.find('viewNode') is not None else ''
                    al = ifnone_to_str(sr.get('alias'), '')
                    als = al if al != '' else make_alias(db1.type, bn)
                    items = []
                    for ur in sr:
                        einput = make_new_input()
                        if ur.get('targetName') is not None:
                            einput['source'] = ur.get('sourceName')
                            einput['target'] = ur.get('targetName')
                            einput['path'] = ph if ph != '' else bn
                            einput['alias'] = als
                            if ur.get('value') != '':
                                isnull = ur.get('null') == 'true'
                                einput['value'] = ur.get('value') if not isnull else 'NULL'
                        if ur.get('parameterName') is not None:
                            einput['parameter'] = ur.get('parameterName')
                            einput['target'] = ur.get('parameterNameOtherView')
                            einput['path'] = ph
                            einput['alias'] = als
                            einput['value'] = pull_parameter_value(einput['parameter'], params)
                        if einput.get('target') != '':
                            items.append(einput)
                    if len(items) > 0:
                        db1.inputs.append(items)

                if sr.tag == 'filterExpression':
                    db1.filter = format_formula(stage_formula(format_filter(sr.find('formula').text, params), fstrict_mode), fstrict_mode)

                if sr.tag == 'elementFilter':
                    scol = sr.get('elementName')
                    ef = sr.find('valueFilter')
                    if ef is not None:
                        flttype = ef.get(xsi + 'type')
                        incld = ef.get('including')
                        fcind = db1.find_element(scol)
                        if fcind != -1:
                            if flttype == 'Column:SingleValueFilter':
                                value = ifnone_to_str(ef.get('value'), '')
                                operator = ifnone_to_str(ef.get('operator'), '')  # "NL"
                                if db1.elements[fcind]['ctype'] == 'NVARCHAR':
                                    sf = '"' + scol + '" = \'' + value + '\'' if value != '' else '"' + scol + '" IS NULL' if operator == 'NL' else ''
                                else:
                                    sf = '"' + scol + '" = ' + value if value != '' else '"' + scol + '" IS NULL' if operator == 'NL' else ''
                            elif flttype == 'Column:RangeValueFilter':
                                lowValue = ef.get('lowValue')
                                highValue = ef.get('highValue')
                                if incld == 'true':
                                    sf = '("' + scol + '" >= ' + lowValue + ' AND "' + scol + '" <= ' + highValue + ')'
                                else:
                                    sf = '("' + scol + '" > ' + lowValue + ' AND "' + scol + '" < ' + highValue + ')'
                            elif flttype == 'Column:ListValueFilter':
                                vl = [vl1.get('value') + ', ' for vl1 in ef]
                                sf = ''.join(s for s in vl)
                                sf = '("' + scol + '" IN (' + sf[:-2] + '))'
                            else:
                                sf = ''
                        else:
                            sf = ''
                        db1.filter += sf if db1.filter == '' else ' AND (' + sf + ')' if sf != '' else ''

                if sr.tag == 'join':
                    db1.join.left_table = remove_prefix(sr.get('leftInput'))
                    db1.join.right_table = remove_prefix(sr.get('rightInput'))
                    db1.join.type = sr.get('joinType')
                    for jsd in sr:
                        if jsd.tag == 'leftElementName':
                            db1.join.left_fields.append(jsd.text)
                        if jsd.tag == 'rightElementName':
                            db1.join.right_fields.append(jsd.text)

                if sr.tag == 'windowFunction':
                    if True:
                        func = Rank()
                        func.name = 'RANK'
                        for pre in sr:
                            if pre.tag == 'partitionElement':
                                func.partition.append(remove_prefix(pre.text).replace(db1.name + '/', ''))
                        for fnc in sr:
                            if fnc.tag == 'order':
                                func.order.append(
                                    remove_prefix(fnc.get('byElement')).replace(db1.name + '/', '') + ' ' + fnc.get(
                                        'direction'))
                        db1.ranks.append(func)

            db1.correct_inputs()
            db1.inject_alias()
            db1.correct_joins()
            nodes.append(db1)

    return produce_query(nodes)


def main():

    try:
        from_folder = sys.argv[1] if len(sys.argv) > 1 else os.getcwd()
        save_folder = sys.argv[2] if len(sys.argv) > 2 else os.getcwd()
        good_chars = (ascii_letters + punctuation + digits + whitespace).encode()
        junk_chars = bytearray(set(range(0x100)) - set(good_chars))
        file_list = get_file_list(from_folder,'.xml')
        if len(file_list) == 0:
            print(f'Папка {from_folder} не содержит xml файлов')
            return

        for f1 in file_list:
            try:
                rfile = open(f1[0], 'r')
                s1 = rfile.read(file_max_size)
                s2 = s1.encode('ascii', 'ignore').translate(None, junk_chars).decode()
                rfile.close()

                fxsi = find_xsi(s2)
                elm_root = ET.fromstring(check_replacement(s2, True))
                set_active_schema(get_schema(elm_root))
                sql_text = parse_str(elm_root, fxsi)

                base_name, _ = os.path.splitext(f1[1])
                sql_file = base_name + '.sql'
                save_path = os.path.join(save_folder, sql_file)
                with open(save_path, 'w', encoding='utf-8') as sfile:
                    sfile.write(sql_text)
                print(f'Файл {sql_file} успешно сохранен')
            except Exception as e1:
                print(f'Файл {f1[1]} не был сохранен из-за ошибки: {e1}')
                continue

    except Exception as e2:
        print(f'В приложении возникла ошибка: {e2}')
        return

if __name__ == '__main__':
    main()

