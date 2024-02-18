import sys
import json
import csv
import os
import argparse
import logging


def setup_logging(config):
    log_path = os.path.join(config['logPath'], config['logFileName'])
    logging.basicConfig(filename=log_path, level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')


def read_config(config_path):
    config = {}
    try:
        with open(config_path) as file:
            for line in file:
                if line.startswith('#') or not line.strip():
                    continue  # Skip comments and empty lines
                key, value = line.strip().split('=', 1)
                config[key.strip()] = value.strip()
    except IOError as e:
        logging.error(f"Error reading config file: {e}")
        sys.exit(1)
    return config


def read_metadata(metadata_path):
    try:
        metadata = []
        with open(metadata_path, newline='') as csvfile:
            reader = csv.reader(csvfile)
            for row in reader:
                position, field_name, field_type, length = row[:4]
                metadata.append((int(position), field_name, field_type, int(length)))
    except IOError as e:
        logging.error(f"Error reading metadata file: {e}")
        sys.exit(1)
    return metadata


def format_number(value, length):
    if value == "" or value is None:
        return ' ' * length
    try:
        float_value = float(value)
        integer_part, decimal_part = str(float_value).split('.')
        formatted_number = f"{int(integer_part):,}.{decimal_part}"
        if len(formatted_number) > length:
            raise ValueError(f"Formatted number '{formatted_number}' exceeds the specified length of {length}.")
        return formatted_number.ljust(length)
    except ValueError as e:
        raise ValueError(f"Value is not a number: {value}")


def format_field(value, field_type, length):
    if field_type == 'Number':
        return format_number(value, length)
    else:  # Assume field_type is 'string'
        value_str = str(value)
        return value_str[:length].ljust(length)


def process_json(json_data, metadata):
    lines = []
    
    if not isinstance(json_data, list):
        json_data = [json_data]

    for item in json_data:
        if not isinstance(item, dict):
            logging.warning(f"Skipping item because it's not a dictionary: {item}")
            continue
        
        formatted_fields = []
        for position, field_name, field_type, length in sorted(metadata, key=lambda x: x[0]):
            value = item.get(field_name, "") if isinstance(item, dict) else ""
            try:
                formatted_field = format_field(value, field_type, length)
            except ValueError as e:
                logging.error(f"Error formatting field: {e}")
                formatted_field = " " * length
            formatted_fields.append(formatted_field)
        line = ''.join(formatted_fields)
        lines.append(line)
    return lines


def main(config_path):
    config = read_config(config_path)
    setup_logging(config)
    metadata_path = os.path.join(config['sourcePath'], config['sourceSheet'])
    json_path = os.path.join(config['sourcePath'], config['sourceName'])

    metadata = read_metadata(metadata_path)
    try:
        with open(json_path) as json_file:
            json_data = json.load(json_file)
    except (IOError, json.JSONDecodeError) as e:
        logging.error(f"Error reading JSON file: {e}")
        sys.exit(1)

    all_iff_lines = process_json(json_data, metadata)

    source_file_name = os.path.basename(json_path)
    
    data_row_lengths = [len(line) for line in all_iff_lines]
    max_data_row_length = max(data_row_lengths) if data_row_lengths else 0
    max_row_length = max(max_data_row_length, len(source_file_name)+6)

    header_line = f"{max_row_length:06}{source_file_name}".ljust(max_row_length, ' ')

    result_path = config['resultPath4IFF']
    result_filename = config.get('extractFile4IFF', 'output') + '.iff'
    result_backup_path = config.get('resultBackupPath4CSV', '')

    os.makedirs(result_path, exist_ok=True)

    iff_filename = os.path.join(result_path, result_filename)
    with open(iff_filename, 'w') as iff_file:
        iff_file.write(header_line)
        for line in all_iff_lines:
            iff_file.write(line.ljust(max_row_length, ' '))

    logging.info(f"Generated IFF file: {iff_filename}")

    if result_backup_path:
        os.makedirs(result_backup_path, exist_ok=True)
        backup_filename = os.path.join(result_backup_path, result_filename)
        with open(backup_filename, 'w') as backup_file:
            backup_file.write(header_line)
            backup_file.writelines(all_iff_lines)

        logging.info(f"Backed up IFF file to: {backup_filename}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Process the configuration file for IFF generation.')
    parser.add_argument('config_file', help='Path to the configuration file')

    args = parser.parse_args()

    if not os.path.exists(args.config_file):
        logging.error(f"Config file {args.config_file} does not exist.")
        sys.exit(1)

    try:
        main(args.config_file)
    except Exception as e:
        logging.exception("An error occurred while running the script.")
        sys.exit(1)