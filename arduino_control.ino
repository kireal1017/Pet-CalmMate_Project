#include <Servo.h>

//간식 프로토콜
#define SNACK         0xF1
#define CAMERA_ON     0xF2
#define CAMERA_OFF    0xF3

//RGB 정의
#define R 2
#define G 3
#define B 4

//서보모터 정의
Servo snack_servo;
Servo camera_servo;


bool snack_state = false;
unsigned long snack_starttime = 0;
const unsigned long snack_opentime = 1000; // 간식 동작 시간 ms

void setup() {
  Serial.begin(9600);
  Serial.println("Receiver Ready");
  
  pinMode(R, OUTPUT); //r
  pinMode(G, OUTPUT); //g
  pinMode(B, OUTPUT); //b
  pinMode(7, INPUT_PULLUP);	//power switch
  
  snack_servo.attach(5);	// snack give motor
  camera_servo.attach(6);	//camera move motor
  snack_servo.write(0);
}

void loop() {
  // 시리얼 수신 처리
  if (Serial.available() > 0) {
    byte incoming = Serial.read();

    switch (incoming) {
      case SNACK:
        Serial.println("Received: SNACK");
        snack_servo.write(180);
        snack_starttime = millis();
        snack_state = true;
        break;

      case CAMERA_ON:
        Serial.println("Received: CAMERA ON");
        digitalWrite(G, HIGH);
        break;

      case CAMERA_OFF:
        Serial.println("Received: CAMERA OFF");
        digitalWrite(G, LOW);
      	camera_servo.write(90);  // 카메라 원위치
        break;

      default:
        if (incoming <= 180) {
          Serial.print("Received CAMERA ANGLE: ");
          Serial.println(incoming);
          camera_servo.write(incoming); //들어온 정수값대로 카메라 각도 제어
        } else {
          Serial.print("Unknown");
        }
        break;
    }
  }

  // snack_servo 자동 복귀 처리
  if (snack_state && millis() - snack_starttime >= snack_opentime) {
    snack_servo.write(0);  // 원위치
    snack_state = false;
  }
}
