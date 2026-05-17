#include "ir_visitor.h"

#include "Constant.h"
#include "Function.h"
#include "GlobalVariable.h"
#include "Instruction.h"

#include <stdexcept>

CminusIRVisitor::CminusIRVisitor()
    : module_("sysy2022_compiler"), builder_(nullptr, &module_) {
    enter_scope();
}

std::string CminusIRVisitor::generate(const AstNode &root) {
    visit_comp_unit(root);
    return module_.print();
}

void CminusIRVisitor::visit_comp_unit(const AstNode &node) {
    if (node.name == "Program" || node.name == "S'") {
        if (!node.children.empty()) {
            visit_comp_unit(node.children[0]);
        }
        return;
    }
    if (node.name != "compUnit" || node.children.empty()) {
        return;
    }
    visit_top_unit(node.children[0]);
    if (node.children.size() >= 2) {
        visit_comp_unit(node.children[1]);
    }
}

void CminusIRVisitor::visit_top_unit(const AstNode &node) {
    if (node.children.empty()) {
        return;
    }
    if (node.children[0].name == "constDecl") {
        visit_const_decl(node.children[0]);
        return;
    }
    if (node.children.size() < 3) {
        throw std::runtime_error("错误的 topUnit 结构");
    }
    Type *type = type_from_node(node.children[0]);
    const AstNode &ident = node.children[1];
    const AstNode &rest = node.children[2];
    if (!rest.children.empty() && rest.children[0].name == "(") {
        visit_func_def(type, ident, rest);
    } else {
        visit_var_decl_from_top(type, ident, rest);
    }
}

void CminusIRVisitor::visit_const_decl(const AstNode &node) {
    if (node.children.size() < 3) {
        throw std::runtime_error("错误的 constDecl 结构");
    }
    Type *type = type_from_node(node.children[1]);
    visit_const_def_list(type, node.children[2]);
}

void CminusIRVisitor::visit_const_def_list(Type *type, const AstNode &node) {
    if (node.children.empty()) {
        return;
    }
    visit_const_def(type, node.children[0]);
    if (node.children.size() >= 2) {
        visit_const_def_list_tail(type, node.children[1]);
    }
}

void CminusIRVisitor::visit_const_def_list_tail(Type *type, const AstNode &node) {
    if (node.children.empty()) {
        return;
    }
    if (node.children.size() >= 2) {
        visit_const_def(type, node.children[1]);
    }
    if (node.children.size() >= 3) {
        visit_const_def_list_tail(type, node.children[2]);
    }
}

void CminusIRVisitor::visit_const_def(Type *type, const AstNode &node) {
    if (node.children.size() < 3) {
        throw std::runtime_error("错误的 constDef 结构");
    }
    const std::string &name = node.children[0].value;
    int init = eval_const(node.children[2]);
    if (current_func_ == nullptr) {
        auto *global = GlobalVariable::create(name, &module_, type, true, ConstantInt::get(init, &module_));
        add_symbol(name, global, type, true);
    } else {
        auto *ptr = builder_.create_alloca(type);
        builder_.create_store(ConstantInt::get(init, &module_), ptr);
        add_symbol(name, ptr, type, true);
    }
}

void CminusIRVisitor::visit_var_decl_from_top(Type *type, const AstNode &ident, const AstNode &rest) {
    int init = 0;
    if (!rest.children.empty() && rest.children[0].name == "firstVarInit") {
        init = eval_const(rest.children[0]);
    }
    auto *global = GlobalVariable::create(ident.value, &module_, type, false, ConstantInt::get(init, &module_));
    add_symbol(ident.value, global, type, false);
    if (rest.children.size() >= 2) {
        visit_var_def_list_tail(type, rest.children[1]);
    }
}

void CminusIRVisitor::visit_var_decl(const AstNode &node) {
    if (node.children.size() < 2) {
        throw std::runtime_error("错误的 varDecl 结构");
    }
    Type *type = type_from_node(node.children[0]);
    visit_var_def_list(type, node.children[1]);
}

void CminusIRVisitor::visit_var_def_list(Type *type, const AstNode &node) {
    if (node.children.empty()) {
        return;
    }
    visit_var_def(type, node.children[0]);
    if (node.children.size() >= 2) {
        visit_var_def_list_tail(type, node.children[1]);
    }
}

void CminusIRVisitor::visit_var_def_list_tail(Type *type, const AstNode &node) {
    if (node.children.empty()) {
        return;
    }
    if (node.children.size() >= 2) {
        visit_var_def(type, node.children[1]);
    }
    if (node.children.size() >= 3) {
        visit_var_def_list_tail(type, node.children[2]);
    }
}

void CminusIRVisitor::visit_var_def(Type *type, const AstNode &node) {
    if (node.children.empty()) {
        throw std::runtime_error("错误的 varDef 结构");
    }
    const std::string &name = node.children[0].value;
    if (current_func_ == nullptr) {
        int init = 0;
        if (node.children.size() >= 2) {
            init = eval_const(node.children[1]);
        }
        auto *global = GlobalVariable::create(name, &module_, type, false, ConstantInt::get(init, &module_));
        add_symbol(name, global, type, false);
        return;
    }

    auto *ptr = builder_.create_alloca(type);
    add_symbol(name, ptr, type, false);
    if (node.children.size() >= 2) {
        const AstNode *init = initializer_node(node.children[1]);
        if (init) {
            builder_.create_store(visit_exp(*init), ptr);
        }
    }
}

void CminusIRVisitor::visit_func_def(Type *return_type, const AstNode &ident, const AstNode &rest) {
    std::vector<std::pair<std::string, Type *>> params;
    if (rest.children.size() >= 2) {
        params = parse_func_params_opt(rest.children[1]);
    }

    std::vector<Type *> param_types;
    for (const auto &param : params) {
        param_types.push_back(param.second);
    }
    auto *func_type = FunctionType::get(return_type, param_types);
    auto *func = Function::create(func_type, ident.value, &module_);
    functions_[ident.value] = func;

    current_func_ = func;
    auto *entry = BasicBlock::create(&module_, "entry" + std::to_string(++label_counter_), func);
    builder_.set_curFunc(func);
    builder_.set_insert_point(entry);
    enter_scope();

    auto arg_it = func->arg_begin();
    for (size_t i = 0; i < params.size(); ++i, ++arg_it) {
        auto *arg = *arg_it;
        arg->set_name(params[i].first);
        auto *ptr = builder_.create_alloca(params[i].second);
        builder_.create_store(arg, ptr);
        add_symbol(params[i].first, ptr, params[i].second, false);
    }

    if (rest.children.size() >= 4) {
        visit_block(rest.children[3], false);
    }

    if (!is_terminated()) {
        if (return_type->is_void_type()) {
            builder_.create_void_ret();
        } else {
            builder_.create_ret(ConstantInt::get(0, &module_));
        }
    }

    leave_scope();
    current_func_ = nullptr;
}

void CminusIRVisitor::visit_block(const AstNode &node, bool create_scope) {
    if (create_scope) {
        enter_scope();
    }
    if (node.children.size() >= 2) {
        visit_block_items(node.children[1]);
    }
    if (create_scope) {
        leave_scope();
    }
}

void CminusIRVisitor::visit_block_items(const AstNode &node) {
    if (node.children.empty() || is_terminated()) {
        return;
    }
    visit_block_item(node.children[0]);
    if (node.children.size() >= 2) {
        visit_block_items(node.children[1]);
    }
}

void CminusIRVisitor::visit_block_item(const AstNode &node) {
    if (node.children.empty()) {
        return;
    }
    if (node.children[0].name == "decl") {
        visit_decl(node.children[0]);
    } else {
        visit_stmt(node.children[0]);
    }
}

void CminusIRVisitor::visit_decl(const AstNode &node) {
    if (node.children.empty()) {
        return;
    }
    if (node.children[0].name == "constDecl") {
        visit_const_decl(node.children[0]);
    } else if (node.children[0].name == "varDecl") {
        visit_var_decl(node.children[0]);
    }
}

void CminusIRVisitor::visit_stmt(const AstNode &node) {
    if (node.children.empty() || is_terminated()) {
        return;
    }
    const AstNode &first = node.children[0];
    if (first.name == "lVal") {
        const std::string &name = first.children[0].value;
        Symbol *symbol = find_symbol(name);
        if (!symbol) {
            throw std::runtime_error("未定义的变量: " + name);
        }
        if (symbol->is_const) {
            throw std::runtime_error("不能对 const 变量赋值: " + name);
        }
        builder_.create_store(visit_exp(node.children[2]), symbol->ptr);
    } else if (first.name == "block") {
        visit_block(first);
    } else if (first.name == "if") {
        visit_if_stmt(node);
    } else if (first.name == "return") {
        if (node.children.size() >= 2 && !node.children[1].children.empty()) {
            builder_.create_ret(visit_exp(node.children[1].children[0]));
        } else {
            builder_.create_void_ret();
        }
    } else if (first.name != ";") {
        (void)visit_exp(first);
    }
}

void CminusIRVisitor::visit_if_stmt(const AstNode &node) {
    Value *cond = ensure_i1(visit_exp(node.children[2]));
    BasicBlock *true_bb = new_block("if_true");
    BasicBlock *false_bb = new_block("if_false");
    BasicBlock *end_bb = nullptr;
    auto ensure_end = [&]() {
        if (end_bb == nullptr) {
            end_bb = new_block("if_end");
        }
        return end_bb;
    };
    builder_.create_cond_br(cond, true_bb, false_bb);

    builder_.set_insert_point(true_bb);
    visit_stmt(node.children[4]);
    bool true_term = is_terminated();
    if (!true_term) {
        builder_.create_br(ensure_end());
    }

    builder_.set_insert_point(false_bb);
    if (node.children.size() >= 6) {
        const AstNode &else_part = node.children[5];
        if (else_part.children.size() >= 2) {
            visit_stmt(else_part.children[1]);
        }
    }
    bool false_term = is_terminated();
    if (!false_term) {
        builder_.create_br(ensure_end());
    }

    if (end_bb != nullptr) {
        builder_.set_insert_point(end_bb);
    }
}

Value *CminusIRVisitor::visit_exp(const AstNode &node) {
    if (node.name == "IntConst") {
        return ConstantInt::get(std::stoi(node.value), &module_);
    }
    if (node.name == "floatConst") {
        throw std::runtime_error("此 C++ visitor 暂不支持 float 类型的 IR 生成");
    }
    if (node.name == "Ident") {
        Symbol *symbol = find_symbol(node.value);
        if (!symbol) {
            throw std::runtime_error("未定义的变量: " + node.value);
        }
        return builder_.create_load(symbol->type, symbol->ptr);
    }
    if (node.name == "lVal") {
        if (node.children.empty()) {
            throw std::runtime_error("错误的 lVal 结构");
        }
        return visit_exp(node.children[0]);
    }
    if (node.name == "number" || node.name == "primaryExp" || node.name == "exp" ||
        node.name == "cond" || node.name == "constExp" || node.name == "initVal" ||
        node.name == "constInitVal" || node.name == "funcRParam") {
        if (node.children.empty()) {
            return const_i32(0);
        }
        return visit_exp(node.children[0]);
    }
    if (node.name == "unaryExp") {
        if (node.children.empty()) {
            return const_i32(0);
        }
        if (node.children[0].name == "Ident" && node.children.size() >= 4 && node.children[1].name == "(") {
            Function *func = find_function(node.children[0].value);
            if (!func) {
                throw std::runtime_error("未定义的函数: " + node.children[0].value);
            }
            std::vector<Value *> args = parse_call_args_opt(node.children[2]);
            return builder_.create_call(func, args);
        }
        if (node.children[0].name == "unaryOp") {
            std::string op = node.children[0].children.empty() ? "" : node.children[0].children[0].name;
            Value *operand = visit_exp(node.children[1]);
            if (op == "-") {
                return builder_.create_isub(const_i32(0), operand);
            }
            if (op == "!") {
                return builder_.create_icmp_eq(operand, const_i32(0));
            }
            return operand;
        }
        return visit_exp(node.children[0]);
    }
    if (node.name == "addExp" || node.name == "mulExp" || node.name == "relExp" ||
        node.name == "eqExp" || node.name == "lAndExp" || node.name == "lOrExp") {
        Value *left = visit_exp(node.children[0]);
        if (node.children.size() >= 2) {
            Value *result = process_tail(node.children[1], left);
            return result ? result : left;
        }
        return left;
    }
    if (!node.children.empty()) {
        return visit_exp(node.children[0]);
    }
    return const_i32(0);
}

Value *CminusIRVisitor::process_tail(const AstNode &tail, Value *left) {
    if (tail.children.empty()) {
        return nullptr;
    }
    std::string op = tail.children[0].name;
    Value *right = visit_exp(tail.children[1]);
    Value *result = emit_binary(op, left, right);
    if (tail.children.size() >= 3) {
        Value *more = process_tail(tail.children[2], result);
        return more ? more : result;
    }
    return result;
}

Value *CminusIRVisitor::emit_binary(const std::string &op, Value *left, Value *right) {
    if (op == "+") return builder_.create_iadd(left, right);
    if (op == "-") return builder_.create_isub(left, right);
    if (op == "*") return builder_.create_imul(left, right);
    if (op == "/") return builder_.create_isdiv(left, right);
    if (op == "%") return builder_.create_irem(left, right);
    if (op == "<") return builder_.create_icmp_lt(left, right);
    if (op == ">") return builder_.create_icmp_gt(left, right);
    if (op == "<=") return builder_.create_icmp_le(left, right);
    if (op == ">=") return builder_.create_icmp_ge(left, right);
    if (op == "==") return builder_.create_icmp_eq(left, right);
    if (op == "!=") return builder_.create_icmp_ne(left, right);
    if (op == "&&" || op == "||") {
        throw std::runtime_error("compiler_ir 的 BinaryInst 暂不支持逻辑 &&/|| 运算符");
    }
    throw std::runtime_error("不支持的二元运算符: " + op);
}

Value *CminusIRVisitor::ensure_i1(Value *value) {
    if (value->get_type()->is_int1_type()) {
        return value;
    }
    return builder_.create_icmp_ne(value, const_i32(0));
}

Type *CminusIRVisitor::type_from_node(const AstNode &node) {
    if (node.children.empty()) {
        return i32_type();
    }
    const std::string &name = node.children[0].name;
    if (name == "int") return i32_type();
    if (name == "void") return void_type();
    if (name == "float") {
        throw std::runtime_error("此 C++ visitor 暂不支持 float 类型的 IR 生成");
    }
    return i32_type();
}

Type *CminusIRVisitor::i32_type() { return Type::get_int32_type(&module_); }
Type *CminusIRVisitor::void_type() { return Type::get_void_type(&module_); }
ConstantInt *CminusIRVisitor::const_i32(int value) { return ConstantInt::get(value, &module_); }

int CminusIRVisitor::eval_const(const AstNode &node) {
    if (node.name == "IntConst") {
        return std::stoi(node.value);
    }
    if (node.children.empty()) {
        return 0;
    }
    for (const auto &child : node.children) {
        int value = eval_const(child);
        if (value != 0 || child.name == "IntConst") {
            return value;
        }
    }
    return 0;
}

std::vector<std::pair<std::string, Type *>> CminusIRVisitor::parse_func_params_opt(const AstNode &node) {
    std::vector<std::pair<std::string, Type *>> params;
    if (!node.children.empty() && node.children[0].name == "funcFParams") {
        collect_func_params(node.children[0], params);
    }
    return params;
}

void CminusIRVisitor::collect_func_params(const AstNode &node, std::vector<std::pair<std::string, Type *>> &params) {
    if (node.children.empty()) return;
    const AstNode &param = node.children[0];
    params.push_back({param.children[1].value, type_from_node(param.children[0])});
    if (node.children.size() >= 2) collect_func_params_tail(node.children[1], params);
}

void CminusIRVisitor::collect_func_params_tail(const AstNode &node, std::vector<std::pair<std::string, Type *>> &params) {
    if (node.children.empty()) return;
    const AstNode &param = node.children[1];
    params.push_back({param.children[1].value, type_from_node(param.children[0])});
    if (node.children.size() >= 3) collect_func_params_tail(node.children[2], params);
}

std::vector<Value *> CminusIRVisitor::parse_call_args_opt(const AstNode &node) {
    std::vector<Value *> args;
    if (!node.children.empty() && node.children[0].name == "funcRParams") {
        collect_call_args(node.children[0], args);
    }
    return args;
}

void CminusIRVisitor::collect_call_args(const AstNode &node, std::vector<Value *> &args) {
    if (node.children.empty()) return;
    args.push_back(visit_exp(node.children[0]));
    if (node.children.size() >= 2) collect_call_args_tail(node.children[1], args);
}

void CminusIRVisitor::collect_call_args_tail(const AstNode &node, std::vector<Value *> &args) {
    if (node.children.empty()) return;
    args.push_back(visit_exp(node.children[1]));
    if (node.children.size() >= 3) collect_call_args_tail(node.children[2], args);
}

const AstNode *CminusIRVisitor::initializer_node(const AstNode &node) {
    if (node.children.empty()) {
        return nullptr;
    }
    if (node.children.size() >= 2 && node.children[0].name == "=") {
        return &node.children[1];
    }
    return &node.children[0];
}

const AstNode *CminusIRVisitor::first_child_named(const AstNode &node, const std::string &name) {
    for (const auto &child : node.children) {
        if (child.name == name) {
            return &child;
        }
    }
    return nullptr;
}

bool CminusIRVisitor::is_terminated() {
    BasicBlock *bb = builder_.get_insert_block();
    return bb != nullptr && bb->get_terminator() != nullptr;
}

BasicBlock *CminusIRVisitor::new_block(const std::string &hint) {
    return BasicBlock::create(&module_, hint + std::to_string(++label_counter_), current_func_);
}

void CminusIRVisitor::enter_scope() { scopes_.push_back({}); }

void CminusIRVisitor::leave_scope() {
    if (scopes_.size() <= 1 && current_func_ == nullptr) {
        return;
    }
    scopes_.pop_back();
}

void CminusIRVisitor::add_symbol(const std::string &name, Value *ptr, Type *type, bool is_const) {
    if (scopes_.empty()) {
        enter_scope();
    }
    auto &scope = scopes_.back();
    if (scope.find(name) != scope.end()) {
        throw std::runtime_error("同一作用域内重复定义的符号: " + name);
    }
    scope[name] = Symbol{ptr, type, is_const};
}

CminusIRVisitor::Symbol *CminusIRVisitor::find_symbol(const std::string &name) {
    for (auto it = scopes_.rbegin(); it != scopes_.rend(); ++it) {
        auto found = it->find(name);
        if (found != it->end()) {
            return &found->second;
        }
    }
    return nullptr;
}

Function *CminusIRVisitor::find_function(const std::string &name) {
    auto it = functions_.find(name);
    if (it == functions_.end()) {
        return nullptr;
    }
    return it->second;
}
