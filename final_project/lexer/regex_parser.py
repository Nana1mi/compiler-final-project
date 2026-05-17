from copy import deepcopy
from .regex_ast import *

REGEX_CHARS = set(r'[]()+*\|')

class RegexParser:

    def __init__(self, pattern: str):
        """
        pattern: 输入正则表达式
        position: 当前解析的位置
        """
        self.pattern = pattern
        self.position = 0

    def peek(self):
        """
        查看当前位置的字符
        """
        if self.position < len(self.pattern):
            return self.pattern[self.position]

        return None

    def consume(self):
        """
        查看当前位置的字符，然后越过它
        """
        if self.position < len(self.pattern):
            ch = self.pattern[self.position]
            self.position += 1
            return ch

        return None

    def parse(self):
        return self.parse_alter()

    def parse_alter(self):
        """
        比如 a|b, a|b|c
        """
        left = self.parse_concat()

        while self.peek() == '|':
            self.consume() # consume '|'
            right = self.parse_concat()
            left = AlterNode(left, right)

        return left

    def parse_concat(self):
        """
        比如 abc, (a|b)c
        不可解析 a|b
        """
        nodes = []
        while self.peek() is not None and self.peek() not in '|)': # ')' 用来处理 (a|b)c 这种情形
            node = self.parse_repeat()
            nodes.append(node)

        if len(nodes) == 0:
            return EpsilonNode()
        elif len(nodes) == 1:
            return nodes[0]
        else:
            result = nodes[0]
            for i in range(1, len(nodes)):
                result = ConcatNode(result, nodes[i])
            return result

    def parse_repeat(self):
        """
        比如 a, a*, (a|b), (a|b)*, [a-z]+
        不可解析 abc, ab*
        """
        node = self.parse_base()
        ch = self.peek()

        if ch == '*':
            self.consume()
            return ClosureNode(node)
        if ch == '+':
            self.consume()
            return ConcatNode(node, ClosureNode(deepcopy(node))) # 深拷贝

        return node

    def parse_base(self):
        """
        比如 epsilon, a, (a|b), [a-z]
        不可解析 abc
        """
        ch = self.peek()
        if ch is None:
            return EpsilonNode()

        if ch == '(':
            self.consume() # consume '('
            node = self.parse_alter()
            self.consume() # consume ')'
            return node

        if ch == '[':
            return self.parse_charset()

        if ch == '\\': # 转义 '\'
            self.consume()
            escaped = self.consume()
            return CharNode(escaped)

        # 否则是单个字符
        self.consume()
        return CharNode(ch)

    def parse_charset(self):
        """
        比如 [bcd], [a-z], [1-9A-Z]
        """
        chars = set()
        self.consume() # consume '['

        while self.peek() != ']':
            ch = self.consume()
            if self.peek() == '-':
                self.consume()
                end_ch = self.consume()
                for i in range(ord(ch), ord(end_ch)+1):
                    chars.add(chr(i))
            else:
                chars.add(ch)

        self.consume() # consume ']'
        return CharSetNode(chars)

def parse_regex(text: str) -> RegexNode:
    """
    text: 正则表达式
    将正则表达式构建成AST
    """
    parser = RegexParser(text)
    return parser.parse()

def escape_regex(text:str):
    """对表达式进行转义"""
    escaped = []
    for ch in text:
        if ch in REGEX_CHARS:
            escaped.append('\\')
        escaped.append(ch)
    return ''.join(escaped)

def build_keyword_regex(kw: str):
    """关键字AST"""
    return parse_regex(escape_regex(kw))

def build_identifier_regex():
    """标识符AST"""
    return parse_regex('[a-zA-Z_][a-zA-Z0-9_]*')

def build_integer_regex():
    """整数AST"""
    return parse_regex('[0-9]+')

def build_float_regex():
    """浮点数AST"""
    return parse_regex('[0-9]+.[0-9]+')

def build_operator_regex(op: str):
    """操作符AST"""
    return parse_regex(escape_regex(op))

def build_delimiter_regex(ch: str):
    """界符AST"""
    return CharNode(ch)
