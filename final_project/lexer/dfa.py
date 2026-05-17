from dataclasses import dataclass, field
from typing import Optional, Dict, List, Set

# hash 和 eq 没写

@dataclass(eq=False)
class DFAState:
    id: int
    is_final: bool = False
    type: Optional[str] = None
    value: Optional[str] = None
    transitions: Dict[str, 'DFAState'] = field(default_factory=dict)

    def __hash__(self):
        return hash(self.id)

    def __eq__(self, other):
        if not isinstance(other, DFAState):
            return False
        return self.id == other.id

    def add_transition(self, char: str, next_state: 'DFAState'):
        """添加状态转移"""
        self.transitions[char] = next_state

    def get_transition(self, char: str):
        """获取char能到达的状态"""
        return self.transitions.get(char)

    def get_all_transitions(self):
        """获取状态转移表"""
        return self.transitions

@dataclass
class DFA:
    start: DFAState
    # accept: DFAState # 没有单一的终态
    states: List[DFAState] = field(default_factory=list)
    alphabet: Set[str] = field(default_factory=set) # DFA的字母表，也就是所有可能的输入字符集合

    def add_state(self, state: DFAState):
        """加入一个新状态"""
        if state not in self.states:
            self.states.append(state)

    def add_to_alphabet(self, char: str):
        """把一个非ε字符加入字母表"""
        if char:
            self.alphabet.add(char)

    def get_final_states(self):
        """有多个正则表达式，所以对应多个终态"""
        return [state for state in self.states if state.is_final == True]





