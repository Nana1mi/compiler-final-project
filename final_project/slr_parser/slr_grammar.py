"""
C-- 文法定义（基于大作业附录，改写为适合 SLR 分析的形式）

关键改造：
1. 将 bType 和 funcType 合并为 typeSpecifier（int | float | void）
2. 顶层单元统一为: type Ident rest，其中 rest 区分函数和变量
3. 消除左递归
"""

from typing import List, Dict, Set, Tuple, Optional
from dataclasses import dataclass, field


@dataclass
class Production:
    """产生式"""
    num: int
    head: str
    body: List[str]

    def __repr__(self):
        body_str = ' '.join(self.body) if self.body else 'ε'
        return f"{self.num}. {self.head} -> {body_str}"


class Grammar:
    """C-- 文法"""

    def __init__(self):
        self.productions: List[Production] = []
        self.non_terminals: Set[str] = set()
        self.terminals: Set[str] = set()
        self.start_symbol = 'Program'

        self._define_grammar()
        self._collect_symbols()

    def _define_grammar(self):
        """定义 C-- 文法规则

        改造策略：
        - typeSpecifier: int | float | void（合并 bType 和 funcType）
        - topUnit: 统一处理顶层声明和函数定义
          - const 开头 → constDecl
          - type Ident '(' → funcDef
          - type Ident rest → varDecl
        """
        num = -1

        def add(head: str, body: List[str]) -> int:
            nonlocal num
            num += 1
            self.productions.append(Production(num, head, body))
            return num

        # 0. 增广文法
        add("S'", ["Program"])

        # 1. Program -> compUnit
        add("Program", ["compUnit"])

        # 2. compUnit -> topUnit compUnit | ε
        add("compUnit", ["topUnit", "compUnit"])
        add("compUnit", [])

        # 3. topUnit -> constDecl | type Ident topRest
        add("topUnit", ["constDecl"])
        add("topUnit", ["type", "Ident", "topRest"])

        # 4. topRest -> '(' funcFParamsOpt ')' block   (函数定义)
        #           | firstVarInit varDeclRestTail ';'  (变量声明)
        add("topRest", ["(", "funcFParamsOpt", ")", "block"])
        add("topRest", ["firstVarInit", "varDeclRestTail", ";"])

        # 5. firstVarInit -> '=' initVal | ε
        add("firstVarInit", ["=", "initVal"])
        add("firstVarInit", [])

        # 6. varDeclRestTail -> ',' varDef varDeclRestTail | ε
        add("varDeclRestTail", [",", "varDef", "varDeclRestTail"])
        add("varDeclRestTail", [])

        # 7. constDecl -> const type constDefList ';'
        add("constDecl", ["const", "type", "constDefList", ";"])

        # 8. type -> int | float | void
        add("type", ["int"])
        add("type", ["float"])
        add("type", ["void"])

        # 9. constDefList -> constDef constDefListTail
        add("constDefList", ["constDef", "constDefListTail"])

        # 10. constDefListTail -> ',' constDef constDefListTail | ε
        add("constDefListTail", [",", "constDef", "constDefListTail"])
        add("constDefListTail", [])

        # 11. constDef -> Ident '=' constInitVal
        add("constDef", ["Ident", "=", "constInitVal"])

        # 12. constInitVal -> constExp
        add("constInitVal", ["constExp"])

        # 13. varDef -> Ident varDefOpt
        add("varDef", ["Ident", "varDefOpt"])

        # 14. varDefOpt -> '=' initVal | ε
        add("varDefOpt", ["=", "initVal"])
        add("varDefOpt", [])

        # 15. initVal -> exp
        add("initVal", ["exp"])

        # 16. funcFParamsOpt -> funcFParams | ε
        add("funcFParamsOpt", ["funcFParams"])
        add("funcFParamsOpt", [])

        # 17. funcFParams -> funcFParam funcFParamsTail
        add("funcFParams", ["funcFParam", "funcFParamsTail"])

        # 18. funcFParamsTail -> ',' funcFParam funcFParamsTail | ε
        add("funcFParamsTail", [",", "funcFParam", "funcFParamsTail"])
        add("funcFParamsTail", [])

        # 19. funcFParam -> type Ident
        add("funcFParam", ["type", "Ident"])

        # 20. block -> '{' blockItems '}'
        add("block", ["{", "blockItems", "}"])

        # 21. blockItems -> blockItem blockItems | ε
        add("blockItems", ["blockItem", "blockItems"])
        add("blockItems", [])

        # 22. blockItem -> decl | stmt
        add("blockItem", ["decl"])
        add("blockItem", ["stmt"])

        # 23. decl -> constDecl | varDecl
        add("decl", ["constDecl"])
        add("decl", ["varDecl"])

        # 24. varDecl -> type varDefList ';'
        add("varDecl", ["type", "varDefList", ";"])

        # 25. varDefList -> varDef varDefListTail
        add("varDefList", ["varDef", "varDefListTail"])

        # 26. varDefListTail -> ',' varDef varDefListTail | ε
        add("varDefListTail", [",", "varDef", "varDefListTail"])
        add("varDefListTail", [])

        # 27. stmt -> lVal '=' exp ';'
        add("stmt", ["lVal", "=", "exp", ";"])
        # 27b. stmt -> exp ';'
        add("stmt", ["exp", ";"])
        # 27c. stmt -> ';'
        add("stmt", [";"])
        # 27d. stmt -> block
        add("stmt", ["block"])
        # 27e. stmt -> if '(' cond ')' stmt elsePart
        add("stmt", ["if", "(", "cond", ")", "stmt", "elsePart"])
        # 27f. stmt -> return returnOpt ';'
        add("stmt", ["return", "returnOpt", ";"])

        # 28. elsePart -> else stmt | ε
        add("elsePart", ["else", "stmt"])
        add("elsePart", [])

        # 29. returnOpt -> exp | ε
        add("returnOpt", ["exp"])
        add("returnOpt", [])

        # 30. exp -> addExp
        add("exp", ["addExp"])

        # 31. cond -> lOrExp
        add("cond", ["lOrExp"])

        # 32. lVal -> Ident
        add("lVal", ["Ident"])

        # 33. primaryExp -> '(' exp ')' | lVal | number
        add("primaryExp", ["(", "exp", ")"])
        add("primaryExp", ["lVal"])
        add("primaryExp", ["number"])

        # 34. number -> IntConst | floatConst
        add("number", ["IntConst"])
        add("number", ["floatConst"])

        # 35. unaryExp -> primaryExp | Ident '(' funcRParamsOpt ')' | unaryOp unaryExp
        add("unaryExp", ["primaryExp"])
        add("unaryExp", ["Ident", "(", "funcRParamsOpt", ")"])
        add("unaryExp", ["unaryOp", "unaryExp"])

        # 36. funcRParamsOpt -> funcRParams | ε
        add("funcRParamsOpt", ["funcRParams"])
        add("funcRParamsOpt", [])

        # 37. unaryOp -> '+' | '-' | '!'
        add("unaryOp", ["+"])
        add("unaryOp", ["-"])
        add("unaryOp", ["!"])

        # 38. funcRParams -> funcRParam funcRParamsTail2
        add("funcRParams", ["funcRParam", "funcRParamsTail2"])

        # 39. funcRParamsTail2 -> ',' funcRParam funcRParamsTail2 | ε
        add("funcRParamsTail2", [",", "funcRParam", "funcRParamsTail2"])
        add("funcRParamsTail2", [])

        # 40. funcRParam -> exp
        add("funcRParam", ["exp"])

        # 41. mulExp -> unaryExp mulExpTail
        add("mulExp", ["unaryExp", "mulExpTail"])

        # 42. mulExpTail -> '*' unaryExp mulExpTail | '/' unaryExp mulExpTail | '%' unaryExp mulExpTail | ε
        add("mulExpTail", ["*", "unaryExp", "mulExpTail"])
        add("mulExpTail", ["/", "unaryExp", "mulExpTail"])
        add("mulExpTail", ["%", "unaryExp", "mulExpTail"])
        add("mulExpTail", [])

        # 43. addExp -> mulExp addExpTail
        add("addExp", ["mulExp", "addExpTail"])

        # 44. addExpTail -> '+' mulExp addExpTail | '-' mulExp addExpTail | ε
        add("addExpTail", ["+", "mulExp", "addExpTail"])
        add("addExpTail", ["-", "mulExp", "addExpTail"])
        add("addExpTail", [])

        # 45. relExp -> addExp relExpTail
        add("relExp", ["addExp", "relExpTail"])

        # 46. relExpTail -> '<' addExp relExpTail | '>' addExp relExpTail | '<=' addExp relExpTail | '>=' addExp relExpTail | ε
        add("relExpTail", ["<", "addExp", "relExpTail"])
        add("relExpTail", [">", "addExp", "relExpTail"])
        add("relExpTail", ["<=", "addExp", "relExpTail"])
        add("relExpTail", [">=", "addExp", "relExpTail"])
        add("relExpTail", [])

        # 47. eqExp -> relExp eqExpTail
        add("eqExp", ["relExp", "eqExpTail"])

        # 48. eqExpTail -> '==' relExp eqExpTail | '!=' relExp eqExpTail | ε
        add("eqExpTail", ["==", "relExp", "eqExpTail"])
        add("eqExpTail", ["!=", "relExp", "eqExpTail"])
        add("eqExpTail", [])

        # 49. lAndExp -> eqExp lAndExpTail
        add("lAndExp", ["eqExp", "lAndExpTail"])

        # 50. lAndExpTail -> '&&' eqExp lAndExpTail | ε
        add("lAndExpTail", ["&&", "eqExp", "lAndExpTail"])
        add("lAndExpTail", [])

        # 51. lOrExp -> lAndExp lOrExpTail
        add("lOrExp", ["lAndExp", "lOrExpTail"])

        # 52. lOrExpTail -> '||' lAndExp lOrExpTail | ε
        add("lOrExpTail", ["||", "lAndExp", "lOrExpTail"])
        add("lOrExpTail", [])

        # 53. constExp -> addExp
        add("constExp", ["addExp"])

    def _collect_symbols(self):
        """收集非终结符和终结符"""
        for prod in self.productions:
            self.non_terminals.add(prod.head)

        for prod in self.productions:
            for symbol in prod.body:
                if symbol not in self.non_terminals:
                    self.terminals.add(symbol)

        self.terminals.add('$')

    def get_productions_by_head(self, head: str) -> List[Production]:
        return [p for p in self.productions if p.head == head]

    def get_production_by_num(self, num: int) -> Optional[Production]:
        for p in self.productions:
            if p.num == num:
                return p
        return None

    def is_terminal(self, symbol: str) -> bool:
        return symbol in self.terminals

    def is_non_terminal(self, symbol: str) -> bool:
        return symbol in self.non_terminals

    def print_grammar(self):
        print("C-- 文法:")
        for prod in self.productions:
            print(prod)
        print(f"\n产生式数量: {len(self.productions)}")
        print(f"非终结符 ({len(self.non_terminals)}): {sorted(self.non_terminals)}")
        print(f"终结符 ({len(self.terminals)}): {sorted(self.terminals)}")


if __name__ == '__main__':
    grammar = Grammar()
    grammar.print_grammar()
