#----------------------- AWS IoT Core -----------------------
ENDPOINT =
CLIENT_ID = 
PATH_TO_CERT =
PATH_TO_KEY =
PATH_TO_ROOT =

#-------------------------AWS S3--------------------------------

S3_AWS_ACCESS_KEY_ID =
S3_AWS_SECRET_ACCESS_KEY =
S3_BUCKET_NAME =
S3_PREFIX =
S3_REGION_NAME = 

# 예민한 정보는 별도 보관할 것

# 입력받고 보낼 메세지 토픽, 나중에는 각자 따로 받아야함
#-------------------------------------------------------------
TOPIC_STATUS  = "rpi/status"
TOPIC_MIC     = "mic/upload" # <- 현재 이거는 아직 안씀
TOPIC_CONTROL = "cmd/control"


from awscrt import io, mqtt, auth, http
from awsiot import mqtt_connection_builder
# AWS 연동


import time, json, threading, subprocess, serial, pyaudio, wave, boto3, pyaudio, wave, datetime
import io as std_io

#-------------------------------------------------------------

# IoT 제어 클래스

class controller:
    def __init__(self):
        self.mqtt_connection = None
        self.is_connected = False
        self.is_subscribed = False
        self.is_streaming = False
        self.PORT = '/dev/ttyACM0'   # 아두이노 포트
        self.BAUD = 9600             # 시리얼 통신 속도
        self.TIMEOUT = 1             # usb하고 연결 안됬을 때의 Time out
        self.nowtime = datetime.now() #현재 시간 측정
        pass

    def process(self, payload:dict) -> dict:
        command = payload.get("message")
        if command == "snack":
            self.snack_signal()
            print("간식 주기 신호 전송 완료")
            return {"status":"snack_give", 
                    "date": self.nowtime.date().isoformat(), 
                    "time": self.nowtime.time().strftime("%H:%M:%S") }
        
        elif command == "camera_on":
            self.start_camera_stream()
            self.is_streaming = True
            print("카메라 스트리밍 시작")
            return {"status":"rpi_camera_on", 
                    "date": self.nowtime.date().isoformat(),
                    "time": self.nowtime.time().strftime("%H:%M:%S") }
            
        elif command == "camera_off":
            self.stop_camera_stream()
            self.is_streaming = False
            print("카메라 스트리밍 종료")
            return {"status":"rpi_camera_off", 
                    "date": self.nowtime.date().isoformat(), 
                    "time": self.nowtime.time().strftime("%H:%M:%S") }
            
        elif command == "speaker":
            self.play_speaker()
            print("스피커 재생")
            return {"status":"user_sound", 
                    "date": self.nowtime.date().isoformat(), 
                    "time": self.nowtime.time().strftime("%H:%M:%S") }
            
        else:
            print("알 수 없는 명령어입니다.")
            
    def play_speaker(self):
        # 스피커 재생 코드
        pass
    
    def stop_camera_stream(self):
        # 실행 중인 gst-launch 프로세스 종료
        subprocess.run(["pkill", "gst-launch-1.0"])
        print("카메라 스트리밍 종료")
    
    def start_camera_stream(self):
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
            print("스트리밍이 시작")
        else:
            print("스트리밍 오류:", stderr.decode())
        
    
    def snack_signal(self):                                     # 간식 주기 신호
        """ 포트 연결 > 전송 > 포트 닫기 순으로 동작함 """
        try:
            ser = serial.Serial(self.PORT, self.BAUD, timeout=self.TIMEOUT)
            time.sleep(2)
            ser.write(bytes([0xF1]))
        except serial.SerialException as e:
            print(f"시리얼 전송 실패 {self.PORT}: {e}")
        finally:
            if 'ser' in locals() and ser.is_open:
                ser.close()
        print("간식 주기 완료")
        

# 녹음 및 S3 업로드 클래스
# 파라미터(엑세스키, 시크릿키, 버킷이름, 리전이름=기본 아시아, S3 프리픽스)

class recording:
    def __init__(self, aws_access_key, aws_secret_key, bucket_name, region_name='ap-northeast-2', s3_prefix='recordings/'):
        self.s3 = boto3.client(
            's3',
            aws_access_key_id = aws_access_key,
            aws_secret_access_key = aws_secret_key,
            region_name = region_name
        )
        self.bucket_name = bucket_name
        self.s3_prefix = s3_prefix

        self.format = pyaudio.paInt16
        self.channels = 1
        self.rate = 44100
        self.chunk = 1024
        self.audio = pyaudio.PyAudio()

        self.stop_event = threading.Event()
        self.thread = None

    def record_audio(self, duration_sec):
        stream = self.audio.open(format=self.format,
                                 channels=self.channels,
                                 rate=self.rate,
                                 input=True,
                                 frames_per_buffer=self.chunk)

        frames = []

        for _ in range(0, int(self.rate / self.chunk * duration_sec)):
            if self.stop_event.is_set():
                break
            data = stream.read(self.chunk)
            frames.append(data)

        stream.stop_stream()
        stream.close()

        wav_buffer = std_io.BytesIO()
        with wave.open(wav_buffer, 'wb') as wf:
            wf.setnchannels(self.channels)
            wf.setsampwidth(self.audio.get_sample_size(self.format))
            wf.setframerate(self.rate)
            wf.writeframes(b''.join(frames))

        wav_buffer.seek(0)
        return wav_buffer

    def upload_to_s3(self, buffer, key):
        try:
            self.s3.upload_fileobj(buffer, self.bucket_name, key)
            print(f"✅ 업로드 완료: s3://{self.bucket_name}/{key}")
        except Exception as e:
            print(f"❌ 업로드 실패: {e}")

    def _worker(self, duration_sec):
        while not self.stop_event.is_set():
            now = datetime.datetime.now()
            s3_key = self.s3_prefix + now.strftime("%Y-%m-%d_%H-%M-%S") + ".wav"
            buffer = self.record_audio(duration_sec)
            if not self.stop_event.is_set():
                self.upload_to_s3(buffer, s3_key)

    def start(self, record_seconds=3):
        if self.thread is None or not self.thread.is_alive():
            print("🔁 녹음 스레드 시작됨.")
            self.thread = threading.Thread(target=self._worker, args=(record_seconds,))
            self.thread.start()

    def stop(self):
        print("🛑 녹음 스레드 중지 요청됨.")
        self.stop_event.set()
        self.thread.join()
        self.audio.terminate()
        print("✅ 녹음 종료 완료.")


# ------------------------------------------------------------- json 메세지 수신 시 콜백백

def on_message_received(topic, payload, **kwargs):
    print(f"[DEBUG] topic={topic}, retained={kwargs.get('is_retained')}, payload={payload}")
    try:
        # 받은 메시지 디코딩 및 JSON 파싱
        decoded = payload.decode()
        data = json.loads(decoded)
        print(data['message'])
        
        if data['message'] == "snack" and data.get('success') is True:
            # threading.Thread(target=snack_signal).start()  # 스레드로 LED 켜기 <- 비동기 처리
            print("간식 주기")
            
        elif data['message'] == "camera_on":  # 카메라 메시지 수신
            # start_camera_stream()  # 카메라 스트리밍 시작
            print("카메라 스트리밍 시작")
            
        elif data['message'] == "camera_off":  # 카메라 끄기
            # stop_camera_stream()  # 카메라 스트리밍 종료
            print("카메라 스트리밍 종료")
        
        
        # 응답 JSON 구성
        

        # 응답 메시지 전송
        mqtt_connection.publish(
            topic=TOPIC_STATUS,
            payload=json.dumps(response),
            qos=mqtt.QoS.AT_LEAST_ONCE
        )
        print(f"메세지 전송 \n{RESPONSE_TOPIC} \n{response}")

    except json.JSONDecodeError:
        print("is not JSON FILE:", payload)


#------------------------------------------------------------- 여기부터 메인

def main():
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
    
    recorder = recording(
        aws_access_key=S3_AWS_ACCESS_KEY_ID,
        aws_secret_key=S3_AWS_SECRET_ACCESS_KEY,
        bucket_name=S3_BUCKET_NAME
    )
    
    recorder.start(record_seconds=2)  # 2초 간격으로 녹음 -> 업로드 파이프라인 가동
    
    mqtt_connection.publish(
        topic=TOPIC_STATUS,
        payload=json.dumps({"status":"ready"}),
        qos=mqtt.QoS.AT_LEAST_ONCE
    )
    
    # 구독중인 메세지들
    
    mqtt_connection.subscribe(
        topic=TOPIC_CONTROL, qos=mqtt.QoS.AT_LEAST_ONCE, callback=on_message_received
    )
    mqtt_connection.subscribe(
        topic=TOPIC_MIC, qos=mqtt.QoS.AT_LEAST_ONCE, callback=on_message_received
    )
    

    # 대기
    print("메시지 대기 중")
    try:
        while True:
            pass
    except KeyboardInterrupt:
        print("연결 종료")
        recorder.stop()
        mqtt_connection.disconnect().result()




if __name__ == "__main__":
    main()
