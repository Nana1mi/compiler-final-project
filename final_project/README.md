# C-- 编译器前端（词法分析 + SLR 语法分析 + 中间代码生成）

本项目是编译原理课程大作业，实现了一个 C-- 语言的完整编译器前端。
流水线为：**词法分析（DFA） → SLR 语法分析（SLR(1) 分析表） → AST 构建 → LLVM IR 生成**。

---

## 目录结构

```
final_project/
├── lexer/            # 词法分析器（基于正则→NFA→DFA→最小化DFA）
│   ├── lexer.py      #   词法分析器主类，DFA 构建与最长匹配
│   ├── regex_parser.py # 为标识符、整数、浮点数、运算符、界符构建正则
│   ├── nfa.py        #   Thompson NFA 构造（CharNode, ConcatNode, UnionNode, ClosureNode）
│   ├── converter.py  #   子集构造法（NFA→DFA）+ Hopcroft 最小化
│   ├── dfa.py        #   DFA 数据结构与状态转移
│   ├── regex_ast.py  #   正则表达式 AST
│   ├── main.py       #   词法分析器独立入口
│   └── __init__.py
├── slr_parser/       # SLR 语法分析器 + AST 构建 + IR 原型生成
│   ├── slr_grammar.py #  C-- BNF 文法定义（98 条产生式）
│   ├── slr_items.py  #   LR(0) 项目集、闭包、GOTO、FIRST/FOLLOW 集
│   ├── slr_table.py  #   SLR(1) ACTION/GOTO 分析表构建
│   ├── slr_parser.py #   SLR 分析器主程序 + AST 构建 + LLVM IR 生成原型
│   └── print_grammar_report.py # 打印文法报告
├── ir_gen/           # C++ 中端集成（调用 compiler_ir 库）
│   ├── main.cpp      #   C++ 中端入口，解析参数
│   ├── ast_json.h/.cpp #   AST JSON 解析器（将 Python 端输出的 AST 转为 C++ 对象）
│   ├── ir_visitor.h/.cpp #   AST 访问器，调用 compiler_ir API 生成 LLVM IR
│   ├── CMakeLists.txt #  CMake 构建配置
│   └── README.md     #   ir_gen 模块详细说明
├── tests/            # 测试用例及生成的 .ll / .ast.json 输出
│   ├── test_full.sy   #  完整功能测试（函数定义/调用/参数/赋值/if-else/二元运算）
│   ├── test_edge.sy   #  边界测试（const/!/else 分支）
│   └── test_return_if.sy # 控制流测试（return 后不生成多余 br）
└── README.md          # 本文件
```

---

## 各模块设计

### 1. 词法分析器（lexer/）

**设计思路**：采用 Thompson NFA 构造 → 子集构造法（NFA → DFA） → Hopcroft DFA 最小化 → 最长匹配词法分析。

**核心流程**：
1. 为标识符、整数、浮点数、运算符、界符分别构建正则表达式
2. 使用 Thompson 算法将正则转换为 NFA
3. 使用子集构造法将 NFA 转换为 DFA
4. 使用 Hopcroft 算法最小化 DFA
5. 运行时对输入源代码进行最长匹配分词

**输出格式**：`[单词符号]\t<[种别],[内容]>`

**种别编号**：
| 种别 | 编号 | 说明 |
|------|------|------|
| KW   | 1-8  | int=1, void=2, return=3, const=4, main=5, float=6, if=7, else=8 |
| OP   | 6-19 | +=6, -=7, *=8, /=9, %=10, ==11, >=12, <=13, ===14, <=15, >=16, !=17, &&=18, ||=19 |
| SE   | 20-25| (=20, )=21, {=22, }=23, ;=24, ,=25 |
| IDN  | 字符串值 | 标识符 |
| INT  | 字符串值 | 整数字面量 |
| FLOAT| 字符串值 | 浮点数字面量 |

### 2. SLR 语法分析器（slr_parser/）

**文法**：基于大作业附录给出的 C-- 文法，改写为 98 条 BNF 产生式（含右递归消除和 Tail 节点设计），165 个 LR(0) 状态，32 个终结符，54 个非终结符。

**核心算法**：
1. **LR(0) 项目集规范族**：计算闭包（closure）和 GOTO 函数
2. **FIRST/FOLLOW 集**：用于 SLR(1) 规约决策
3. **SLR(1) 分析表**：构建 ACTION 表和 GOTO 表，遇冲突时优先移进
4. **基于栈的分析**：同步维护状态栈、符号栈和 AST 栈

**AST 构建策略**：
- Shift 时创建叶子节点（Ident, IntConst, floatConst）
- Reduce 时创建非终结符节点，子节点为弹出的 AST 节点
- 表达式采用 Tail 节点设计（如 addExp → mulExp addExpTail）消除左递归

**文法关键设计**：
- 顶层统一为 `type Ident topRest`，topRest 区分函数定义和变量声明
- 表达式层级：lOrExp → lAndExp → eqExp → relExp → addExp → mulExp → unaryExp → primaryExp
- 每个运算符层级使用 Tail 模式处理右递归

### 3. 中间代码生成（slr_parser/ 中的 IRGenerator + ir_gen/ C++ 集成）

**Python 原型（IRGenerator）**：
- 直接嵌入 slr_parser.py，用于验证 IR 生成逻辑
- 支持：全局/局部变量、const 变量、函数定义/调用/参数、赋值、return、if/else、一元/二元/比较运算

**C++ 中端集成（ir_gen/）**：
- Python 端导出 AST 为 JSON 格式（`--ast-out`）
- C++ 端 `ast_json.cpp` 解析 JSON 构建 AST 对象树
- `ir_visitor.cpp` 使用 visitor 模式遍历 AST，调用 `compiler_ir` 库 API 生成 LLVM IR
- 覆盖：整型变量/常量、函数、参数、调用、赋值、return、算术/比较表达式、if/else

**IR 生成关键设计**：
- 使用 `alloca` + `store` + `load` 管理局部变量
- 表达式求值返回 `(type, value)` 元组，避免类型信息重复
- Tail 节点通过 `_process_tail` 方法处理运算符链
- `is_terminated()` 检查避免在已有 ret/br 的基本块后添加多余分支
- 函数调用优先于变量引用检测

### 4. 测试用例（tests/）

| 测试文件 | 测试内容 |
|----------|----------|
| test_full.sy | 完整功能：全局变量、函数定义/调用、参数传递、局部变量、赋值、二元运算、if/else |
| test_edge.sy | 边界情况：const 声明、! 运算符、else 分支 |
| test_return_if.sy | 控制流：return 后不生成多余 br 指令 |

---

## 使用方法

### 环境要求
- Python 3.8+（词法分析 + SLR 语法分析 + IR 原型）
- C++17 编译器（WSL 下 g++，用于 C++ 中端集成）
- CMake（可选，用于构建 C++ 中端）

### 运行词法分析

Windows PowerShell：
```powershell
python -m lexer.main .\tests\test_full.sy
```

WSL/Linux：
```bash
cd final_project
python3 -m lexer.main tests/test_full.sy
```

### 运行完整流水线（词法 → 语法 → IR）

Windows PowerShell：
```powershell
python .\slr_parser\slr_parser.py .\tests\test_full.sy --ir-out .\tests\test_full.ll
python .\slr_parser\slr_parser.py .\tests\test_edge.sy --ir-out .\tests\test_edge.ll --ast-out .\tests\test_edge.ast.json
python .\slr_parser\slr_parser.py .\tests\test_return_if.sy --ir-out .\tests\test_return_if.ll --ast-out .\tests\test_return_if.ast.json
```

WSL/Linux：
```bash
cd final_project
python3 slr_parser/slr_parser.py tests/test_full.sy --ir-out tests/test_full.ll
python3 slr_parser/slr_parser.py tests/test_edge.sy --ir-out tests/test_edge.ll --ast-out tests/test_edge.ast.json
python3 slr_parser/slr_parser.py tests/test_return_if.sy --ir-out tests/test_return_if.ll --ast-out tests/test_return_if.ast.json
```

参数说明：
- `--ir-out <path>`：将生成的 LLVM IR 输出到指定文件
- `--ast-out <path>`：将构建的 AST 导出为 JSON 文件（供 C++ 中端使用）

### 打印文法报告

```powershell
python .\slr_parser\print_grammar_report.py
```

```bash
cd final_project
python3 slr_parser/print_grammar_report.py
```

### 构建 C++ 中端（WSL/Linux）

**方式一：直接 g++ 编译**
```bash
cd final_project
mkdir -p ir_gen/build
g++ -std=c++17 -g -Wall -Wno-attributes -Wno-unused-variable \
  -I../compiler_ir/include \
  ir_gen/main.cpp ir_gen/ast_json.cpp ir_gen/ir_visitor.cpp ../compiler_ir/src/*.cpp \
  -o ir_gen/build/ir_gen_demo
./ir_gen/build/ir_gen_demo tests/test_full.ast.json --out tests/test_full.cpp.ll
```

**方式二：CMake**
```bash
cd final_project/ir_gen
cmake -S . -B build
cmake --build build
./build/ir_gen_demo ../tests/test_full.ast.json --out ../tests/test_full.cpp.ll
```

**Demo 模式**（不依赖 AST JSON，内置简单测试）：
```bash
./ir_gen/build/ir_gen_demo --demo
```

---

## 跨语言流水线

```
源文件(.sy)
    │
    ▼
[Python] lexer.tokenize() ───→ Token 序列
    │
    ▼
[Python] SLRParser.parse() ──→ AST（内存）
    │           │
    │           ▼（--ast-out）
    │        AST JSON（.ast.json）
    │
    ▼（--ir-out）
[Python] IRGenerator.generate() ──→ LLVM IR（.ll）

    │
    ▼（C++ 中端路径）
[C++] parse_ast_json_file() ───→ AstNode 对象树
    │
    ▼
[C++] CminusIRVisitor.generate() ──→ LLVM IR（.cpp.ll）
    │（调用 compiler_ir 库 API）
    ▼
[compiler_ir] Module/Function/BasicBlock/Instruction ──→ .ll 文本
```

---

## 已知限制

| 功能 | Python 端 | C++ 端 |
|------|-----------|--------|
| int 变量/常量 | ✓ | ✓ |
| 函数定义/调用 | ✓ | ✓ |
| 赋值/return | ✓ | ✓ |
| if/else | ✓ | ✓ |
| 算术运算 (+-*/%) | ✓ | ✓ |
| 比较运算 (<>==!=) | ✓ | ✓ |
| 逻辑运算 (&&\|\|) | ✓（IR 级） | 未实现 |
| 逻辑非 (!) | ✓ | ✓ |
| float 类型 | ✓（解析） | 未实现（compiler_ir 无浮点支持） |
| 数组 | 未实现 | 未实现 |
| for/while 循环 | 未实现 | 未实现 |

---

## 开发笔记

- **词法分析**：基于 lab3 的 DFA 框架改造，调整种别编号和输出格式以匹配大作业规范
- **语法分析**：lab5 为 LL(1) 预测分析器，本作业要求 SLR，故重写为基于 LR(0) 项目集的 SLR(1) 分析器
- **IR 生成**：先在 Python 端完成原型验证，再在 C++ 端通过 visitor 模式调用 compiler_ir 库
- **AST JSON 跨语言传输**：Python 端导出 AST 为 JSON → C++ 端解析 JSON 构建对象树 → visitor 生成 IR
- 所有输出信息（错误提示、调试打印、文法报告）均使用中文
