# IPC

CLSH - 클러스터쉘(CLuster SHell)
다수의 원격 쉘에 명령어를 실행하고 결과 수집 후 출력
Linux 환경에서 Docker를 활용하여 진행

기본 사용 옵션
1. node1, node2, node3, node4의 /proc/loadavg 읽어오기
   >     ex) $clsh -h node1,node2,node3,node4 cat /proc/loadavg
   >     -> clsh ~ node4 : 실행 옵션 / cat /proc/loadavg : 원격 실행할 명령어
   > 
   >     결과 : node1: 0.02 0.01 0.00 1/202 23042
   >     node4: 0.02 0.01 0.00 1/202 23042
   >     node2: 0.02 0.01 0.00 1/202 23042
   >     node3: 0.02 0.01 0.00 1/202 23042
   >     -> '노드이름': '각 노드의 출력', 응답이 오는 순서대로 출력

2. 호스트 파일에 노드의 이름을 저장하여 사용
   호스트 파일에는 한 라인에 하나의 호스트 이름 혹은 IP 주소가 저장
  >      ex) $cat ./hostfile의 내용이 아래와 같을 때
             node1
             node2
             node3
             node4
             $clsh -hostfile ./hostfile cat /proc/loadavg 의 명령어는
             $clsh -h node1,node2,node3,node4 cat /proc/loadavg 를 명령어와 동일하다.

추가 사용 옵션
1. --hostfile 옵션을 생략할 경우의 동작
   1. CLSH_HOST 환경 변수에서 호스트 이름 읽어오기, `:`(콜론)으로 구분
   2. CLSH_HOSTFILE 환경 변수에서 파일 이름 읽어오기(default : 상대경로, `/`로 시작할 경우 절대 경로 처리)
   3. 현재 디렉토리에서 .hostfile 읽어오기
   위 3가지 실패할 경우, 에러 처리
   >        ex1) export CLSH_HOSTS=node1:node12:node30
                 $clsh cat /proc/loadavg
                 Note: use CLSH_HOSTS environment
                 node1: ...
                 node12: ...
                 node30: ...
            ex2) export CLSH_HOSTFILE=clusterfile
                 $clsh cat /proc/loadavg
                 Note: use hostfile 'clusterfile' (CLSH_HOSTFILE env)
                 node1: ...
                 node12: ...
                 node30: ...
            ex3) $clsh cat /proc/loadavg
                 Note: use hostfile '.hostfile' (default)
                 node1: ...
                 node12: ...
                 node30: ...
            ex Error) CLSH_HOSTS 환경 변수가 없는 경우
                     -> CLSH_HOSTFILE 환경 변수 검사, 없는 경우
                     -> .hostfile 검사, 없는 경우
                     -> 에러 문구 출력 후 종료

2. 쉘 Redirection 구현
   >      ex) $ ls /etc/*.conf | clsh -hostfile ./hostfile -b xargs ls
          명령어 설명 : ls 의 결과를 clsh 로 전달하여 원격 실행

3. 출력 옵션 구현
   >      ex) $ clsh -out=/tmp/run/ -err=/tmp/run/error/ ls /etc
          명령어 설명 : 노드에서 명령어 실행 결과(표준 출력)를 /tmp/run/<Node이름>.out 에 저장
                        노드에서 명령어 실행 결과(표준 에러)를 /tmp/run/error/<Node이름>.err 에 저장

4. Interactive Mode 구현
   
   >       통신할 노드를 선택하는 방식
         ex) $ clsh -hostfile ./hostfile -i
             Enter 'quit' to leave this interactive mmode
             Working with nodes: node1,node2,node3
             clsh> uname
             ---------------
             node1: ...
             node2: ...
             node3: ...
             ---------------
             clsh>
     
   -i 옵션 입력 후 연결 가능한 노드 목록 중 원하는 노드를 입력하면 선택한
   노드들만 통신(단일, 다수 가능)
   노드 미 입력시 연결 가능한 모든 노드들과 통신

   
   
       

   
       



