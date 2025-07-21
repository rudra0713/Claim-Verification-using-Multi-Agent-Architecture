planner_agent_system_message = '''Given a claim and a table, you determine a step by step action plan for
determining the claim veracity from the input table. Ensure that your action plan is clear and can be executed by the 
Executor agent.'''

planner_agent_description = '''The Planner agent's job is to create an action plan based on the claim and the table.
 Therefore, always call this agent at the beginning of the execution process'''

planner_agent_in_context_examples = '''
Here are some examples for you. Each example has a claim and a table as inputs
and the action plan as output. For each example, I'll show you how to think through the process step by step.

Example 1:
claim: The average sales in Q1 was higher than Q2.
Table: {
     "quarter": ["Q1", "Q1", "Q1", "Q2", "Q2", "Q2", "Q3", "Q3"],
     "sales": [100, 150, 120, 90, 110, 95, 100, 100],
     "expense": [500, 600, 700, 800, 900, 1000, 1100, 1200]
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


# executor_agent_system_message = '''Given the action plan, execute it with proper explanation. Return the final verdict,
# which can be one of {supported, refuted, not verifiable}. Ensure that your response is clear and can be processed by
# the User agent to produce a JSON output.'''
executor_agent_system_message = '''Given the action plan, execute it with proper explanation. Return the final verdict,
which can be one of {supported, refuted, not verifiable}. Ensure that your response is clear and can be processed by
the User agent to produce a JSON output. Use the `format_verdict` function to return your final verdict in JSON format,
e.g., format_verdict("supported").'''

executor_agent_description = '''
The Executor agent's task is to execute the action plan from the Planner agent on the claim and the table. 
Hence, invoke this agent after the Planner agent. 
'''

executor_agent_in_context_examples = '''
Here are some examples for you. Each example has a claim, a table and an
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

user_agent_system_message = '''
Start the conversation by giving the claim and dataframe to the Planner agent or return the final result from the Executor agent. 
If you are returning the final result, your response must be a valid JSON object with the following structure:
{
    "prediction": "support" | "refute" | "not verifiable info"
}
Example:
{
    "prediction": "refute"
}
Ensure that the response is strictly in JSON format and includes the "prediction" key with one of the allowed values.
'''

user_agent_description = '''
The User agent initiates the chat.
'''