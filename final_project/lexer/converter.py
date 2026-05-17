"""
NFA到DFA转换和DFA最小化
"""
from .nfa import NFA, NFAState, epsilon_closure, move
from .dfa import DFA, DFAState
from typing import Set, List, Optional, Dict, Tuple
from collections import defaultdict


def nfa_to_dfa(nfa: NFA) -> DFA:
    """NFA转换为DFA
    算法步骤：
    1. 计算初态的ε闭包作为DFA初态
    2. 对每个DFA状态和每个输入字符，计算新状态
    3. 重复直到没有新状态产生
    4. 包含NFA终态的DFA状态标记为终态
    """

    count = 0
    # NFA状态集 与 DFA状态 的映射
    set2state: Dict[frozenset[NFAState], DFAState] = {}
    # BFS遍历列表
    worklist: List[frozenset] = []

    start_set = epsilon_closure({nfa.start})
    start_state = DFAState(id=count)
    count += 1
    #进行标记
    _mark_dfa_state(start_state, start_set)

    start_set_frozen = frozenset(start_set)
    worklist.append(start_set_frozen)
    set2state[start_set_frozen] = start_state

    dfa = DFA(start=start_state)
    dfa.add_state(start_state)

    # NFA所有状态的转移char集合
    alphabet = _get_alphabet(nfa)
    dfa.alphabet = alphabet

    while worklist:
        cur_set = worklist.pop(0)
        cur_state = set2state[cur_set]

        # 遍历所有字符 对当前状态集的 可能转移
        for char in alphabet:
            new_set = epsilon_closure(move(set(cur_set), char))

            # 可能move得不到新集合
            if not new_set:
                continue

            new_set_frozen = frozenset(new_set)

            # 没有映射的新集合，才构建一个对应的映射
            if new_set_frozen not in set2state:
                new_state = DFAState(id=count)
                count += 1
                # 进行标记
                _mark_dfa_state(new_state, new_set)

                # dfa要加新状态，但是当前状态的转移不在if里面加
                dfa.add_state(new_state)

                # 更新工作列表和字典
                set2state[new_set_frozen] = new_state
                worklist.append(new_set_frozen)

            # 就算不是新集合，这个转移也是原来没有的
            cur_state.add_transition(char, set2state[new_set_frozen])

    return dfa

def _mark_dfa_state(dfa_state: DFAState, nfa_states: Set[NFAState]):
    """标记DFA状态是否为终态，以及token类型

    优先级：FLOAT > INT > IDN > OP > SE
    这样可以确保浮点数优先于整数，双字符运算符优先于单字符
    """
    # 收集所有终态的token类型
    token_priority = {'FLOAT': 5, 'INT': 4, 'IDN': 3, 'OP': 2, 'SE': 1}

    best_type = None
    best_value = None
    best_priority = -1

    for nfa_state in nfa_states:
        if nfa_state.is_final:
            dfa_state.is_final = True
            # 按优先级选择
            priority = token_priority.get(nfa_state.type, 0)
            if priority > best_priority:
                best_priority = priority
                best_type = nfa_state.type
                best_value = nfa_state.value

    if best_type is not None:
        dfa_state.type = best_type
        dfa_state.value = best_value


def _get_alphabet(nfa: NFA) -> Set[str]:
    """从NFA提取字母表（排除ε）"""
    alphabet = set()
    for state in nfa.states:
        for char in state.transitions.keys():
            if char:  # 排除ε
                alphabet.add(char)
    return alphabet


def minimize_dfa(dfa: DFA) -> DFA:
    """DFA最小化
    算法步骤：
    1. 初始划分：终态组和非终态组
    2. 对每个组，检查组内状态是否等价，如果两个状态对同一输入转移到不同组，则不等价
    3. 分割不等价的状态
    4. 重复直到划分不再变化
    5. 合并同一组的状态
    """
    if len(dfa.states) <= 1 :
        return dfa

    # 不同终态按照token划为不同的par
    finals: Dict[Tuple[Optional[str], Optional[str]], List[DFAState]] = {}
    for state in dfa.states:
        if state.is_final:
            key = (state.type, state.value)
            if key not in finals:
                finals[key] = []
            finals[key].append(state)

    partitions: List[Set[DFAState]] = []

   # 所有的非终态划为一组
    non_final = {state for state in dfa.states if not state.is_final}
    if non_final:
        partitions.append(non_final)

    # 加入之前划分好的终态
    for states in finals.values():
        partitions.append(set(states))

    # while循环，每轮遍历所有par，如果所有par都不更新，退出
    changed = True
    while changed:
        changed = False
        # 存储这一轮的新划分结果
        new_partitions = []

        #遍历par
        for par in partitions:
            sub_par = _split_partition(par, partitions, dfa.alphabet)
            if len(sub_par) > 1:
                changed = True
            new_partitions.extend(sub_par)

        # 更新 partitions
        partitions = new_partitions

    # 构建最小化DFA
    return _build_minimized_dfa(dfa, partitions)

def _split_partition(partition: Set[DFAState],
                     all_partitions: List[Set[DFAState]],
                     alphabet: Set[str]) -> List[Set[DFAState]]:
    """尝试分割一个分区"""
    if len(partition) <= 1:
        return [partition]

    # 找到区分状态的条件
    states = list(partition)

    # 对每个字符，检查转移目标所在的分区
    for char in alphabet:
        # 计算每个状态转移到哪个分区
        target_partitions = {}
        for state in states:
            next_state = state.get_transition(char)
            if next_state is None:
                target_partition_id = -1  # 表示没有转移
            else:
                target_partition_id = _find_partition_id(next_state, all_partitions)
            target_partitions[state] = target_partition_id

        # 如果有不同的目标分区，则分割
        unique_targets = set(target_partitions.values())
        if len(unique_targets) > 1:
            # 按目标分区分组
            groups = defaultdict(set)
            for state, target_id in target_partitions.items():
                groups[target_id].add(state)
            return list(groups.values())

    return [partition]


def _find_partition_id(state: DFAState, partitions: List[Set[DFAState]]) -> int:
    """找到状态所在的分区ID"""
    for i, partition in enumerate(partitions):
        if state in partition:
            return i
    return -1


def _build_minimized_dfa(old_dfa: DFA, partitions: List[Set[DFAState]]) -> DFA:
    """从分区构建最小化DFA"""
    count = 0
    # 每个分区构造一个状态， 并给它编号，此字典是编号-新状态映射
    par2state: Dict[int, DFAState] = {}

    for i, par in enumerate(partitions):
        # 取第一个作为representative
        rep = next(iter(par))
        # 构建新状态
        new_state = DFAState(
            id=count,
            is_final=rep.is_final,
            type=rep.type,
            value=rep.value
        )
        count += 1
        par2state[i] = new_state

    # 新的一轮循环来添加状态转移
    for i, par in enumerate(partitions):
        rep = next(iter(par))
        cur_state = par2state[i]

        for ch, tar in rep.transitions.items():
            tar_id = _find_partition_id(tar, partitions)
            if tar_id >= 0:
                tar_state = par2state[tar_id]
                cur_state.add_transition(ch, tar_state)

    # 寻找新初态
    start_id = _find_partition_id(old_dfa.start, partitions)
    new_start = par2state[start_id]

    # 构建新DFA
    min_dfa = DFA(start=new_start)
    min_dfa.alphabet = old_dfa.alphabet.copy()
    for state in par2state.values():
        min_dfa.add_state(state)

    return min_dfa



