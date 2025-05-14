import csv
import os
import re


def process_utf16_spaced_csv(input_file):
    """
    Process a UTF-16 encoded CSV with spaces between characters and extract
    Borough, Ward, Code, and Income values

    Args:
        input_file (str): Path to the input CSV file

    Returns:
        dict: Dictionary mapping (borough, ward, code) tuples to income values
    """
    # Read the file with UTF-16 encoding
    try:
        with open(input_file, 'r', encoding='utf-16') as f:
            lines = f.readlines()
        print(f"Successfully read file {input_file} with utf-16 encoding. Found {len(lines)} lines.")
    except UnicodeDecodeError:
        # Try alternative UTF-16 variants if standard fails
        try:
            with open(input_file, 'r', encoding='utf-16-le') as f:
                lines = f.readlines()
            print(f"Successfully read file {input_file} with utf-16-le encoding. Found {len(lines)} lines.")
        except UnicodeDecodeError:
            with open(input_file, 'r', encoding='utf-16-be') as f:
                lines = f.readlines()
            print(f"Successfully read file {input_file} with utf-16-be encoding. Found {len(lines)} lines.")

    # Function to remove spaces between characters
    def remove_char_spaces(text):
        # First remove spaces between single characters
        processed = re.sub(r'(\w) (\w)', r'\1\2', text)
        # Keep applying until no more changes (for longer sequences)
        while processed != text:
            text = processed
            processed = re.sub(r'(\w) (\w)', r'\1\2', text)
        return processed

    # Process all lines to remove spaces between characters
    processed_lines = [remove_char_spaces(line) for line in lines]

    # Find the header row (contains "Borough" and "Ward name" or similar)
    header_row_index = -1
    for i, line in enumerate(processed_lines):
        if 'Borough' in line and ('Wardname' in line or 'Ward name' in line):
            header_row_index = i
            break

    if header_row_index == -1:
        # Try using the second line as header, which often contains the headers
        header_row_index = 1
        print(f"Using line {header_row_index + 1} as header: {processed_lines[header_row_index][:100]}...")

    # Split the header by tabs
    headers = processed_lines[header_row_index].strip().split('\t')

    # Find Borough and Ward name columns
    borough_idx = -1
    ward_idx = -1

    for idx, header in enumerate(headers):
        if 'Borough' in header:
            borough_idx = idx
        if 'Ward' in header:
            ward_idx = idx

    if borough_idx == -1 or ward_idx == -1:
        # Try manual indices (often Borough is at index 0 and Ward is at index 1)
        print("Trying manual indices for Borough and Ward")
        borough_idx = 0
        ward_idx = 1

    # Extract the E-codes (these are the ward codes)
    codes = []
    for idx, header in enumerate(headers):
        if 'E05' in header:
            codes.append((idx, header.strip()))

    if not codes:
        # Try using the pattern matching approach
        print("No E-codes found in headers. Trying pattern matching.")
        for idx, header in enumerate(headers):
            if re.search(r'E0\d+', header):
                codes.append((idx, header.strip()))

    if not codes:
        # As a last resort, assume all columns beyond Borough and Ward are codes
        print("Still no E-codes found. Using all columns beyond Borough and Ward as codes.")
        start_idx = max(borough_idx, ward_idx) + 1
        for idx in range(start_idx, len(headers)):
            if headers[idx].strip():
                codes.append((idx, f"Code_{idx}"))

    print(f"Found {len(codes)} codes in the header")

    # Initialize the output dictionary: (borough, ward, code) -> income
    income_data = {}

    # Process each data row (starting from the row after the header)
    processed_rows = 0
    for i in range(header_row_index + 1, len(processed_lines)):
        line = processed_lines[i].strip()
        if not line:
            continue

        # Split by tabs
        columns = line.split('\t')

        # Ensure we have enough columns
        if len(columns) <= max(borough_idx, ward_idx):
            continue

        borough = columns[borough_idx].strip() if borough_idx < len(columns) else ""
        ward = columns[ward_idx].strip() if ward_idx < len(columns) else ""

        if not borough or not ward:
            continue

        # For each ward, find which code column has a value
        for code_idx, code in codes:
            if code_idx < len(columns):
                income = columns[code_idx].strip()
                if income and income != "":
                    # Remove commas from values (e.g., "38,870" -> "38870")
                    income = income.replace(',', '')
                    # Store in dictionary
                    income_data[(borough, ward, code)] = income
                    processed_rows += 1
                    break  # Only use the first code with a value

    print(f"Processed {processed_rows} data points from {input_file}")
    return income_data


def combine_income_data(mean_file, median_file, output_file):
    """
    Process both mean and median income files and combine into a single CSV

    Args:
        mean_file (str): Path to the mean income CSV file
        median_file (str): Path to the median income CSV file
        output_file (str): Path to save the combined output CSV file
    """
    # Make sure the output directory exists
    output_dir = os.path.dirname(output_file)
    if output_dir and not os.path.exists(output_dir):
        os.makedirs(output_dir)

    # Process both files
    print("Processing mean income file...")
    mean_data = process_utf16_spaced_csv(mean_file)

    print("\nProcessing median income file...")
    median_data = process_utf16_spaced_csv(median_file)

    # Combine the data
    combined_data = []

    # Add header
    combined_data.append(['Borough', 'Ward', 'Code', 'Mean_Income', 'Median_Income'])

    # Get all unique (borough, ward, code) combinations
    all_keys = set(mean_data.keys()) | set(median_data.keys())

    # Sort by borough and ward for better readability
    sorted_keys = sorted(all_keys, key=lambda x: (x[0], x[1]))

    # Add data rows
    for key in sorted_keys:
        borough, ward, code = key
        mean = mean_data.get(key, "")
        median = median_data.get(key, "")
        combined_data.append([borough, ward, code, mean, median])

    # Write the output CSV
    with open(output_file, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerows(combined_data)

    print(f"\nCombination completed! Created {len(combined_data) - 1} data rows.")
    print(f"Output saved to {output_file}")


if __name__ == "__main__":
    mean_file = r"C:\Users\bilgi\Downloads\Ward map.csv"
    median_file = r"C:\Users\bilgi\Downloads\Ward map (1).csv"
    output_file = "../delete/borough_ward_income.csv"

    combine_income_data(mean_file, median_file, output_file)