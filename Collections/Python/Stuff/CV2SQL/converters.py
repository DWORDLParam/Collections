
from stuff import single_str


# Конвертирует CASE с языка Calculation Engine в стандартный SQL
def case_to_case(in_str: str) -> str:
    if not 'case' in in_str.lower():
        return in_str

    br1 = -1
    p1 = in_str.lower().find('case')
    for s1 in range(len(in_str)):
        if s1 >= p1 + 4:
            if in_str[s1] == '(':
                br1 = s1
                break
    if br1 == -1:
        return in_str

    c1 = []
    c2 = []
    for s2 in range(len(in_str)):
        if s2 > br1:
            if in_str[s2] == '(':
                c1.append(s2)
    for s3 in range(len(in_str)):
        if s3 > br1:
            if in_str[s3] == ')':
                c2.append(s3)
    if len(c1) >= len(c2):
        return in_str

    for cp in range(len(c1)):
        c2.pop(0)
    br2 = c2[0]

    cr = []
    elval = ''
    ss = in_str[br1 + 1:][:(len(in_str) - br2) * -1]

    while len(ss) > 0:
        if ',' in ss:
            c3 = []
            cmp1 = ss.find(',')
            v1 = single_str(ss[:cmp1].strip())
            ss = ss[cmp1 + 1:].strip()
            c3.append(v1)
            cmp2 = ss.find(',')
            v2 = single_str(ss[:cmp2].strip())
            ss = ss[cmp2 + 1:].strip()
            c3.append(v2)
            cr.append(c3)
        else:
            elval = ss.strip()
            break

    if len(cr) == 0:
        return in_str

    result = 'CASE\n'
    for r1 in cr:
        result += 'WHEN ' + r1[1] + ' THEN ' + r1[0] + '\n'
    result += 'ELSE ' + elval + '\n' if elval != '' else ''
    result += 'END'

    return result


# Конвертирует IF с языка Calculation Engine в стандартный SQL
def if_to_case(in_str: str) -> str:
    def is_it_if(in_str: str, pos: int) -> bool:
        result = False
        chars_after = [' ', '(']
        chars_before = ['', ' ', ',', ')', '(']
        if in_str[pos:][:2].lower() == 'if':
            sample = in_str[pos - 1 if pos - 1 >= 0 else pos:][:4 if pos - 1 >= 0 else 3].lower()
            ca = 0
            cb = 0
            while True:
                if sample == chars_before[cb] + 'if' + chars_after[ca]:
                    result = True
                    break
                ca += 1
                if ca >= len(chars_after):
                    ca = 0
                    cb += 1
                if cb >= len(chars_before):
                    break
        return result

    def find_delimeter(in_str: str, dlm: str) -> int:
        cf = 0
        for ip1 in range(len(in_str)):
            if in_str[ip1] == '(':
                cf += 1
            elif in_str[ip1] == ')':
                cf -= 1

            if (in_str[ip1] == dlm) and (cf == 0):
                return ip1
        return 0

    def post_format(in_str: str) -> str:
        levels = []
        cur_lvl = 0
        new_lvl = 0
        in_str = single_str(in_str.replace('END\n ', 'END '), '\n')
        s_list = in_str.split('\n')
        for i1 in range(len(s_list)):
            if new_lvl != cur_lvl:
                new_lvl = cur_lvl
            fc = s_list[i1].find('CASE') if i1 > 0 else -1
            fe = s_list[i1].find('END')
            if fc >= 0:
                cur_lvl += 5
            elif fe >= 0:
                cur_lvl -= 5
            levels.append([s_list[i1], new_lvl])

        return ''.join(' ' * s1[1] + s1[0] + '\n' for s1 in levels)[:-1]

    result = in_str[:]

    while True:

        br_start = -1
        br_stop = -1
        for ips in range(len(result) - 1, -1, -1):
            if is_it_if(result, ips):
                br_start = ips
                break

        if br_start == -1:
            break

        cs = 0
        br_found = False
        for s2 in range(len(result)):
            if s2 > br_start:
                if result[s2] == '(':
                    cs += 1
                    br_found = True
                elif result[s2] == ')':
                    cs -= 1

            if br_found and (cs == 0):
                br_stop = s2
                break

        if br_stop == -1:
            break

        ss = result[br_start + 2:][:(len(result) - br_stop) * -1].strip()
        sk = find_delimeter(ss, '(')
        if ss[:sk].strip() == '':
            ss = ss[sk + 1:]

        if ',' in ss:
            cmp1 = find_delimeter(ss, ',')
            v1 = single_str(ss[:cmp1].strip())
            ss = ss[cmp1 + 1:].strip(' ')
            cmp2 = find_delimeter(ss, ',')
            v2 = single_str(ss[:cmp2].strip())
            v3 = single_str(ss[cmp2 + 1:].strip())
        else:
            break

        sres = 'CASE\nWHEN ' + v1 + ' THEN ' + v2 + '\n'
        sres += 'ELSE ' + v3 + '\n' if v3 != '' else ''
        sres += 'END\n '

        result = result[:br_start] + sres + result[br_stop + 1:] if br_start > 0 else sres[:-2]

    if result[:4].strip(' ').lower() != 'case':
        result_lines = result.splitlines()
        result = ''.join(s1 + ' ' for s1 in result_lines).strip()
    elif result.count('CASE') > 1:
        result = post_format(result)

    return result


# Конвертирует некоторые функции привидения типов с языка Calculation Engine в стандартный SQL
def convert_to(in_str: str) -> str:
    def found_in(in_str: str, pattern: str) -> str:
        result = ''
        prefix = [' ', ',', '.', '(', ')', '+', '-', '/', '*', ':', '<', '>', '=']
        for p1 in prefix:
            if p1 + pattern.lower() in in_str.lower():
                result = p1
                break
        return result

    result = in_str
    while True:
        f1 = found_in(result, 'int(')
        if f1 != '':
            result = result.upper().replace(f1 + 'INT(', f1 + 'TO_INT(')
        f2 = found_in(result, 'string(')
        if f2 != '':
            result = result.upper().replace(f2 + 'STRING(', f2 + 'TO_STRING(')
        f3 = found_in(result, 'date(')
        if f3 != '':
            result = result.upper().replace(f3 + 'DATE(', f3 + 'TO_DATE(')
        if f1 + f2 + f3 == '':
            break

    return result


# Конвертирует IN с языка Calculation Engine в стандартный SQL
def in_to_in(in_str: str) -> str:
    result = in_str[:]
    if not 'in(' in in_str.lower():
        return in_str

    while True:

        br1 = -1
        p1 = result.lower().find('in(')
        for s1 in range(len(result)):
            if s1 >= p1 + 2:
                if result[s1] == '(':
                    br1 = s1
                    break
        if br1 == -1:
            break

        c1 = [sc1 for sc1 in range(len(result)) if (result[sc1] == '(') and (sc1 > br1)]
        c2 = [sc2 for sc2 in range(len(result)) if (result[sc2] == ')') and (sc2 > br1)]

        if len(c1) >= len(c2):
            break

        while True:
            if (len(c1) > 0) and (len(c2) > 0) and (c1[0] > c2[0]):
                br2 = c2[0]
                break
            elif (len(c1) == 0) and (len(c2) > 0):
                br2 = c2[0]
                break
            elif (len(c1) > 0) and (len(c2) > 0) and (c1[0] < c2[0]):
                c1.pop(0)
                c2.pop(0)

        ss = result[br1 + 1:][:(len(result) - br2) * -1]

        while True:

            g1 = [sg1 for sg1 in range(len(ss)) if ss[sg1] == '(']
            g2 = [sg2 for sg2 in range(len(ss)) if ss[sg2] == ')']

            if (len(g1) == len(g2)) and (len(g1) > 0):
                gm2 = min(g2)
                gm1 = max([gx for gx in g1 if gx < gm2])
                gm21 = (len(ss) - (gm2+1)) * -1
                gr = ss[gm1:][:gm21] if gm21 < 0 else ss[gm1:]
                gr = gr.replace(',','^').replace('(','[').replace(')',']')
                ss = ss[:gm1] + gr + ss[gm2 + 1:]
            else:
                break

        s_list = ss.split(',')
        if len(s_list) < 2:
            break

        if len(s_list[0].strip()) < len(s_list[1].strip()):
            break

        s4 = ''.join(s_list[i1].strip().replace('^',',').replace('[','(').replace(']',')') + ', ' for i1 in range(1, len(s_list)))[:-2]
        sr = s_list[0].strip().replace('^',',').replace('[','(').replace(']',')') + ' IN (' + s4 + ')'

        result = result[:br1 - 2] + sr + result[br2 + 1:]
        if not 'in(' in result.lower():
            break

    return result


def format_formula(in_str: str, strict: bool = True) -> str:
    if strict:
        return in_str
    else:
        result = case_to_case(in_str)
        result = if_to_case(result)
        result = in_to_in(result)
        result = convert_to(result)
        # здесь можно добавить дополнительные конвертеры
        # result = your_converter(result)
        return result
