"""
LR(0) 项目集规范族 + FOLLOW 集计算

用于 SLR 分析器。
"""

from typing import List, Dict, Set, Tuple, Optional, FrozenSet
from dataclasses import dataclass, field
from slr_grammar import Grammar, Production


@dataclass(frozen=True)
class Item:
    """LR(0) 项目: A -> α·β"""
    prod_num: int  # 产生式编号
    dot_pos: int   # · 的位置 (0 = 在最前, len(body) = 在最后)

    def symbol_after_dot(self, grammar: Grammar) -> Optional[str]:
        """获取 · 后面的符号"""
        prod = grammar.get_production_by_num(self.prod_num)
        if prod is None:
            return None
        if self.dot_pos < len(prod.body):
            return prod.body[self.dot_pos]
        return None

    def is_reduce_item(self, grammar: Grammar) -> bool:
        """是否为规约项目（· 在最后）"""
        prod = grammar.get_production_by_num(self.prod_num)
        return prod is not None and self.dot_pos == len(prod.body)

    def __repr__(self):
        return f"Item({self.prod_num}, dot={self.dot_pos})"


class ItemSet:
    """LR(0) 项目集"""

    def __init__(self, items: FrozenSet[Item], grammar: Grammar):
        self.items: FrozenSet[Item] = items
        self.id: int = -1  # 状态编号，后续分配
        self._grammar = grammar

    def __hash__(self):
        return hash(self.items)

    def __eq__(self, other):
        if not isinstance(other, ItemSet):
            return False
        return self.items == other.items

    def __repr__(self):
        lines = []
        for item in sorted(self.items, key=lambda i: (i.prod_num, i.dot_pos)):
            prod = self._grammar.get_production_by_num(item.prod_num)
            if prod:
                body_str = ' '.join(prod.body) if prod.body else 'ε'
                before = body_str[:item.dot_pos].rstrip() if item.dot_pos > 0 else ''
                after = body_str[item.dot_pos:].lstrip() if item.dot_pos < len(prod.body) else ''
                dot_str = f"{before} · {after}".strip() if before or after else '·'
                lines.append(f"  {prod.head} -> {dot_str}")
        return f"I{self.id}:\n" + '\n'.join(lines)


class LR0Machine:
    """LR(0) 项目集规范族"""

    def __init__(self, grammar: Grammar):
        self.grammar = grammar
        self.states: List[ItemSet] = []  # 所有状态
        self.transitions: Dict[int, Dict[str, int]] = {}  # state_id -> {symbol -> next_state_id}

        self._build()

    def _closure(self, items: FrozenSet[Item]) -> FrozenSet[Item]:
        """计算项目集的闭包"""
        closure = set(items)
        queue = list(items)

        while queue:
            item = queue.pop(0)
            sym = item.symbol_after_dot(self.grammar)

            if sym and self.grammar.is_non_terminal(sym):
                # 对于 A -> α·Bβ，将 B 的所有产生式 B -> ·γ 加入闭包
                for prod in self.grammar.get_productions_by_head(sym):
                    new_item = Item(prod.num, 0)
                    if new_item not in closure:
                        closure.add(new_item)
                        queue.append(new_item)

        return frozenset(closure)

    def _goto(self, items: FrozenSet[Item], symbol: str) -> FrozenSet[Item]:
        """计算 GOTO(I, X)"""
        result = set()

        for item in items:
            sym = item.symbol_after_dot(self.grammar)
            if sym == symbol:
                # 将 · 向后移动一位
                new_item = Item(item.prod_num, item.dot_pos + 1)
                result.add(new_item)

        return self._closure(frozenset(result))

    def _build(self):
        """构建 LR(0) 项目集规范族"""
        start_item = Item(0, 0)
        initial = self._closure(frozenset({start_item}))

        worklist = [initial]
        seen = {initial}
        item_to_id = {initial: 0}
        next_state_id = 1  # 新状态 ID 计数器

        while worklist:
            current = worklist.pop(0)

            state_id = item_to_id[current]
            state = ItemSet(current, self.grammar)
            state.id = state_id
            self.states.append(state)
            self.transitions[state_id] = {}

            symbols = set()
            for item in current:
                sym = item.symbol_after_dot(self.grammar)
                if sym:
                    symbols.add(sym)

            for sym in symbols:
                next_items = self._goto(current, sym)
                if not next_items:
                    continue

                if next_items not in seen:
                    seen.add(next_items)
                    new_id = next_state_id
                    next_state_id += 1
                    item_to_id[next_items] = new_id
                    worklist.append(next_items)
                else:
                    new_id = item_to_id[next_items]

                self.transitions[state_id][sym] = new_id

    def print_all(self):
        """打印所有状态"""
        for state in self.states:
            print(state)
            print(f"  GOTO: {self.transitions[state.id]}")
            print()


class FirstFollow:
    """FIRST 和 FOLLOW 集计算"""

    def __init__(self, grammar: Grammar):
        self.grammar = grammar
        self.first: Dict[str, Set[str]] = {}
        self.follow: Dict[str, Set[str]] = {}

        self._compute_first()
        self._compute_follow()

    def _compute_first(self):
        """计算 FIRST 集"""
        # 初始化
        for nt in self.grammar.non_terminals:
            self.first[nt] = set()

        # 终结符的 FIRST 集就是自身
        for t in self.grammar.terminals:
            self.first[t] = {t}

        # 迭代直到收敛
        changed = True
        while changed:
            changed = False
            for prod in self.grammar.productions:
                if self._add_first(prod.head, prod.body):
                    changed = True

    def _add_first(self, head: str, body: List[str]) -> bool:
        changed = False

        if not body:  # ε 产生式
            if 'ε' not in self.first[head]:
                self.first[head].add('ε')
                changed = True
            return changed

        all_derive_epsilon = True
        for symbol in body:
            if self._is_terminal(symbol):
                if symbol not in self.first[head]:
                    self.first[head].add(symbol)
                    changed = True
                all_derive_epsilon = False
                break
            else:
                for t in self.first.get(symbol, set()):
                    if t != 'ε' and t not in self.first[head]:
                        self.first[head].add(t)
                        changed = True
                if 'ε' not in self.first.get(symbol, set()):
                    all_derive_epsilon = False
                    break

        if all_derive_epsilon and 'ε' not in self.first[head]:
            self.first[head].add('ε')
            changed = True

        return changed

    def _compute_follow(self):
        """计算 FOLLOW 集"""
        for nt in self.grammar.non_terminals:
            self.follow[nt] = set()

        self.follow[self.grammar.start_symbol].add('$')

        changed = True
        while changed:
            changed = False
            for prod in self.grammar.productions:
                if self._add_follow(prod.head, prod.body):
                    changed = True

    def _add_follow(self, head: str, body: List[str]) -> bool:
        changed = False

        for i, symbol in enumerate(body):
            if symbol in self.grammar.non_terminals:
                beta = body[i + 1:]

                if beta:
                    first_beta = self._first_of_sequence(beta)
                    for t in first_beta:
                        if t != 'ε' and t not in self.follow[symbol]:
                            self.follow[symbol].add(t)
                            changed = True

                    if self._derives_epsilon(beta):
                        for t in self.follow[head]:
                            if t not in self.follow[symbol]:
                                self.follow[symbol].add(t)
                                changed = True
                else:
                    for t in self.follow[head]:
                        if t not in self.follow[symbol]:
                            self.follow[symbol].add(t)
                            changed = True

        return changed

    def _first_of_sequence(self, sequence: List[str]) -> Set[str]:
        result = set()
        for symbol in sequence:
            if self._is_terminal(symbol):
                result.add(symbol)
                break
            for t in self.first.get(symbol, set()):
                if t != 'ε':
                    result.add(t)
            if 'ε' not in self.first.get(symbol, set()):
                break
        else:
            result.add('ε')
        return result

    def _derives_epsilon(self, sequence: List[str]) -> bool:
        for symbol in sequence:
            if self._is_terminal(symbol):
                return False
            if 'ε' not in self.first.get(symbol, set()):
                return False
        return True

    def _is_terminal(self, symbol: str) -> bool:
        return symbol in self.grammar.terminals

    def print_first(self):
        print("\nFIRST 集:")
        for nt in sorted(self.grammar.non_terminals):
            print(f"  FIRST({nt}) = {{ {', '.join(sorted(self.first.get(nt, set())))} }}")

    def print_follow(self):
        print("\nFOLLOW 集:")
        for nt in sorted(self.grammar.non_terminals):
            print(f"  FOLLOW({nt}) = {{ {', '.join(sorted(self.follow.get(nt, set())))} }}")


if __name__ == '__main__':
    grammar = Grammar()
    machine = LR0Machine(grammar)
    machine.print_all()

    ff = FirstFollow(grammar)
    ff.print_first()
    ff.print_follow()
