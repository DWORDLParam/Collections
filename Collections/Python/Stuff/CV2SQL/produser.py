
import random
from stuff import ifnone_to_str, normalize_path, build_agg_function, single_str, make_alias, make_new_input


class Join:
    left_table: str
    right_table: str
    type: str
    left_fields: any
    right_fields: any

    def __init__(self):
        self.left_table = ''
        self.right_table= ''
        self.type = ''
        self.left_fields = []
        self.right_fields = []


class Rank:
    name: str
    partition: any
    order: any

    def __init__(self):
        self.name = ''
        self.partition = []
        self.order = []


class DataBlock:
    name: str
    type: str
    filter: str
    join: any
    ranks: any
    inputs: any
    elements: any
    results: dict

    def __init__(self):
        self.type = 'undefined'
        self.filter = ''
        self.join = Join()
        self.ranks = []
        self.inputs = []
        self.elements = []
        self.results = {}
        self.results['select'] = ''
        self.results['from'] = ''
        self.results['join'] = ''
        self.results['where'] = ''
        self.results['group'] = ''

    def find_element(self, ename: str) -> int:
        result = -1
        ind = result
        for c1 in self.elements:
            ind += 1
            if c1.get('name') == ename:
                result = ind
                break
        return result

    def find_input(self, iname: str) -> any:
        for i1 in self.inputs:
            for i2 in i1:
                if i2.get('target') == iname:
                    return i2

    def make_select_section(self):
        result = ''
        if self.type == 'View:Union':
            shift = ' ' * 3
            for i1 in range(len(self.inputs)):
                result += shift + 'UNION ALL\n' + shift + '--+\n' if i1 > 0 else ''
                result += shift + 'SELECT\n'
                bpath = ''
                bals = ''
                for i2 in self.inputs[i1]:
                    p1 = i2['parameter']
                    ei = self.find_element(i2['target'])
                    if ei > -1:
                        elm = self.elements[ei]
                    else:
                        if p1 == '':
                            continue
                    b1 = i2.get('alias') + '.' if i2.get('alias') != '' else ''
                    bals = ' AS ' + b1[:-1] if b1 != '' else ''
                    fn1 = '"' + i2.get('source') + '"' if ifnone_to_str(i2.get('source'), '') != '' else ''
                    n1 = i2.get('target')
                    bpath = i2.get('path')
                    v1 = ifnone_to_str(i2.get('value'), '')
                    v3 = v1 + ' as ' + n1 + ',\n' if i1 == 0 else v1 + ',\n'
                    o1 = b1 + fn1 + ' as ' + n1 + ',\n' if i1 == 0 else b1 + fn1 + ',\n'
                    if v1 != '':
                        result += shift + v3
                    else:
                        fn3 = b1 + fn1 if fn1 != '' else 'NULL'
                        result += shift + fn3 + ' as ' + n1 + ',\n' if i1 == 0 else shift + fn3 + ',\n'

                result = result[:-2] + '\n'
                result += shift + 'FROM ' + normalize_path(bpath) + bals + '\n'

            self.results['select'] = result

        else:
            result += 'SELECT\n'
            for i1 in self.inputs:
                for i2 in i1:
                    p1 = i2['parameter']
                    ei = self.find_element(i2['target'])
                    if ei > -1:
                        elm = self.elements[ei]
                    else:
                        if p1 == '':
                            continue

                    b1 = i2.get('alias') + '.' if i2.get('alias') != '' else ''
                    fr1 = elm['formula']
                    s1 = '"' + i2.get('source') + '"' if i2.get('source') != '' else ''
                    a1 = build_agg_function(elm, s1, b1)
                    n1 = i2.get('target')
                    v1 = ifnone_to_str(i2.get('value'), '')

                    if a1 != '':
                        result += a1 + ' AS ' + n1 + ',\n'
                    elif v1 != '':
                        result += v1 + ' AS ' + n1 + ',\n'
                    elif (fr1 != '') and (s1 == ''):
                        result += fr1 + ' AS ' + n1 + ',\n'
                    else:
                        result += b1 + s1 + ' AS ' + n1 + ',\n'

                    self.results['select'] = result[:-2] + '\n'

    def append_rank_function(self):
        result = ''
        if len(self.ranks) == 0:
            return
        for wf in self.ranks:
            s1 = ''
            for part in wf.partition:
                i1 = self.find_input(part)
                if i1 is not None:
                    b1 = i1['alias'] + '.' if i1['alias'] != '' else ''
                    s1 += b1 + '"' + i1['source'] + '", '
            sp = s1[:-2] if s1 != '' else ''

            s2 = ''
            for qitem in wf.order:
                ql = qitem.split(' ')
                i2 = self.find_input(ql[0])
                if i2 is not None:
                    b2 = i2['alias'] + '.' if i2['alias'] != '' else ''
                    s2 += b2 + '"' + i2['source'] + '" ' + ql[1] + ', ' if len(ql) > 0 else b2 + '"' + i2[
                        'source'] + '", '

            result += wf.name + '() OVER (PARTITION BY ' + sp + ' ORDER BY ' + s2[:-2] + ') AS WF_' + str(
                random.randint(10, 99)) + '_' + wf.name + ',\n'

        if result != '':
            self.results['select'] = self.results['select'][:-1] + ',\n' + result[:-2] + '\n'

    def make_from_section(self):
        result = ''
        if self.type == 'View:Union':
            self.results['from'] = ''
        else:
            fpath = self.inputs[0][0].get('path')
            fals = self.inputs[0][0].get('alias')
            result += 'FROM ' + normalize_path(fpath) + ' AS ' + fals
            if self.join.type == '':
                self.results['from'] = result + '\n'
            else:
                self.results['from'] = ''

    def make_join_section(self):
        result = ''
        if self.type == 'View:JoinNode' and self.join.type != '':
            ltab = self.join.left_table.replace(self.name + '/', '')
            lals = self.inputs[0][0].get('alias')
            result += 'FROM ' + normalize_path(ltab) + ' AS ' + lals + '\n'
            if self.join.type.lower() == 'leftouter':
                js1 = 'LEFT JOIN '
            elif self.join.type.lower() == 'rightouter':
                js1 = 'RIGHT JOIN '
            elif self.join.type.lower() == 'inner':
                js1 = 'INNER JOIN '
            elif self.join.type.lower() == 'full':
                js1 = 'FULL JOIN '
            elif self.join.type.lower() == 'cross':
                js1 = 'CROSS JOIN '
            elif self.join.type.lower() == 'referential':
                js1 = 'INNER JOIN '
            rtab = self.join.right_table.replace(self.name + '/', '')
            rals = self.inputs[1][0].get('alias') if len(self.inputs) > 1 else make_alias(self.type, rtab)
            fldl = ''.join(
                lals + '."' + self.join.left_fields[fi] + '" = ' + rals + '."' + self.join.right_fields[fi] + '" AND '
                for fi in range(len(self.join.left_fields)))
            result += js1 + normalize_path(rtab) + ' AS ' + rals + ' ON ' + fldl[:-5]
            self.results['join'] = result + '\n'
        else:
            self.results['join'] = ''

    def make_where_section(self):
        result = 'WHERE ' + self.filter
        self.results['where'] = result + '\n' if self.filter != '' else ''

    def make_group_section(self):
        def get_input(target: str, formula: str) -> str:
            i1 = self.find_input(target)
            if i1 is not None:
                b1 = i1.get('alias') + '.' if i1.get('alias') != '' else ''
                fn1 = '"' + i1.get('source') + '"' if i1.get('source') != '' else ''
                return b1 + fn1 if formula == '' else single_str(formula.replace('\n', ' '))

        result = 'GROUP BY' + '\n'
        shift = ' ' * 3
        if self.type == 'View:Aggregation':
            cl = [shift + get_input(c['name'], c['formula']) + ',\n' for c in self.elements if
                  ifnone_to_str(c['agg'], 'NONE').lower() in ['none', 'formula']]
            s1 = ''.join(s for s in cl)
            result += s1
            self.results['group'] = result[:-2]
        else:
            self.results['group'] = ''

    def correct_inputs(self):
        for e1 in self.elements:
            en = e1['name']
            ef = e1['formula']
            ea = ifnone_to_str(e1['agg'], 'NONE')
            i1 = self.find_input(en)
            ials = i1['alias'] if i1 is not None else self.inputs[0][0]['alias']

            if self.type == 'View:Aggregation':
                if (ef != '') and (ea == 'NONE'):
                    if i1 is None:
                        einput = make_new_input()
                        einput['target'] = en
                        einput['alias'] = ials
                        self.inputs[0].append(einput)
                elif (ef != '') and (ea != 'NONE'):
                    if i1 is None:
                        einput = make_new_input()
                        einput['target'] = en
                        einput['alias'] = ials
                        self.inputs[0].append(einput)

            elif self.type == 'View:Projection':
                if ef != '':
                    if i1 is None:
                        einput = make_new_input()
                        einput['target'] = en
                        einput['alias'] = ials
                        self.inputs[0].append(einput)

            elif self.type == 'View:JoinNode':
                if ef != '':
                    if i1 is None:
                        found = False
                        for ii2 in range(len(self.inputs)):
                            for i3 in self.inputs[ii2]:
                                if i3['target'] in ef:
                                    einput = make_new_input()
                                    ef_a = ef.replace('"' + i3['target'] + '"', i3['alias'] + '."' + i3['target'] + '"')
                                    e1['formula'] = ef_a
                                    einput['target'] = en
                                    einput['alias'] = i3['alias']
                                    self.inputs[ii2].append(einput)
                                    found = True
                                    break
                            if found:
                                break

    def inject_alias(self):
        fstr = self.filter
        if fstr != '':
            for i1 in self.inputs:
                for i2 in i1:
                    tp1 = fstr.find('"' + i2['target'] + '"')
                    if ((tp1 > 0) and (fstr[tp1 - 1] != '.')) or (tp1 == 0):
                        als = i2['alias'] + '.' if i2['alias'] != '' else ''
                        fstr = fstr.replace('"' + i2['target'] + '"', als + '"' + i2['target'] + '"')
                self.filter = fstr

        for e1 in self.elements:
            fstr = e1['formula']
            if fstr != '':
                for i1 in self.inputs:
                    for i2 in i1:
                        tp1 = fstr.find('"' + i2['target'] + '"')
                        if ((tp1 > 0) and (fstr[tp1 - 1] != '.')) or (tp1 == 0):
                            als = i2['alias'] + '.' if i2['alias'] != '' else ''
                            fstr = fstr.replace('"' + i2['target'] + '"', als + '"' + i2['target'] + '"')
                    for i3 in i1:
                        if i3['target'] == fstr:
                            als = i3['alias'] + '.' if i3['alias'] != '' else ''
                            fstr = als + '"' + i3['target'] + '"'
                e1['formula'] = fstr

    def correct_joins(self):
        if self.type == 'View:JoinNode':
            for i1 in self.inputs:
                for i2 in i1:
                    if i2['path'] != i2['alias']:
                        if i2['alias'] in self.join.left_table:
                            self.join.left_table = i2['path']
                        elif i2['alias'] in self.join.right_table:
                            self.join.right_table = i2['path']
                        break

    def showdata(self):
        print('name=' + self.name)
        print('type=' + self.type)
        print('filter=' + self.filter)
        if self.join.type != '':
            print('jltab=' + self.join.left_table)
            print('jrtab=' + self.join.right_table)
            print('jtype=' + self.join.type)
            for ijf in range(len(self.join.left_fields)):
                print(self.join.left_fields[ijf] + '=' + self.join.right_fields[ijf])
        if len(self.ranks) > 0:
            for f1 in range(len(self.ranks)):
                func = self.ranks[f1]
                print('function=' + func.name)
                print('partition=' + func.partition)
                for f2 in func.order:
                    print('order=' + f2)

        for c1 in self.elements:
            print(c1)
        for e1 in self.inputs:
            for e2 in e1:
                print(e2)
            print('--')


def produce_query(node_list: list) -> str:
    result = 'WITH \n' if len(node_list) > 1 else ''
    lastnodename = node_list[len(node_list) - 1].name
    for nl in node_list:
        nl.make_select_section()
        nl.append_rank_function()
        nl.make_from_section()
        nl.make_join_section()
        nl.make_where_section()
        nl.make_group_section()
        if nl.name == lastnodename:
            sq = nl.results['select'] + nl.results['from'] + nl.results['join'] + nl.results['where'] + nl.results[
                'group']
        else:
            sq = nl.name + ' as (\n' + nl.results['select'] + nl.results['from'] + nl.results['join'] + nl.results[
                'where'] + nl.results['group'] + '),\n--\n'
        result += sq

    return result
