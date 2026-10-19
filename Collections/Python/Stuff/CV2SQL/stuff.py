
import random
from variables import get_active_schema, default_schema, default_xsi, replace_list


def make_new_element():
    result = dict()
    result['name'] = ''
    result['ctype'] = ''
    result['formula'] = ''
    result['agg'] = ''
    result['atype'] = ''
    result['exagg'] = ''
    result['reelm'] = []
    result['rest'] = []
    return result


def make_new_rest_element():
    result = dict()
    result['restelm'] = ''
    result['restvalue'] = []
    return result


def make_new_input():
    result = dict()
    result['target'] = ''
    result['source'] = ''
    result['path'] = ''
    result['alias'] = ''
    result['value'] = ''  # 'NULL'
    result['parameter'] = ''
    return result


def make_new_parameter():
    result = dict()
    result['name'] = ''
    result['ctype'] = ''
    result['value'] = ''
    return result


def find_xsi(xml_str: str) -> str:
    result = default_xsi
    sp = xml_str.find('xmlns:xsi=')
    if sp == 0:
        return result
    s1 = xml_str[sp + 11:]
    sp = s1.find('xmlns:')
    if sp == 0:
        return result
    result = '{' + s1[:(len(s1) - sp + 2) * -1] + '}'
    return result


def get_schema(root) -> str:
    result = default_schema
    for sh in root:
        if sh.tag == 'defaultSchema':
            result = '"' + sh.get('schemaName') + '"'
            break
    return result


def check_replacement(xml_str: str, direction: bool) -> str:
    result = xml_str
    for ri in replace_list:
        result = result.replace(ri[0], ri[1]) if direction else result.replace(ri[1], ri[0])
    return result


def remove_prefix(in_str: str, dchar: str = '', prf: str = '') -> str:
    sp = in_str.find(dchar)
    if (dchar == '') and (prf == ''):
        return in_str[3:]
    elif (dchar == '') and (prf != ''):
        return in_str[3:].replace(prf, '')
    elif (dchar != '') and (prf != ''):
        return in_str[sp + 1:].replace(prf, '') if sp != 0 else in_str
    else:
        return in_str[sp + 1:] if sp != 0 else in_str


def normalize_path(in_str: str) -> str:
    def delimeter_exists(in_str: str) -> bool:
        result = False
        delimeters = ['.', ':']
        for d1 in delimeters:
            if d1 in in_str:
                return True
        return result

    result = in_str
    if delimeter_exists(in_str):
        s1 = check_replacement(in_str.replace('::', '/'), False)
        ql = s1.split('.')
        sc = ql[0].count('"')
        if sc == 2:
            result = ql[0] + '."' + s1.replace(ql[0] + '.', '') + '"'
        else:
            result = get_active_schema() + '."' + s1 + '"'
    else:
        pass
    return result


def make_alias(qtype: str, in_alias: str) -> str:
    ltr = qtype[5:][0]
    if ltr == 'J':
        return in_alias
    elif ltr == '':
        return 'Z' + str(random.randint(10, 99)) + str(abs(hash(in_alias)))[:2]
    else:
        return ltr + str(random.randint(10, 99))


def ifnone_to_str(in_val, default: str) -> str:
    return in_val if in_val is not None else default


def single_str(in_str: str, ex_str: str = ' ') -> str:
    result = in_str[:]
    while True:
        if result.count(ex_str + ex_str) == 0:
            break
        else:
            result = result.replace(ex_str + ex_str, ex_str)
    return result


def format_filter(in_str: str, params) -> str:
    if len(params) == 0:
        return in_str
    else:
        result = in_str[:]
        for ff in params:
            pname = '\'$$' + ff.get('name') + '$$\''
            if ff.get('ctype') == 'NVARCHAR':
                pval = '\'' + ifnone_to_str(ff.get('value'), '') + '\''
            elif ff.get('ctype') == 'VARCHAR':
                pval = '\'' + ifnone_to_str(ff.get('value'), '') + '\''
            elif ff.get('ctype') == 'DATE':
                pval = '\'' + ifnone_to_str(ff.get('value'), 'NULL') + '\''
            elif ff.get('ctype') == 'FORMULA':
                pval = ifnone_to_str(ff.get('value'), '')
            else:
                pval = ff.get('value')
            result = result.replace(pname, pval)
        return result


def stage_formula(in_str: str, strict: bool = True) -> str:
    if strict:
        return in_str
    else:
        result = in_str[:]
        result = result.replace('in (', 'in(')
        result = result.replace('if (', 'if(')
        return result


def get_parameters(root, params):
    params.clear()
    for pr in root:
        if pr.tag == 'parameter':
            parm = make_new_parameter()
            parm['name'] = pr.get('name')
            typ = pr.find('inlineType')
            if typ is not None:
                parm['ctype'] = typ.get('primitiveType')
            parm['value'] = pr.find('defaultValue').text
            if parm['value'] is None:
                parm['value'] = ''
                dex = pr.find('defaultExpression')
                if dex is not None:
                    frml = dex.find('formula').text
                    if frml != '':
                        parm['value'] = frml
                        parm['ctype'] = 'FORMULA'
            params.append(parm)


def pull_parameter_value(pname: str, params) -> str:
    result = ''
    if len(params) == 0:
        return result
    for pr in params:
        if pr.get('name') == pname:
            result = pr.get('value')
            break
    return result


def build_agg_function(bae: dict, fname: str, als: str) -> str:
    def build_filter(cl: list) -> str:
        result = ''
        if len(cl) == 0:
            return result
        result += ' FILTER (WHERE '
        for c0 in cl:
            s1 = ''.join('\'' + c8[1] + '\', ' for c8 in c0['restvalue'])[:-2]
            s2 = ' IN ' if c0['restvalue'][0] else ' NOT IN '
            result += '(' + als + '"' + c0['restelm'] + '"' + s2 + '(' + s1 + ')) AND '
        return result[:-5] + ')'

    result = ''
    a1 = bae['exagg'].replace('COUNT_DISTINCT', 'COUNT') if len(bae['reelm']) > 0 else bae['exagg']
    a2 = ifnone_to_str(bae['agg'], 'NONE') if a1 == '' else a1
    a3 = ifnone_to_str(bae['formula'], '')
    a4 = ifnone_to_str(bae['atype'], '')
    a5 = ''.join(als + '"' + re + '", ' for re in bae['reelm'])[:-2]
    a6 = als + fname

    # FORMULA
    if (a4 == a2) and (a4 == 'FORMULA'):
        pass
    # SUM(AAA) FILTER() AS AAA
    elif (a4 == a2) and (a4 != 'FORMULA') and (a2 != 'NONE') and (a3 == ''):
        result += a2 + '(' + a6 + ')'
        result += build_filter(bae['rest'])
    # SUM(BBB) FILTER() AS BBB
    elif (a4 != a2) and (a4 == '') and (a2 != 'NONE') and (a3 == ''):
        result += a2 + '(' + a6 + ')'
        result += build_filter(bae['rest'])
    # SUM(FORMULA) FILTER() AS AAA
    elif (a4 == a2) and (a4 != 'FORMULA') and (a2 != 'NONE') and (a3 != ''):
        result += a2 + '(' + a3 + ')'
        result += build_filter(bae['rest'])
    # COUNT(FORMULA) over (partition by AAA) AS AAA
    elif (a4 != a2) and (a4 == 'FORMULA') and (a2 != 'NONE') and (a3 != '') and (a5 != ''):
        result += a2 + '(' + a3 + ') OVER (PARTITION BY ' + a5 + ')'
    return result
