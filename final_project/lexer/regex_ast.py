"""
+ 闭包可以用 * 闭包表示
后续可以加入 ? 节点
"""

from dataclasses import dataclass
from typing import Set

@dataclass
class RegexNode:
    """基类节点"""
    pass

@dataclass
class CharNode(RegexNode):
    """一个字符"""
    char: str

@dataclass
class EpsilonNode(RegexNode):
    """epsilon"""
    pass

@dataclass
class ConcatNode(RegexNode):
    """拼接两个节点 eg: ab = a . b"""
    left: RegexNode
    right: RegexNode

@dataclass
class AlterNode(RegexNode):
    """从两个节点中选一个  eg: a | b"""
    left: RegexNode
    right: RegexNode

@dataclass
class ClosureNode(RegexNode):
    """计算闭包 是 * 不是 +"""
    child: RegexNode

@dataclass
class CharSetNode(RegexNode):
    """字符集合  eg: [a-z]"""
    charset: Set[str]