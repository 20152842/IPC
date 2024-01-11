import argparse
import subprocess
import sys
import socket
import concurrent.futures
import os
import shlex
import select
from io import StringIO

TEST_TE = "hi"

HOSTFILE_CURRENTDIR="hostfile"
HOSTFILE_CURRENTDIR_PATH="/hostfile"
LOCALHOST = '127.0.0.1'


def makeParser():
  parser = argparse.ArgumentParser(description="Input options")

  parser.add_argument("--host")
  parser.add_argument("--hostfile")
  parser.add_argument("--out")
  parser.add_argument("--err")
  parser.add_argument("-i", action="store_true")

  args, command = parser.parse_known_args()

  combined = ' '.join(command)
  return args, combined

def get_node_info():
    container_details = []
    # 컨테이너 정보에서 호스트 노드의 컨테이너 이름과 포트 가져오기
    container_info = get_container_info()
    for container in container_info:
        container_name = container[0]

        # 컨테이너 이름을 이용하여 컨테이너의 IP 주소 가져오기
        ip_result = subprocess.run(["docker", "inspect", "-f", 
                                    "{{range.NetworkSettings.Networks}}{{.IPAddress}}{{end}}", container_name], capture_output=True, text=True)
        container_ip = LOCALHOST

        # 포트 가져오기
        container_port = container[-1]
        
        container_details.append((container_name.decode('utf-8').split('-')[1],
                                  container_ip, container_port.decode('utf-8').split(':')[-1].split('->')[0]))
    
    return container_details  

def get_container_info():
    # Docker Compose 명령어 실행하여 컨테이너 정보 가져오기
    result = subprocess.run(["docker-compose", "ps"], capture_output=True, text=False)
    output_lines = result.stdout.splitlines()
    container_info = [line.split() for line in output_lines[1:]]  # 컨테이너 정보 파싱
    return container_info
  
    
def error_AttrAndNone(args, attr):
  if not(hasattr(args, attr) and getattr(args, attr) != None):
    return False
  return True

def check_null_nodes(nodes):
    null_nodes = [node for node in nodes if node is None]
    if null_nodes:
      print(f"Error: No information found for node. "
            + "Check input nodes exactly")
      sys.exit(1)


def get_nodes_from_hostfile(all_nodes, hostfile_nodes):
    return [find_by_attr(all_nodes, node) for node in hostfile_nodes]
    
def find_by_attr(all_Nodes, attr):
    result = [item for item in all_Nodes if item[0] == attr]
    if result:
      return result[0]
    else:
      pass
    
def find_node_by_name(nodes, node_name):
    for node_tuple in nodes:
        if node_tuple[0] == node_name:
            return node_tuple
    return None  # 찾는 요소가 없을 경우 None 반환
    
    
def ssh_command(container_ip, container_port, command):
  ssh_cmd = subprocess.Popen(['ssh', container_ip, '-p', container_port, command], 
                            stdin=subprocess.PIPE,
                            stdout=subprocess.PIPE,
                            stderr=subprocess.PIPE)
  stdout, stderr = ssh_cmd.communicate()
  return stdout, stderr

def ssh_command_Redirection(container_ip, container_port, command, file_path):
  ssh_cmd = subprocess.Popen(['ssh', container_ip, '-p', container_port, command], 
                            stdin=read_pipe_input_to_file(file_path),
                            stdout=subprocess.PIPE,
                            stderr=subprocess.PIPE,
                            )
  stdout, stderr = ssh_cmd.communicate()
  return stdout, stderr
  
def local_command(command):
  cmd = subprocess.Popen(command.split(),
                         stdout=subprocess.PIPE)
  stdout, _ = cmd.communicate()
  return stdout

def local_to_ssh_command(container_ip, container_port, command):
  ssh_cmd = subprocess.Popen(['ssh', container_ip, '-p', container_port, command], 
                            stdin=subprocess.PIPE,
                            stdout=subprocess.PIPE,
                            stderr=subprocess.PIPE)
  stdout, stderr = ssh_cmd.communicate()
  return stdout, stderr


# 병렬로 SSH 연결 시도
def simple_CLSH(nodes, command):
  
  node_names = [node[0] for node in nodes]
  node_names_join = ', '.join(node_names)
  
  if not (args.host or args.hostfile or args.out or args.err or args.i):
    print("Enter ‘quit’ to leave this interactive mode")
    print("Working with nodes: " + node_names_join)
    while True:
      command = input("clsh local > ")
      if command == "quit":
        quit()
      # local_command_stdout = local_command(command)
      with concurrent.futures.ThreadPoolExecutor(max_workers=len(nodes)) as executor:
          results = {executor.submit(ssh_command, node[1], node[2], command): node for node in nodes}
          for future in concurrent.futures.as_completed(results):
              node = results[future]
              # try:
              output, error = future.result()
              # Option 3                  
              print(f"{node[0]}: {output.decode('utf-8')}")

  
  if not(args.i):
    with concurrent.futures.ThreadPoolExecutor(max_workers=len(nodes)) as executor:
        results = {executor.submit(ssh_command, node[1], node[2], command): node for node in nodes}
        for future in concurrent.futures.as_completed(results):
            node = results[future]
            # try:
            output, error = future.result()
            # Option 3                  
            option3(output, error, node[0])
            print(f"{node[0]}: {output.decode('utf-8')}")
        quit()
        
  if args.i:
    print("Enter ‘quit’ to leave this interactive mode")
    print("Working with nodes: " + node_names_join)
    print("If you want to communicate with a single container, please enter its name.")
    print("If you leave it blank, communication will be established with all containers.")
    node_input = input("Node Input : ")
    while True:
      if node_input is not None and find_by_attr(nodes, node_input):
        command = input("clsh > ")
        if command == "quit":
          quit()
        node_info = find_node_by_name(nodes, node_input)
        output, error = ssh_command(node_info[1], node_info[2], command)
        
        option3(output, error, node_info[0])
        print(f"{node_info[0]}: {output.decode('utf-8')}")
        
      elif len(node_input) != 0 and not(find_by_attr(nodes, node_input)):
        print("Input node just one exactly")
        node_input = input("Node Input : ")

      elif len(node_input) == 0:
        command = input("clsh > ")
        if command == "quit":
          quit()
        with concurrent.futures.ThreadPoolExecutor(max_workers=len(nodes)) as executor:
            results = {executor.submit(ssh_command, node[1], node[2], command): node for node in nodes}
            for future in concurrent.futures.as_completed(results):
                node = results[future]
                output, error = future.result()
                option3(output, error, node[0])
                print(f"{node[0]}: {output.decode('utf-8')}")
            
def shell_Redirection(nodes, command, file_path):
    with concurrent.futures.ThreadPoolExecutor(max_workers=len(nodes)) as executor:
        results = {executor.submit(ssh_command_Redirection, node[1], node[2], command, file_path): node for node in nodes}
        for future in concurrent.futures.as_completed(results):
            node = results[future]
            output,error = future.result()
            option3(output, error, node[0])
            print(f"{node[0]}: {output.decode('utf-8')}")
                
def option3(output, error, node):
  # out & err = True
  # out 인자에 주어진 파일 경로에 밑에 '노드이름.out'파일에 out 값 넣기
  # err 인자에 주어진 파일 경로에 밑에 '노드이름.err'파일에 err 값 넣기
  if args.out is not None:
    if not os.path.exists(args.out) :
      os.makedirs(args.out)
    output_file_path = args.out + node + ".out"
  else:
    output_file_path = None
    
  if args.err is not None:
    if not os.path.exists(args.err):
      os.makedirs(args.err)
    error_file_path = args.err + node + ".err"
  else:
    error_file_path = None
    
  output_len = len(output.decode())
  error_len = len(error.decode())
  
  if output_len != 0 and error_len != 0 and output_file_path is not None and error_file_path is not None:
      # 표준 출력과 표준 에러 모두 파일에 저장
      with open(output_file_path, 'w') as out_file, open(error_file_path, 'w') as err_file:
          out_file.write(output.decode())
          err_file.write(error.decode())
  elif output_len != 0 and error_len == 0 and output_file_path is not None:
      # 표준 출력만 파일에 저장
      with open(output_file_path, 'w') as out_file:
          out_file.write(output.decode())
  elif output_len == 0 and error_len != 0 and error_file_path is not None:
      # 표준 에러만 파일에 저장
      with open(error_file_path, 'w') as err_file:
          err_file.write(error.decode())



def get_nodes_from_CLSH_HOSTS(clsh_hosts):
  print("Note : use CLSH_HOSTS env")
  if clsh_hosts:
      nodes = clsh_hosts.split(':')
      return nodes
  else:
      return None

def get_hostfile_path(hostfile):
  print("Note : use hostfile " + hostfile + "(CLSH_HOSTFILE env)")
  if hostfile.startswith('/'):
      return hostfile  # 절대 경로
  else:
      return os.path.join(os.getcwd(), hostfile)  # 상대 경로
      
def read_hostfile(hostfile_path):
    with open(hostfile_path, 'r') as file:
        lines = file.readlines()
        nodes = [line.strip() for line in lines if line.strip()]
    return nodes


          
def basic_host():
  nodes = args.host.split(",")
  target_nodes = [find_by_attr(all_Nodes, node) for node in nodes]
  check_null_nodes(target_nodes)
  simple_CLSH(target_nodes, command)
  quit()

def basic_hostfile():
  hostfile_nodes = read_hostfile(args.hostfile)
  target_nodes = get_nodes_from_hostfile(all_Nodes, hostfile_nodes)
  check_null_nodes(target_nodes)
  simple_CLSH(target_nodes, command)  
  quit()

def basic_host_Redirection(file_path):
  nodes = args.host.split(",")
  target_nodes = [find_by_attr(all_Nodes, node) for node in nodes]
  check_null_nodes(target_nodes)
  shell_Redirection(target_nodes, command, file_path)
  quit()

def basic_hostfile_Redirection(file_path):
  hostfile_nodes = read_hostfile(args.hostfile)
  target_nodes = get_nodes_from_hostfile(all_Nodes, hostfile_nodes)
  check_null_nodes(target_nodes)
  shell_Redirection(target_nodes, command, file_path)  
  quit()


def save_pipe_input_to_file(file_path, pipe_input):
    # 파일에 입력 저장
    with open(file_path, 'w') as file:
        file.write(pipe_input)
  
def read_pipe_input_to_file(file_path):
    # 파일로부터 입력을 읽어옴
    return open(file_path, 'r')

        
def option1():
  if args.host == None and args.hostfile == None:
    CLSH_HOSTS = os.environ.get('CLSH_HOSTS')
    CLSH_HOSTFILE = os.environ.get('CLSH_HOSTFILE')
    if(CLSH_HOSTS != None):
      print("CLSH_HOSTS env exist.")
      # export CLSH_HOSTS=work01:work02:work03:work04
      nodes = get_nodes_from_CLSH_HOSTS(CLSH_HOSTS)
      target_nodes = [find_by_attr(all_Nodes, node) for node in nodes]
      
      check_null_nodes(target_nodes)
      simple_CLSH(target_nodes, command)
    
    elif(CLSH_HOSTFILE != None):
      print("CLSH_HOSTS env doesn't exist. Finding CLSH_HOSTFILE env...")
      path = get_hostfile_path(CLSH_HOSTFILE)
      nodes = read_hostfile(path)
      target_nodes = [find_by_attr(all_Nodes, node) for node in nodes]
      
      check_null_nodes(target_nodes)
      simple_CLSH(target_nodes, command)  
          
    elif not(os.path.isfile(HOSTFILE_CURRENTDIR_PATH)):
      print("CLSH_HOSTS and CLSH_HOSTFILE env don't exist. Finding hostfile...")
      hostfile_nodes = read_hostfile(HOSTFILE_CURRENTDIR)
      target_nodes = get_nodes_from_hostfile(all_Nodes, hostfile_nodes)
      
      check_null_nodes(target_nodes)
      simple_CLSH(target_nodes, command)            
    else:
      print("--hostfile 옵션이 제공되지 않았습니다")
      quit()
      
def option1_Redirection(file_path):
  if args.host == None and args.hostfile == None:
    CLSH_HOSTS = os.environ.get('CLSH_HOSTS')
    CLSH_HOSTFILE = os.environ.get('CLSH_HOSTFILE')
    if(CLSH_HOSTS != None):
      print("CLSH_HOSTS env exist.")
      # export CLSH_HOSTS=work01:work02:work03:work04
      nodes = get_nodes_from_CLSH_HOSTS(CLSH_HOSTS)
      target_nodes = [find_by_attr(all_Nodes, node) for node in nodes]
      
      check_null_nodes(target_nodes)
      shell_Redirection(target_nodes, command, file_path)
    
    elif(CLSH_HOSTFILE != None):
      print("CLSH_HOSTS env doesn't exist. Finding CLSH_HOSTFILE env...")
      path = get_hostfile_path(CLSH_HOSTFILE)
      nodes = read_hostfile(path)
      target_nodes = [find_by_attr(all_Nodes, node) for node in nodes]
      
      check_null_nodes(target_nodes)
      shell_Redirection(target_nodes, command, file_path)  
          
    elif not(os.path.isfile(HOSTFILE_CURRENTDIR_PATH)):
      print("CLSH_HOSTS and CLSH_HOSTFILE env don't exist. Finding hostfile...")
      hostfile_nodes = read_hostfile(HOSTFILE_CURRENTDIR)
      target_nodes = get_nodes_from_hostfile(all_Nodes, hostfile_nodes)
      
      check_null_nodes(target_nodes)
      shell_Redirection(target_nodes, command, file_path)            
    else:
      print("--hostfile 옵션이 제공되지 않았습니다")
      quit()
      
      
def option2():
  # print("Finding PIPE...")
  # 입력이 있는지 확인하기 위해 select 사용
  pipe_input, _, _ = select.select([sys.stdin], [], [], 0)
  
  if pipe_input:
    file_path = os.getenv('PIPE_INPUT_FILE', './pipe_input.txt')
    save_pipe_input_to_file(file_path, pipe_input[0].read())
    
    for attr in vars(args):
      if attr == "host" and error_AttrAndNone(args, attr):
        basic_host_Redirection(file_path)
      if attr == "hostfile" and error_AttrAndNone(args, attr):
        basic_hostfile_Redirection(file_path)  
  # Option 1 : hostfile 생략
    option1_Redirection(file_path)    
    quit()
  else:
      print("No PIPE. Passing...")


  
      
if __name__ == '__main__':
  # attr = ['host', "hostfile", "out", "err"]
  args, command = makeParser()
  all_Nodes = get_node_info()
  
  option2()

  # Basic
  for attr in vars(args):
    if attr == "host" and error_AttrAndNone(args, attr):
      basic_host()
    if attr == "hostfile" and error_AttrAndNone(args, attr):
      basic_hostfile()
  # Option 1 : hostfile 생략
  option1()

