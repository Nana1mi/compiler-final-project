; ModuleID = 'sysy2022_compiler'
source_filename = "test_full.sy"

declare i32 @getint()
declare i32 @getch()
declare i32 @getarray(i32*)
declare void @putint(i32)
declare void @putch(i32)
declare void @putarray(i32, i32*)
declare void @starttime()
declare void @stoptime()

@globalVar = global i32 100
define i32 @add(i32 %a, i32 %b) {
label_1:
  %op0 = alloca i32
  store i32 %a, i32* %op0
  %op1 = alloca i32
  store i32 %b, i32* %op1
  %op2 = alloca i32
  %op3 = load i32, i32* %op0
  %op4 = load i32, i32* %op1
  %op5 = add i32 %op3, %op4
  store i32 %op5, i32* %op2
  %op6 = load i32, i32* %op2
  ret i32 %op6
}

define i32 @main() {
label_2:
  %op7 = alloca i32
  store i32 1, i32* %op7
  %op8 = alloca i32
  store i32 2, i32* %op8
  %op9 = alloca i32
  %op10 = load i32, i32* %op7
  %op11 = load i32, i32* %op8
  %op12 = call i32 @add(i32 %op10, i32 %op11)
  store i32 %op12, i32* %op9
  %op13 = load i32, i32* %op9
  %op14 = icmp sgt i32 %op13, 0
  br i1 %op14, label %label_3, label %label_4

label_3:
  %op15 = load i32, i32* %op9
  store i32 %op15, i32* %op7
  br label %label_5

label_4:
  store i32 0, i32* %op7
  br label %label_5

label_5:
  %op16 = load i32, i32* %op7
  ret i32 %op16
}

