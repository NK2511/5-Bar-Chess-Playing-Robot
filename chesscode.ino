#include <Servo.h>

// Define servos
Servo servo1;
Servo servo2;

// Pin numbers
int servo1_pin = 9;
int servo2_pin = 10;

// Current servo positions
int current_angle1 = 90;
int current_angle2 = 90;

void setup() {
  // Attach servos to pins
  servo1.attach(servo1_pin);
  servo2.attach(servo2_pin);

  // Start the servos at 90 degrees
  servo1.write(current_angle1);
  servo2.write(current_angle2);
  
  // Begin serial communication
  Serial.begin(9600);
}

void loop() {
  // Check if data is available from Python
  if (Serial.available()) {
    // Read the incoming data (angle1, angle2)
    String data = Serial.readStringUntil('\n');
    int angle1 = data.substring(0, data.indexOf(',')).toInt();
    int angle2 = data.substring(data.indexOf(',') + 1).toInt();

    // Move the servos gradually (smooth movement)
    move_servo_smoothly(servo1, current_angle1, angle1);
    move_servo_smoothly(servo2, current_angle2, angle2);

    // Update current angles
    current_angle1 = angle1;
    current_angle2 = angle2;
  }
}

void move_servo_smoothly(Servo &servo, int start_angle, int target_angle) {
  int step = (target_angle > start_angle) ? 1 : -1;
  
  for (int angle = start_angle; angle != target_angle; angle += step) {
    servo.write(angle);
    delay(15);  // Adjust delay for smoother motion (lower delay = smoother)
  }
}
