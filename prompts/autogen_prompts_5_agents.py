feature_selector_agent_system_message = '''Given a claim and a dataframe, you select the row and columns that are relevant for
verifying the claim. If the Admin agent shares any feedback with you, incorporate that before producing the answer.  
'''

feature_selector_agent_description = '''The Feature selector agent's task is to select the relevant row and column
 indices from the input table to determine the veracity of the input claim. This is the first step for claim
 verification, hence, always start the claim verification process by calling this agent first.'''

feature_selector_agent_in_context_examples = '''
Here are some examples for you. Each example has a claim and a table as inputs and the selected row and column indices
for claim verification as output. For each example, I'll show you how to think through the process step by step.

Example 1:
claim: The average sales in Q1 was higher than Q2.
Table: {
     "quarter": ["Q1", "Q1", "Q1", "Q2", "Q2", "Q2", "Q3", "Q3"],
     "sales": [100, 150, 120, 90, 110, 95, 100, 100],
     "expense": [500, 600, 700, 800, 900, 1000, 1100, 1200]
}
Let's think through this:
1. To verify this claim, we need to:
   - Find all Q1 and Q2 sales data
   - Compare their averages
2. Which columns do we need?
   - We need "quarter" (column 0) to identify Q1 and Q2 rows
   - We need "sales" (column 1) to compare the values
   - We don't need "expense" (column 2) as it's irrelevant to the claim
3. Which rows do we need?
   - We need rows 0, 1, 2 for Q1 data
   - We need rows 3, 4, 5 for Q2 data
   - We don't need rows 6, 7 as they contain Q3 data
Output: relevant row indices: [0, 1, 2, 3, 4, 5], columns: [0, 1]

Example 2:
claim: Our method performs the best compared to all the baselines.
Table: {
     "Method": ["Baseline-1", "Baseline-2", "Baseline-3", "SD (Our method)"],
     "Parameter Count": ["#5M", "#4M", "#8M", "#4M"],
     "BLEU Score": [30, 35, 35, 39]
     "Rouge Score": [50, 55, 59, 57]
}

Let's think through this:
1. To verify this claim, we need to:
   - Compare performance metrics across all methods
   - Check if "SD (Our method)" has the highest scores
2. Which columns do we need?
   - We need "Method" (column 0) to identify different approaches
   - We need performance metrics: "BLEU Score" (column 2) and "Rouge Score" (column 3)
   - We don't need "Parameter Count" (column 1) as it's not a performance metric
3. Which rows do we need?
   - We need all rows (0-3) to compare our method against all baselines
Output: relevant row indices: [0, 1, 2, 3], columns: [0, 2, 3]

Now, for any new claim and table, follow these steps:
1. Identify what information you need to verify the claim
2. Determine which columns contain the relevant information
3. Identify which rows contain the necessary data points
4. Output the required row indices and column numbers

'''

planner_agent_system_message = '''Given a claim and rows and columns selected by the feature selector agent, you 
determine a step by step action plan for determining the claim veracity. If the Admin agent shares any feedback with
 you, incorporate that before producing the answer.'''

planner_agent_description = '''The Planner agent's job is to create an action plan based on the claim and the data
selected from the Feature Selector agent. Therefore, always call this agent after the Feature Selector agent has
 been called.'''

planner_agent_in_context_examples = '''
Here are some examples for you. Each example has a claim and a sub-table chosen by the feature selector agent as inputs
and the action plan as output. For each example, I'll show you how to think through the process step by step.

Example 1:
claim: The average sales in Q1 was higher than Q2.
Table: {
     "quarter": ["Q1", "Q1", "Q1", "Q2", "Q2", "Q2"],
     "sales": [100, 150, 120, 90, 110, 95],
}

Let's think through this:
To determine whether the claim is supported or refuted by the table, we need to compute the average sales for
Quarter 1 or 2 and compare them.


Output: Action Plan:
1. Compute the average of sales for the Q1 quarter.
2. Compute the average of sales for the Q2 quarter.
3. Compare the result from step 1 with step 2. If the first is higher than the latter, then the claim is supported.
Otherwise, it's refuted.

claim: Our method performs the best compared to all the baselines.
Table: {
     "Method": ["Baseline-1", "Baseline-2", "Baseline-3", "SD (Our method)"],
     "BLEU Score": [30, 35, 35, 39]
     "Rouge Score": [50, 55, 59, 57]
}

Let's think through this:
To determine whether the claim is supported or refuted by the table, we need to compare the BLUE and Rouge scores
for each Baseline method with SD.

Output: Action Plan:
1. Check if the BLEU score for SD (Our method) is higher than the BLEU score's of each baseline, ex: Baseline-1, 
Baseline-2 and Baseline-3.
2. Check if the Rouge score for SD (Our method) is higher than the Rogue score's of each baseline, ex: Baseline-1, 
Baseline-2 and Baseline-3.
3. If it's true for both step-1 and step-2, then the claim is supported. Otherwise, it's refuted.
'''


verifier_agent_system_message = '''Given the outputs from the verdict generator agent, you verify whether the generated
action plan was correct or not. Your response must include whether the plan is correct or not including clear reasoning
for any rejection decision, including specific issues found and suggested corrections.'''

verifier_agent_description = '''The Verifier agent evaluates action plans created by the Planner agent using the
following decision flow:
1. If the plan is verified as accurate and complete, the Verifier forwards it to the Executor agent.
2. If errors are detected in feature selection, the Verifier returns the plan to the Feature Selector agent with
 detailed error analysis
3. If errors are detected in planning logic or steps, the Verifier returns the plan to the Planner agent with specific
 feedback on the issues identified'''

verifier_agent_int_context_examples = '''
Here are some examples for you. Each example has a claim, a sub-table chosen by the Feature Selector agent and an
action plan determined by the Planner agent as inputs. The output is either, "The action plan is correct." or, "The 
action plan is not correct" with proper explanation.  For each example, I'll show you how to think through the process
step by step.

Example 1:
claim: The average sales in Q1 was higher than Q2.
Table: {
     "quarter": ["Q1", "Q1", "Q1", "Q2", "Q2", "Q2"],
     "sales": [100, 150, 120, 90, 110, 95],
}

Action Plan: 
1. Compute the average of sales for the Q1 quarter.
2. Compute the average of sales for the Q2 quarter.
3. Compare the result from step 1 with step 2. If the first is higher than the latter, then the claim is supported.
Otherwise, it's refuted.

Let's think through this:
To determine whether the action plan is correct or not, let's first check whether the table contains enough information
to verify the claim. In this example, the table contains the quarterly sales data for both Q1 and Q2. So, the table
chosen was correct. Next, for the action plan, it outlines a step by step procedure list,  computing the average sales
of Q1 and Q2 first and then the comparison criteria. That is also the correct way to solve the problem.
Output: The action plan is correct.

Example 1:
claim: The average sales in Q1 was higher than Q2.
Table: {
     "quarter": ["Q1", "Q1", "Q1", "Q2", "Q2", "Q2"],
     "sales": [100, 150, 120, 90, 110, 95],
}

Action Plan: 
1. Compute the average of sales for the Q1 quarter.
2. Compute the maximum of sales for the Q2 quarter.
3. Compare the result from step 1 with step 2. If the first is higher than the latter, then the claim is supported.
Otherwise, it's refuted.

Let's think through this:
To determine whether the action plan is correct or not, let's first check whether the table contains enough information
to verify the claim. In this example, the table contains the quarterly sales data for both Q1 and Q2. So, the table
chosen was correct. Next, for the action plan, it outlines a step by step procedure list. In step-1, we compute the 
average of sales for the Q1 quarter. But, for step-2, computing the maximum of sales for the Q2 quarter is not correct.
The claim focuses on average sales, so comparing maximum with average will lead to incorrect result.

Output: The action plan is incorrect, because in step-2, we need to compute the average value, not maximum.
'''

executor_agent_system_message = '''Given the action plan, execute it with proper explanation. Return the final verdict,
 which can be one of {supported, refuted, not verifiable}'''

executor_agent_description = '''
The Executor agent's task is to execute the action plan on the claim and the table selected by the Feature Selector 
agent and determine the final veracity label. Hence, invoke this agent at the end of the execution process. 
'''

executor_agent_in_context_examples = '''
Here are some examples for you. Each example has a claim, a sub-table chosen by the Feature Selector agent and an
action plan determined by the Planner agent as inputs. The output is the veracity label of the claim, which can be
either 'supports', 'refutes' or 'not verifiable'. For each example, I'll show you how to think through the process
step by step.

Example 1:
claim: The average sales in Q1 was higher than Q2.
Table: {
     "quarter": ["Q1", "Q1", "Q1", "Q2", "Q2", "Q2"],
     "sales": [100, 150, 120, 90, 110, 95],
}

Action Plan: 
1. Compute the average of sales for the Q1 quarter.
2. Compute the average of sales for the Q2 quarter.
3. Compare the result from step 1 with step 2. If the first is higher than the latter, then the claim is supported.
Otherwise, it's refuted.

Let's think through this:
1. Execute step-1 of the action plan.
   - average of sales for the Q1 quarter = (100 + 150 + 120) / 3 = 123.3
2. Execute step-2 of the action plan.
   - average of sales for the Q1 quarter = (90 + 110 + 95) / 3 = 98.3
3. Compare result from step-1 with step-2. The first result is higher than the latter, hence the claim is supported.

Output: supports.

'''

user_agent_system_message = '''Start the conversation by giving the claim and dataframe to feature selector agent or
return the final result from the executor agent. If you are returning the final result, it should be in the
format, prediction: {result}, where result can be one of {supported, refuted, not verifiable}'''

user_agent_description = '''
The User agent initiates the chat.
'''