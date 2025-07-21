import json, sys
from sklearn.metrics import confusion_matrix
from sklearn.metrics import f1_score, accuracy_score
from read_json import *
import json, random
import statistics
import numpy as np
from collections import Counter
from collections import defaultdict
label_map = {
    'supports': 0,
    'support': 0,
    'refutes': 1,
    'refute': 1,
    'not enough info': 2,
    'not verifiable info': 2,
    'True': 0,
    'False': 1,
    'true': 0,
    'false': 1

}


def mining_additional_analysis(file_name):
    data = json.load(open(file_name, 'r'))
    mining_data = json.load(open('mining_data/mining.json', 'r'))
    ob = {}
    for sample in mining_data:
        ob[sample['unique_id']] = (sample['document_title'], sample['document_tab'], sample['type'])
    error_ids_no_exp = []
    error_ids_with_exp = []
    type_count = defaultdict(int)
    for sample in data:
        pr_l = label_map[sample['predicted_label']]
        gl_l = label_map[sample['gold_label']]
        exp = sample['predicted_planner_explanation']

        if gl_l in [0, 1] and pr_l == 2:
            u_id = sample['unique_id']
            if 'No explanation provided' in exp:
                error_ids_no_exp.append(u_id)
                type_count[ob[u_id][2]] += 1
            else:
                error_ids_with_exp.append(u_id)
    print(f"error_ids_no_exp : {error_ids_no_exp}")
    print(f"len(error_ids_no_exp): {len(error_ids_no_exp)}")
    print(f"type count for error_ids_no_exp: {type_count}")
    print(f"error_ids_with_exp : {error_ids_with_exp}")
    print(f"len(error_ids_with_exp): {len(error_ids_with_exp)}")
    print(f"all errors: ")
    print(error_ids_no_exp + error_ids_with_exp)

    return


def findver_additional_analysis(file_name, test_split):
    data = json.load(open(file_name, 'r'))
    test_data = json.load(open('findver_data' + os.sep + test_split + '.json', 'r'))
    retrieval_data = json.load(open('findver_outputs' + os.sep + test_split + '_outputs' + os.sep + 'retriever_output' + os.sep + 'top_' + str(10) + os.sep + 'text-embedding-3-large' + '.json', 'r'))
    retrieval_data_ob = {}
    for example in retrieval_data:
        retrieval_data_ob[example['example_id']] = example["retrieved_context"]
    retrieval_data_oracle = {}
    for row in test_data:
        unique_id = row['example_id']
        claim = row['statement']
        label = row['entailment_label']
        retrieval_data_oracle[unique_id] = row["relevant_context"]
    recalls_2 = []
    recalls_01 = []
    for elem in data:
        # elem = d[list(d.keys())[0]]
        # print(elem)
        unique_id = elem['unique_id']
        claim = elem['claim']
        gold_label = str(elem['gold_label']).strip()
        gold_label = label_map[gold_label]
        predicted_label = label_map[elem['predicted_label']]
        matched = set(retrieval_data_oracle[unique_id]).intersection(set(retrieval_data_ob[unique_id]))
        matched_portion = len(matched) / len(retrieval_data_oracle[unique_id])
        print(f"matched_portion: {round(matched_portion, 2)}")

        if predicted_label == 2:
            # print(f"oracle context: {retrieval_data_oracle[unique_id]}")
            # print(f"TE context: {retrieval_data_ob[unique_id]}")
            recalls_2.append(matched_portion)
        else:
            # print(f"oracle context: {retrieval_data_oracle[unique_id]}")
            # print(f"TE context: {retrieval_data_ob[unique_id]}")
            recalls_01.append(matched_portion)

    recall_2 = round(sum(recalls_2) / len(recalls_2) * 100, 2)
    print(f"recall_2: {len(recalls_2), recall_2}")
    recall_01 = round(sum(recalls_01) / len(recalls_01) * 100, 2)
    print(f"recall_01: {len(recalls_01), recall_01}")
    return


def findver_test_analysis(file_name):
    data = json.load(open(file_name, 'r'))
    print(len(data))
    predicted_labels_set = set([l['predicted_label'] for l in data])
    print(predicted_labels_set)
    predicted_labels_list = [l['predicted_label'] for l in data]
    print(Counter(predicted_labels_list))
    return


def compute_f1(gold_labels, predicted_labels):
    """
    Compute F1 score between gold (true) labels and predicted labels.

    Parameters:
    -----------
    gold_labels : list or array-like
        The true/gold standard labels
    predicted_labels : list or array-like
        The predicted labels from a model

    Returns:
    --------
    float
        The F1 score
    dict
        Dictionary containing precision, recall, and f1 score
    """

    sklearn_f1_macro = f1_score(gold_labels, predicted_labels, average='macro')
    sklearn_f1_micro = f1_score(gold_labels, predicted_labels, average='micro')
    return round(sklearn_f1_macro, 3), round(sklearn_f1_micro, 3)


def process_predicted_label(predicted_label: str, claim: str) -> int:
    """
    Process a predicted label string to determine if it supports, refutes, or has insufficient information.

    Args:
        predicted_label (str): The input string to process

    Returns:
        str: One of "supports", "refutes", or "not enough info"
    """
    # Convert to lowercase for case-insensitive matching
    text = predicted_label.lower()

    # List of keywords indicating refutation
    refute_keywords = ['refute', 'refuted', 'refutes', 'refuting', 'false', 'incorrect', 'wrong']

    # List of keywords indicating support
    support_keywords = ['support', 'supports', 'supporting', 'supported', 'true', 'correct', 'right']

    not_verifiable_keywords = ['not verifiable']

    # Check for refutation keywords
    for keyword in refute_keywords:
        if keyword in text:
            return 1

    # Check for support keywords
    for keyword in support_keywords:
        if keyword in text:
            return 0
    for keyword in not_verifiable_keywords:
        if keyword in text:
            return 2

    print(f"predicted_label: {predicted_label}, claim: {claim}")
    print("...........")
    # If no keywords found, return not enough info
    return 2


def analyze_result(file_name, make_random_guess=False):
    data = json.load(open(file_name, 'r'))
    # for d in data:
    gold_labels_3_class = []
    predicted_labels_3_class = []
    incorrect_predictions = []
    g_s_p_ns = []  # gold support, predicted not support (i.e. refute or non verifiable info)
    unique_ids = [elem['unique_id'] for elem in data]
    # print(unique_ids)
    s_vs_nei = []
    error_all = []
    case_1_ids = []
    case_2_ids = []
    count_case_2 = []
    for elem in data:
        # elem = d[list(d.keys())[0]]
        # print(elem)
        unique_id = elem['unique_id']
        claim = elem['claim']
        gold_label = str(elem['gold_label']).strip()
        gold_label = label_map[gold_label]

        predicted_label = label_map[elem['predicted_label']]

        # predicted_label = process_predicted_label(elem['predicted_label'], claim)

        predicted_planner_explanation = elem['predicted_planner_explanation']
        # predicted_executor_explanation = elem['predicted_executor_explanation']

        # conf_matrix = confusion_matrix(gold_labels, predicted_labels)
        # if 'Error code: 402' in predicted_planner_explanation:
        #     continue
        # if predicted_label == 2:
        #     continue

        gold_labels_3_class.append(gold_label)
        if predicted_label == 2 and make_random_guess:
            predicted_label = random.randint(0, 1)
            count_case_2.append(unique_id)
        predicted_labels_3_class.append(predicted_label)
        # if gold_label in [0, 1]:
        #     gold_labels_2_class.append(gold_label)
        #     predicted_labels_2_class.append(predicted_label)
        # if gold_label != predicted_label:
        #     print(f"unique_id: {unique_id}", gold_label, predicted_label)
        #     # print(f"claim: {claim}")
        #     # print(f"predicted_planner_explanation: {predicted_planner_explanation}")
        #     # print(f"predicted_executor_explanation: {predicted_executor_explanation}")
        #     # print()
        #     incorrect_predictions.append(unique_id)
        # if gold_label == predicted_label:
        #     print(f"correct: {unique_id}")
        # if (gold_label == 0 and predicted_label == 2) or (gold_label == 2 and predicted_label == 0):
        #     s_vs_nei.append(elem)
        if gold_label != predicted_label:
            error_all.append(elem)
    print(len(gold_labels_3_class))

    conf_matrix_3_class = confusion_matrix(gold_labels_3_class, predicted_labels_3_class)
    f1_scores = compute_f1(gold_labels_3_class, predicted_labels_3_class)
    accuracy = accuracy_score(gold_labels_3_class, predicted_labels_3_class)
    print(f"f1_score_macro: {f1_scores[0]}, f1_score_micro: {f1_scores[1]}, accuracy: {accuracy}")
    print(f"confusion matrix")
    print(conf_matrix_3_class)
    total_samples = np.sum(conf_matrix_3_class)  # Total number of rows (samples)
    normalized_conf_matrix = np.round((conf_matrix_3_class / total_samples) * 100, 1)
    # print(f"normalized_conf_matrix ")
    # print(normalized_conf_matrix)

    # print(f"count_case_2: {len(count_case_2)}")
    # print(f"case 1: {len(case_1_ids), case_1_ids}")
    # print(f"case 2: {len(case_2_ids), case_2_ids}")

    # with open("error_v10.json", 'w') as file_o:
    #     json.dump(error_all, file_o, default=dataframe_to_json_serializable, indent=4)

    # print(f"incorrect predictions: {incorrect_predictions}")


if __name__ == '__main__':
    #
    print("Scitab dataset")
    result_file_name = 'prediction_v14_scitab_1224_claims_deepseek-chat_updated_2.json'
    analyze_result(result_file_name)
    # result_file_name = 'prediction_v14_scitab_cells_used_1224_claims_deepseek-chat.json'
    # analyze_result(result_file_name)

    # print("SemTabFact dataset")
    # result_file_name = 'prediction_v14_semtabfact_test_653_claims_deepseek-chat.json'
    # analyze_result(result_file_name)
    # print("SemTabFact dataset")
    #
    # result_file_name = 'prediction_v14_semtabfact_test_cells_used_653_claims_deepseek-chat_updated.json'
    # analyze_result(result_file_name)
    #
    # print("Findver Testmini")
    # result_file_name = 'prediction_v14_findver_text-embedding-3-large_top_10_700_claims_deepseek-chat.json'
    # findver_test_analysis(result_file_name)
    #
    # # analyze_result(result_file_name, make_random_guess=True)
    #
    # print("Findver Test")
    # result_file_name = 'prediction_v14_findver_text-embedding-3-large_top_10_1700_claims_deepseek-chat_merged_3.json'
    # # analyze_result(result_file_name, make_random_guess=True)
    # findver_test_analysis(result_file_name)
    # findver_additional_analysis(result_file_name, test_split='test')

    # print("Mining dataset")
    # result_file_name = 'prediction_v14_mining_data_2029_claims_deepseek-chat.json'
    # analyze_result(result_file_name)
    # mining_additional_analysis(result_file_name)
    # print("Mining dataset")
    # result_file_name = 'prediction_v14_mining_data_2029_claims_deepseek-chat_updated_prompt_updated.json'
    # analyze_result(result_file_name)
    # # mining_additional_analysis(result_file_name)
    # result_file_name = 'prediction_v14_mining_data_2029_claims_deepseek-chat_updated_prompt_2_updated.json'
    # analyze_result(result_file_name)
    # # mining_additional_analysis(result_file_name)
    # result_file_name = 'prediction_v14_mining_data_2029_claims_deepseek-chat_updated_cells_used_updated.json'
    # analyze_result(result_file_name)
