"""
打印本项目使用的 SLR 文法产生式表。

PDF 附录给出了 36 条紧凑的 EBNF 风格规则。
SLR 分析器使用了展开后的 BNF 文法，因此可选部分、重复部分和表达式 Tail
都有独立的产生式。本报告用于开发报告和测试附录。
"""

from slr_grammar import Grammar
from slr_items import FirstFollow, LR0Machine


PDF_RULE_MAP = [
    ("0", "增广起始规则 S' -> Program，为 SLR accept 状态而添加。"),
    ("1", "Program。"),
    ("2", "compUnit 的重复展开为递归的 compUnit/topUnit。"),
    ("3-10", "decl/constDecl/varDecl 及初始化辅助规则。"),
    ("11-14", "funcDef 及函数参数辅助规则。"),
    ("15-17", "block/blockItem/stmt，可选 exp/else 均已展开。"),
    ("18-26", "exp/cond/lVal/primaryExp/number/unaryExp/函数调用参数。"),
    ("27-32", "左递归表达式改写为基值 + Tail 形式。"),
    ("33", "constExp。"),
    ("34-36", "IntConst/Ident/floatConst 为词法 token，非 SLR 产生式。"),
]


def main():
    grammar = Grammar()
    machine = LR0Machine(grammar)
    ff = FirstFollow(grammar)

    print("SLR 文法产生式表")
    print("=" * 80)
    for prod in grammar.productions:
        body = " ".join(prod.body) if prod.body else "ε"
        print(f"{prod.num}\t{prod.head} -> {body}")

    print()
    print("统计摘要")
    print("=" * 80)
    print(f"产生式数量: {len(grammar.productions)}")
    print(f"LR(0) 状态数: {len(machine.states)}")
    print(f"终结符数量: {len(grammar.terminals)}")
    print(f"非终结符数量: {len(grammar.non_terminals)}")

    print()
    print("与 PDF 规则对应关系")
    print("=" * 80)
    for pdf_rule, note in PDF_RULE_MAP:
        print(f"PDF 规则 {pdf_rule}\t{note}")

    print()
    print("FIRST 集")
    print("=" * 80)
    for nt in sorted(grammar.non_terminals):
        values = ", ".join("$" if value == "ε" else value for value in sorted(ff.first.get(nt, set())))
        print(f"FIRST({nt}) = {{ {values} }}")

    print()
    print("FOLLOW 集")
    print("=" * 80)
    for nt in sorted(grammar.non_terminals):
        values = ", ".join("$" if value == "ε" else value for value in sorted(ff.follow.get(nt, set())))
        print(f"FOLLOW({nt}) = {{ {values} }}")


if __name__ == "__main__":
    main()
