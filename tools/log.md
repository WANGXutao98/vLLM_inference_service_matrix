
计算平均total completions 长度
```
awk -F'[:=, ]' '{for(i=1;i<=NF;i++){if($i=="total_tokens"){total_tokens_sum+=$(i+1);count++}}} END {if(count>0)print "Average total_tokens: " total_tokens_sum/count; else print "No records found."}' vllm_infer.log
```

计算平均耗时
awk -F'[:=,]' '{ cost_time_sum += $(NF-1); count++ } END { if (count > 0) print "Average cost_time: " cost_time_sum / count; else print "No records found." }' vllm_infer.log