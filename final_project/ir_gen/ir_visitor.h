#ifndef CMINUS_IR_VISITOR_H
#define CMINUS_IR_VISITOR_H

#include "ast_json.h"

#include "BasicBlock.h"
#include "Constant.h"
#include "Function.h"
#include "IRbuilder.h"
#include "Module.h"
#include "Type.h"
#include "Value.h"

#include <map>
#include <memory>
#include <string>
#include <vector>

class CminusIRVisitor {
public:
    CminusIRVisitor();

    std::string generate(const AstNode &root);

private:
    struct Symbol {
        Value *ptr = nullptr;
        Type *type = nullptr;
        bool is_const = false;
    };

    Module module_;
    IRBuilder builder_;
    Function *current_func_ = nullptr;
    int label_counter_ = 0;
    std::vector<std::map<std::string, Symbol>> scopes_;
    std::map<std::string, Function *> functions_;

    void visit_comp_unit(const AstNode &node);
    void visit_top_unit(const AstNode &node);
    void visit_const_decl(const AstNode &node);
    void visit_const_def_list(Type *type, const AstNode &node);
    void visit_const_def_list_tail(Type *type, const AstNode &node);
    void visit_const_def(Type *type, const AstNode &node);
    void visit_var_decl_from_top(Type *type, const AstNode &ident, const AstNode &rest);
    void visit_var_decl(const AstNode &node);
    void visit_var_def_list(Type *type, const AstNode &node);
    void visit_var_def_list_tail(Type *type, const AstNode &node);
    void visit_var_def(Type *type, const AstNode &node);
    void visit_func_def(Type *return_type, const AstNode &ident, const AstNode &rest);
    void visit_block(const AstNode &node, bool create_scope = true);
    void visit_block_items(const AstNode &node);
    void visit_block_item(const AstNode &node);
    void visit_decl(const AstNode &node);
    void visit_stmt(const AstNode &node);
    void visit_if_stmt(const AstNode &node);

    Value *visit_exp(const AstNode &node);
    Value *process_tail(const AstNode &tail, Value *left);
    Value *emit_binary(const std::string &op, Value *left, Value *right);
    Value *ensure_i1(Value *value);
    Type *type_from_node(const AstNode &node);
    Type *i32_type();
    Type *void_type();
    ConstantInt *const_i32(int value);
    int eval_const(const AstNode &node);

    std::vector<std::pair<std::string, Type *>> parse_func_params_opt(const AstNode &node);
    void collect_func_params(const AstNode &node, std::vector<std::pair<std::string, Type *>> &params);
    void collect_func_params_tail(const AstNode &node, std::vector<std::pair<std::string, Type *>> &params);
    std::vector<Value *> parse_call_args_opt(const AstNode &node);
    void collect_call_args(const AstNode &node, std::vector<Value *> &args);
    void collect_call_args_tail(const AstNode &node, std::vector<Value *> &args);

    const AstNode *initializer_node(const AstNode &node);
    const AstNode *first_child_named(const AstNode &node, const std::string &name);
    bool is_terminated();
    BasicBlock *new_block(const std::string &hint);

    void enter_scope();
    void leave_scope();
    void add_symbol(const std::string &name, Value *ptr, Type *type, bool is_const);
    Symbol *find_symbol(const std::string &name);
    Function *find_function(const std::string &name);
};

#endif
