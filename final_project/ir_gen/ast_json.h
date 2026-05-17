#ifndef CMINUS_AST_JSON_H
#define CMINUS_AST_JSON_H

#include <string>
#include <vector>

struct AstNode {
    int id = 0;
    std::string name;
    std::string value;
    std::vector<AstNode> children;
};

AstNode parse_ast_json_file(const std::string &path);

#endif
