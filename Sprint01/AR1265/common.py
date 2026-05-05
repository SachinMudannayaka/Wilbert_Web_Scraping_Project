import pandas as pd
import json
from datetime import datetime
import os
import shutil
import hashlib


def hash_row(row):
    row_data = "".join(map(str, row))
    return hashlib.sha256(row_data.encode()).hexdigest()


def returnJsonPath(uniqueIdentity):
    """
    Returns the JSON file path based on the unique identity and current date, with incrementing numbers to avoid duplicates.

    Parameters:
        uniqueIdentity (str): Unique identifier.

    Returns:
        str: Full path to the JSON file.
    """
    # Get the current date in mmddyyyy format
    date_str = datetime.now().strftime("%m%d%Y")

    # Construct the folder and file path
    folder_path = os.path.join("out", f"{uniqueIdentity}_{date_str}")
    file_name = f"{uniqueIdentity}_{date_str}.json"
    full_path = os.path.join(folder_path, file_name)

    # Check if the folder exists, create it if not
    if not os.path.exists(folder_path):
        os.makedirs(folder_path)

    # Check if the file exists, if so increment the name
    counter = 1
    while os.path.exists(full_path):
        file_name = f"{uniqueIdentity}_{date_str}_{counter}.json"
        full_path = os.path.join(folder_path, file_name)
        counter += 1

    return full_path


def returnSourceFilePath(uniqueIdentity, extension):
    """
    Returns the source file path with the specified extension based on the unique identity and current date, with incrementing numbers to avoid duplicates.

    Parameters:
        uniqueIdentity (str): Unique identifier.
        extension (str): File extension (e.g., 'xlsx', 'csv').

    Returns:
        str: Full path to the source file.
    """
    # Validate the extension (add a dot if missing)
    if not extension.startswith("."):
        extension = f".{extension}"

    # Get the current date in mmddyyyy format
    date_str = datetime.now().strftime("%m%d%Y")

    # Construct the folder and file path
    folder_path = os.path.join("out", f"{uniqueIdentity}_{date_str}")
    file_name = f"{uniqueIdentity}_{date_str}{extension}"
    full_path = os.path.join(folder_path, file_name)

    # Check if the folder exists, create it if not
    if not os.path.exists(folder_path):
        os.makedirs(folder_path)

    # Check if the file exists, if so increment the name
    counter = 1
    while os.path.exists(full_path):
        file_name = f"{uniqueIdentity}_{date_str}_{counter}{extension}"
        full_path = os.path.join(folder_path, file_name)
        counter += 1

    return full_path


def save_output_to_json(UniqueIdentity, region, jurisdiction, category, title, errors, data, jsonPath, casKeyValue):
    """
    Saves the given information to a JSON file.

    Parameters:
        UniqueIdentity (str): Unique identifier.
        region (str): Region information.
        category (str): Category information.
        title (str): Title information.
        errors (list): List of errors.
        data (pd.DataFrame): DataFrame containing data.
        jsonPath (str): Path to save the JSON file.
    """
    try:
        # Create hash
        data["sha_hash"] = data.apply(hash_row, axis=1)
        # Replace null (NaN) values with empty strings
        data = data.fillna("")
        # Convert all values in the DataFrame to strings
        data = data.applymap(str)
        # Replace spaces with underscores in column names to json
        data.columns = [col.replace(" ", "_") for col in data.columns]
        # Create a list of dictionaries from the DataFrame
        data_list = data.to_dict(orient='records')

        # Prepare the output dictionary
        output = {
            "UniqueIdentity": UniqueIdentity,
            "region": region,
            "Jurisdiction": jurisdiction,
            "category": category,
            "title": title,
            "casKey": None if not casKeyValue else casKeyValue,
            "dateAndTime": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "errors": errors,
            "data": data_list
        }

        # Save the output dictionary to the JSON file
        with open(jsonPath, 'w', encoding='utf-8') as json_file:
            json.dump(output, json_file, indent=4, ensure_ascii=False)

        print(f"Data has been saved to {jsonPath}")
    except Exception as e:
        print(f"An error occurred while saving to JSON: {e}")


def clean_newlines_in_dataframe(dataframe):
    """
    Removes leading and trailing whitespace or newlines from all cells in a DataFrame.

    Parameters:
        dataframe (pd.DataFrame): The DataFrame to clean.

    Returns:
        pd.DataFrame: A cleaned DataFrame with stripped strings.
    """
    return dataframe.applymap(lambda x: x.strip() if isinstance(x, str) else x)


def deleteTodayFiles(uniqueIdentity):
    # Get today's date in the format MMDDYYYY
    date_str = datetime.now().strftime("%m%d%Y")

    # Construct the folder path
    folder_path = os.path.join("out", f"{uniqueIdentity}_{date_str}")

    # Check if the folder exists
    if os.path.exists(folder_path) and os.path.isdir(folder_path):
        # Loop through all the files and folders in the directory and delete them
        for filename in os.listdir(folder_path):
            file_path = os.path.join(folder_path, filename)

            try:
                # If it's a file, delete it
                if os.path.isfile(file_path):
                    os.remove(file_path)
                # If it's a directory, delete it and all its contents
                elif os.path.isdir(file_path):
                    shutil.rmtree(file_path)
            except Exception as e:
                print(f"Error deleting {file_path}: {e}")
