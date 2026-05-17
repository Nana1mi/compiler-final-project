cmake_minimum_required(VERSION 3.16)

project(cminus_ir_gen_demo)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_CXX_FLAGS "${CMAKE_CXX_FLAGS} -g -Wall -Wno-attributes -Wno-unused-variable")

set(COMPILER_IR_DIR "${CMAKE_CURRENT_SOURCE_DIR}/../../compiler_ir")

file(GLOB_RECURSE COMPILER_IR_SRC "${COMPILER_IR_DIR}/src/*.cpp")

add_executable(ir_gen_demo
    main.cpp
    ast_json.cpp
    ir_visitor.cpp
    ${COMPILER_IR_SRC}
)

target_include_directories(ir_gen_demo PRIVATE
    "${COMPILER_IR_DIR}/include"
)
