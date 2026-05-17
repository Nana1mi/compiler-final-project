@c = constant i32 3
define i32 @main() {
label_entry1:
  %op0 = alloca i32
  store i32 1, i32* %op0
  %op1 = icmp eq i32 0, 0
  br i1 %op1, label %label_if_true2, label %label_if_false3
label_if_true2:                                                ; preds = %label_entry1
  %op2 = load i32, i32* @c
  store i32 %op2, i32* %op0
  br label %label_if_end4
label_if_false3:                                                ; preds = %label_entry1
  store i32 3, i32* %op0
  br label %label_if_end4
label_if_end4:                                                ; preds = %label_if_true2, %label_if_false3
  %op3 = load i32, i32* %op0
  ret i32 %op3
}
