import os
import subprocess
import threading

def execute(cmd_command):
  print(f'executing {cmd_command}')
  subprocess.call(cmd_command.split(), shell=False, stdout=subprocess.PIPE)

def main():
  files = os.listdir(os.curdir)
  files_to_convert = list(filter(lambda file: '.ipynb' in file, files))
  current_dir = os.path.dirname(os.path.realpath(__file__))
  threads = []
  for file in files_to_convert:
    cmd_command = "jupyter nbconvert --to python " + current_dir + '\\'+ file
    _t = threading.Thread(target=execute, args=(cmd_command,))
    _t.start()
    threads.append(_t)
  for thread in threads:
    thread.join()
  print('done')

main()