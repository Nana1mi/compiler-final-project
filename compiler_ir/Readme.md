# compiler_ir — C-- 中间代码生成库

本项目是一个轻量级 LLVM IR 生成库，采用面向对象设计，提供了完整的 IR 值类型系统、指令构建、函数与基本块管理等功能。
库的设计参考了 LLVM IR 的层次结构，适用于编译原理课程的中端代码生成。

---

## 目录结构

```
compiler_ir/
├── include/           # 头文件
│   ├── Value.h        #   值基类（所有 IR 实体的公共基类）
│   ├── Type.h         #   类型系统（i1, i32, float, void, pointer, array, function）
│   ├── User.h         #   使用者基类（管理 operand-use 关系）
│   ├── Constant.h     #   常量接口与 ConstantInt 实现
│   ├── GlobalVariable.h # 全局变量
│   ├── Module.h       #   模块（顶层容器，管理函数、全局变量、类型）
│   ├── Function.h     #   函数（含 FunctionType）
│   ├── BasicBlock.h   #   基本块
│   ├── Instruction.h  #   指令（二元运算、比较、调用、分支、返回、alloca、load/store、gep、zext）
│   └── IRbuilder.h    #   IRBuilder（便捷指令创建）
├── src/               # 实现文件（与 include 一一对应）
├── IRprinter.cpp      #   （在 src/ 中）IR 打印，输出 LLVM .ll 格式文本
├── main.cpp           # 测试入口（验证库能否正常编译）
├── script/
│   └── generate.sh    # Linux/macOS 一键构建脚本
├── CMakeLists.txt     # CMake 构建配置
├── Readme.md          # 本文件
└── .git/              # Git 仓库
```

---

## 架构设计

```
Value（值基类）
  ├── Type（类型）
  │     ├── IntegerType（i1, i32）
  │     ├── FloatType（float）
  │     ├── PointerType（pointer）
  │     ├── ArrayType（array）
  │     ├── FunctionType（函数类型）
  │     └── VoidType / LabelType
  │
  ├── User（使用者，管理 operand-use 链）
  │     ├── Instruction（指令）
  │     │     ├── BinaryInst    （add / sub / mul / sdiv / mod）
  │     │     ├── CmpInst       （EQ / NE / GT / GE / LT / LE）
  │     │     ├── CallInst      （函数调用）
  │     │     ├── BranchInst    （br / cond_br）
  │     │     ├── ReturnInst    （ret / void ret）
  │     │     ├── AllocaInst    （alloca）
  │     │     ├── LoadInst      （load）
  │     │     ├── StoreInst     （store）
  │     │     ├── GetElementPtrInst（gep）
  │     │     ├── ZextInst      （零位扩展）
  │     │     └── PhiInst       （phi 节点）
  │     └── Constant（常量）
  │           └── ConstantInt   （整型常量）
  │
  ├── GlobalVariable（全局变量）
  ├── BasicBlock（基本块，指令容器）
  └── Function（函数，基本块容器）

Module（模块，顶层容器）
  ├── 管理所有 Function
  ├── 管理所有 GlobalVariable
  ├── 缓存基础 Type（i1, i32, float, void, label）
  └── 提供 pointer/array 类型缓存
```

---

## 核心 API 概览

### Module — 模块

模块是 IR 的顶层容器，管理函数列表、全局变量列表、类型系统和符号表。

```cpp
Module module("my_module");                    // 创建模块
auto *i32 = module.get_int32_type();           // 获取 i32 类型
auto *i1  = module.get_int1_type();            // 获取 i1 类型
auto *void_ty = module.get_void_type();        // 获取 void 类型
auto *float_ty = module.get_float_type();      // 获取 float 类型
auto *ptr = module.get_int32_ptr_type();       // 获取 i32* 类型
auto *i32_ptr = module.get_pointer_type(i32);  // 获取 i32* 类型
auto *arr = module.get_array_type(i32, 10);    // 获取 [10 x i32] 类型

module.add_function(func);                     // 添加函数
module.add_global_variable(gvar);              // 添加全局变量
std::string ir = module.print();               // 打印为 LLVM IR 文本
```

### Function & FunctionType — 函数

```cpp
// 创建函数类型：返回 i32，参数为 (i32, i32)
auto *func_type = FunctionType::get(i32, {i32, i32});
// 创建函数并添加到模块
auto *func = Function::create(func_type, "my_func", &module);
// 创建入口基本块
auto *entry = BasicBlock::create(&module, "entry", func);
```

### BasicBlock — 基本块

```cpp
// 创建基本块（自动添加到函数）
auto *bb = BasicBlock::create(&module, "label_name", func);
// 在函数末尾创建基本块
auto *bb2 = BasicBlock::create(&module, "label2", func);
```

### IRBuilder — 指令构建器

IRBuilder 提供便捷的指令创建接口，自动将指令插入到当前基本块中。

```cpp
IRBuilder builder(entry, &module);
builder.set_curFunc(func);
builder.set_insert_point(bb);  // 切换插入的基本块

// 算术运算
builder.create_iadd(lhs, rhs);   // add
builder.create_isub(lhs, rhs);   // sub
builder.create_imul(lhs, rhs);   // mul
builder.create_isdiv(lhs, rhs);  // sdiv
builder.create_irem(lhs, rhs);   // mod

// 比较运算
builder.create_icmp_eq(lhs, rhs);  // icmp eq
builder.create_icmp_ne(lhs, rhs);  // icmp ne
builder.create_icmp_gt(lhs, rhs);  // icmp sgt
builder.create_icmp_ge(lhs, rhs);  // icmp sge
builder.create_icmp_lt(lhs, rhs);  // icmp slt
builder.create_icmp_le(lhs, rhs);  // icmp sle

// 控制流
builder.create_br(target_bb);                          // 无条件跳转
builder.create_cond_br(cond, true_bb, false_bb);       // 条件跳转
builder.create_ret(value);                             // 返回值
builder.create_void_ret();                             // void 返回

// 内存操作
builder.create_alloca(type);                           // alloca
builder.create_store(value, ptr);                      // store
builder.create_load(ptr);                              // load
builder.create_gep(ptr, {idx1, idx2});                 // getelementptr

// 函数调用
builder.create_call(func, {arg1, arg2});               // call

// 类型转换
builder.create_zext(value, dest_type);                 // zext
```

### Constant — 常量

```cpp
auto *c = ConstantInt::get(42, &module);    // 整型常量 42
```

### GlobalVariable — 全局变量

```cpp
// 创建全局变量：@g = global i32 10
GlobalVariable::create("g", &module, i32, false, ConstantInt::get(10, &module));
// 创建常量全局变量：@c = constant i32 5
GlobalVariable::create("c", &module, i32, true, ConstantInt::get(5, &module));

// 获取全局变量列表
auto gvars = module.get_global_variable();
auto *first = gvars.front();
```

### Instruction — 指令类型判断

每条指令提供 `is_xxx()` 方法用于类型判断：

```cpp
inst->is_ret();       // 是否为 ret
inst->is_br();        // 是否为 br
inst->is_add();       // 是否为 add
inst->is_load();      // 是否为 load
inst->is_store();     // 是否为 store
inst->is_call();      // 是否为 call
inst->isTerminator(); // 是否为终结指令（ret 或 br）
inst->isBinary();     // 是否为二元运算
```

---

## 使用示例

### 示例：生成简单的 main 函数

```cpp
#include "BasicBlock.h"
#include "Constant.h"
#include "Function.h"
#include "GlobalVariable.h"
#include "IRbuilder.h"
#include "Module.h"
#include "Type.h"

int main() {
    Module module("demo");
    auto *i32 = Type::get_int32_type(&module);

    // 全局变量: @a = global i32 10
    GlobalVariable::create("a", &module, i32, false, ConstantInt::get(10, &module));

    // 函数: define i32 @main()
    auto *main_type = FunctionType::get(i32, {});
    auto *main_func = Function::create(main_type, "main", &module);
    auto *entry = BasicBlock::create(&module, "entry", main_func);

    IRBuilder builder(entry, &module);
    builder.set_curFunc(main_func);

    // store 10, @a
    auto *global_a = module.get_global_variable().front();
    builder.create_store(ConstantInt::get(10, &module), global_a);

    // ret i32 0
    builder.create_ret(ConstantInt::get(0, &module));

    // 输出 IR
    std::cout << module.print() << std::endl;
    return 0;
}
```

输出：

```llvm
; ModuleID = 'demo'

@g_a = global i32 10

define i32 @main() {
label_1:
  store i32 10, i32* @g_a
  ret i32 0
}
```

---

## 编译与构建

### 环境要求

- C++17 编译器（g++ / clang++）
- CMake 3.12+（可选）
- Linux / macOS / WSL

### 方式一：直接 g++ 编译

```bash
cd compiler_ir
g++ -std=c++17 -g -Wall -I include main.cpp src/*.cpp -o build/demo
./build/demo
```

### 方式二：CMake

```bash
cd compiler_ir
mkdir -p build && cd build
cmake ..
make
./ir_demo
```

### 方式三：一键脚本（Linux/macOS）

```bash
cd compiler_ir
bash script/generate.sh
```

### 作为子模块使用

在其他项目中使用 compiler_ir 时，只需：
1. 将 `include/` 目录加入头文件搜索路径（`-I compiler_ir/include`）
2. 链接 `src/` 下的所有 .cpp 文件

例如在 `final_project/ir_gen/` 中：

```bash
g++ -std=c++17 -I../../compiler_ir/include \
  main.cpp ast_json.cpp ir_visitor.cpp ../../compiler_ir/src/*.cpp \
  -o build/ir_gen_demo
```

---

## 指令类型一览

| 指令类 | 操作码 | LLVM IR 示例 |
|--------|--------|-------------|
| BinaryInst | add / sub / mul / sdiv / mod | `%1 = add i32 %a, %b` |
| CmpInst | EQ / NE / GT / GE / LT / LE | `%1 = icmp slt i32 %a, %b` |
| CallInst | call | `%1 = call i32 @func(i32 %a)` |
| BranchInst | br / cond_br | `br i1 %cond, label %t, label %f` |
| ReturnInst | ret | `ret i32 %a` / `ret void` |
| AllocaInst | alloca | `%1 = alloca i32` |
| LoadInst | load | `%1 = load i32, i32* %ptr` |
| StoreInst | store | `store i32 %val, i32* %ptr` |
| GetElementPtrInst | getelementptr | `%1 = getelementptr [10 x i32], [10 x i32]* %p, i32 0, i32 %i` |
| ZextInst | zext | `%1 = zext i1 %a to i32` |

---

## 已知限制

- `ConstantInt` 仅支持整型常量，无浮点常量类（`ConstantFloat` 未实现）
- 无浮点二元运算指令（`fadd`, `fsub`, `fmul`, `fdiv` 等）
- 无 `fcmp` 浮点比较指令
- 数组和指针操作（GEP）提供了 API，但在 C-- 前端中未使用

---

## 开发说明

- 文件间存在多文件交叉依赖，建议使用 CMake 或一次性编译所有源文件
- `script/generate.sh` 适用于 Linux/macOS，Windows 下不支持 .sh 脚本
- 所有头文件和源文件注释已中文化，`@date` 字段统一更新为 2025-05-17
