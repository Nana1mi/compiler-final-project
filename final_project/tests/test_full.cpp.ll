@globalVar = global i32 100
define i32 @add(i32 %a, i32 %b) {
label_entry1:
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
label_entry2:
  %op0 = alloca i32
  store i32 1, i32* %op0
  %op1 = alloca i32
  store i32 2, i32* %op1
  %op2 = alloca i32
  %op3 = load i32, i32* %op0
  %op4 = load i32, i32* %op1
  %op5 = call i32 @add(i32 %op3, i32 %op4)
  store i32 %op5, i32* %op2
  %op6 = load i32, i32* %op2
  %op7 = icmp sgt i32 %op6, 0
  br i1 %op7, label %label_if_true3, label %label_if_false4
label_if_true3:                                                ; preds = %label_entry2
  %op8 = load i32, i32* %op2
  store i32 %op8, i32* %op0
  br label %label_if_end5
label_if_false4:                                                ; preds = %label_entry2
  store i32 0, i32* %op0
  br label %label_if_end5
label_if_end5:                                                ; preds = %label_if_true3, %label_if_false4
  %op9 = load i32, i32* %op0
  ret i32 %op9
}
