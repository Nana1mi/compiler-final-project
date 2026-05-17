"""
词法分析器主程序入口
"""
import sys
import os
from .lexer import Lexer


def main():
    """主函数"""
    lexer = Lexer()
    
    if len(sys.argv) > 1:
        # 从文件读取
        input_file = sys.argv[1]
        try:
            with open(input_file, 'r', encoding='utf-8') as f:
                source = f.read()
        except FileNotFoundError:
            print(f"错误：文件 '{input_file}' 未找到")
            return
        except Exception as e:
            print(f"读取文件错误：{e}")
            return
    else:
        # 从标准输入读取
        print("请输入源代码（Ctrl+D 结束）：")
        source = sys.stdin.read()
    
    # 词法分析
    tokens = lexer.tokenize(source)
    
    # 输出结果
    output = lexer.format_tokens(tokens)
    if output:
        print(output)


def run_test(test_dir: str):
    """运行测试用例
    
    Args:
        test_dir: 测试目录路径
    """
    lexer = Lexer()
    
    # 查找所有 .sy 文件
    test_files = []
    for filename in os.listdir(test_dir):
        if filename.endswith('.sy'):
            test_files.append(filename)
    
    test_files.sort()
    
    for test_file in test_files:
        print(f"\n{'='*60}")
        print(f"测试：{test_file}")
        print('='*60)
        
        input_path = os.path.join(test_dir, test_file)
        ref_file = test_file.replace('.sy', '.ref')
        ref_path = os.path.join(test_dir, ref_file)
        
        # 读取输入
        with open(input_path, 'r', encoding='utf-8') as f:
            source = f.read()
        
        # 词法分析
        tokens = lexer.tokenize(source)
        output = lexer.format_tokens(tokens)
        
        # 读取参考输出
        if os.path.exists(ref_path):
            with open(ref_path, 'r', encoding='utf-8') as f:
                expected = f.read().strip()
            
            # 比较
            actual = output.strip()
            
            if actual == expected:
                print("通过")
            else:
                print("失败")
                print("\n期望输出：")
                print(expected)
                print("\n实际输出：")
                print(actual)
                
                # 显示差异
                print("\n差异：")
                expected_lines = expected.split('\n')
                actual_lines = actual.split('\n')
                for i, (exp, act) in enumerate(zip(expected_lines, actual_lines)):
                    if exp != act:
                        print(f"  第 {i+1} 行：")
                        print(f"    期望：{exp}")
                        print(f"    实际：{act}")
                
                if len(expected_lines) != len(actual_lines):
                    print(f"  行数：期望 {len(expected_lines)} 行，实际 {len(actual_lines)} 行")
        else:
            print(f"参考文件未找到：{ref_path}")
            print("\n输出：")
            print(output)


if __name__ == '__main__':
    # 检查是否是测试模式
    if len(sys.argv) > 1 and sys.argv[1] == '--test':
        test_dir = sys.argv[2] if len(sys.argv) > 2 else 'code/test'
        run_test(test_dir)
    else:
        main()
