#예민한 정보는 별도 보관
#----------------------- AWS IoT Core -----------------------
ENDPOINT = 
CLIENT_ID = 
PATH_TO_CERT = 
PATH_TO_KEY = 
PATH_TO_ROOT = 

# 입력받고 보낼 메세지 토픽, 나중에는 각자 따로 받아야함
#-------------------------------------------------------------
SUBSCRIBE_TOPIC = "give/snack"          # 입력받는 토픽
RESPONSE_TOPIC = "today/snack/response" # 응답하는 토픽


from awscrt import io, mqtt, auth, http
from awsiot import mqtt_connection_builder
# AWS 연동

from datetime import datetime
# 날짜 및 시간

import time, json, threading, subprocess, serial

#-------------------------------------------------------------
    
def snack_signal():                                     # 간식 주기 신호
    """ 포트 연결 > 전송 > 포트 닫기 순으로 동작함 """
    try:
        ser = serial.Serial(PORT, BAUD, timeout=TIMEOUT)
        time.sleep(2)
        ser.write(bytes([0xF1]))
    except serial.SerialException as e:
        print(f"시리얼 전송 실패 {PORT}: {e}")
    finally:
        if 'ser' in locals() and ser.is_open:
            ser.close()


#-------------------------------------------------------------

def start_camera_stream():
    """ 카메라 스트리밍 시작 """
    '''
    pipeline = (
        "gst-launch-1.0 autovideosrc "
        "! videoconvert "
        "! video/x-raw,format=I420,width=640,height=480 "
        "! x264enc bframes=0 key-int-max=45 tune=zerolatency "
        "byte-stream=true speed-preset=ultrafast "
        "! h264parse "
        "! video/x-h264,stream-format=avc,alignment=au,profile=baseline "
        "! kvssink stream-name=rpi-video"
    )
    subprocess.Popen(pipeline, shell=True, executable="/bin/bash")
    
    # 로그 확인 (출력된 로그에서 'streaming started' 메시지를 찾음)
    stdout, stderr = process.communicate()
    if "streaming started" in stdout.decode() or "stream is ready" in stdout.decode():
        print("스트리밍이 시작되었습니다.")
    else:
        print("스트리밍 시작 오류:", stderr.decode())
    '''
    print("카메라")
 

def stop_camera_stream():
    # 실행 중인 gst-launch 프로세스 종료
    subprocess.run(["pkill", "gst-launch-1.0"])
    print("카메라 스트리밍 종료")
    

#-------------------------------------------------------------

# 메시지를 받았을 때 실행되는 콜백 함수
def on_message_received(topic, payload, **kwargs):
    print(f"[DEBUG] topic={topic}, retained={kwargs.get('is_retained')}, payload={payload}")
    try:
        # 받은 메시지 디코딩 및 JSON 파싱
        decoded = payload.decode()
        data = json.loads(decoded)
        print(data['message'])
        
        if data['message'] == "MQTT 간식 신호 발행 완료" and data.get('success') is True:
            threading.Thread(target=snack_signal).start()  # 스레드로 LED 켜기 <- 비동기 처리
            
        elif data['message'] == "MQTT camera on":  # 카메라 메시지 수신
            start_camera_stream()  # 카메라 스트리밍 시작
            
        elif data['message'] == "MQTT camera off":  # 카메라 끄기
            stop_camera_stream()  # 카메라 스트리밍 종료
        
        nowtime = datetime.now() #현재 시간 측정
        # 응답 JSON 구성
        response = {
            "status": "LED 켜짐",
            "date": nowtime.date().isoformat(),
            "time": nowtime.time().strftime("%H:%M:%S")
        }

        # 응답 메시지 전송
        mqtt_connection.publish(
            topic=RESPONSE_TOPIC,
            payload=json.dumps(response),
            qos=mqtt.QoS.AT_LEAST_ONCE
        )
        print(f"메세지 전송 \n{RESPONSE_TOPIC} \n{response}")

    except json.JSONDecodeError:
        print("is not JSON FILE:", payload)

# AWS IoT MQTT 연결 준비
event_loop_group = io.EventLoopGroup(1)
host_resolver = io.DefaultHostResolver(event_loop_group)
client_bootstrap = io.ClientBootstrap(event_loop_group, host_resolver)

mqtt_connection = mqtt_connection_builder.mtls_from_path(
    endpoint=ENDPOINT,
    cert_filepath=PATH_TO_CERT,
    pri_key_filepath=PATH_TO_KEY,
    ca_filepath=PATH_TO_ROOT,
    client_id=CLIENT_ID,
    clean_session=False,
    keep_alive_secs=30,
)

# 연결 시도
print("conntecting aws iot")
mqtt_connection.connect().result()
print("connected")

# 메시지 구독
print(f"구독 중인 토픽: {SUBSCRIBE_TOPIC}")

mqtt_connection.subscribe(
    topic=SUBSCRIBE_TOPIC,
    qos=mqtt.QoS.AT_LEAST_ONCE,
    callback=on_message_received
)

# 대기
print("메시지 대기 중")
try:
    while True:
        pass
except KeyboardInterrupt:
    print("연결 종료")
    mqtt_connection.disconnect().result()

