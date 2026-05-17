"""
SLR 分析表构建

基于 LR(0) 项目集规范族和 FOLLOW 集构建 SLR 分析表。
"""

from typing import Dict, Optional
from slr_grammar import Grammar
from slr_items import LR0Machine, FirstFollow


class SLRTable:
    """SLR 分析表"""

    def __init__(self, grammar: Grammar):
        self.grammar = grammar
        self.machine = LR0Machine(grammar)
        self.ff = FirstFollow(grammar)

        # ACTION 表: action[state][terminal] = ('shift', next_state) | ('reduce', prod_num) | ('accept',) | ('error',)
        self.action: Dict[int, Dict[str, tuple]] = {}
        # GOTO 表: goto[state][non_terminal] = next_state
        self.goto: Dict[int, Dict[str, int]] = {}

        self._build()

    def _build(self):
        """构建 SLR 分析表"""
        for state in self.machine.states:
            sid = state.id
            self.action[sid] = {}
            self.goto[sid] = {}

            # 先处理移进项目（shift 优先于 reduce）
            for item in state.items:
                prod = self.grammar.get_production_by_num(item.prod_num)
                if prod is None:
                    continue

                sym_after = item.symbol_after_dot(self.grammar)

                if sym_after is not None:
                    if self.grammar.is_terminal(sym_after):
                        next_id = self.machine.transitions[sid].get(sym_after)
                        if next_id is not None:
                            self.action[sid][sym_after] = ('shift', next_id)
                    else:
                        next_id = self.machine.transitions[sid].get(sym_after)
                        if next_id is not None:
                            self.goto[sid][sym_after] = next_id

            # 再处理规约项目（不覆盖已有的 shift）
            for item in state.items:
                prod = self.grammar.get_production_by_num(item.prod_num)
                if prod is None:
                    continue

                sym_after = item.symbol_after_dot(self.grammar)

                if sym_after is None:
                    # 规约项目 A -> α·
                    if item.prod_num == 0:
                        # S' -> Program· : accept
                        self.action[sid]['$'] = ('accept',)
                    else:
                        # SLR: 对 FOLLOW(A) 中的每个终结符进行规约
                        for t in self.ff.follow[prod.head]:
                            if t == 'ε':
                                continue
                            # 只在没有动作时填入 reduce（shift 优先）
                            if t not in self.action[sid]:
                                self.action[sid][t] = ('reduce', prod.num)

    def get_action(self, state: int, terminal: str) -> Optional[tuple]:
        """获取 ACTION 表条目"""
        return self.action.get(state, {}).get(terminal)

    def get_goto(self, state: int, non_terminal: str) -> Optional[int]:
        """获取 GOTO 表条目"""
        return self.goto.get(state, {}).get(non_terminal)

    def print_table(self):
        """打印分析表"""
        print("\nSLR ACTION 表:")
        print("=" * 80)

        all_terminals = set()
        for sid in self.action:
            all_terminals.update(self.action[sid].keys())

        terminals = sorted(all_terminals)
        header = f"{'状态':<6}"
        for t in terminals:
            header += f"{t:<14}"
        print(header)
        print("-" * 80)

        for sid in sorted(self.action.keys()):
            row = f"I{sid:<5}"
            for t in terminals:
                act = self.action[sid].get(t, '')
                if act:
                    if act[0] == 'shift':
                        row += f"s{act[1]:<13}"
                    elif act[0] == 'reduce':
                        row += f"r{act[1]:<13}"
                    elif act[0] == 'accept':
                        row += f"{'acc':<14}"
                    else:
                        row += f"{'err':<14}"
                else:
                    row += f"{'':<14}"
            print(row)

        print("\nSLR GOTO 表:")
        print("=" * 80)

        all_nts = set()
        for sid in self.goto:
            all_nts.update(self.goto[sid].keys())

        nts = sorted(all_nts)
        header = f"{'State':<6}"
        for nt in nts:
            header += f"{nt:<12}"
        print(header)
        print("-" * 80)

        for sid in sorted(self.goto.keys()):
            if not self.goto[sid]:
                continue
            row = f"I{sid:<5}"
            for nt in nts:
                g = self.goto[sid].get(nt, '')
                row += f"{g if g else '':<12}"
            print(row)


if __name__ == '__main__':
    grammar = Grammar()
    table = SLRTable(grammar)
    table.print_table()
