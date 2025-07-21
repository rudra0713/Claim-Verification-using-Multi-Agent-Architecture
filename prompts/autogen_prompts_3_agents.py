planner_agent_system_message = '''Given a claim and a table, determine a step-by-step action plan for verifying the claim's veracity using the table. Ensure your action plan is clear and can be executed by the Executor agent. The final verdict must be one of: "support", "refute", or "not verifiable info".'''

planner_agent_description = '''The Planner agent's job is to create an action plan based on the claim and the table. Always call this agent at the beginning of the execution process.'''

planner_agent_in_context_examples = '''
Here are some examples for you. Each example has a claim and a table as inputs and the action plan as output. For each example, I'll show you how to think through the process step by step.

Example 1:
Claim: The average sales in Q1 was higher than Q2.
Table: {
     "quarter": ["Q1", "Q1", "Q1", "Q2", "Q2", "Q2", "Q3", "Q3"],
     "sales": [100, 150, 120, 90, 110, 95, 100, 100],
     "expense": [500, 600, 700, 800, 900, 1000, 1100, 1200]
}

Let's think through this:
To determine whether the claim is supported or refuted by the table, we need to compute the average sales for Quarters 1 and 2 and compare them.

Output: Action Plan:
1. Compute the average of sales for the Q1 quarter.
2. Compute the average of sales for the Q2 quarter.
3. Compare the result from step 1 with step 2. If the first is higher than the latter, return "support". Otherwise, return "refute".

Example 2:
Claim: Our method performs the best compared to all the baselines.
Table: {
     "Method": ["Baseline-1", "Baseline-2", "Baseline-3", "SD (Our method)"],
     "BLEU Score": [30, 35, 35, 39],
     "Rouge Score": [50, 55, 59, 57]
}

Let's think through this:
To determine whether the claim is supported or refuted by the table, we need to compare the BLEU and Rouge scores for each Baseline method with SD.

Output: Action Plan:
1. Check if the BLEU score for SD (Our method) is higher than the BLEU scores of each baseline (Baseline-1, Baseline-2, Baseline-3).
2. Check if the Rouge score for SD (Our method) is higher than the Rouge scores of each baseline (Baseline-1, Baseline-2, Baseline-3).
3. If both step 1 and step 2 are true, return "support". Otherwise, return "refute".
'''

executor_agent_system_message = '''Given the action plan, execute it with a clear explanation. Return the final verdict as a single word: "support", "refute", or "not verifiable info". Ensure your final message is just the verdict keyword to terminate the chat.'''

executor_agent_description = '''The Executor agent's task is to execute the action plan from the Planner agent on the claim and the table. Invoke this agent after the Planner agent.'''

executor_agent_in_context_examples = '''
Here are some examples for you. Each example has a claim, a table, and an action plan determined by the Planner agent as inputs. The output is the veracity label of the claim: "support", "refute", or "not verifiable info". For each example, I'll show you how to think through the process step by step.

Example 1:
Claim: The average sales in Q1 was higher than Q2.
Table: {
     "quarter": ["Q1", "Q1", "Q1", "Q2", "Q2", "Q2"],
     "sales": [100, 150, 120, 90, 110, 95],
}
Action Plan:
1. Compute the average of sales for the Q1 quarter.
2. Compute the average of sales for the Q2 quarter.
3. Compare the result from step 1 with step 2. If the first is higher than the latter, return "support". Otherwise, return "refute".

Let's think through this:
1. Average of sales for Q1 = (100 + 150 + 120) / 3 = 123.3
2. Average of sales for Q2 = (90 + 110 + 95) / 3 = 98.3
3. Compare 123.3 with 98.3. Since 123.3 > 98.3, the claim is supported.

Output: "support"
'''

user_agent_system_message = '''Start the conversation by giving the claim and table to the Planner agent. Once the Executor agent provides the final verdict ("support", "refute", or "not verifiable info"), the chat will terminate. Do not respond after receiving the verdict.'''

user_agent_description = '''The User agent initiates the chat.'''
