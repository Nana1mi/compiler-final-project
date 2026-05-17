#include "ast_json.h"
#include "ir_visitor.h"

#include "BasicBlock.h"
#include "Constant.h"
#include "Function.h"
#include "GlobalVariable.h"
#include "IRbuilder.h"
#include "Module.h"
#include "Type.h"

#include <fstream>
#include <iostream>
#include <stdexcept>
#include <string>

namespace {

std::string run_demo() {
    Module module("sysy2022_compiler");
    auto *i32_type = Type::get_int32_type(&module);

    GlobalVariable::create("a", &module, i32_type, false, ConstantInt::get(10, &module));

    auto *main_type = FunctionType::get(i32_type, {});
    auto *main_func = Function::create(main_type, "main", &module);
    auto *entry = BasicBlock::create(&module, "ENTRY", main_func);

    IRBuilder builder(entry, &module);
    builder.set_curFunc(main_func);

    auto *global_a = module.get_global_variable().front();
    builder.create_store(ConstantInt::get(10, &module), global_a);
    builder.create_ret(ConstantInt::get(0, &module));

    return module.print();
}

void write_output(const std::string &path, const std::string &content) {
    if (path.empty()) {
        std::cout << content;
        return;
    }
    std::ofstream output(path);
    if (!output) {
        throw std::runtime_error("无法打开输出文件: " + path);
    }
    output << content;
}

} // namespace

int main(int argc, char **argv) {
    try {
        std::string output_path;
        std::string ast_path;

        for (int i = 1; i < argc; ++i) {
            std::string arg = argv[i];
            if (arg == "--demo") {
                write_output(output_path, run_demo());
                return 0;
            }
            if (arg == "--out") {
                if (i + 1 >= argc) {
                    throw std::runtime_error("--out 需要指定一个路径");
                }
                output_path = argv[++i];
                continue;
            }
            ast_path = arg;
        }

        if (ast_path.empty()) {
            std::cerr << "用法: ir_gen_demo <ast.json> [--out output.ll]\n"
                      << "       ir_gen_demo --demo\n";
            return 2;
        }

        AstNode root = parse_ast_json_file(ast_path);
        CminusIRVisitor visitor;
        write_output(output_path, visitor.generate(root));
        return 0;
    } catch (const std::exception &ex) {
        std::cerr << "ir_gen 错误: " << ex.what() << "\n";
        return 1;
    }
}
