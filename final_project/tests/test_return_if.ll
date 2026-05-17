; ModuleID = 'sysy2022_compiler'
source_filename = "test_return_if.sy"

declare i32 @getint()
declare i32 @getch()
declare i32 @getarray(i32*)
declare void @putint(i32)
declare void @putch(i32)
declare void @putarray(i32, i32*)
declare void @starttime()
declare void @stoptime()

define i32 @main() {
label_1:
  %op0 = alloca i32
  store i32 1, i32* %op0
  %op1 = load i32, i32* %op0
  %op2 = icmp sgt i32 %op1, 0
  br i1 %op2, label %label_2, label %label_3

label_2:
  %op3 = load i32, i32* %op0
  ret i32 %op3

label_3:
  ret i32 0

}

