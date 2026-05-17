define i32 @main() {
label_entry1:
  %op0 = alloca i32
  store i32 1, i32* %op0
  %op1 = load i32, i32* %op0
  %op2 = icmp sgt i32 %op1, 0
  br i1 %op2, label %label_if_true2, label %label_if_false3
label_if_true2:                                                ; preds = %label_entry1
  %op3 = load i32, i32* %op0
  ret i32 %op3
label_if_false3:                                                ; preds = %label_entry1
  ret i32 0
}
