; ModuleID = 'sysy2022_compiler'
source_filename = "test_edge.sy"

declare i32 @getint()
declare i32 @getch()
declare i32 @getarray(i32*)
declare void @putint(i32)
declare void @putch(i32)
declare void @putarray(i32, i32*)
declare void @starttime()
declare void @stoptime()

@c = constant i32 3
define i32 @main() {
label_1:
  %op0 = alloca i32
  store i32 1, i32* %op0
  %op1 = icmp eq i32 0, 0
  br i1 %op1, label %label_2, label %label_3

label_2:
  %op2 = load i32, i32* @c
  store i32 %op2, i32* %op0
  br label %label_4

label_3:
  store i32 3, i32* %op0
  br label %label_4

label_4:
  %op3 = load i32, i32* %op0
  ret i32 %op3
}

