# C++ IR generator integration

This directory is the C++ middle-end integration point required by the project
PDF.  The Python pipeline performs lexical analysis, SLR parsing, and AST JSON
export.  `ir_gen_demo` reads that AST JSON and uses visitor functions to call
the provided `compiler_ir` API.

Build:

```powershell
cmake -S . -B build
cmake --build build
.\build\Debug\ir_gen_demo.exe
```

If the generator is built by a single-config CMake generator, the executable may
be at:

```powershell
.\build\ir_gen_demo.exe
```

WSL without CMake:

```bash
mkdir -p build
g++ -std=c++17 -g -Wall -Wno-attributes -Wno-unused-variable \
  -I../compiler_ir/include \
  main.cpp ast_json.cpp ir_visitor.cpp ../compiler_ir/src/*.cpp \
  -o build/ir_gen_demo
./build/ir_gen_demo ../tests/test_full.ast.json --out ../tests/test_full.cpp.ll
```

Demo mode:

```bash
./build/ir_gen_demo --demo
```

Covered visitor nodes:

- global/local `constDecl` and `varDecl`
- `funcDef`, function parameters, and function calls
- `block`, `stmt`, assignment, `return`, and `if/else`
- integer constants, identifiers, unary `+/-/!`
- integer arithmetic and comparison expressions

Current limitations:

- `float` is parsed by the frontend but rejected by this C++ visitor because the
  provided `compiler_ir` code has no float constant/binary instruction support.
- `&&` and `||` are parsed, but short-circuit IR is not implemented in this C++
  visitor yet.
- Arrays are outside the current grammar subset.
