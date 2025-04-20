// C++ code
// 마스터 통신

//통신 프로토콜 <- 실제 라즈베리에서도 적용할 예정
#define SNACK 		0xF1
#define CAMERA_ON 	0xF2
#define CAMERA_OFF 	0xF3

// 핀 정의 <- 라즈베리와 통신할 때는 내용이 달라짐
const int button 		= 2; 	// 간식 배급
const int switch_pin 	= 3; 	// 카메라 호출
const int camera_angle	= A0;	// 카메라 호출 시 서보 제어


// 상태 변수
volatile bool send_food = false;	//
bool prevSwitchState = HIGH;		// 카메라가 켜기고 꺼졌음을 한 번만 말하는 변수
bool sendingPot = false;			// 카메라 서보는 기본 비활성화
unsigned long lastPotSendTime = 0;		// 
const unsigned long potInterval = 200;  // 가변저항 전송 주기 ms

void setup() {
  Serial.begin(9600);					// 시리얼 통신

  pinMode(button, INPUT_PULLUP); 		// 간식 버튼
  pinMode(switch_pin, INPUT_PULLUP);	// 카메라 호출 스위치

  attachInterrupt(digitalPinToInterrupt(button), buttonPressed, FALLING);
  //버튼 값이 내려가는 시점에서 간식 주기
}

void loop() {
  
  if(send_food) {			//간식
    Serial.write(SNACK);
    send_food = false;
  }

  // 스위치 상태 확인
  bool switchState = digitalRead(switch_pin);
  if(prevSwitchState == HIGH && switchState == LOW) {			// 스위치 켜짐
    Serial.write(CAMERA_ON);
    sendingPot = true;
  } else if (prevSwitchState == LOW && switchState == HIGH) {	// 스위치 꺼짐
    Serial.write(CAMERA_OFF);
    sendingPot = false;
  }
  
  prevSwitchState = switchState;

  // 가변저항 값 전송, 200ms마다 전송함
  if(sendingPot && millis() - lastPotSendTime >= potInterval) {
    int potValue = map(analogRead(camera_angle), 0, 1023, 0, 180);
    Serial.write(potValue);
    lastPotSendTime = millis();
  }
}

void buttonPressed() {
  send_food = true;	//간식 주기
}
