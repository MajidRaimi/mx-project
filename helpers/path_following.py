import cv2
import numpy as np
import threading
import queue
import time
import os
import pandas as pd
from djitellopy import Tello
import matplotlib.pyplot as plt

# Create folder to save input frames
os.makedirs("sample_input", exist_ok=True)

# Global variables
latest_frame = None
exit_event = threading.Event()  # Event to signal all threads to exit
frame_counter = 0  # For naming saved frames
commands_finished_event = threading.Event()  # Event to signal command execution completion
mission_cancelled_event = threading.Event()  # Event to signal immediate mission cancellation and landing
save_frame_event = threading.Event()  # Event to signal when to save a frame

# Queues for inter-thread communication
command_request_queue = queue.Queue()  # For command_executor_thread to send command details to user_input_thread
user_response_queue = queue.Queue()  # For user_input_thread to send user's decision back to command_executor_thread

# Initialize the Tello drone
drone = Tello()
try:
    drone.connect()
    drone.streamon()
    print('-----------------')
    print(f' Battery Level: {drone.get_battery()}%')
    print('-----------------')
    input('Check battery level and press Enter to continue...')
    drone.takeoff()
    drone.move_up(int(100))  # Initial upward movement to a good height
    time.sleep(3)
    # Read a frame to clear buffer after initial movements, before first action
    dump_data = drone.get_frame_read().frame
    time.sleep(1) # Give a moment for the frame to be ready
    save_frame_event.set() # Save initial frame after drone stabilizes from takeoff and initial move_up

except Exception as e:
    print(f"Failed to connect to Tello drone or perform initial commands: {e}")
    print("Please ensure the drone is on, connected to Wi-Fi, and try again.")
    exit_event.set()  # Set exit event to ensure clean shutdown if connection fails
    exit()  # Exit if drone connection fails

def frame_reader_thread(drone_obj, exit_event):
    """
    Continuously reads frames from the Tello drone and updates the global latest_frame.
    This runs in a separate thread to ensure continuous frame updates,
    independent of drone command execution or user input.
    """
    global latest_frame
    print("Starting frame reader thread...")
    while not exit_event.is_set():
        try:
            latest_frame = drone_obj.get_frame_read().frame
        except Exception as e:
            print(f"Error fetching frame: {e}")
            # Do not set exit_event here, as temporary frame errors shouldn't crash mission
        time.sleep(0.03)  # Small delay to prevent busy-waiting
    print("Frame reader thread finished.")

def user_input_thread(command_req_q, user_resp_q, exit_event):
    """
    Prompts the user for confirmation before executing each drone command.
    Receives command details from command_req_q and sends user's 'yes'/'no'
    response back via user_resp_q.
    """
    return
    print("Starting user input thread...")
    while not exit_event.is_set():
        try:
            # Wait for a command request from the executor thread
            pass
            # Use a timeout to prevent indefinite blocking if the main program exits unexpectedly
            # action, value = command_req_q.get(timeout=5)

            # Prompt user for confirmation
            # prompt = f"\nExecute action '{action}' with value '{value}'? (y/n): "
            # user_response = input(prompt).strip().lower()

            # Send user's response back to the executor thread
            # user_resp_q.put(user_response)
        except queue.Empty:
            # No command in queue, continue checking exit_event
            pass
        except Exception as e:
            print(f"Error in user input thread: {e}")
            exit_event.set()  # Signal exit on unexpected error
    print("User input thread finished.")

def command_executor_thread(drone_obj, commands_df, command_req_q, user_resp_q, mission_cancelled_event, commands_finished_event, exit_event, save_frame_event):
    """
    Executes drone commands read from an Excel DataFrame, after user confirmation.
    Sends zero RC control commands when idle to keep the drone stable.
    Signals the main loop to save frames before and after each action.
    """
    print("Starting command executor thread...")
    command_index = 0
    num_commands = len(commands_df)

    try:
        while not exit_event.is_set() and command_index < num_commands:
            # Send zero RC control to keep drone stable while waiting for next command or user input
            try:
                drone_obj.send_rc_control(0, 0, 0, 0)
            except Exception as e:
                print(f"Error sending RC control: {e}")

            row = commands_df.iloc[command_index]
            action = str(row['action']).strip().lower()
            value = int(row['value'])  # Ensure value is integer

            # 1. Send command to user_input_thread for confirmation
            print(f"Awaiting user confirmation for: {action} {value}")
            # command_req_q.put((action, value))

            # 2. Wait for user response from the user_input_thread
            # user_response = user_resp_q.get()

            if False:
                print(f"Mission cancelled by user. Landing drone.")
                mission_cancelled_event.set()  # Signal immediate landing
                exit_event.set()  # Signal all threads to exit
                break  # Exit command loop as mission is cancelled

            # --- Save frame BEFORE executing the action ---
            print("Signaling to save frame before action...")
            save_frame_event.set()
            # Wait a moment for the main loop to process the save request
            time.sleep(0.1)
            save_frame_event.clear() # Clear the event after signaling

            # 3. Execute command based on action
            print(f"Executing: {action} {value}")
            try:
                if action == 'move_up':
                    drone_obj.move_up(int(value))
                elif action == 'move_down':
                    drone_obj.move_down(int(value))
                elif action == 'move_left':
                    drone_obj.move_left(int(value))
                elif action == 'move_right':
                    drone_obj.move_right(int(value))
                elif action == 'move_forward':
                    drone_obj.move_forward(int(value))
                elif action == 'move_back':
                    drone_obj.move_back(int(value))
                elif action == 'rotate_clockwise':
                    drone_obj.rotate_clockwise(int(value))
                elif action == 'rotate_counter_clockwise':
                    drone_obj.rotate_counter_clockwise(int(value))
                elif action == 'takeoff':
                    drone_obj.takeoff()
                elif action == 'land':  # If 'land' is explicitly in commands, execute it
                    drone_obj.land()
                    exit_event.set()  # Land command means mission is explicitly over
                    break  # Exit command loop
                else:
                    print(f"Unknown action: '{action}'. Skipping.")

                time.sleep(3)  # Allow drone to stabilize after each blocking command

                # --- Save frame AFTER executing the action ---
                print("Signaling to save frame after action...")
                save_frame_event.set()
                # Wait a moment for the main loop to process the save request
                time.sleep(3)
                save_frame_event.clear() # Clear the event after signaling

            except Exception as e:
                print(f"Error executing drone command {action} {value}: {e}")
                mission_cancelled_event.set()  # Signal cancellation on execution error
                exit_event.set()
                break  # Exit command loop on error

            command_index += 1
            time.sleep(1)  # Small delay between processing commands to prevent busy-waiting

        # After loop, if not cancelled and all commands processed, signal commands finished
        if not mission_cancelled_event.is_set() and command_index >= num_commands:
            print("All navigation commands from Excel executed.")
            commands_finished_event.set()  # Signal that all commands are done
            exit_event.set()  # Signal main loop to exit after commands are done

    except Exception as e:
        print(f"An unexpected error occurred in command executor thread: {e}")
        mission_cancelled_event.set()
        exit_event.set()
    finally:
        print("Command executor thread finished.")

# --- Excel File Input and Processing ---
frame_reader_t = None
user_input_t = None
command_executor_t = None

try:
    excel_file_path = "data/commands.csv"

    if not os.path.exists(excel_file_path):
        raise FileNotFoundError(f"Error: File not found at '{excel_file_path}'")

    commands_df = pd.read_csv(excel_file_path)

    # Validate required columns
    required_columns = ['action', 'value']
    if not all(col in commands_df.columns for col in required_columns):
        raise ValueError(f"Error: Excel file must contain all required columns: {required_columns}")

    # Ensure 'value' column is numeric and handle missing values by filling with 0
    commands_df['value'] = pd.to_numeric(commands_df['value'], errors='coerce').fillna(0).astype(int)
    # Ensure 'action' column is string
    commands_df['action'] = commands_df['action'].astype(str)

    print("Excel file loaded successfully. Starting drone navigation based on instructions.")

    # Start the threads
    frame_reader_t = threading.Thread(target=frame_reader_thread, args=(drone, exit_event), name="FrameReaderThread")
    frame_reader_t.start()

    user_input_t = threading.Thread(target=user_input_thread, args=(command_request_queue, user_response_queue, exit_event), name="UserInputThread")
    user_input_t.start()

    command_executor_t = threading.Thread(target=command_executor_thread, args=(drone, commands_df, command_request_queue, user_response_queue, mission_cancelled_event, commands_finished_event, exit_event, save_frame_event), name="CommandExecutorThread")
    command_executor_t.start()

except FileNotFoundError as e:
    print(e)
    exit_event.set()  # Set exit event to stop other threads gracefully
except ValueError as e:
    print(e)
    exit_event.set()  # Set exit event to stop other threads gracefully
except Exception as e:
    print(f"An unexpected error occurred during Excel processing or thread startup: {e}")
    exit_event.set()  # Set exit event to stop other threads gracefully

# plt.ion()  # Turn on interactive mode for matplotlib for real-time plot updates
try:
    # Main loop for frame display and saving
    while not exit_event.is_set():
        if latest_frame is not None:
            display_frame = latest_frame.copy()

            # Check if save_frame_event is set
            if save_frame_event.is_set():
                frame_path = os.path.join("sample_input", f"frame_{frame_counter:05d}.jpg")
                cv2.imwrite(frame_path, display_frame)
                print(f"Saved frame_{frame_counter:05d}.jpg")
                frame_counter += 1
                save_frame_event.clear()  # Clear the event after saving the frame

            # Display the frame using matplotlib
            rgb_frame = cv2.cvtColor(display_frame, cv2.COLOR_BGR2RGB)
            if 'fig' not in globals():  # Create figure and axis only once
                pass
                # fig, ax = plt.subplots(figsize=(8, 6))  # Adjust figure size as needed
                # img_plot = ax.imshow(rgb_frame)
                # ax.set_title("Drone View (Press Ctrl+C in console to stop)")
                # ax.axis('off')  # Hide axes ticks and labels
                # plt.tight_layout()  # Adjust layout to prevent labels overlapping
            else:
                print()
                # img_plot.set_data(rgb_frame)  # Update existing plot data

            # plt.draw()  # Redraw the plot
            # plt.pause(0.01)  # Short pause for UI update and to allow other threads to run

        # Check if mission was cancelled or commands are finished
        if mission_cancelled_event.is_set() or commands_finished_event.is_set():
            print("Mission cancelled or all commands executed. Preparing to land.")
            exit_event.set()  # Signal main loop to exit and trigger the finally block

        time.sleep(0.05)  # Small sleep to prevent busy-waiting in the main display loop

finally:
    print("Program ending. Attempting to land drone and clean up resources...")
    # Ensure exit event is set for all threads to terminate gracefully
    exit_event.set()

    # Wait for all threads to finish, with a timeout
    threads_to_join = [frame_reader_t, user_input_t, command_executor_t]
    for t in threads_to_join:
        if t and t.is_alive():
            print(f"Waiting for {t.name} to finish...")
            t.join(timeout=5)  # Increased timeout to allow threads to finish their current operations
            if t.is_alive():
                print(f"Warning: {t.name} did not terminate gracefully.")

    # Land the drone and stop the video stream
    try:
        if drone:  # Check if drone object was successfully initialized
            drone.land()
            drone.streamoff()
            print("Drone landed and stream off.")
    except Exception as e:
        print(f"Error during drone landing or stream off: {e}")
    finally:
        plt.close('all')  # Close all matplotlib plots
        print("Program finished.")