import autogen
from autogen import ConversableAgent, GroupChat, GroupChatManager, Cache
from autogen.oai.client import OpenAIWrapper
from read_json import *
from prompts.autogen_prompts_3_agents_v14_semtabfact_cells_used_2 import *
import argparse
import time
import json
import logging
import pandas as pd
from typing import Optional, List, Dict, Any, Union

# Set up logging
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')

# Modified generate_oai_reply to handle Together AI dictionary responses and add error logging
def generate_oai_reply(self, messages, sender, config):
    client = OpenAIWrapper(config=self.llm_config)
    try:
        logging.debug(f"Sending API request for model {config['config_list'][0]['model']}: {json.dumps(messages, indent=2)}")
        response = client.chat.completions.create(
            model=config["config_list"][0]["model"],
            messages=messages,
            temperature=config.get("temperature", 0),
            max_tokens=config.get("max_tokens", 1500),
        )
        content = response.choices[0].message.content
        # Handle dictionary response
        if isinstance(content, dict) and "content" in content:
            content = content["content"]
        if content is None or not isinstance(content, str) or content.strip() == "":
            logging.error(f"Invalid or empty response content: {content}")
            return False, None
        logging.debug(f"API response: {content}")
        return True, content
    except Exception as e:
        logging.error(f"API call failed: {str(e)}")
        return False, None


ConversableAgent._generate_oai_reply = generate_oai_reply

# Termination condition
def is_termination_msg(message):
    content = message.get("content", "").strip().lower()
    logging.debug(f"Checking inside is_termination_msg: {content}")
    lines = content.split('\n')
    return any(line.strip() in ["support", "refute", "not enough info"] for line in lines)

def calculate_confidence(response):
    confidence = 0.9
    response_lower = response.lower()
    uncertainty_indicators = [
        "unclear", "assume", "assumption", "might", "possibly", "not sure", "incomplete",
        "strict", "subjective", "interpret", "interpretation", "depends", "vague",
        "partial", "partially", "some", "limited", "insufficient"
    ]
    for indicator in uncertainty_indicators:
        if indicator in response_lower:
            confidence = max(0.6, confidence - 0.1)
    return confidence

# In EnhancedPlannerAgent
class EnhancedPlannerAgent(ConversableAgent):
    def generate_reply(self, messages: Optional[List[Dict[str, Any]]] = None, sender: Optional["Agent"] = None, **kwargs) -> Union[str, Dict, None]:
        response = super().generate_reply(messages, sender, **kwargs)
        if response is None or not isinstance(response, str):
            logging.error(f"PlannerAgent generated invalid response: {response}")
            return "Error: No valid response generated\nnot enough info\nConfidence: 0.50"
        confidence = calculate_confidence(response)
        return f"{response}\nConfidence: {confidence:.2f}"

# In EnhancedExecutorAgent
class EnhancedExecutorAgent(ConversableAgent):
    def generate_reply(self, messages: Optional[List[Dict[str, Any]]] = None, sender: Optional["Agent"] = None, **kwargs) -> Union[str, Dict, None]:
        response = super().generate_reply(messages, sender, **kwargs)
        if response is None or not isinstance(response, str):
            logging.error(f"ExecutorAgent generated invalid response: {response}")
            return "Error: No valid response generated\nnot enough info\nConfidence: 0.50"
        lines = response.strip().split('\n')
        has_verdict = any(line.strip() in ["support", "refute", "not enough info"] for line in lines[-2:])
        content_for_confidence = '\n'.join(lines[:-1] if has_verdict else lines)
        confidence = calculate_confidence(content_for_confidence)
        if not has_verdict:
            response += "\nnot enough info"
        response += f"\nConfidence: {confidence:.2f}"
        return response

# Updated EnhancedDataSufficiencyAgent with relaxed validation and dynamic table simplification
class EnhancedDataSufficiencyAgent(ConversableAgent):
    def generate_reply(self, messages: Optional[List[Dict[str, Any]]] = None, sender: Optional["Agent"] = None,
                       **kwargs) -> Union[str, Dict, None]:
        max_attempts = 3
        original_messages = messages
        for attempt in range(max_attempts):
            try:
                response = super().generate_reply(messages, sender, **kwargs)
                # Handle dictionary response from Together AI
                if isinstance(response, dict) and "content" in response:
                    response = response["content"]
                # Validate response
                if response is None or not isinstance(response, str) or response.strip() == "":
                    logging.error(f"Attempt {attempt + 1}: Invalid response: {response}")
                    if attempt == max_attempts - 1:
                        return {
                            "content": "<explanation>DataSufficiencyAgent failed to generate a valid response after retries.</explanation>\nnot enough info"}
                    continue

                logging.info(f"DataSufficiencyAgent response: {response}")
                response_lower = response.lower()
                # Check for allowed response options
                allowed_responses = ["support", "refute", "not enough info", "proceed to planning"]
                last_line = response_lower.strip().split("\n")[-1].strip()
                decision_found = last_line in allowed_responses

                # Relaxed explanation check: at least one non-empty line before verdict
                lines = response.strip().split("\n")
                explanation_found = len([line for line in lines[:-1] if line.strip()]) > 0 if lines else False

                if decision_found and explanation_found:
                    if sender.name == "User_Agent":
                        if last_line == "not enough info":
                            return {"content": response}
                        elif last_line == "proceed to planning":
                            if "<enhanced_claim>" not in response:
                                original_claim = messages[-1]["content"].split("Please verify this claim: ")[1].split(
                                    " Using the table:")[0]
                                response = response.replace("<enhanced_claim>", f"<enhanced_claim>{original_claim}")
                            return {"content": response}
                        else:
                            return {"content": response}
                    return {"content": response}
                else:
                    logging.warning(f"Attempt {attempt + 1}: Response lacks clear decision or explanation: {response}")
                    if attempt == max_attempts - 1:
                        return {
                            "content": f"{response}\n<explanation>DataSufficiencyAgent response lacks a clear decision or explanation; defaulting to unverifiable.</explanation>\nnot enough info"}
                    # Retry with simplified prompt on second-to-last attempt
                    if attempt == max_attempts - 2:
                        logging.info("Retrying with simplified prompt")
                        messages = self._simplify_prompt(original_messages)
                    continue

            except Exception as e:
                logging.error(f"Attempt {attempt + 1}: Exception in generate_reply: {str(e)}")
                if attempt == max_attempts - 1:
                    return {
                        "content": f"<explanation>DataSufficiencyAgent failed after retries: {str(e)}</explanation>\nnot enough info"}
        return {"content": f"<explanation>DataSufficiencyAgent failed after retries.</explanation>\nnot enough info"}

    def _simplify_prompt(self, messages: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Simplify the prompt by summarizing the table and claim."""
        last_message = messages[-1]["content"]
        claim = last_message.split("Please verify this claim: ")[1].split(" Using the table:")[0]
        caption = last_message.split("the table caption: ")[1].split(".")[0]
        table_data = self._kwargs.get("table_data", "")

        # Generate simplified CSV-like table
        simplified_table = self._generate_simplified_table(table_data)

        simplified_content = (
            f"Please verify this claim: {claim} Using summarized table: {simplified_table}, "
            f"caption: {caption}. Provide a brief explanation, then conclude with exactly one of: "
            f"'support', 'refute', or 'not enough info' on a new line. Example:\n"
            f"Explanation: The table shows relevant data supporting the claim.\n"
            f"support"
        )
        return messages[:-1] + [{"role": "user", "content": simplified_content}]

    def _generate_simplified_table(self, table_data: str) -> str:
        """Generate a simplified CSV-like table from HTML table_data."""
        if not table_data:
            logging.warning("Empty table_data, returning minimal table")
            return "No data available"

        # Parse HTML table to extract headers and rows
        try:
            from bs4 import BeautifulSoup
            soup = BeautifulSoup(table_data, 'html.parser')
            table = soup.find('table')
            if not table:
                logging.warning("No table found in table_data")
                return "No data available"

            headers = [th.get_text().strip().replace(",", " ") for th in table.find_all('th')]
            if not headers:
                headers = ["Col1", "Col2"]  # Fallback headers
            rows = []
            for tr in table.find_all('tr'):
                cells = [td.get_text().strip().replace(",", " ").replace("[BOLD]", "") for td in tr.find_all('td')]
                if cells:
                    rows.append(cells)

            # Ensure rows align with headers
            max_cols = len(headers)
            simplified_rows = [",".join(headers)]
            for row in rows[:10]:  # Limit to 10 rows
                if len(row) > max_cols:
                    row = row[:max_cols]
                elif len(row) < max_cols:
                    row = row + [""] * (max_cols - len(row))
                simplified_rows.append(",".join(row))

            return "\n".join(simplified_rows)
        except Exception as e:
            logging.error(f"Failed to parse HTML table: {str(e)}")
            return "No data available"

# Custom User Agent
class FactCheckingUserAgent(ConversableAgent):
    def receive(self, message, sender, request_reply=None, silent=False):
        message_content = message['content'] if isinstance(message, dict) else message
        logging.info(f"User_Agent received: {message_content} from {sender.name}")
        if sender.name in ["DataSufficiencyAgent", "Executor_Agent"]:
            lines = message_content.strip().lower().split('\n')
            verdict = next((line.strip() for line in lines if line.strip() in ["support", "refute", "not enough info"]), None)
            if verdict:
                logging.info(f"Verdict received: {verdict}")
                return False  # Terminate chat
        return super().receive(message, sender, request_reply, silent)

# Extract final verdict
def extract_final_verdict(chat_result):
    logging.info(f"Full chat history: {chat_result.chat_history}")
    for msg in reversed(chat_result.chat_history):
        if msg.get('name') in ['DataSufficiencyAgent', 'Executor_Agent'] and 'content' in msg:
            content = msg['content'].strip().lower()
            logging.info(f"Extracting verdict from {msg.get('name')}: {content}")
            lines = content.split('\n')
            for line in reversed(lines):
                if line.strip() in ["support", "refute", "not enough info"]:
                    return line.strip()
            logging.warning(f"Invalid verdict format in {msg.get('name')} response: {content}")
    logging.warning("No valid verdict found in chat history")
    return "not enough info"

# Extract planner explanation
def extract_planner_explanation(chat_result):
    for msg in chat_result.chat_history:
        if msg.get('name') == 'Planner_Agent' and 'content' in msg:
            content = msg['content'].strip()
            explanation = '\n'.join(line for line in content.split('\n') if not line.startswith("Confidence:"))
            try:
                confidence = next(float(line.split(":")[1].strip().split()[0]) for line in content.split('\n') if line.startswith("Confidence:"))
            except (StopIteration, ValueError):
                confidence = None
            logging.info(f"Extracting explanation from Planner_Agent: {content}")
            return {"explanation": explanation, "confidence": confidence}
    logging.warning("No valid Planner_Agent response found")
    return {"explanation": "No explanation provided", "confidence": None}

# Extract executor explanation
def extract_executor_explanation(chat_result):
    for msg in chat_result.chat_history:
        if msg.get('name') == 'Executor_Agent' and 'content' in msg:
            content = msg['content'].strip()
            # Extract explanation (excluding Confidence line)
            explanation_lines = [line for line in content.split('\n') if not line.startswith("Confidence:")]
            explanation = '\n'.join(explanation_lines)
            # Extract cells_used (if present)
            cells_used = None
            if '<cells_used>' in content and '</cells_used>' in content:
                start_idx = content.index('<cells_used>') + len('<cells_used>')
                end_idx = content.index('</cells_used>')
                cells_used = content[start_idx:end_idx].strip()
                logging.info(f"Executor_Agent cells_used: {cells_used}")
            # Extract confidence
            try:
                confidence = next(float(line.split(":")[1].strip().split()[0]) for line in content.split('\n') if line.startswith("Confidence:"))
            except (StopIteration, ValueError):
                confidence = None
            logging.info(f"Extracting explanation from Executor_Agent: {content}")
            return {
                "explanation": explanation,
                "confidence": confidence,
                "cells_used": cells_used
            }
    logging.warning("No valid Executor_Agent response found")
    return {
        "explanation": "No explanation provided",
        "confidence": None,
        "cells_used": None
    }

# Extract data sufficiency explanation
def extract_data_sufficiency_explanation(chat_result):
    for msg in chat_result.chat_history:
        if msg.get('name') == 'DataSufficiencyAgent' and 'content' in msg:
            content = msg['content'].strip()
            explanation = '\n'.join(line for line in content.split('\n') if not line.startswith("Plan improved"))
            logging.info(f"Extracting explanation from DataSufficiencyAgent: {content}")
            return {"explanation": explanation}
    logging.warning("No valid DataSufficiencyAgent response found")
    return {"explanation": "No explanation provided"}

# Custom speaker selection function
def custom_speaker_selection_func(last_speaker: ConversableAgent, groupchat: GroupChat) -> Union[ConversableAgent, str]:
    messages = groupchat.messages
    if len(messages) == 0:
        logging.debug("Returning DataSufficiencyAgent (initial message)")
        return data_sufficiency_agent

    last_message = messages[-1]
    logging.debug(f"last_speaker.name: {last_speaker.name}, last_message: {last_message}")

    # Default transitions
    if last_speaker.name == "User_Agent":
        logging.debug("Returning DataSufficiencyAgent")
        return data_sufficiency_agent
    elif last_speaker.name == "DataSufficiencyAgent":
        if "not enough info" in last_message["content"].lower():
            logging.debug("DataSufficiencyAgent determined claim unverifiable, returning User_Agent")
            return user_agent
        elif "Proceed to planning" in last_message["content"]:
            logging.debug("DataSufficiencyAgent determined claim verifiable, returning Planner_Agent")
            return planner_agent
        else:
            logging.debug("DataSufficiencyAgent provided verdict, returning User_Agent")
            return user_agent
    elif last_speaker.name == "Planner_Agent":
        logging.debug("Returning Executor_Agent")
        return executor_agent
    elif last_speaker.name == "Executor_Agent":
        logging.debug("Returning User_Agent")
        return user_agent

    logging.debug("Falling back to auto")
    return "auto"

def arg_parse():
    parser = argparse.ArgumentParser()
    parser.add_argument('--model', default='')
    parser.add_argument('--parameters', default='')
    parser.add_argument('--number_of_claims', default=100)
    parser.add_argument('--dataset_name', default='scitab')
    parser.add_argument('--only_allow_unique_tables', type=str, default="False")
    parser.add_argument('--only_error_ids', type=str, default="False")
    return parser.parse_args()

if __name__ == '__main__':
    args = arg_parse()
    args.only_allow_unique_tables = args.only_allow_unique_tables.lower() == 'true'
    args.only_error_ids = args.only_error_ids.lower() == 'true'

    llm_config = {
        "timeout": 2000,
        "max_retries": 3,
        "config_list": autogen.config_list_from_json(
            "OAI_CONFIG_LIST",
            filter_dict={"model": [args.model]},
        ),
        "temperature": 0
    }

    data_sufficiency_llm_config = {
        "timeout": 2000,
        "max_retries": 3,
        "config_list": autogen.config_list_from_json(
            "OAI_CONFIG_LIST",
            filter_dict={"model": [args.model]},
        ),
        "temperature": 0
    }
    logging.info("Initialized config")

    user_agent = FactCheckingUserAgent(
        name="User_Agent",
        system_message=user_agent_system_message,
        llm_config=llm_config,
        human_input_mode="NEVER",
        description=user_agent_description,
        is_termination_msg=is_termination_msg
    )

    planner_agent = EnhancedPlannerAgent(
        name="Planner_Agent",
        system_message=planner_agent_system_message + planner_agent_in_context_examples,
        llm_config=llm_config,
        human_input_mode="NEVER",
        description=planner_agent_description
    )

    executor_agent = EnhancedExecutorAgent(
        name="Executor_Agent",
        system_message=executor_agent_system_message + executor_agent_in_context_examples,
        llm_config=llm_config,
        human_input_mode="NEVER",
        description=executor_agent_description,
        code_execution_config=False
    )

    data_sufficiency_agent = EnhancedDataSufficiencyAgent(
        name="DataSufficiencyAgent",
        system_message=data_sufficiency_agent_system_message,
        llm_config=data_sufficiency_llm_config,
        human_input_mode="NEVER",
        description=data_sufficiency_agent_description
    )
    logging.info("Initialized all solo agents")

    allowed_transitions = {
        user_agent: [data_sufficiency_agent],
        data_sufficiency_agent: [planner_agent, user_agent],
        planner_agent: [executor_agent],
        executor_agent: [user_agent]
    }

    constrained_graph_chat = GroupChat(
        agents=[user_agent, planner_agent, executor_agent, data_sufficiency_agent],
        allowed_or_disallowed_speaker_transitions=allowed_transitions,
        speaker_transitions_type="allowed",
        messages=[],
        max_round=5,
        send_introductions=False,
        speaker_selection_method=custom_speaker_selection_func
    )

    constrained_group_chat_manager = GroupChatManager(
        groupchat=constrained_graph_chat,
        llm_config=llm_config
    )
    logging.info("Initialized group chat agent")

    tables_to_read = read_semtabfact(threshold=int(args.number_of_claims), dataset_name=args.dataset_name)
    logging.info(f"len of tables_to_read: {len(tables_to_read)}")
    model_predictions = []
    BATCH_SIZE = 10

    for batch_start in range(0, len(tables_to_read), BATCH_SIZE):
        batch_end = min(batch_start + BATCH_SIZE, len(tables_to_read))
        batch_tables = tables_to_read[batch_start:batch_end]

        for index, table_read in enumerate(batch_tables):
            overall_index = batch_start + index
            unique_id, table_data, table_caption, claim, label = table_read
            message = (
                f"Please verify this claim: {claim} Using the table: {table_data}, "
                f"the table caption: {table_caption}.\n"
                "Provide a brief explanation, then conclude with exactly one of: 'support', 'refute', or 'not enough info' on a new line. "
                "Example:\n"
                "Explanation: The table shows relevant data supporting the claim.\n"
                "support"
            )
            max_attempts = 3
            for attempt in range(max_attempts):
                try:
                    # Pass table_data to the agent
                    data_sufficiency_agent._kwargs = {
                        "table_data": table_data
                    }
                    with Cache.disk(cache_seed=45) as cache:
                        chat_result = user_agent.initiate_chat(
                            constrained_group_chat_manager,
                            message=message,
                            summary_method="reflection_with_llm",
                            cache=cache
                        )

                        final_verdict = extract_final_verdict(chat_result)
                        planner_result = extract_planner_explanation(chat_result)
                        executor_result = extract_executor_explanation(chat_result)
                        data_sufficiency_result = extract_data_sufficiency_explanation(chat_result)
                        cost = chat_result.cost
                        model_prediction = {
                            'unique_id': unique_id,
                            'claim': claim,
                            'table': table_data,
                            'table_caption': table_caption,
                            'gold_label': label,
                            'predicted_label': final_verdict,
                            'predicted_planner_explanation': planner_result["explanation"],
                            'predicted_planner_confidence': planner_result["confidence"],
                            'predicted_executor_explanation': executor_result["explanation"],
                            'predicted_executor_confidence': executor_result["confidence"],
                            'predicted_executor_cells_used': executor_result["cells_used"],
                            'predicted_data_sufficiency_explanation': data_sufficiency_result["explanation"],
                        }
                        model_predictions.append(model_prediction)
                        logging.info(f"model prediction: {final_verdict} for index: {overall_index + 1}")
                        break

                except Exception as e:
                    logging.error(f"Attempt {attempt + 1} failed: {str(e)}")
                    if attempt < max_attempts - 1:
                        logging.info(f"Attempt {attempt + 1} failed: {str(e)}. Retrying...")
                        time.sleep(30)
                    else:
                        logging.error(f"Failed after {max_attempts} attempts for claim {overall_index + 1}")
                        model_prediction = {
                            'unique_id': unique_id,
                            'claim': claim,
                            'gold_label': label,
                            'table': table_data,
                            'table_caption': table_caption,
                            'predicted_label': "not enough info",
                            'predicted_planner_explanation': f"Error: {str(e)}",
                            'predicted_planner_confidence': None,
                            'predicted_executor_explanation': f"Error: {str(e)}",
                            'predicted_executor_confidence': None,
                            'predicted_executor_cells_used': None,
                            'predicted_data_sufficiency_explanation': f"Error: {str(e)}",
                            'cost': 0
                        }
                        model_predictions.append(model_prediction)
            time.sleep(5)
        logging.info("Saving in output file intermediate")
        output_file_name = f'prediction_v14_{args.dataset_name}_cells_used_{str(len(tables_to_read))}_claims_{args.model.replace("/", "")}_intermediate_updated.json'
        with open(output_file_name, 'w') as file_o:
            json.dump(model_predictions, file_o, default=dataframe_to_json_serializable, indent=4)
            logging.info(f"Saved in output file intermediate: {output_file_name}")

    logging.info("Saving in output file final")
    output_file_name = f'prediction_v14_{args.dataset_name}_cells_used_{str(len(tables_to_read))}_claims_{args.model.replace("/", "")}_updated.json'
    with open(output_file_name, 'w') as file_o:
        json.dump(model_predictions, file_o, default=dataframe_to_json_serializable, indent=4)
    logging.info(f"Saved in output file final: {output_file_name}")