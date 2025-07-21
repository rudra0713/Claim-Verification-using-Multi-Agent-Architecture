import autogen
from autogen import ConversableAgent, GroupChat, GroupChatManager, Cache
from autogen.oai.client import OpenAIWrapper
from read_json import *
from prompts.autogen_prompts_3_agents_v14_findver_4 import *
import argparse
import time
import json
import logging
import pandas as pd
from typing import Optional, List, Dict, Any, Union

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')


# Standard reply generation
def generate_oai_reply(self, messages, sender, config):
    client = OpenAIWrapper(config=self.llm_config)
    response = client.chat.completions.create(
        model=config["config_list"][0]["model"],
        messages=messages,
        temperature=config.get("temperature", 0),
        max_tokens=config.get("max_tokens", 1500),
    )
    return True, response.choices[0].message.content

ConversableAgent._generate_oai_reply = generate_oai_reply

# Termination condition
def is_termination_msg(message):
    content = message.get("content", "").strip().lower()
    print(f"checking inside is_termination_msg: {content}")
    lines = content.split('\n')
    return any(line.strip() in ["support", "refute", "not enough info"] for line in lines)

def calculate_confidence(response):
    confidence = 0.9
    response_lower = response.lower()
    uncertainty_indicators = [
        "unclear", "assume", "assumption", "might", "possibly", "not sure", "incomplete",
        "strict",
        "subjective", "interpret", "interpretation", "depends", "vague",
        "partial", "partially", "some", "limited", "insufficient"
    ]
    for indicator in uncertainty_indicators:
        if indicator in response_lower:
            confidence = max(0.6, confidence - 0.1)
    return confidence

# Custom Planner Agent with confidence
class EnhancedPlannerAgent(ConversableAgent):
    def generate_reply(self, messages: Optional[List[Dict[str, Any]]] = None, sender: Optional["Agent"] = None, **kwargs) -> Union[str, Dict, None]:
        response = super().generate_reply(messages, sender, **kwargs)
        if response is None or not isinstance(response, str):
            return {"content": response, "confidence": None}
        confidence = calculate_confidence(response)
        return {
            "content": f"{response}\nConfidence: {confidence:.2f}",
            "confidence": confidence
        }

# Custom Executor Agent with confidence
class EnhancedExecutorAgent(ConversableAgent):
    def generate_reply(self, messages: Optional[List[Dict[str, Any]]] = None, sender: Optional["Agent"] = None,
                       **kwargs) -> Union[str, Dict, None]:
        response = super().generate_reply(messages, sender, **kwargs)
        if response is None or not isinstance(response, str):
            return {"content": "Error: No valid response generated\nnot enough info\nConfidence: 0.50",
                    "confidence": 0.50}

        # Ensure response ends with verdict and confidence
        lines = response.strip().split('\n')
        has_verdict = any(line.strip() in ["support", "refute", "not enough info"] for line in lines[-2:])

        # Calculate confidence based on content (excluding verdict line)
        content_for_confidence = '\n'.join(lines[:-1] if has_verdict else lines)
        confidence = calculate_confidence(content_for_confidence)

        # Append or correct verdict and confidence
        if not has_verdict:
            response += "\nnot enough info"
        response += f"\nConfidence: {confidence:.2f}"

        return {"content": response, "confidence": confidence}

# Custom DataSufficiencyAgent (formerly Verifier Agent)
class EnhancedDataSufficiencyAgent(ConversableAgent):
    def generate_reply(self, messages: Optional[List[Dict[str, Any]]] = None, sender: Optional["Agent"] = None,
                       **kwargs) -> Union[str, Dict, None]:
        response = super().generate_reply(messages, sender, **kwargs)
        if response is None or not isinstance(response, str):
            logging.error("DataSufficiencyAgent failed to generate a valid response")
            return {"content": "<explanation>DataSufficiencyAgent failed to generate a valid response due to internal error.</explanation>\nnot enough info"}

        if sender.name == "User_Agent":
            logging.info(f"DataSufficiencyAgent response: {response}")
            if "not enough info" in response.lower():
                return {"content": response}
            elif "Proceed to planning" in response:
                if "<enhanced_claim>" not in response:
                    original_claim = messages[-1]["content"].split("Please verify this claim: ")[1].split(" Using the table:")[0]
                    response = response.replace("<enhanced_claim>", f"<enhanced_claim>{original_claim}")
                return {"content": response}
            else:
                logging.warning("DataSufficiencyAgent response lacks clear decision")
                return {"content": f"{response}\n<explanation>DataSufficiencyAgent response lacks a clear decision on verifiability; defaulting to unverifiable.</explanation>\nnot enough info"}
        return {"content": response}

# Custom User Agent
class FactCheckingUserAgent(ConversableAgent):
    def receive(self, message, sender, request_reply=None, silent=False):
        message_content = message['content'] if isinstance(message, dict) else message
        logging.info(f"User_Agent received: {message_content} from {sender.name}")
        if sender.name in ["DataSufficiencyAgent", "Executor_Agent"]:  # Updated from Verifier_Agent
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
        if msg.get('name') in ['DataSufficiencyAgent', 'Executor_Agent'] and 'content' in msg:  # Updated from Verifier_Agent
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
            explanation = '\n'.join(line for line in content.split('\n') if not line.startswith("Confidence:"))
            try:
                confidence = next(float(line.split(":")[1].strip().split()[0]) for line in content.split('\n') if line.startswith("Confidence:"))
            except (StopIteration, ValueError):
                confidence = None
            logging.info(f"Extracting explanation from Executor_Agent: {content}")
            return {"explanation": explanation, "confidence": confidence}
    logging.warning("No valid Executor_Agent response found")
    return {"explanation": "No explanation provided", "confidence": None}

# Extract data sufficiency explanation (formerly verifier explanation)
def extract_data_sufficiency_explanation(chat_result):  # Updated from extract_verifier_explanation
    for msg in chat_result.chat_history:
        if msg.get('name') == 'DataSufficiencyAgent' and 'content' in msg:  # Updated from Verifier_Agent
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
        print("Returning DataSufficiencyAgent (initial message)")  # Updated from Verifier_Agent
        return data_sufficiency_agent  # Updated from verifier_agent

    last_message = messages[-1]
    print(f"last_speaker.name: {last_speaker.name}, last_message: {last_message}")

    # Default transitions
    if last_speaker.name == "User_Agent":
        print("Returning DataSufficiencyAgent")  # Updated from Verifier_Agent
        return data_sufficiency_agent  # Updated from verifier_agent
    elif last_speaker.name == "DataSufficiencyAgent":  # Updated from Verifier_Agent
        if "not enough info" in last_message["content"].lower():
            print("DataSufficiencyAgent determined claim unverifiable, returning User_Agent")  # Updated from Verifier
            return user_agent
        elif "Proceed to planning" in last_message["content"]:
            print("DataSufficiencyAgent determined claim verifiable, returning Planner_Agent")  # Updated from Verifier
            return planner_agent
    elif last_speaker.name == "Planner_Agent":
        print("Returning Executor_Agent")
        return executor_agent
    elif last_speaker.name == "Executor_Agent":
        print("Returning User_Agent")
        return user_agent

    print("Falling back to auto")
    return "auto"


def arg_parse():
    parser = argparse.ArgumentParser()
    parser.add_argument('--model', default='')
    parser.add_argument('--parameters', default='')
    parser.add_argument('--number_of_claims', default=100)
    parser.add_argument('--dataset_name', default='scitab')
    parser.add_argument('--data_split', default='testmini')
    parser.add_argument('--only_allow_unique_tables', type=str, default="False")
    parser.add_argument('--data_retrieval_mode', type=str, default='oracle', choices=["oracle", "bm25", "contriever-msmarco", "text-embedding-3-large"])
    parser.add_argument('--only_error_ids', type=str, default="False")
    parser.add_argument('--top_n', type=str, default=3)
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

    data_sufficiency_llm_config = {  # Updated from verifier_llm_config
        "timeout": 2000,
        "max_retries": 3,
        "config_list": autogen.config_list_from_json(
            "OAI_CONFIG_LIST",
            filter_dict={"model": [args.model]},
        ),
        "temperature": 0
    }
    print("Initialized config")

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

    data_sufficiency_agent = EnhancedDataSufficiencyAgent(  # Updated from verifier_agent
        name="DataSufficiencyAgent",  # Updated from Verifier_Agent
        system_message=data_sufficiency_agent_system_message,  # Updated from verifier_agent_system_message
        llm_config=data_sufficiency_llm_config,  # Updated from verifier_llm_config
        human_input_mode="NEVER",
        description=data_sufficiency_agent_description  # Updated from verifier_agent_description
    )
    print("Initialized all solo agents")

    allowed_transitions = {
        user_agent: [data_sufficiency_agent],  # Updated from verifier_agent
        data_sufficiency_agent: [planner_agent, user_agent],  # Updated from verifier_agent
        planner_agent: [executor_agent],
        executor_agent: [user_agent]
    }

    constrained_graph_chat = GroupChat(
        agents=[user_agent, planner_agent, executor_agent, data_sufficiency_agent],  # Updated from verifier_agent
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
    print("Initialized group chat agent")

    tables_to_read = read_findver(threshold=int(args.number_of_claims), data_retrieval_mode=args.data_retrieval_mode, data_split=args.data_split, top_n=args.top_n)
    print(f"len of tables_to_read: {len(tables_to_read)}")
    model_predictions = []
    BATCH_SIZE = 10
    # unique_ids_already_read = []
    # try:
    #     intermediate_file_path = f'prediction_v14_{args.dataset_name}_{args.data_retrieval_mode}_top_{args.top_n}_{str(len(tables_to_read))}_claims_{args.model}_intermediate.json'
    #     existing_data = json.load(open(intermediate_file_path, 'r'))
    #     unique_ids_already_read = [s['unique_id'] for s in existing_data]
    # except:
    #     unique_ids_already_read = []
    # print(f"unique_ids_already_read: {unique_ids_already_read}")
    # print(f"unique_ids_already_read length: {len(unique_ids_already_read)}")
    for batch_start in range(0, len(tables_to_read), BATCH_SIZE):
        batch_end = min(batch_start + BATCH_SIZE, len(tables_to_read))
        batch_tables = tables_to_read[batch_start:batch_end]

        for index, table_read in enumerate(batch_tables):
            overall_index = batch_start + index
            # unique_id, table_id, row_headers, col_headers, table_data, table_caption, claim, label = table_read
            unique_id, context, table_caption, claim, label = table_read
            # if unique_id in unique_ids_already_read:
            #     continue
            # col_headers = process_headers(col_headers)
            # sample_data = pd.DataFrame(table_data, columns=col_headers)
            # sample_data = table_to_html(unique_id, col_headers, table_data)

            message = f"""Please verify this claim: {claim} Using the context: {context} .
            The final response should be one of: 'support', 'refute', or 'not enough info'. Example: 'support' """

            max_attempts = 3
            for attempt in range(max_attempts):
                try:
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
                        data_sufficiency_result = extract_data_sufficiency_explanation(chat_result)  # Updated from verifier_result
                        cost = chat_result.cost
                        model_prediction = {
                            'unique_id': unique_id,
                            'claim': claim,
                            'context': context,
                            'table_caption': table_caption,
                            'gold_label': label,
                            'predicted_label': final_verdict,
                            'predicted_planner_explanation': planner_result["explanation"],
                            'predicted_planner_confidence': planner_result["confidence"],
                            'predicted_executor_explanation': executor_result["explanation"],
                            'predicted_executor_confidence': executor_result["confidence"],
                            'predicted_data_sufficiency_explanation': data_sufficiency_result["explanation"],  # Updated from predicted_verifier_explanation
                        }
                        model_predictions.append(model_prediction)
                        print(f"model prediction: {final_verdict} for index: {overall_index + 1}")
                        break

                except Exception as e:
                    logging.error(f"Attempt {attempt + 1} failed: {str(e)}")
                    if attempt < max_attempts - 1:
                        print(f"Attempt {attempt + 1} failed: {str(e)}. Retrying...")
                        time.sleep(30)
                    else:
                        print(f"Failed after {max_attempts} attempts for claim {overall_index + 1}")
                        model_prediction = {
                            'unique_id': unique_id,
                            'claim': claim,
                            'gold_label': label,
                            'context': context,
                            'table_caption': table_caption,
                            'predicted_label': "not enough info",
                            'predicted_planner_explanation': f"Error: {str(e)}",
                            'predicted_planner_confidence': None,
                            'predicted_executor_explanation': f"Error: {str(e)}",
                            'predicted_executor_confidence': None,
                            'predicted_data_sufficiency_explanation': f"Error: {str(e)}",  # Updated from predicted_verifier_explanation
                            'cost': 0
                        }
                        model_predictions.append(model_prediction)
        print("saving in output file intermediate ;;;;")
        if args.data_retrieval_mode == 'oracle':
            output_file_name = f'prediction_v14_{args.dataset_name}_{args.data_retrieval_mode}_{str(len(tables_to_read))}_claims_{args.model}_intermediate_v4_prompt.json'
        else:
            output_file_name = f'prediction_v14_{args.dataset_name}_{args.data_retrieval_mode}_top_{args.top_n}_{str(len(tables_to_read))}_claims_{args.model}_intermediate_v4_prompt.json'
        with open(output_file_name, 'w') as file_o:

        # with open(output_file_name, 'w') as file_o:
            # most likely don't need the dataframe serializable anymore, since the table is in HTML format.
            json.dump(model_predictions, file_o, default=dataframe_to_json_serializable, indent=4)
            print(f"saved in output file intermediate: {output_file_name}")

    print("saving in output file final  ;;;;")
    if args.data_retrieval_mode == 'oracle':
        output_file_name = f'prediction_v14_{args.dataset_name}_{args.data_retrieval_mode}_{str(len(tables_to_read))}_claims_{args.model}_v4_prompt.json'
    else:
        output_file_name = f'prediction_v14_{args.dataset_name}_{args.data_retrieval_mode}_top_{args.top_n}_{str(len(tables_to_read))}_claims_{args.model}_v4_prompt.json'

    with open(output_file_name, 'w') as file_o:
        json.dump(model_predictions, file_o, default=dataframe_to_json_serializable, indent=4)
        print(f"saved in output file final: {output_file_name}")
