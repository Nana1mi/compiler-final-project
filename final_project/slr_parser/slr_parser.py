"""
SLR 语法分析器 - 带语法树构建和 LLVM IR 生成

输出:
1. 词法分析: [单词符号]\t<[种别],[内容]>
2. 语法分析: [序号]\t[栈顶符号]#[面临输入符号]\t[执行动作]
3. 中间代码: LLVM IR (.ll 格式)
"""

import sys
import os
import json
from typing import List, Optional, Dict
from slr_grammar import Grammar, Production
from slr_table import SLRTable


class Token:
    def __init__(self, type_: str, value: str, num):
        self.type = type_
        self.value = value
        self.num = num

    def __repr__(self):
        return f"Token({self.type}, {self.value!r})"


def token_to_grammar_symbol(token: Token) -> str:
    if token.type == 'KW':
        # PDF 要求 main 按关键字输出，但附录文法中函数名位置仍按 Ident 处理。
        if token.value.lower() == 'main':
            return 'Ident'
        return token.value.lower()
    elif token.type == 'IDN':
        return 'Ident'
    elif token.type == 'INT':
        return 'IntConst'
    elif token.type == 'FLOAT':
        return 'floatConst'
    elif token.type in ('OP', 'SE'):
        return token.value
    else:
        return token.value


class ASTNode:
    """语法树节点"""
    _id_counter = 0

    def __init__(self, name: str, children: List['ASTNode'] = None, value: str = ""):
        self.name = name
        self.children = children or []
        self.value = value
        ASTNode._id_counter += 1
        self.id = ASTNode._id_counter

    def __repr__(self):
        return f"ASTNode({self.name}, children={len(self.children)})"

    def to_dict(self) -> dict:
        data = {
            "id": self.id,
            "name": self.name,
            "children": [child.to_dict() for child in self.children],
        }
        if self.value:
            data["value"] = self.value
        return data


class SLRParser:
    """SLR 语法分析器 + 语法树构建"""

    def __init__(self):
        self.grammar = Grammar()
        self.table = SLRTable(self.grammar)
        self.step = 0

    def parse(self, tokens: List[Token]) -> Optional[ASTNode]:
        self.step = 0
        state_stack = [0]
        symbol_stack = ['$']
        ast_stack: List[Optional[ASTNode]] = [None]  # 与 symbol_stack 同步

        input_pos = 0

        while True:
            if not state_stack:
                self._print_step("$", self._get_input_str(tokens, input_pos), "error")
                return None

            current_state = state_stack[-1]

            if input_pos < len(tokens):
                token = tokens[input_pos]
                current_input = self._get_input_str(tokens, input_pos)
                terminal = token_to_grammar_symbol(token)
            else:
                token = None
                current_input = '$'
                terminal = '$'

            action = self.table.get_action(current_state, terminal)

            if action is None:
                self._print_step(symbol_stack[-1], current_input, "error")
                return None

            action_type = action[0]

            if action_type == 'shift':
                next_state = action[1]
                self._print_step(symbol_stack[-1], current_input, "move")
                state_stack.append(next_state)
                symbol_stack.append(terminal)
                # 创建叶子节点
                if terminal in ('Ident', 'IntConst', 'floatConst'):
                    ast_stack.append(ASTNode(terminal, value=token.value if token else ''))
                else:
                    ast_stack.append(ASTNode(terminal, value=token.value if token else terminal))
                input_pos += 1

            elif action_type == 'reduce':
                prod_num = action[1]
                prod = self.grammar.get_production_by_num(prod_num)

                self._print_step(prod.head, current_input, f"reduction {prod.num}")

                body_len = len(prod.body)
                child_nodes = []
                for _ in range(body_len):
                    node = ast_stack.pop()
                    if node:
                        child_nodes.append(node)
                    state_stack.pop()
                    symbol_stack.pop()

                child_nodes.reverse()  # 恢复左到右顺序

                if prod.head == "S'":
                    # 增广文法，直接取子节点
                    root = child_nodes[0] if child_nodes else ASTNode("Program")
                    ast_stack.append(root)
                elif prod.head in ('IntConst', 'floatConst', 'Ident'):
                    # 叶子节点已在 shift 时创建
                    ast_stack.append(child_nodes[0] if child_nodes else ASTNode(prod.head))
                else:
                    ast_stack.append(ASTNode(prod.head, children=child_nodes))

                prev_state = state_stack[-1]
                next_state = self.table.get_goto(prev_state, prod.head)
                if next_state is None:
                    return None
                state_stack.append(next_state)
                symbol_stack.append(prod.head)

            elif action_type == 'accept':
                self._print_step("Program", "$", "accept")
                root = ast_stack[-1]
                return root

            elif action_type == 'error':
                self._print_step(symbol_stack[-1], current_input, "error")
                return None

        return None

    def _get_input_str(self, tokens: List[Token], pos: int) -> str:
        if pos < len(tokens):
            token = tokens[pos]
            if token.type == 'KW' and token.value.lower() == 'main':
                return 'Ident'
            if token.type == 'IDN':
                return 'Ident'
            elif token.type == 'INT':
                return 'IntConst'
            elif token.type == 'FLOAT':
                return 'floatConst'
            else:
                return token.value
        return '$'

    def _print_step(self, stack_top: str, current_input: str, action: str):
        self.step += 1
        print(f"{self.step}\t{stack_top}#{current_input}\t{action}")


# ============================================================
# LLVM IR 生成器
# ============================================================

class IRGenerator:
    """将语法树转换为 LLVM IR (.ll 格式)"""

    def __init__(self):
        self.module_id = "sysy2022_compiler"
        self.source_filename = ""
        self.reg_counter = 0
        self.label_counter = 0
        self.variables: Dict[str, str] = {}  # var_name -> alloca ptr
        self.global_variables: Dict[str, str] = {}  # var_name -> global ptr
        self.variable_types: Dict[str, str] = {}
        self.current_func = None
        self.current_bb = None
        self.lines: List[str] = []
        self.param_counter = 0

    def new_reg(self) -> str:
        self.reg_counter += 1
        return f"%op{self.reg_counter - 1}"

    def new_label(self) -> str:
        self.label_counter += 1
        return f"label_{self.label_counter}"

    def emit(self, line: str):
        self.lines.append(line)

    def _current_block_terminated(self) -> bool:
        """判断当前基本块是否已有终结指令（ret 或 br）。"""
        for line in reversed(self.lines):
            stripped = line.strip()
            if not stripped:
                continue
            if stripped.endswith(':'):
                return False
            return stripped.startswith('ret ') or stripped.startswith('br ')
        return False

    def generate(self, root: ASTNode, source_file: str = "") -> str:
        self.source_filename = source_file
        self.lines = []
        self.reg_counter = 0
        self.label_counter = 0
        self.variables = {}
        self.global_variables = {}
        self.variable_types = {}

        # 模块头部
        self.emit(f"; ModuleID = '{self.module_id}'")
        self.emit(f"source_filename = \"{self.source_filename}\"")
        self.emit("")

        # 声明库函数
        self.emit("declare i32 @getint()")
        self.emit("declare i32 @getch()")
        self.emit("declare i32 @getarray(i32*)")
        self.emit("declare void @putint(i32)")
        self.emit("declare void @putch(i32)")
        self.emit("declare void @putarray(i32, i32*)")
        self.emit("declare void @starttime()")
        self.emit("declare void @stoptime()")
        self.emit("")

        # 遍历顶层单元
        self._visit_compUnit(root)

        return '\n'.join(self.lines)

    def _visit_compUnit(self, node: ASTNode):
        """compUnit -> topUnit compUnit | ε"""
        # 处理 Program 根节点（包裹 compUnit）
        if node.name == 'Program':
            if node.children:
                self._visit_compUnit(node.children[0])
            return
        # 处理 S' 等包裹节点
        if node.name == "S'":
            if node.children:
                self._visit_compUnit(node.children[0])
            return
        if not node.children:
            return
        # topUnit compUnit
        if len(node.children) >= 1:
            self._visit_topUnit(node.children[0])
        if len(node.children) >= 2:
            self._visit_compUnit(node.children[1])

    def _visit_topUnit(self, node: ASTNode):
        """topUnit -> constDecl | type Ident topRest"""
        if not node.children:
            return
        first_child = node.children[0]
        if first_child.name == 'constDecl':
            # constDecl
            self._visit_constDecl(first_child)
        else:
            # type Ident topRest
            if len(node.children) < 3:
                return
            type_node = node.children[0]
            ident_node = node.children[1]
            rest_node = node.children[2]
            type_name = self._get_type_name(type_node)

            if rest_node.children and rest_node.children[0].name == '(':
                # 函数定义
                self._visit_funcDef(type_name, ident_node, rest_node)
            else:
                # 变量声明
                self._visit_varDecl(type_name, ident_node, rest_node)

    def _visit_constDecl(self, node: ASTNode):
        """constDecl -> const type constDefList ';'"""
        if len(node.children) < 3:
            return
        type_name = self._get_type_name(node.children[1])
        self._visit_constDefList(type_name, node.children[2])

    def _visit_constDefList(self, type_name: str, node: ASTNode):
        """constDefList -> constDef constDefListTail"""
        if not node.children:
            return
        self._visit_constDef(type_name, node.children[0])
        if len(node.children) >= 2:
            self._visit_constDefListTail(type_name, node.children[1])

    def _visit_constDefListTail(self, type_name: str, node: ASTNode):
        """constDefListTail -> ',' constDef constDefListTail | ε"""
        if not node.children:
            return
        if len(node.children) >= 2:
            self._visit_constDef(type_name, node.children[1])
        if len(node.children) >= 3:
            self._visit_constDefListTail(type_name, node.children[2])

    def _visit_constDef(self, type_name: str, node: ASTNode):
        """constDef -> Ident '=' constInitVal"""
        if len(node.children) < 3:
            return
        var_name = node.children[0].value
        init_val = self._eval_const(node.children[2])
        if self.current_func is None:
            self.emit(f"@{var_name} = constant {type_name} {init_val}")
            self.global_variables[var_name] = f"@{var_name}"
            self.variable_types[var_name] = type_name
        else:
            alloca_ptr = self.new_reg()
            self.emit(f"  {alloca_ptr} = alloca {type_name}")
            self.emit(f"  store {type_name} {init_val}, {type_name}* {alloca_ptr}")
            self.variables[var_name] = alloca_ptr
            self.variable_types[var_name] = type_name

    def _visit_varDecl(self, type_name: str, ident_node: ASTNode, rest_node: ASTNode):
        """变量声明: type Ident [= initVal] [, varDef]* ;"""
        if self.current_func is None:
            # 全局变量
            var_name = ident_node.value
            init_val = 0
            # 检查是否有初始化
            if rest_node.children and rest_node.children[0].name == 'firstVarInit':
                init_val = self._eval_const(rest_node.children[0])
            self.emit(f"@{var_name} = global {type_name} {init_val}")
            self.global_variables[var_name] = f"@{var_name}"
            self.variable_types[var_name] = type_name
        else:
            # 局部变量
            var_name = ident_node.value
            alloca_ptr = self.new_reg()
            self.emit(f"  {alloca_ptr} = alloca {type_name}")
            self.variables[var_name] = alloca_ptr
            self.variable_types[var_name] = type_name

            # 检查是否有初始化
            if rest_node.children and rest_node.children[0].name == 'firstVarInit':
                first_var_init = rest_node.children[0]
                init_node = self._get_initializer_node(first_var_init)
                if init_node:
                    init_ty, init_val = self._visit_exp(init_node)
                    self.emit(f"  store {init_ty} {init_val}, {type_name}* {alloca_ptr}")

    def _visit_funcDef(self, type_name: str, ident_node: ASTNode, rest_node: ASTNode):
        """函数定义: type Ident '(' funcFParamsOpt ')' block"""
        func_name = ident_node.value
        self.current_func = func_name
        self.variables = {}
        self.param_counter = 0
        self.has_return = False  # 标记是否已生成 return 语句

        is_void = type_name == 'void'
        return_type = 'void' if is_void else 'i32'

        # 获取参数
        # topRest -> '(' funcFParamsOpt ')' block, children are ['(', funcFParamsOpt, ')', block]
        params = []
        param_types = []
        if len(rest_node.children) > 1:
            func_params_opt = rest_node.children[1]  # funcFParamsOpt
            if func_params_opt.children and func_params_opt.children[0].name == 'funcFParams':
                params, param_types = self._visit_funcFParams(func_params_opt.children[0])

        param_str = ', '.join(f'{t} %{n}' for n, t in zip(params, param_types))
        self.emit(f"define {return_type} @{func_name}({param_str}) {{")

        entry_label = self.new_label()
        self.emit(f"{entry_label}:")
        self.current_bb = entry_label

        # 为参数创建 alloca (use param names from the source)
        for pname, ptype in zip(params, param_types):
            alloca_ptr = self.new_reg()
            self.emit(f"  {alloca_ptr} = alloca {ptype}")
            self.variables[pname] = alloca_ptr
            self.variable_types[pname] = ptype
            # store 参数值 (use %pname to reference the parameter)
            self.emit(f"  store {ptype} %{pname}, {ptype}* {alloca_ptr}")

        # 访问函数体
        # topRest -> '(' funcFParamsOpt ')' block, so block is at index 3
        block_node = rest_node.children[3] if len(rest_node.children) > 3 else None
        if block_node and block_node.name == 'block':
            self._visit_block(block_node)
        elif len(rest_node.children) > 2:
            # 备选：尝试索引 2
            block_node = rest_node.children[2]
            if block_node.name == 'block':
                self._visit_block(block_node)

        # 如果当前基本块没有终结指令，添加默认 return。
        if not self._current_block_terminated() and is_void:
            self.emit("  ret void")
        elif not self._current_block_terminated() and not is_void:
            self.emit(f"  ret i32 0")

        self.emit("}")
        self.emit("")
        self.current_func = None

    def _visit_funcFParams(self, node: ASTNode) -> tuple:
        """funcFParams -> funcFParam funcFParamsTail"""
        names = []
        types = []
        if node.children:
            param = node.children[0]
            if param.children and len(param.children) >= 2:
                ptype = self._get_type_name(param.children[0])
                pname = param.children[1].value
                names.append(pname)
                types.append(ptype)
            if len(node.children) >= 2:
                tail = node.children[1]
                n2, t2 = self._visit_funcFParamsTail(tail)
                names.extend(n2)
                types.extend(t2)
        return names, types

    def _visit_funcFParamsTail(self, node: ASTNode) -> tuple:
        if not node.children:
            return [], []
        names = []
        types = []
        # funcFParamsTail -> ',' funcFParam funcFParamsTail | ε
        if len(node.children) >= 2:
            param = node.children[1]
            if param.children and len(param.children) >= 2:
                ptype = self._get_type_name(param.children[0])
                pname = param.children[1].value
                names.append(pname)
                types.append(ptype)
            if len(node.children) >= 3:
                n2, t2 = self._visit_funcFParamsTail(node.children[2])
                names.extend(n2)
                types.extend(t2)
        return names, types

    def _visit_funcRParams(self, node: ASTNode) -> list:
        """funcRParams -> funcRParam funcRParamsTail2, returns list of (type, value) tuples"""
        args = []
        if node.children and len(node.children) >= 1:
            param = node.children[0]
            ty, val = self._visit_exp(param.children[0] if param.children else param)
            args.append((ty, val))
            if len(node.children) >= 2:
                args.extend(self._visit_funcRParamsTail2(node.children[1]))
        return args

    def _visit_funcRParamsTail2(self, node: ASTNode) -> list:
        """, funcRParam funcRParamsTail2 | ε"""
        args = []
        if not node.children:
            return args
        if len(node.children) >= 2:
            param = node.children[1]
            ty, val = self._visit_exp(param.children[0] if param.children else param)
            args.append((ty, val))
            if len(node.children) >= 3:
                args.extend(self._visit_funcRParamsTail2(node.children[2]))
        return args

    def _visit_block(self, node: ASTNode):
        """block -> '{' blockItems '}'"""
        if node.children and len(node.children) >= 2:
            self._visit_blockItems(node.children[1])

    def _visit_blockItems(self, node: ASTNode):
        """blockItems -> blockItem blockItems | ε"""
        if not node.children:
            return
        if len(node.children) >= 1:
            self._visit_blockItem(node.children[0])
        if self._current_block_terminated():
            return
        if len(node.children) >= 2:
            self._visit_blockItems(node.children[1])

    def _visit_blockItem(self, node: ASTNode):
        """blockItem -> decl | stmt"""
        if not node.children:
            return
        child = node.children[0]
        if child.name == 'decl':
            self._visit_decl(child)
        else:
            self._visit_stmt(child)

    def _visit_decl(self, node: ASTNode):
        """decl -> constDecl | varDecl"""
        if not node.children:
            return
        child = node.children[0]
        if child.name == 'constDecl':
            self._visit_constDecl(child)
        elif child.name == 'varDecl':
            # varDecl -> type varDefList ';'
            if child.children and len(child.children) >= 2:
                type_name = self._get_type_name(child.children[0])
                vardef_list = child.children[1]
                self._visit_varDefList(type_name, vardef_list)

    def _visit_varDefList(self, type_name: str, node: ASTNode):
        """varDefList -> varDef varDefListTail"""
        if not node.children:
            return
        vardef = node.children[0]
        if vardef.children and len(vardef.children) >= 1:
            ident = vardef.children[0]
            var_name = ident.value
            alloca_ptr = self.new_reg()
            self.emit(f"  {alloca_ptr} = alloca {type_name}")
            self.variables[var_name] = alloca_ptr
            self.variable_types[var_name] = type_name

            if len(vardef.children) >= 2:
                vardef_opt = vardef.children[1]
                init_node = self._get_initializer_node(vardef_opt)
                if init_node:
                    init_ty, init_val = self._visit_exp(init_node)
                    self.emit(f"  store {init_ty} {init_val}, {type_name}* {alloca_ptr}")

        if len(node.children) >= 2:
            tail = node.children[1]
            self._visit_varDefListTail(type_name, tail)

    def _visit_varDefListTail(self, type_name: str, node: ASTNode):
        if not node.children:
            return
        if len(node.children) >= 2:
            vardef = node.children[1]
            if vardef.children and len(vardef.children) >= 1:
                ident = vardef.children[0]
                var_name = ident.value
                alloca_ptr = self.new_reg()
                self.emit(f"  {alloca_ptr} = alloca {type_name}")
                self.variables[var_name] = alloca_ptr
                self.variable_types[var_name] = type_name

                if len(vardef.children) >= 2:
                    vardef_opt = vardef.children[1]
                    init_node = self._get_initializer_node(vardef_opt)
                    if init_node:
                        init_ty, init_val = self._visit_exp(init_node)
                        self.emit(f"  store {init_ty} {init_val}, {type_name}* {alloca_ptr}")

        if len(node.children) >= 3:
            self._visit_varDefListTail(type_name, node.children[2])

    def _visit_stmt(self, node: ASTNode):
        """stmt -> lVal '=' exp ';' | exp ';' | ';' | block | if ... | return ..."""
        if not node.children:
            return

        first = node.children[0]

        if first.name == 'lVal':
            # lVal '=' exp ';'
            var_name = first.children[0].value if first.children else ''
            if len(node.children) >= 3:
                val_ty, val_val = self._visit_exp(node.children[2])
                if var_name in self.variables:
                    ptr = self.variables[var_name]
                    ty = self._get_var_type(var_name)
                    self.emit(f"  store {ty} {val_val}, {ty}* {ptr}")
                elif var_name in self.global_variables:
                    # 全局变量
                    ty = self._get_var_type(var_name)
                    self.emit(f"  store {ty} {val_val}, {ty}* @{var_name}")

        elif first.name in ('addExp', 'lOrExp', 'mulExp', 'relExp', 'eqExp', 'lAndExp', 'exp', 'primaryExp', 'unaryExp', 'number', 'IntConst', 'floatConst', 'Ident', 'lVal', 'unaryOp'):
            # exp ';'
            self._visit_exp(first)

        elif first.name == ';':
            pass  # 空语句

        elif first.name == 'block':
            self._visit_block(first)

        elif first.name == 'if':
            self._visit_if_stmt(node)

        elif first.name == 'return':
            self.has_return = True
            if len(node.children) >= 2:
                return_opt = node.children[1]
                if return_opt.children:
                    val_ty, val_val = self._visit_exp(return_opt.children[0])
                    self.emit(f"  ret {val_ty} {val_val}")
                else:
                    self.emit(f"  ret void")
            else:
                self.emit(f"  ret i32 0")

    def _visit_if_stmt(self, node: ASTNode):
        """if '(' cond ')' stmt elsePart"""
        true_label = self.new_label()
        false_label = self.new_label()
        end_label = self.new_label()

        if len(node.children) >= 4:
            cond_ty, cond_val = self._visit_exp(node.children[2])
            cond_ty, cond_val = self._ensure_i1(cond_ty, cond_val)

        self.emit(f"  br i1 {cond_val}, label %{true_label}, label %{false_label}")
        self.emit("")

        self.emit(f"{true_label}:")
        self.current_bb = true_label
        if len(node.children) >= 5:
            self._visit_stmt(node.children[4])

        true_terminated = self._current_block_terminated()
        if not true_terminated:
            self.emit(f"  br label %{end_label}")
        self.emit("")

        self.emit(f"{false_label}:")
        self.current_bb = false_label
        if len(node.children) >= 6:
            else_part = node.children[5]
            if len(else_part.children) >= 2:
                self._visit_stmt(else_part.children[1])

        false_terminated = self._current_block_terminated()
        if not false_terminated:
            self.emit(f"  br label %{end_label}")
        self.emit("")

        if not true_terminated or not false_terminated:
            self.emit(f"{end_label}:")
            self.current_bb = end_label

    def _visit_exp(self, node: ASTNode) -> tuple:
        """表达式求值，返回 (type, value) 元组"""
        if not node.children:
            if node.name in ('IntConst',):
                return ('i32', node.value)
            elif node.name == 'floatConst':
                return ('float', node.value)
            return ('i32', '0')

        first = node.children[0]

        # 数字常量
        if first.name in ('IntConst',):
            return ('i32', first.value)
        if first.name == 'floatConst':
            return ('float', first.value)

        # 函数调用: unaryExp -> Ident '(' funcRParamsOpt ')'（必须在 Ident 变量引用之前检测）
        if first.name == 'Ident' and len(node.children) >= 4 and node.children[1].name == '(':
            func_name = first.value
            args = []
            if len(node.children) >= 3:
                params_opt = node.children[2]  # funcRParamsOpt
                if params_opt.children and params_opt.children[0].name == 'funcRParams':
                    args = self._visit_funcRParams(params_opt.children[0])
            args_str = ', '.join(f'{t} {v}' for t, v in args)
            ret_reg = self.new_reg()
            self.emit(f"  {ret_reg} = call i32 @{func_name}({args_str})")
            return ('i32', ret_reg)

        # 标识符（变量引用）
        if first.name == 'Ident':
            var_name = first.value
            if var_name in self.variables:
                ptr = self.variables[var_name]
                ty = self._get_var_type(var_name)
                reg = self.new_reg()
                self.emit(f"  {reg} = load {ty}, {ty}* {ptr}")
                return (ty, reg)
            elif var_name in self.global_variables:
                ty = self._get_var_type(var_name)
                reg = self.new_reg()
                self.emit(f"  {reg} = load {ty}, {ty}* @{var_name}")
                return (ty, reg)
            else:
                return ('i32', f'@{var_name}')

        # 一元运算
        if first.name == 'unaryOp':
            op = first.value if first.value else (first.children[0].value if first.children else '')
            operand_ty, operand_val = self._visit_exp(node.children[1])
            if op == '-':
                reg = self.new_reg()
                self.emit(f"  {reg} = sub i32 0, {operand_val}")
                return ('i32', reg)
            elif op == '!':
                reg = self.new_reg()
                self.emit(f"  {reg} = icmp eq i32 {operand_val}, 0")
                return ('i1', reg)
            return (operand_ty, operand_val)

        # 二元运算 — 处理 Tail 节点中的运算符
        # 对于 addExp -> mulExp addExpTail 等节点，需要：
        # 1. 对第一个子节点（mulExp）求值作为左操作数
        # 2. 处理 Tail 子节点，其中可能包含运算符
        if node.name in ('addExp', 'mulExp', 'relExp', 'eqExp', 'lAndExp', 'lOrExp'):
            left_node = node.children[0]
            left = self._visit_exp(left_node)
            # 检查 Tail 节点
            if len(node.children) >= 2:
                tail = node.children[1]
                result = self._process_tail(tail, left)
                if result:
                    return result
            return left

        # 递归求值
        return self._visit_exp(first)

    def _process_tail(self, tail_node: ASTNode, left: tuple) -> tuple:
        """处理 Tail 节点（如 addExpTail、mulExpTail 等）。返回结果，若是 ε 则返回 None。"""
        if not tail_node.children:
            return None
        # Tail -> operator right Tail | ε
        op = tail_node.children[0].name
        if op not in ('+', '-', '*', '/', '%', '<', '>', '<=', '>=', '==', '!=', '&&', '||'):
            return None
        if len(tail_node.children) < 2:
            return None
        right_node = tail_node.children[1]
        right = self._visit_exp(right_node)
        result = self._emit_binary(op, left, right)
        # 检查剩余 Tail 是否还有更多运算符
        if len(tail_node.children) >= 3:
            more = self._process_tail(tail_node.children[2], result)
            if more:
                return more
        return result

    def _emit_binary(self, op: str, left: tuple, right: tuple) -> tuple:
        reg = self.new_reg()
        left_ty, left_val = left
        right_ty, right_val = right

        if op in ('+', '-', '*', '/', '%'):
            if op == '+':
                self.emit(f"  {reg} = add i32 {left_val}, {right_val}")
            elif op == '-':
                self.emit(f"  {reg} = sub i32 {left_val}, {right_val}")
            elif op == '*':
                self.emit(f"  {reg} = mul i32 {left_val}, {right_val}")
            elif op == '/':
                self.emit(f"  {reg} = sdiv i32 {left_val}, {right_val}")
            elif op == '%':
                self.emit(f"  {reg} = srem i32 {left_val}, {right_val}")
            return ('i32', reg)
        elif op in ('<', '>', '<=', '>=', '==', '!='):
            cmp_op = {'<': 'slt', '>': 'sgt', '<=': 'sle', '>=': 'sge', '==': 'eq', '!=': 'ne'}[op]
            self.emit(f"  {reg} = icmp {cmp_op} i32 {left_val}, {right_val}")
            return ('i1', reg)
        elif op == '&&':
            _, left_bool = self._ensure_i1(left_ty, left_val)
            _, right_bool = self._ensure_i1(right_ty, right_val)
            self.emit(f"  {reg} = and i1 {left_bool}, {right_bool}")
            return ('i1', reg)
        elif op == '||':
            _, left_bool = self._ensure_i1(left_ty, left_val)
            _, right_bool = self._ensure_i1(right_ty, right_val)
            self.emit(f"  {reg} = or i1 {left_bool}, {right_bool}")
            return ('i1', reg)
        return ('i32', reg)

    def _get_type_name(self, node: ASTNode) -> str:
        if not node.children:
            return 'i32'
        first = node.children[0]
        if first.name == 'int':
            return 'i32'
        elif first.name == 'float':
            return 'float'
        elif first.name == 'void':
            return 'void'
        return 'i32'

    def _get_var_type(self, var_name: str) -> str:
        return self.variable_types.get(var_name, 'i32')

    def _get_initializer_node(self, node: ASTNode) -> Optional[ASTNode]:
        """从 '= initVal' 风格的辅助节点中提取表达式节点。"""
        if not node.children:
            return None
        if len(node.children) >= 2 and node.children[0].name == '=':
            return node.children[1]
        return node.children[0]

    def _ensure_i1(self, ty: str, val: str) -> tuple:
        if ty == 'i1':
            return ty, val
        reg = self.new_reg()
        if ty == 'float':
            self.emit(f"  {reg} = fcmp une float {val}, 0.0")
        else:
            self.emit(f"  {reg} = icmp ne i32 {val}, 0")
        return 'i1', reg

    def _eval_const(self, node: ASTNode) -> int:
        """求值常量表达式"""
        if not node.children:
            try:
                return int(node.value)
            except:
                return 0
        if node.name == 'IntConst':
            return int(node.value)
        # 递归查找 IntConst
        for child in node.children:
            if child.name == 'IntConst':
                return int(child.value)
            val = self._eval_const(child)
            if val != 0:
                return val
        return 0


def run_pipeline(source: str, source_file: str = "", ir_output_file: str = "", ast_output_file: str = ""):
    """运行完整的编译流水线"""
    # 词法分析
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
    from lexer.lexer import Lexer as LexerClass

    lexer = LexerClass()
    tokens = lexer.tokenize(source)

    print("=== 词法分析 ===")
    print(lexer.format_tokens(tokens))
    print()

    # 语法分析 + IR 生成
    parser = SLRParser()
    print("=== 语法分析 ===")
    root = parser.parse(tokens)

    if root is None:
        print("\n语法分析失败!")
        return None

    if ast_output_file:
        with open(ast_output_file, 'w', encoding='utf-8') as f:
            json.dump(root.to_dict(), f, ensure_ascii=False, indent=2)
            f.write('\n')

    print()
    print("=== 中间代码 (LLVM IR) ===")
    ir_gen = IRGenerator()

    ir = ir_gen.generate(root, source_file)
    print(ir)

    if ir_output_file:
        with open(ir_output_file, 'w', encoding='utf-8') as f:
            f.write(ir)
            f.write('\n')

    return ir


def main():
    if len(sys.argv) > 1:
        filename = sys.argv[1]
        ir_output_file = ""
        ast_output_file = ""
        if "--ir-out" in sys.argv:
            idx = sys.argv.index("--ir-out")
            if idx + 1 >= len(sys.argv):
                print("错误: --ir-out 需要指定一个 .ll 输出路径")
                sys.exit(1)
            ir_output_file = sys.argv[idx + 1]
        if "--ast-out" in sys.argv:
            idx = sys.argv.index("--ast-out")
            if idx + 1 >= len(sys.argv):
                print("错误: --ast-out 需要指定一个 .json 输出路径")
                sys.exit(1)
            ast_output_file = sys.argv[idx + 1]

        if not os.path.exists(filename):
            print(f"错误: 文件 {filename} 不存在")
            sys.exit(1)
        with open(filename, 'r', encoding='utf-8') as f:
            source = f.read()
        run_pipeline(source, os.path.basename(filename), ir_output_file, ast_output_file)
    else:
        test_dir = os.path.join(os.path.dirname(__file__), '..', 'tests')
        for test_file in sorted(os.listdir(test_dir)):
            if test_file.endswith('.sy'):
                filepath = os.path.join(test_dir, test_file)
                with open(filepath, 'r', encoding='utf-8') as f:
                    source = f.read()
                print(f"\n{'='*80}")
                print(f"File: {test_file}")
                print('='*80)
                run_pipeline(source, test_file)


if __name__ == '__main__':
    main()
