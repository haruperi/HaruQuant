##############################################################################################
##                            DATA EXTRACTION FILE                                          ##
##############################################################################################
import json
import os


#----------------------------------------------------------------------------------------------#


def get_project_settings(import_filepath):
    """
    Reads credentials from a specified JSON file.

    Args:
        import_filepath (str): The file path to the settings.json file.

    Returns:
        dict: The project credentials as a dictionary.

    Raises:
        ImportError: If the file does not exist at the specified path.
    """
    # Test the filepath to make sure it exists
    if os.path.exists(import_filepath):
        # If yes, import the file
        f = open(import_filepath, "r")
        # Read the information
        settings = json.load(f)
        # Close the file
        f.close()
        # Return the project settings
        return settings
    # Notify user if settings.json doesn't exist
    else:
        raise ImportError("settings.json does not exist at provided location")


#----------------------------------------------------------------------------------------------#
