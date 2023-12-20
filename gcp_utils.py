# standard imports
import os
import uuid
import json
import logging
import glob
import posixpath
import requests


# import 3rd party libraries
from google.cloud import storage  # used for GCS'

# function gets a list of files to process based on an input directory and a file extension
def get_files_to_process(file_pattern='*.txt'):
    """Gets a list of files to process based on an input directory and a file extension.

    Args:
        input_dir (str): Path to the directory where the files to process are located.
        file_pattern (str): File pattern of the files to process.

    Returns: files_to_process (list): List of files to process.
    """

    # get a list of files to process
    files_to_process = glob.glob(file_pattern)
    logging.debug(f'Found {len(files_to_process)} files to process.')
    return files_to_process

def parse_gs_url(gs_url):
    """
    Parse a gs:// URL into bucket and object path.

    :param gs_url: The gs:// URL to parse (e.g., gs://my-bucket/path/to/object)
    :return: A tuple containing the bucket name and object path
    """
    if gs_url.startswith("gs://"):
        parts = gs_url[5:].split("/", 1)
        if len(parts) == 2:
            bucket_name, object_path = parts
            return bucket_name, object_path

    raise ValueError("Invalid gs:// URL")
def load_text_file (filename):
    """Loads a text file from GCS or local file system.

    Args:
        filename (str): Path to the file to load.

    Returns: text (str): Text from the file.
    """

    # if using GCS, need to download the file from GCS first
    if config.USING_GCS:
        # download the file from GCS
        gcs_client = storage.Client()
        bucket_name , blob_path = parse_gs_url(filename)
        bucket = gcs_client.get_bucket(bucket_name)
        blob = bucket.blob(blob_path)
        text = blob.download_as_text()
    else:
        # load the file from the local file system
        with open(filename, 'r') as f:
            text = f.read()

    return text

def write_text_file (filename, text):
    """Writes a text file to GCS or local file system.

    Args:
        filename (str): Path to the file to write.
        text (str): Text to write to the file.

    Returns: None
    """

    # if using GCS, need to upload the file to GCS first
    if config.USING_GCS:
        # upload the file to GCS
        gcs_client = storage.Client()
        bucket_name, blob_path = parse_gs_url(filename)
        bucket = gcs_client.get_bucket(bucket_name)
        blob = bucket.blob(blob_path)

        # see if the file already exists
        if blob.exists():
            logging.warning(f'File {filename} already exists.  Overwriting.')
        blob.upload_from_string(text)
        logging.info(f'Uploaded file to GCS: {filename}')
        return True

    if os.path.exists(filename):
        logging.warning(f'File {filename} already exists.  Overwriting.')

    with open(filename, 'w') as f:
        f.write(text)

    logging.info(f'Wrote file: {filename}')


# put a file to gcs
def put_file_to_gcs(input_file_name, destination_dir):
    """Copies a file to GCS.

    Args:
        input_file_name (str): Path to the file to copy.
        destination_dir (str): Path to the directory where the file will be copied.

    Returns: None
    """

    destination_file = f'{destination_dir}/{os.path.basename(input_file_name)}'

    gcs_client = storage.Client()
    bucket_name, blob_path = parse_gs_url(destination_file)
    bucket = gcs_client.get_bucket(bucket_name)
    blob = bucket.blob(blob_path)

    # see if the file already exists
    if blob.exists():
        logging.warning(f'Directory {destination_dir} already exists.  Overwriting.')

    blob.upload_from_filename(input_file_name)
    logging.info(f'Uploaded file to GCS: {destination_dir}')
    return True


# get a file from gcs
def get_file_from_repo(input_file_name, destination_dir):
    """Copies a file from GCS.

    Args:
        input_file_name (str): Path to the file to copy.
        destination_dir (str): Path to the directory where the file will be copied.

    Returns: None
    """

    destination_file = f'{destination_dir}/{os.path.basename(input_file_name)}'

    gcs_client = storage.Client()
    bucket_name, blob_path = parse_gs_url(input_file_name)
    bucket = gcs_client.get_bucket(bucket_name)
    blob = bucket.blob(blob_path)

    # see if the local file already exists
    if os.path.exists(destination_file):
        logging.warning(f'File {destination_file} already exists.  Overwriting.')

    try:
        blob.download_to_filename(destination_file)
        logging.info(f'Downloaded file from GCS: {destination_file}')
        return destination_file
    except Exception as e:
        logging.error(f'File {destination_file} does not exist in GCS.')
        raise e



    return destination_file


def get_unique_identifier():
    """Gets a unique identifier.

    Returns: unique_identifier (str): A unique identifier.
    """

    # encapsulate the logic for getting a unique identifier in a function so it can be reused or changed to different
    # schemes if needed.
    unique_identifier = str(uuid.uuid4())
    return unique_identifier

def get_posix_path(pattern):

    directories = glob.glob(pattern)
    posix_directories = []

    for directory in directories:
        parts = os.path.normpath(directory).split(os.path.sep)
        posix_directory = posixpath.join(*parts)
        posix_directories.append(posix_directory)

    return posix_directories

def download_file_from_url(url, dest_filename):

    response = requests.get(url)

    # Ensure the request was successful
    if response.status_code == 200:
        # Open the file in write mode and write the contents of the response to it
        with open(dest_filename, 'wb') as f:
            f.write(response.content)

    return dest_filename
    # TODO: what happens if request fails?


def get_filename_from_url(url):
    return url.split('/')[-1]


def is_text_file(filename):
    try:
        with open(filename, 'tr') as f:
            f.read()
        return True
    except UnicodeDecodeError:
        return False


def delete_file(filename = None):
    if filename is None:
        return False
    if os.path.exists(filename):
        os.remove(filename)
        return True
    return False


def delete_files_in_dir(working_dir):
    for filename in os.listdir(working_dir):
        file_path = os.path.join(working_dir, filename)
        try:
            if os.path.isfile(file_path) or os.path.islink(file_path):
                os.remove(file_path)
        except Exception as e:
            logging.error('Failed to delete %s. Reason: %s' % (file_path, e))



if __name__ == '__main__':

    download_path = "./output"

    # test getting a list of files
    if False:
        try:
            input_dir = './input'
            file_extension = '.txt'
            files_to_process = get_files_to_process(input_dir, file_extension)
            print(files_to_process)
        except Exception as e:
            print(f"Error: {e}")

    # test getting a unique identifier
    if True:
        try:
            unique_identifier = get_unique_identifier()
            print(unique_identifier)
        except Exception as e:
            print(f"Error: {e}")

    # test getting a list of posix paths
    if False:
        try:
            posix_directories = get_posix_path(f'{download_path}/youtube/*')
            print(posix_directories)
        except Exception as e:
            print(f"Error: {e}")

    # test copying a file to GCS
    if False:
        try:
            input_file_name = './input/test_input.txt'
            destination_dir = 'gs://gpt-funhouse/corpus/temp/output'
            copy_file_to_repo(input_file_name, destination_dir)
        except Exception as e:
            print(f"Error: {e}")
