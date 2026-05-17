"""
词法分析器主类 - 适配大作业输出格式

输出格式: [单词符号]\t<[种别],[内容]>

种别编号:
  KW:  int=1, void=2, return=3, const=4, main=5, float=6, if=7, else=8
  OP:  +=6, -=7, *=8, /=9, %=10, ==11, >=12, <=13, ===14, <=15, >=16, !=17, &&=18, ||=19
  SE:  (=20, )=21, {=22, }=23, ;=24, ,=25
  IDN: 值为标识符字符串
  INT: 值为整数字符串
  FLOAT: 值为浮点数字符串
"""
from dataclasses import dataclass
from .regex_parser import (
    build_identifier_regex,
    build_integer_regex, build_float_regex,
    build_operator_regex, build_delimiter_regex
)
from .nfa import NFA, NFABuilder, combine_nfas
from .dfa import DFA
from .converter import nfa_to_dfa, minimize_dfa
from typing import List, Optional, Tuple

# 关键字（不区分大小写）
KEYWORDS = {
    'int': 1, 'void': 2, 'return': 3, 'const': 4, 'main': 5,
    'float': 6, 'if': 7, 'else': 8
}

# 运算符编号（按 PDF 规范）
# (6)+(7)-(8)*(9)/(10)%(11)=(12)>(13)<(14)==(15)<=(16)>=(17)!=(18)&&(19)||
# 即: +=6, -=7, *=8, /=9, %=10, ==11, >=12, <=13, ===14, <=15, >=16, !=17, &&=18, ||=19
OPERATORS = [
    ('==', 14), ('<=', 15), ('>=', 16), ('!=', 17), ('&&', 18), ('||', 19),
    ('+', 6), ('-', 7), ('*', 8), ('/', 9), ('%', 10),
    ('=', 11), ('>', 12), ('<', 13), ('!', 0)
]
OPERATOR_NUMS = dict(OPERATORS)

# 界符编号
# (=20, )=21, {=22, }=23, ;=24, ,=25
DELIMITERS = [
    ('(', 20), (')', 21), ('{', 22), ('}', 23), (';', 24), (',', 25)
]
DELIMITER_NUMS = dict(DELIMITERS)


@dataclass
class Token:
    """Token定义"""
    type: str  # KW, IDN, INT, FLOAT, OP, SE
    value: str  # token值
    num: int | str  # 关键字/运算符/界符使用编号，字面量和标识符保留原值
    line: int  # 行号
    col: int  # 列号


class Lexer:
    """词法分析器"""

    def __init__(self):
        self.dfa: DFA | None = None
        self._build_dfa()

    def _build_dfa(self):
        """构建用于词法分析的DFA

        注意：由于关键字和标识符的冲突，我们采用以下策略：
        1. 为标识符、整数、浮点数、运算符、界符分别构建DFA
        2. 运行时使用最长匹配，并在输出时检查标识符是否为关键字
        """
        # 构建各token类型的NFA
        nfas: List[NFA] = []
        builder = NFABuilder()

        # 浮点数（必须在整数之前，因为浮点数包含整数模式）
        float_nfa = builder.build(build_float_regex(), 'FLOAT')
        nfas.append(float_nfa)

        # 整数
        int_nfa = builder.build(build_integer_regex(), 'INT')
        nfas.append(int_nfa)

        # 标识符
        idn_nfa = builder.build(build_identifier_regex(), 'IDN')
        nfas.append(idn_nfa)

        # 运算符，为每个字符构建一个NFA，双字符优先（DFA最长匹配自动处理）
        for op, _ in OPERATORS:
            op_nfa = builder.build(build_operator_regex(op), 'OP', op)
            nfas.append(op_nfa)

        # 界符
        for delim, _ in DELIMITERS:
            delim_nfa = builder.build(build_delimiter_regex(delim), 'SE', delim)
            nfas.append(delim_nfa)

        combined_nfa = combine_nfas(nfas)

        # 转换为DFA
        dfa = nfa_to_dfa(combined_nfa)

        # 最小化DFA
        self.dfa = minimize_dfa(dfa)

    def tokenize(self, source: str) -> List[Token]:
        """对源代码进行词法分析

        Args:
            source: 源代码字符串

        Returns:
            Token列表
        """
        tokens = []
        line = 1
        col = 1
        pos = 0

        while pos < len(source):
            char = source[pos]

            # 跳过空白字符和制表符
            if char in ' \t':
                pos += 1
                col += 1
                continue

            # 换行符
            if char == '\n':
                pos += 1
                line += 1
                col = 1
                continue

            # 尝试匹配token
            token, new_pos = self._match_token(source, pos, line, col)

            if token:
                tokens.append(token)
                # 更新位置（token可能跨多字符）
                for i in range(pos, new_pos):
                    if source[i] == '\n':
                        line += 1
                        col = 1
                    else:
                        col += 1
                pos = new_pos
            else:
                # 无法识别的字符，报告错误
                tokens.append(Token(
                    type='ERROR',
                    value=char,
                    num=-1,
                    line=line,
                    col=col
                ))
                pos += 1
                col += 1

        return tokens

    def _match_token(self, source: str, start_pos: int, line: int, col: int) -> Tuple[Optional[Token], int]:
        """尝试从start_pos开始匹配一个token（最长匹配）

        Args:
            source: 源代码
            start_pos: 起始位置
            line: 当前行号
            col: 当前列号

        Returns:
            (匹配的token, 结束位置) 或 (None, start_pos)
        """
        matches: List[tuple] = []
        cur_state = self.dfa.start
        pos = start_pos

        while pos < len(source):
            ch = source[pos]
            nxt_state = cur_state.get_transition(ch)

            if nxt_state is None:
                break

            cur_state = nxt_state
            pos += 1

            if cur_state.is_final:
                matches.append((pos, cur_state.type, cur_state.value))

        if not matches:
            return None, start_pos

        # 取最后一个（最长匹配）
        end_pos, token_type, value = matches[-1]
        matched_str = source[start_pos: end_pos]

        # 检查标识符是否为关键字
        if token_type == 'IDN':
            lower_str = matched_str.lower()
            if lower_str in KEYWORDS:
                token_num = KEYWORDS[lower_str]
                return Token(type='KW', value=matched_str, num=token_num, line=line, col=col), end_pos

        token_num = self._get_token_num(token_type, matched_str)

        return Token(type=token_type, value=matched_str, num=token_num, line=line, col=col), end_pos

    def _get_token_num(self, token_type: str, value: str) -> int | str:
        """获取token编号"""
        if token_type == 'KW':
            return KEYWORDS.get(value.lower(), 0)
        elif token_type == 'OP':
            return OPERATOR_NUMS.get(value, 0)
        elif token_type == 'SE':
            return DELIMITER_NUMS.get(value, 0)
        elif token_type in ('INT', 'FLOAT', 'IDN'):
            return value
        return 0

    def format_token(self, token: Token) -> str:
        """格式化输出token，符合大作业规范: [单词符号]\t<[种别],[内容]>"""
        if token.type == 'ERROR':
            return f"{token.value}\t<ERROR,{token.num}>"
        elif token.type == 'INT':
            return f"{token.value}\t<INT,{token.value}>"
        elif token.type == 'FLOAT':
            return f"{token.value}\t<FLOAT,{token.value}>"
        elif token.type == 'IDN':
            return f"{token.value}\t<IDN,{token.value}>"
        else:
            return f"{token.value}\t<{token.type},{token.num}>"

    def format_tokens(self, tokens: List[Token]) -> str:
        """格式化整个token序列"""
        return '\n'.join(self.format_token(token) for token in tokens)


def run_lexer(source: str) -> str:
    """运行词法分析器并返回格式化输出"""
    lexer = Lexer()
    tokens = lexer.tokenize(source)
    return lexer.format_tokens(tokens)
