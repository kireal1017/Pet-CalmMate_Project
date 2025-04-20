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


from datetime import datetime
# 날짜 및 시간

import time, json, threading
import RPi.GPIO as GPIO
# GPIO 제어 라이브러리

#--------------------------- GPIO setup ----------------------
GPIO.setmode(GPIO.BCM)          # GPIO pin numbering
GPIO.setup(17, GPIO.OUT)        # 17번 LED
LED = 17

#-------------------------------------------------------------
    
def snack_signal():
    GPIO.output(LED, GPIO.HIGH)   # LED 켜기
    time.sleep(3)                 # 1초 대기
    GPIO.output(LED, GPIO.LOW)    # LED 끄기

# 메시지를 받았을 때 실행되는 콜백 함수
def on_message_received(topic, payload, **kwargs):
    try:
        # 받은 메시지 디코딩 및 JSON 파싱
        decoded = payload.decode()
        data = json.loads(decoded)
        print(data['message'])
        
        if data['message'] == "MQTT 간식 신호 발행 완료" and data.get('success') is True:
            threading.Thread(target=snack_signal).start()  # 스레드로 LED 켜기 <- 비동기 처리
        
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
print(f"토픽 구독 중: {SUBSCRIBE_TOPIC}")

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
    GPIO.cleanup()

'''
try:
    while True:
        GPIO.output(LED, GPIO.HIGH) # LED 켜기
        time.sleep(1) # 1초 대기
        GPIO.output(LED, GPIO.LOW)
        time.sleep(1)
finally:
    GPIO.cleanup()
'''
