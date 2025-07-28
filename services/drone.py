from djitellopy import Tello
import time


class Drone():
    global drone

    drone = Tello()
    drone.connect()
    drone.streamon()

    if drone.get_battery() > 80:
        print(f"\033[92mBattery level: {drone.get_battery()}%\033[0m")
    elif drone.get_battery() > 0 and drone.get_battery() < 80:
        print(f"\033[93mBattery level: {drone.get_battery()}%\033[0m")
    else:
        print(f"\033[91mBattery level: {drone.get_battery()}%\033[0m")
        print("Please charge the drone 🙏")
        exit()

    @staticmethod
    def takeoff():
        drone.takeoff()

    @staticmethod
    def move_up(height):
        drone.move_up(height)

    @staticmethod
    def move_down(height):
        drone.move_down(height)

    @staticmethod
    def move_left(height):
        drone.move_left(height)

    @staticmethod
    def move_right(height):
        drone.move_right(height)

    @staticmethod
    def move_forward(height):
        drone.move_forward(height)

    @staticmethod
    def land():
        drone.land()

    @staticmethod
    def take_image():
        time.sleep(2)

        try:
            _ = drone.get_frame_read().frame
            time.sleep(0.5)

            frame = drone.get_frame_read().frame
            return frame
        except Exception as e:
            print(f"Error capturing frame: {e}")
            return None

    @staticmethod
    def is_drone_connected():
        return drone.connect()

    @staticmethod
    def get_battery():
        return drone.get_battery()
