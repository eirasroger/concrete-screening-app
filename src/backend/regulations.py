import os

# NOTE: We navigate from the script location to the data folder
def list_regulations():
    # Get the directory of the current script (regulation_utils.py)
    script_dir = os.path.dirname(os.path.abspath(__file__))
    # Go up two levels (from backend -> src -> interactive_interface) and then into data/regulations
    regulations_folder = os.path.join(script_dir, '..', '..', 'data', 'regulations')
    
    try:
        files = os.listdir(regulations_folder)
        options = [os.path.splitext(f)[0] for f in files if f.endswith((".json", ".yaml"))]
        return sorted(options)
    except FileNotFoundError:
        return ["ERROR: 'data/regulations' not found"]
