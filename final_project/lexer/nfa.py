from dataclasses import dataclass, field
from typing import Optional, Dict, List, Set
from .regex_ast import *

EPSILON = '' # 一个空字符

@dataclass(eq=False)
# eq 和 hash 还没加
class NFAState:
    id: int
    is_final: bool = False
    type: Optional[str] = None
    value: Optional[str] = None
    transitions: Dict[str, List['NFAState']] = field(default_factory=dict)

    def __hash__(self):
        return hash(self.id)

    def __eq__(self, other):
        if not isinstance(other, NFAState):
            return False
        return self.id == other.id

    def add_transition(self, char: str, next_state: 'NFAState'):
        """添加状态转移"""
        if char not in self.transitions:
            self.transitions[char] = []
        self.transitions[char].append(next_state)

    def get_transitions(self, char: str):
        """获取字符对应的转移"""
        return self.transitions.get(char, [])


@dataclass
class NFA:
    start: NFAState
    accept: NFAState
    states: List[NFAState] = field(default_factory=list)

    def add_state(self, state: NFAState):
        """添加状态"""
        if state not in self.states:
            self.states.append(state)

class NFABuilder:
    """将AST转化为NFA"""

    def __init__(self):
        self.state_count = 0

    def new_state(self, is_final: bool = False, type: Optional[str] = None, value: Optional[str] = None):
        """创建新的NFA状态，默认参数为假和空"""
        state = NFAState(
            id = self.state_count, is_final = is_final, type = type, value = value
        )
        self.state_count += 1
        return state

    def build_nfa(self, node: RegexNode, type: Optional[str] = None, value: Optional[str] = None) -> NFA:
        """从AST构建NFA

        Args:
            node: AST节点
            type: 如果这个正则匹配的是某种token，记录token类型
            value: 某些token的具体值
        Return:
            构建好的NFA
        """
        nfa = self._build_nodes(node)
        nfa.accept.is_final = True
        if type is not None:
            nfa.accept.type = type
            nfa.accept.value = value
        return nfa

    def build(self, node: RegexNode, type: Optional[str] = None, value: Optional[str] = None) -> NFA:
        """兼容旧调用方式"""
        return self.build_nfa(node, type, value)

    def _build_nodes(self, node: RegexNode) -> NFA:
        """用递归构建NFA 通用入口"""
        if isinstance(node, CharNode):
            return self._build_char(node)
        elif isinstance(node, EpsilonNode):
            return self._build_epsilon(node)
        elif isinstance(node, ConcatNode):
            return self._build_concat(node)
        elif isinstance(node, AlterNode):
            return self._build_alter(node)
        elif isinstance(node, ClosureNode):
            return self._build_closure(node)
        elif isinstance(node, CharSetNode):
            return self._build_charset(node)
        else:
            raise ValueError(f"不支持的类型：{type(node)}")


    def _build_char(self, node: CharNode):
        """构建单个字符的NFA"""
        s0 = self.new_state()
        s1 = self.new_state()
        s0.add_transition(node.char, s1)
        nfa = NFA(s0, s1, [s0, s1])
        return nfa

    def _build_epsilon(self, node: EpsilonNode):
        """构建ε的NFA"""
        s0 = self.new_state()
        s1 = self.new_state()
        s0.add_transition(EPSILON, s1)
        nfa = NFA(s0, s1, [s0, s1])
        return nfa

    def _build_concat(self, node: ConcatNode):
        """构建ab...的NFA"""
        nfa_left = self._build_nodes(node.left)
        nfa_right = self._build_nodes(node.right)

        nfa_left.accept.add_transition(EPSILON, nfa_right.start)
        nfa = NFA(start=nfa_left.start, accept=nfa_right.accept)
        nfa.states = nfa_left.states + nfa_right.states
        return nfa

    def _build_alter(self, node: AlterNode):
        """构建a|b...的NFA"""
        nfa_up = self._build_nodes(node.left)
        nfa_down = self._build_nodes(node.right)

        s0 = self.new_state()
        s1 = self.new_state()
        s0.add_transition(EPSILON, nfa_up.start)
        s0.add_transition(EPSILON, nfa_down.start)
        nfa_up.accept.add_transition(EPSILON, s1)
        nfa_down.accept.add_transition(EPSILON, s1)
        nfa = NFA(start=s0, accept=s1)
        nfa.states = [s0, s1] + nfa_up.states + nfa_down.states
        return nfa

    def _build_closure(self, node: ClosureNode):
        """构建 * 的NFA"""
        nfa_child = self._build_nodes(node.child)
        s0 = self.new_state()
        s1 = self.new_state()

        s0.add_transition(EPSILON, nfa_child.start)
        s0.add_transition(EPSILON, s1)
        nfa_child.accept.add_transition(EPSILON, nfa_child.start)
        nfa_child.accept.add_transition(EPSILON, s1)

        nfa = NFA(start=s0, accept=s1)
        nfa.states = [s0, s1] + nfa_child.states

        return nfa

    def _build_charset(self, node: CharSetNode):
        """构建字符集的NFA"""
        s0 = self.new_state()
        s1 = self.new_state()

        for i in node.charset:
            s0.add_transition(i, s1)

        nfa = NFA(s0, s1, [s0, s1])
        return nfa

# 其他函数
def combine_nfas(nfas: List[NFA]) -> NFA:
    """合并多个NFA"""
    if len(nfas) == 0:
        raise ValueError("无可合并的NFA")

    if len(nfas) == 1:
        return nfas[0]

    max_id = 0
    for nfa in nfas:
        for state in nfa.states:
            if max_id < state.id:
                max_id = state.id

    builder = NFABuilder()
    builder.state_count = max_id + 1

    # 连接所有nfa初态的超级初态
    super_start = builder.new_state()
    # 虚拟终态，并不连接所有nfa的终态，因为每个终态都有自己的type和value
    dummy_accept = builder.new_state()

    all_states = [super_start]

    for nfa in nfas:
        super_start.add_transition(EPSILON, nfa.start)
        all_states.extend(nfa.states)

    all_states.append(dummy_accept)

    combined = NFA(start=super_start, accept=dummy_accept)
    combined.states = all_states
    return combined

def epsilon_closure(states: Set[NFAState]) -> Set[NFAState]:
    """计算ε-闭包：从状态集states出发，仅通过ε边能到达的所有状态"""
    closure = set(states)
    worklist = list(states)

    while worklist:
        state = worklist.pop()
        for next_state in state.get_transitions(EPSILON):
            if next_state not in closure:
                closure.add(next_state)
                worklist.append(next_state)

    return closure

def move(states: Set[NFAState], char: str) -> Set[NFAState]:
    """计算move操作：从状态集states出发，经过字符char能到达的所有状态"""
    result = set()

    for state in states:
        for next_state in state.get_transitions(char):
                result.add(next_state)

    return result

