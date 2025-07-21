import json
import pandas as pd
import os


def read_selected_table(list_of_ids, threshold=-1, only_allow_two_labels=False, only_allow_unique_tables=False):
    data = json.load(open('sci_tab_dataset.json', 'r'))
    table_info = []
    table_ids_already_selected = []
    for row in data:
        if not list_of_ids or row['id'] in list_of_ids:
            label = row['label']
            if only_allow_two_labels and label == 'not enough info':
                continue
            col_headers = row['table_column_names']
            table_id = row['table_id']
            unique_id = row['id']
            table_caption = row['table_caption']
            claim = row['claim']
            if only_allow_unique_tables and table_id in table_ids_already_selected:
                continue
                # print(f"col_headers: {col_headers}")
            row_headers = []
            for row_d in row['table_content_values']:
                row_headers.append(row_d[0])
            # print(f"row_headers: {row_headers}")
            table_info.append((unique_id, table_id, row_headers, col_headers, row['table_content_values'],
                               table_caption, claim, label))
            table_ids_already_selected.append(table_id)
            if threshold != -1 and len(table_info) == threshold:
                break
    return table_info


def read_semtabfact(threshold=-1, dataset_name='semtabfact_test'):
    data = json.load(open(dataset_name + '.json', 'r'))
    table_info = []
    for row in data:
        unique_id = row['unique_id']
        table_caption = row['table_caption']
        claim = row['claim']
        label = row['label']
        table_data = row['table']
        table_info.append((unique_id, table_data,  table_caption, claim, label))
        if threshold != -1 and len(table_info) == threshold:
            break
    return table_info


def read_mining(list_of_ids, threshold=-1, dataset_name='mining_data'):
    data = json.load(open(dataset_name + os.sep + 'mining.json', 'r'))
    table_info = []
    for row in data:
        unique_id = row['unique_id']

        if list_of_ids:
            if unique_id not in list_of_ids:
                continue
        table_caption = row['table_caption']
        claim = row['claim']
        label = row['label']
        table_data = row['table']
        table_info.append((unique_id, table_data,  table_caption, claim, label))
        if threshold != -1 and len(table_info) == threshold:
            break
    return table_info


def get_context(reports_dir, report_id, retrieve_data):
    report_path = os.path.join(reports_dir, report_id)
    report_data = json.load(open(report_path, 'r'))
    all_data = {}
    context_data = report_data['context']
    for c in context_data:
        all_data[c['id']] = (c['context'], c['type'])

    retrieval_evidence = []
    for i, retrieved_example in enumerate(retrieve_data):
        all_data_c = all_data[retrieved_example]
        retrieval_evidence.append(f"[{all_data_c[1]} id = {i}] {all_data_c[0]}")
        # retrieval_evidence = [f"[paragraph id = {i}] {paragraphs[i]['context']}" for i in retrieved_example['retrieved_context']]

    context = "\n".join(retrieval_evidence)
    return context


def read_findver(threshold=-1, reports_dir='findver_financial_reports', dataset_name='findver_data', data_split='testmini', data_retrieval_mode='oracle', top_n=3):
    print(f"threshold: {threshold}")
    test_data = json.load(open(dataset_name + os.sep + data_split + '.json', 'r'))
    retrieval_data_ob = {}
    if data_retrieval_mode != 'oracle':
        retrieval_data = json.load(open('findver_outputs' + os.sep + data_split + '_outputs' + os.sep + 'retriever_output' + os.sep + 'top_' + str(top_n) + os.sep + data_retrieval_mode + '.json', 'r'))
        retrieval_data_ob = {}
        for example in retrieval_data:
            retrieval_data_ob[example['example_id']] = example["retrieved_context"]
    table_info = []
    for row in test_data:
        unique_id = row['example_id']
        claim = row['statement']
        if data_split == 'testmini':
            label = row['entailment_label']
        else:
            label = None
        if data_retrieval_mode == 'oracle':
            # directly read from the testmini file
            retrieved_context = row["relevant_context"]
        else:
            retrieved_context = retrieval_data_ob[unique_id]
        report_id = row["report"]
        table_data = get_context(reports_dir, report_id, retrieved_context)
        table_info.append((unique_id, table_data,  '', claim, label))
        print(f"len(table_info) : {len(table_info)}")
        if threshold != -1 and len(table_info) == threshold:
            break
    # print(table_info)
    return table_info


def process_headers(headers):
    return [hdr.replace('[BOLD]', '').replace('<bold>', '').replace('</bold>', '').replace('[ITALIC]', '').replace('<italic>', '').replace('</italic>', '') for hdr in headers]


def dataframe_to_json_serializable(obj):
    if isinstance(obj, pd.DataFrame):
        return obj.to_dict(orient='records')
    return obj


def table_to_html(unique_id, table_column_names, table_content_values):
    """
    Convert a 2D table into an HTML table string.

    Parameters:
    - table_column_names (list): List of column header names.
    - table_content_values (list of lists): 2D list of table row values.

    Returns:
    - str: HTML string representing the table.
    """
    def format_cell_content(cell):
        """Helper function to format cell content based on special tags and Unicode."""
        if isinstance(cell, str):
            if cell == "[EMPTY]":
                return ""
            # Replace Unicode \u2217 with *
            # cell = cell.replace("\u2217", "*")
        return str(cell)

    # Start the HTML string without styling
    html = """
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <title>Table</title>
    </head>
    <body>
        <table>
    """

    # Add table headers
    html += "            <thead>\n                <tr>\n"
    for header in table_column_names:
        formatted_header = format_cell_content(header)
        html += f"                    <th>{formatted_header}</th>\n"
    html += "                </tr>\n            </thead>\n"

    # Add table body
    html += "            <tbody>\n"
    for row in table_content_values:
        # Check if the row is a section header (all cells are identical and not numeric)
        if len(set(row)) == 1 and not row[0].replace(".", "").isdigit():
            # Treat this row as a section header
            html += "                <tr>\n"
            html += f"                    <td colspan='{len(table_column_names)}'>{row[0]}</td>\n"
            html += "                </tr>\n"
        else:
            # Regular data row
            html += "                <tr>\n"
            for cell in row:
                formatted_cell = format_cell_content(cell)
                html += f"                    <td>{formatted_cell}</td>\n"
            html += "                </tr>\n"
    html += "            </tbody>\n"

    # Close the HTML string
    html += "        </table>\n    </body>\n</html>"
    # with open("html_tables/" + unique_id + ".html", "w", encoding="utf-8") as f:
    #     f.write(html)
    #
    # print(f"HTML table generated and saved to {unique_id}.html.")

    return html


# import pandas as pd
# import re
#
# import pandas as pd
# import re
# import os
# from typing import Optional
#
# CODE DOES NOT WORK VERY WELL IN GENERATNG TABLES

# def parse_findver_table(text: str, unique_id: str) -> Optional[pd.DataFrame]:
#     """
#     Parse a FinDVer table from markdown-like text into a pandas DataFrame and save as HTML.
#
#     Args:
#         text (str): Raw text containing the table.
#         unique_id (str): Unique identifier for the HTML output file.
#
#     Returns:
#         pd.DataFrame or None: Parsed table as a DataFrame, or None if parsing fails.
#     """
#     # Split text into lines
#     lines = text.strip().split('\n')
#
#     # Identify table lines (lines containing '|')
#     table_lines = [line.strip() for line in lines if '|' in line]
#     if not table_lines:
#         return None
#
#     # Helper function to split and clean cells
#     def clean_cells(cells: list) -> list:
#         cleaned = []
#         for cell in cells:
#             cell = cell.strip()
#             if not cell:
#                 continue
#             # Remove currency symbols
#             cell = re.sub(r'\$\s*', '', cell)
#             # Convert parentheses to negative numbers, e.g., "( 22 )" -> "-22"
#             cell = re.sub(r'\(\s*(\d+)\s*\)', r'-\1', cell)
#             # Replace em-dash with '0'
#             cell = cell.replace('\u2014', '0')
#             # Remove trailing colons
#             cell = cell.rstrip(':')
#             cleaned.append(cell)
#         return cleaned
#
#     # Detect header lines
#     header_lines = []
#     data_lines = []
#     header_candidates = []
#     max_columns = 0
#
#     # Analyze lines to identify headers vs. data
#     for i, line in enumerate(table_lines):
#         cells = [cell.strip() for cell in line.split('|') if cell.strip()]
#         num_cells = len(cells)
#         if num_cells > max_columns:
#             max_columns = num_cells
#
#         # Heuristic: Headers often have fewer numeric values and more text
#         numeric_count = sum(1 for cell in cells if re.match(r'^-?\d+(\.\d+)?$', cell.strip()))
#         if numeric_count == 0 or (i < 3 and num_cells >= 2):  # Likely a header if no numbers or early in table
#             header_candidates.append((i, cells))
#         else:
#             data_lines.append(cells)
#
#     # Select the header line with the most columns or last non-numeric line
#     if header_candidates:
#         # Prefer the last header candidate with the most columns
#         header_idx, header_cells = max(header_candidates, key=lambda x: len(x[1]))
#         header_lines = table_lines[:header_idx + 1]
#         headers = clean_cells(header_cells)
#     else:
#         # Fallback: Use the first line with the most columns
#         headers = clean_cells(table_lines[0].split('|'))
#         header_lines = table_lines[:1]
#         data_lines = [clean_cells(line.split('|')) for line in table_lines[1:]]
#
#     # Ensure headers are unique and non-empty
#     headers = headers[:max_columns]  # Limit to max columns seen
#     if not headers:
#         return None
#     # Handle duplicate or empty headers
#     header_counts = {}
#     new_headers = []
#     for i, h in enumerate(headers):
#         if not h:
#             h = f'Column_{i}'
#         if h in header_counts:
#             header_counts[h] += 1
#             h = f'{h}_{header_counts[h]}'
#         else:
#             header_counts[h] = 0
#         new_headers.append(h)
#     headers = new_headers
#
#     # Process data rows
#     data_rows = []
#     for cells in data_lines:
#         cleaned_cells = clean_cells(cells)
#         if not cleaned_cells:
#             continue
#         # Pad or truncate to match header length
#         cleaned_cells = cleaned_cells[:len(headers)] + [''] * (len(headers) - len(cleaned_cells)) if len(
#             cleaned_cells) < len(headers) else cleaned_cells[:len(headers)]
#         data_rows.append(cleaned_cells)
#
#     # Create DataFrame
#     if not data_rows:
#         return None
#     df = pd.DataFrame(data_rows, columns=headers)
#
#     # Clean DataFrame: Ensure all values are strings, replace empty with '0' for numeric columns
#     for col in headers[1:]:  # Skip first column (assumed to be labels)
#         df[col] = df[col].replace('', '0').astype(str)
#     df[headers[0]] = df[headers[0]].astype(str)
#
#     # Incorporate header context (e.g., "January 31") as prefix if needed
#     context = ' '.join(' '.join(clean_cells(line.split('|'))) for line in header_lines[:-1] if line)
#     if context:
#         df[headers[0]] = df[headers[0]].apply(lambda x: f"{context} {x}" if x else context)
#
#     # Save DataFrame as HTML
#     df_fv = pd.DataFrame(data_rows, columns=headers)
#     df_fv_html = df_fv.to_html(index=False, border=1, classes="table table-striped")
#     os.makedirs("html_tables", exist_ok=True)  # Create directory if it doesn't exist
#     html_path = f"html_tables/{unique_id}.html"
#     with open(html_path, "w", encoding="utf-8") as f:
#         f.write(df_fv_html)
#     print(f"HTML table generated and saved to {html_path}.")
#
#     return df


if __name__ == '__main__':
    pass
    # report_data = json.load(open('findver_financial_reports/A-2024-03-05_10-Q.json', 'r'))
    # all_data = {}
    # context_data = report_data['context']
    # for index, cd in enumerate(context_data):
    #     if cd['type'] == 'table':
    #         parse_findver_table(cd['context'], str(cd['id']))
    #         if index == 5:
    #             break
