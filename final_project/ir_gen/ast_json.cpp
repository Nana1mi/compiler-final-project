#include "ast_json.h"

#include <cctype>
#include <fstream>
#include <stdexcept>

namespace {

class JsonParser {
public:
    explicit JsonParser(std::string text) : text_(std::move(text)) {}

    AstNode parse_ast_node() {
        AstNode node;
        expect('{');
        bool first = true;
        while (!peek('}')) {
            if (!first) {
                expect(',');
            }
            first = false;
            std::string key = parse_string();
            expect(':');
            if (key == "id") {
                node.id = parse_int();
            } else if (key == "name") {
                node.name = parse_string();
            } else if (key == "value") {
                node.value = parse_string();
            } else if (key == "children") {
                node.children = parse_children();
            } else {
                skip_value();
            }
        }
        expect('}');
        return node;
    }

private:
    std::string text_;
    size_t pos_ = 0;

    void skip_ws() {
        while (pos_ < text_.size() && std::isspace(static_cast<unsigned char>(text_[pos_]))) {
            ++pos_;
        }
    }

    bool peek(char ch) {
        skip_ws();
        return pos_ < text_.size() && text_[pos_] == ch;
    }

    void expect(char ch) {
        skip_ws();
        if (pos_ >= text_.size() || text_[pos_] != ch) {
            throw std::runtime_error(std::string("JSON 解析错误: 期望 '") + ch + "'");
        }
        ++pos_;
    }

    int parse_int() {
        skip_ws();
        bool neg = false;
        if (pos_ < text_.size() && text_[pos_] == '-') {
            neg = true;
            ++pos_;
        }
        int value = 0;
        bool has_digit = false;
        while (pos_ < text_.size() && std::isdigit(static_cast<unsigned char>(text_[pos_]))) {
            has_digit = true;
            value = value * 10 + (text_[pos_] - '0');
            ++pos_;
        }
        if (!has_digit) {
            throw std::runtime_error("JSON 解析错误: 期望整数");
        }
        return neg ? -value : value;
    }

    std::string parse_string() {
        skip_ws();
        expect('"');
        std::string result;
        while (pos_ < text_.size()) {
            char ch = text_[pos_++];
            if (ch == '"') {
                return result;
            }
            if (ch == '\\') {
                if (pos_ >= text_.size()) {
                    throw std::runtime_error("JSON 解析错误: 非法转义字符");
                }
                char esc = text_[pos_++];
                switch (esc) {
                case '"':
                case '\\':
                case '/':
                    result.push_back(esc);
                    break;
                case 'n':
                    result.push_back('\n');
                    break;
                case 'r':
                    result.push_back('\r');
                    break;
                case 't':
                    result.push_back('\t');
                    break;
                default:
                    throw std::runtime_error("JSON 解析错误: 不支持的转义字符");
                }
            } else {
                result.push_back(ch);
            }
        }
        throw std::runtime_error("JSON 解析错误: 未终止的字符串");
    }

    std::vector<AstNode> parse_children() {
        std::vector<AstNode> children;
        expect('[');
        bool first = true;
        while (!peek(']')) {
            if (!first) {
                expect(',');
            }
            first = false;
            children.push_back(parse_ast_node());
        }
        expect(']');
        return children;
    }

    void skip_value() {
        skip_ws();
        if (peek('{')) {
            int depth = 0;
            do {
                char ch = text_[pos_++];
                if (ch == '{') {
                    ++depth;
                } else if (ch == '}') {
                    --depth;
                } else if (ch == '"') {
                    --pos_;
                    (void)parse_string();
                }
            } while (depth > 0 && pos_ < text_.size());
        } else if (peek('[')) {
            int depth = 0;
            do {
                char ch = text_[pos_++];
                if (ch == '[') {
                    ++depth;
                } else if (ch == ']') {
                    --depth;
                } else if (ch == '"') {
                    --pos_;
                    (void)parse_string();
                }
            } while (depth > 0 && pos_ < text_.size());
        } else if (peek('"')) {
            (void)parse_string();
        } else {
            while (pos_ < text_.size() && text_[pos_] != ',' && text_[pos_] != '}' && text_[pos_] != ']') {
                ++pos_;
            }
        }
    }
};

} // namespace

AstNode parse_ast_json_file(const std::string &path) {
    std::ifstream input(path);
    if (!input) {
        throw std::runtime_error("无法打开 AST JSON 文件: " + path);
    }
    std::string text((std::istreambuf_iterator<char>(input)), std::istreambuf_iterator<char>());
    JsonParser parser(text);
    return parser.parse_ast_node();
}
