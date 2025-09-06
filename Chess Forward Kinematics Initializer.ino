#include <Wire.h>
#include <Adafruit_PWMServoDriver.h>

Adafruit_PWMServoDriver pwm = Adafruit_PWMServoDriver();

int servo1 = 0;   // Motor 1 pin
int servo5 = 15;  // Motor 2 pin

float angle1 = 90; // Starting angles (midpoint)
float angle5 = 90;

void setup() {
  Serial.begin(9600);
  pwm.begin();
  pwm.setPWMFreq(50);  // 50Hz for analog servos

  Serial.println("Use W/S to adjust angle1 (base), A/D for angle5 (elbow)");
  Serial.println("Type: Save H8  to save the current angles for coordinate H8");
  Serial.println("----------");

  moveServos(angle1, angle5);
}

void loop() {
  if (Serial.available()) {
    String input = Serial.readStringUntil('\n');
    input.trim();  // Remove whitespace
    input.toUpperCase(); // Handle lowercase too

    bool moved = false; // Flag to check if a move occurred

    if (input == "W") {
      angle1 += 1;
      moved = true;
    } else if (input == "S") {
      angle1 -= 1;
      moved = true;
    } else if (input == "A") {
      angle5 += 1;
      moved = true;
    } else if (input == "D") {
      angle5 -= 1;
      moved = true;
    } else if (input.startsWith("SAVE ")) {
      String coord = input.substring(5); // Get text after 'SAVE '
      Serial.print("Saved ");
      Serial.print(coord);
      Serial.print(" => theta1: ");
      Serial.print(angle1);
      Serial.print(", theta5: ");
      Serial.println(angle5);
    } else {
      Serial.println("Invalid command. Use W/S/A/D or Save <coord>");
    }

    angle1 = constrain(angle1, 0, 180);
    angle5 = constrain(angle5, 0, 180);

    if (moved) {
      moveServos(angle1, angle5);
      Serial.print("Moved to => theta1: ");
      Serial.print(angle1);
      Serial.print(", theta5: ");
      Serial.println(angle5);
    }
  }
}


void moveServos(float a1, float a5) {
  int pwm1 = map(a1, 0, 180, 102, 512);
  int pwm5 = map(a5, 0, 180, 102, 512);
  pwm.setPWM(servo1, 0, pwm1);
  pwm.setPWM(servo5, 0, pwm5);
}
