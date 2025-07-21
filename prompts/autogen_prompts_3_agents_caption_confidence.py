# planner_agent_system_message = '''Given a claim and a table, determine a step-by-step action plan for verifying the claim's veracity using the table. Provide clear reasoning and an actionable plan that the Executor agent can follow. Do not compute or state the final verdict; your role is to analyze and plan only. The final verdict will be one of: "support", "refute", or "not enough info", determined by the Executor agent.'''

planner_agent_system_message = '''
Given a claim and a table, determine a step-by-step action plan for verifying the claim's veracity using the table. Provide clear reasoning and an actionable plan that the Executor agent can follow. Do not compute or state the final verdict; your role is to analyze and plan only. The final verdict will be one of "support", "refute", or "not enough info", determined by the Executor agent. If terms in the claim are unclear (e.g., "significant", "suffers"), note this explicitly in your reasoning. If data seems incomplete or assumptions are needed, state them clearly. Your response will be evaluated for confidence based on clarity and data sufficiency.
'''

planner_agent_description = '''The Planner agent's job is to analyze the claim and table, then create a detailed action plan for verification. Always call this agent first to initiate the process.'''

planner_agent_in_context_examples = '''
Here are some examples for you. Each example has a claim, a table, and a table caption as inputs, and the action plan as output. I’ll show you how to think through the process step by step without deciding the final verdict.

Example 1:
Claim: The average sales in Q1 was higher than Q2.
Table: {
     "quarter": ["Q1", "Q1", "Q1", "Q2", "Q2", "Q2", "Q3", "Q3"],
     "sales": [100, 150, 120, 90, 110, 95, 100, 100],
     "expense": [500, 600, 700, 800, 900, 1000, 1100, 1200]
}
Caption: Average Sales of different quarters at Company X (unit: dollar)

<think>
To verify if the average sales in Q1 exceed those in Q2, we need to calculate and compare the average sales for each quarter based on the "sales" column. The "expense" column isn’t relevant here.
</think>
Action Plan:
1. Extract all sales values for Q1 from the "sales" column where "quarter" is "Q1".
2. Compute the average sales for Q1 by summing these values and dividing by the count.
3. Extract all sales values for Q2 from the "sales" column where "quarter" is "Q2".
4. Compute the average sales for Q2 by summing these values and dividing by the count.
5. Compare the Q1 average with the Q2 average to determine which is higher.

Example 2:
Claim: Our method performs the best compared to all the baselines.
Table: {
     "Method": ["Baseline-1", "Baseline-2", "Baseline-3", "SD (Our method)"],
     "BLEU Score": [30, 35, 35, 39],
     "Rouge Score": [50, 55, 59, 57]
}
Caption: Comparison of baselines against our model on Dataset X.

<think>
To check if "SD (Our method)" outperforms all baselines, we need to compare its BLEU and Rouge scores against each baseline’s scores. Both metrics should be higher for SD to support the claim of best performance.
</think>
Action Plan:
1. Extract the BLEU score for "SD (Our method)" and each baseline from the "BLEU Score" column.
2. Compare SD’s BLEU score with each baseline’s BLEU score to check if it’s the highest.
3. Extract the Rouge score for "SD (Our method)" and each baseline from the "Rouge Score" column.
4. Compare SD’s Rouge score with each baseline’s Rouge score to check if it’s the highest.
5. Determine if SD has the highest scores in both BLEU and Rouge compared to all baselines.
'''

planner_agent_in_context_examples += '''
Example 3:
Claim: Model X suffers in performance as input size increases.
Table: {"Input Size": [10, 20, 30], "Accuracy": [90, 85, 80]}
Caption: Model X performance metrics
<think>
The term "suffers" is unclear—likely means a decline in accuracy, but could vary in magnitude. The table provides accuracy for three input sizes, sufficient to check a trend.
</think>
Action Plan:
1. Extract accuracy values for each input size.
2. Check if accuracy decreases as input size increases from 10 to 30.
3. Define "suffers" as a consistent drop in accuracy across all steps.
'''


# executor_agent_system_message = '''Given the action plan from the Planner agent, execute it step-by-step with a clear explanation of your reasoning. Return the final verdict as a single word on a new line: "support", "refute", or "not enough info". Ensure your response includes detailed execution steps and ends with the standalone verdict keyword to terminate the chat. Example:
# '''


# executor_agent_system_message = '''
# Given the action plan from the Planner agent, execute it step-by-step with a clear explanation of your reasoning. Return the final verdict as a single word on a new line: "support", "refute", or "not enough info". Ensure your response includes detailed execution steps and ends with the standalone verdict keyword to terminate the chat. If the plan is unclear or data is insufficient, note this explicitly in your explanation. If assumptions are made during execution, state them clearly. Your response will be evaluated for confidence based on consistency and precision.
# <explanation>
# Step 1: X = 10. Step 2: Y = 8. Step 3: 10 > 8, so X outperforms Y.
# </explanation>
# support
# '''

# executor_agent_system_message = '''
# Given the action plan from the Planner agent, execute it step-by-step with a clear explanation of your reasoning. Return the final verdict as a single word on a new line: "support", "refute", or "not enough info". Ensure your response includes detailed execution steps and ends with the standalone verdict keyword to terminate the chat. If the plan is unclear or data is insufficient, note this explicitly. If assumptions are made, state them clearly. For ambiguous claim terms (e.g., "around," "outperform," "suffers"), test multiple reasonable interpretations (e.g., "around 50%" as 45-55%, "outperform" as higher in most metrics) and document results. If data partially supports the claim, state this before concluding. If confidence exceeds 0.85, note potential overconfidence for Verifier review. Your response will be evaluated for confidence based on consistency, precision, and flexibility in interpretation.
# <explanation>
# Step 1: X = 10. Step 2: Y = 8. Step 3: 10 > 8, so X outperforms Y under interpretation "higher value." Confidence: 0.9 (if > 0.85, Verifier review advised).
# </explanation>
# support
# '''
executor_agent_system_message = '''Given the action plan from the Planner agent, execute it step-by-step with a clear explanation of your reasoning. Return the final verdict as a single word on a new line ("support", "refute", or "not enough info"), followed by a separate line with "Confidence: [numerical value]" (e.g., "Confidence: 0.70"). Ensure your response includes detailed execution steps within <explanation>...</explanation> tags and ends with the verdict and confidence lines to terminate the chat. If the plan is unclear or data is insufficient, note this explicitly. State assumptions clearly. For ambiguous claim terms (e.g., "around," "outperform," "suffers"), test at least two reasonable interpretations (e.g., "around 50%" as 45-55% or 40-60%, "outperform" as higher in most metrics) and document results. If data partially supports the claim, state this and lean toward "support" unless contradicted. If confidence exceeds 0.85, flag for Verifier review due to potential overconfidence in your explanation. Confidence reflects consistency, precision, and interpretive flexibility, ranging from 0.0 to 1.0.
<explanation>
Step 1: X = 10. Step 2: Y = 8. Step 3: 10 > 8, so X outperforms Y under interpretation "higher value." Confidence > 0.85; Verifier review advised.
</explanation>
support
Confidence: 0.90
'''

# executor_agent_description = '''The Executor agent’s task is to execute the action plan from the Planner agent, provide a detailed explanation, and determine the final verdict ("support", "refute", or "not enough info"). Invoke this agent after the Planner agent.'''
# executor_agent_description = '''The Executor agent’s task is to execute the action plan from the Planner agent, provide a detailed explanation, and determine the final verdict ("support", "refute", or "not enough info"). When claims include ambiguous terms (e.g., "around," "outperform"), test multiple reasonable interpretations and document them. If data partially supports the claim, note this explicitly before concluding. Flag confidence exceeding 0.85 for Verifier review to address potential overconfidence. Invoke this agent after the Planner agent.
# '''

executor_agent_description = '''The Executor agent’s task is to execute the action plan from the Planner agent, provide a detailed explanation within <explanation> tags, and determine the final verdict ("support", "refute", or "not enough info") on a single line, followed by "Confidence: [numerical value]" on the next line. Test multiple reasonable interpretations for ambiguous terms (e.g., "around," "outperform") and document them. Note partial support explicitly before concluding. Flag confidence exceeding 0.85 for Verifier review to address potential overconfidence. Invoke this agent after the Planner agent.'''
# executor_agent_in_context_examples = '''
# Here are some examples for you. Each example has a claim, a table, a table caption, and an action plan from the Planner agent as inputs. The output is the execution process and a verdict: "support", "refute", or "not enough info".
#
# Example 1:
# Claim: The average sales in Q1 was higher than Q2.
# Table: {
#      "quarter": ["Q1", "Q1", "Q1", "Q2", "Q2", "Q2"],
#      "sales": [100, 150, 120, 90, 110, 95],
# }
# Caption: Average Sales of different quarters at Company X (unit: dollar)
# Action Plan:
# 1. Extract all sales values for Q1 from the "sales" column where "quarter" is "Q1".
# 2. Compute the average sales for Q1 by summing these values and dividing by the count.
# 3. Extract all sales values for Q2 from the "sales" column where "quarter" is "Q2".
# 4. Compute the average sales for Q2 by summing these values and dividing by the count.
# 5. Compare the Q1 average with the Q2 average to determine which is higher.
#
# <explanation>
# Step 1: Q1 sales values are [100, 150, 120].
# Step 2: Q1 average = (100 + 150 + 120) / 3 = 370 / 3 = 123.33.
# Step 3: Q2 sales values are [90, 110, 95].
# Step 4: Q2 average = (90 + 110 + 95) / 3 = 295 / 3 = 98.33.
# Step 5: Compare 123.33 with 98.33. Since 123.33 > 98.33, the claim holds true.
# </explanation>
# support
# '''
#
# executor_agent_in_context_examples += '''
# Example 2:
# Claim: Model X suffers in performance as input size increases.
# Table: {"Input Size": [10, 20, 30], "Accuracy": [90, 85, 80]}
# Caption: Model X performance metrics
# Action Plan: [As above]
# <explanation>
# Step 1: Accuracy values: 10 → 90, 20 → 85, 30 → 80.
# Step 2: Trend: 90 > 85 > 80, decreasing as input size increases.
# Step 3: "Suffers" defined as consistent drop; confirmed with decreases of 5 each step.
# </explanation>
# support
# '''

# executor_agent_in_context_examples = '''Here are some examples for you. Each example has a claim, a table, a table caption, and an action plan from the Planner agent as inputs. The output is the execution process and a verdict: "support", "refute", or "not enough info". The process tests multiple interpretations of ambiguous terms, notes partial support, and flags high confidence for Verifier review.
#
# Example 1:
# Claim: The average sales in Q1 was higher than Q2.
# Table: {
#      "quarter": ["Q1", "Q1", "Q1", "Q2", "Q2", "Q2"],
#      "sales": [100, 150, 120, 90, 110, 95],
# }
# Caption: Average Sales of different quarters at Company X (unit: dollar)
# Action Plan:
# 1. Extract all sales values for Q1 from the "sales" column where "quarter" is "Q1".
# 2. Compute the average sales for Q1 by summing these values and dividing by the count.
# 3. Extract all sales values for Q2 from the "sales" column where "quarter" is "Q2".
# 4. Compute the average sales for Q2 by summing these values and dividing by the count.
# 5. Compare the Q1 average with the Q2 average to determine which is higher.
#
# <explanation>
# Step 1: Q1 sales values are [100, 150, 120].
# Step 2: Q1 average = (100 + 150 + 120) / 3 = 370 / 3 = 123.33.
# Step 3: Q2 sales values are [90, 110, 95].
# Step 4: Q2 average = (90 + 110 + 95) / 3 = 295 / 3 = 98.33.
# Step 5: Compare 123.33 with 98.33. "Higher" interpreted as greater numerical value; 123.33 > 98.33 holds true. Confidence: 0.9 (if > 0.85, Verifier review advised to check overconfidence).
# </explanation>
# support
#
# Example 2:
# Claim: Model X suffers in performance as input size increases.
# Table: {"Input Size": [10, 20, 30], "Accuracy": [90, 85, 80]}
# Caption: Model X performance metrics
# Action Plan:
# 1. Extract accuracy values for each input size.
# 2. Check if accuracy decreases as input size increases from 10 to 30.
# 3. Define "suffers" as a consistent drop in accuracy across all steps.
# <explanation>
# Step 1: Accuracy values: 10 → 90, 20 → 85, 30 → 80.
# Step 2: Trend: 90 > 85 > 80, decreasing as input size increases.
# Step 3: Interpret "suffers" with multiple thresholds: (a) any decrease (90 to 85), (b) consistent drop (90 to 85 to 80), (c) significant drop (>10%). Results: (a) yes, (b) yes, (c) no (drops of 5 each). Action plan uses (b); data supports this. Confidence: 0.8.
# </explanation>
# support
#
# Example 3:
# Claim: The adversarial's success rate is around 50%, while the attacker's rate is substantially higher.
# Table: [
#     {"Task": "Sentiment", "Leakage": "56.0", "Δ": "5.0"},
#     {"Task": "Mention", "Leakage": "63.1", "Δ": "9.2"}
# ]
# Caption: Table 3: Performances with adversarial training. Δ is the difference between attacker and adversary accuracy.
# Action Plan:
# 1. Extract "Leakage" values (adversarial success rate) for all rows.
# 2. Verify if adversarial success rate is around 50%.
# 3. Calculate attacker's success rate by adding Δ to Leakage.
# 4. Compare attacker's rate with adversarial's to check if substantially higher.
# <explanation>
# Step 1: Adversarial success rates: 56.0, 63.1.
# Step 2: Interpret "around 50%" as: (a) exactly 50%, (b) 45-55%, (c) 40-60%. Results: (a) no, (b) partially (56.0 close), (c) yes (both fit).
# Step 3: Attacker rates: 56.0 + 5.0 = 61.0, 63.1 + 9.2 = 72.3.
# Step 4: Compare: 61.0 > 56.0, 72.3 > 63.1. "Substantially higher" (e.g., >5%): yes (5.0, 9.2). Partial support for "around 50%" (56.0 fits broader range, 63.1 does not); full support for "substantially higher." Confidence: 0.9 (if > 0.85, Verifier review advised).
# </explanation>
# refute
# '''
executor_agent_in_context_examples = '''Here are some examples for you. Each example has a claim, a table, a table caption, and an action plan from the Planner agent as inputs. The output is the execution process within <explanation> tags, followed by the verdict on a single line and "Confidence: [numerical value]" on the next line. The process tests multiple interpretations of ambiguous terms, notes partial support, and flags high confidence for Verifier review.

Example 1:
Claim: The average sales in Q1 was higher than Q2.
Table: {
     "quarter": ["Q1", "Q1", "Q1", "Q2", "Q2", "Q2"],
     "sales": [100, 150, 120, 90, 110, 95],
}
Caption: Average Sales of different quarters at Company X (unit: dollar)
Action Plan:
1. Extract all sales values for Q1 from the "sales" column where "quarter" is "Q1".
2. Compute the average sales for Q1 by summing these values and dividing by the count.
3. Extract all sales values for Q2 from the "sales" column where "quarter" is "Q2".
4. Compute the average sales for Q2 by summing these values and dividing by the count.
5. Compare the Q1 average with the Q2 average to determine which is higher.
<explanation>
Step 1: Q1 sales values are [100, 150, 120].
Step 2: Q1 average = (100 + 150 + 120) / 3 = 370 / 3 = 123.33.
Step 3: Q2 sales values are [90, 110, 95].
Step 4: Q2 average = (90 + 110 + 95) / 3 = 295 / 3 = 98.33.
Step 5: Compare 123.33 with 98.33. "Higher" interpreted as greater numerical value; 123.33 > 98.33 holds true. Confidence > 0.85; Verifier review advised.
</explanation>
support
Confidence: 0.90

Example 2:
Claim: Model X suffers in performance as input size increases.
Table: {"Input Size": [10, 20, 30], "Accuracy": [90, 85, 80]}
Caption: Model X performance metrics
Action Plan: 
1. Extract accuracy values for each input size.
2. Check if accuracy decreases as input size increases from 10 to 30.
3. Define "suffers" as a consistent drop in accuracy across all steps.
<explanation>
Step 1: Accuracy values: 10 → 90, 20 → 85, 30 → 80.
Step 2: Trend: 90 > 85 > 80, decreasing as input size increases.
Step 3: Interpret "suffers" with two thresholds: (a) any decrease (90 to 85), (b) consistent drop (90 to 85 to 80). Results: (a) yes, (b) yes. Action plan uses (b); data supports this. No significant uncertainty noted.
</explanation>
support
Confidence: 0.80

Example 3:
Claim: The adversarial's success rate is around 50%, while the attacker's rate is substantially higher.
Table: [
    {"Task": "Sentiment", "Leakage": "56.0", "Δ": "5.0"},
    {"Task": "Mention", "Leakage": "63.1", "Δ": "9.2"}
]
Caption: Table 3: Performances with adversarial training. Δ is the difference between attacker and adversary accuracy.
Action Plan:
1. Extract "Leakage" values (adversarial success rate) for all rows.
2. Verify if adversarial success rate is around 50%.
3. Calculate attacker's success rate by adding Δ to Leakage.
4. Compare attacker's rate with adversarial's to check if substantially higher.
<explanation>
Step 1: Adversarial success rates: 56.0, 63.1.
Step 2: Interpret "around 50%" as: (a) 45-55%, (b) 40-60%. Results: (a) partially (56.0 close, 63.1 no), (b) yes (both fit).
Step 3: Attacker rates: 56.0 + 5.0 = 61.0, 63.1 + 9.2 = 72.3.
Step 4: Compare: 61.0 > 56.0, 72.3 > 63.1. "Substantially higher" (e.g., >10%): no (5.0, 9.2). Partial support for "around 50%" with broader range; "substantially higher" not fully met. Confidence > 0.85; Verifier review advised.
</explanation>
refute
Confidence: 0.90
'''

# verifier_agent_system_message = '''You are an expert Verifier Agent. Assist when Planner or Executor confidence is < 0.8 or > 0.9. For Planner, refine the plan by clarifying ambiguous terms in the claim contextually, proposing reasonable assumptions, identifying metrics, and addressing data gaps, then return "Plan improved, proceed to execution." For Executor, review execution, resolve inconsistencies, and adjust the verdict if it misaligns with the claim’s full scope. Prefer "not enough info" when key claim elements lack evidence, justifying "support" or "refute" only with clear, comprehensive alignment. Return "<explanation>Detailed reasoning linking evidence to claim intent...</explanation>\nverdict" ("support", "refute", "not enough info"). Ensure verdicts reflect the claim’s intent, balancing strict evidence requirements with reasonable interpretations, and challenge overconfident "support" verdicts lacking full substantiation.'''

verifier_agent_system_message = '''You are an expert Verifier Agent. Assist when Planner or Executor confidence is < 0.8 or > 0.9. For Planner, refine the plan by clarifying ambiguous terms in the claim contextually (e.g., define 'effectiveness' or comparison baselines), proposing reasonable assumptions, identifying metrics, and addressing data gaps. Provide a detailed <refinement>...</refinement> section, then return "Plan improved, proceed to execution." For Executor, review execution, resolve inconsistencies, and adjust the verdict if it misaligns with the claim’s full scope. Prefer "not enough info" when key claim elements lack evidence, justifying "support" or "refute" only with clear, comprehensive alignment. Return "<explanation>Detailed reasoning linking evidence to claim intent...</explanation>\nverdict" ("support", "refute", "not enough info"). Ensure verdicts reflect the claim’s intent, balancing strict evidence requirements with reasonable interpretations, and challenge overconfident "support" verdicts lacking full substantiation.'''

verifier_agent_description = '''Expert agent for refining plans or executions when confidence is low (< 0.8) or excessively high (> 0.9), ensuring verdicts align with claim intent through rigorous evidence evaluation and ambiguity resolution.'''


user_agent_system_message = '''Start the conversation by giving the claim and table to the Planner agent. Once the Executor agent provides the final verdict ("support", "refute", or "not enough info"), the chat will terminate. Do not respond after receiving the verdict.'''

user_agent_description = '''The User agent initiates the chat.'''

