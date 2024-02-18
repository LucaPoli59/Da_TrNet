import os


PROJECT_NAME = "data_analytics2"
PROJECT_PATH = os.getcwd()
while os.path.basename(os.getcwd()) != PROJECT_NAME:
    os.chdir("..")
    PROJECT_PATH = os.getcwd()

os.popen(f"pip install -r {os.path.join(PROJECT_PATH, 'requirements.txt')}")
