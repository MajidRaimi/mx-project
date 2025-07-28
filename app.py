import os
import tempfile
import uuid
import numpy as np
from PIL import Image
import streamlit as st
import torch

# Multiple fixes for PyTorch-Streamlit compatibility
os.environ["STREAMLIT_SERVER_FILE_WATCHER_TYPE"] = "none"
os.environ["STREAMLIT_SERVER_ENABLE_FILE_WATCHER"] = "false"
os.environ["STREAMLIT_DISABLE_FILE_WATCHER"] = "true"

# Additional PyTorch path fix
torch.classes.__path__ = []

from ultralytics import SAM
from package import (
    pick_wall_point,
    save_image,
    save_image_with_point,
    draw_result_on_image,
    draw_points,
    connect_points,
)

SAM_WEIGHTS = "sam2_t.pt"

def initialize_drone():
    """Initialize drone connection and store in session state"""
    if 'drone_instance' not in st.session_state:
        try:
            from djitellopy import Tello
            
            # Create drone instance
            drone = Tello()
            drone.RESPONSE_TIMEOUT = 5  # Increase timeout for stability
            drone.connect()
            
            # Get battery and store in session state
            battery = drone.get_battery()
            
            st.session_state.drone_instance = drone
            st.session_state.battery_level = battery
            st.session_state.is_connected = True
            st.session_state.drone_flying = False
            
            return True, battery, drone
            
        except Exception as e:
            print(f"Drone connection failed: {e}")
            st.session_state.is_connected = False
            st.session_state.battery_level = 0
            st.session_state.drone_instance = None
            return False, 0, None
    
    else:
        # Use existing drone instance
        return (st.session_state.is_connected, 
                st.session_state.battery_level, 
                st.session_state.drone_instance)

def main():
    st.set_page_config(
        page_title="Wall Segmentation Step-by-Step", layout="centered")
    st.title("🧱 Wall Segmentation Pipeline")
    st.markdown(
        "Upload an image or use drone controls to capture and process wall segmentation.")

    # Initialize drone connection (only once)
    is_connected, battery_level, drone_instance = initialize_drone()
    
    # GAP slider - always visible
    gap = st.slider("🔢 Select GAP (grid spacing)",
                    min_value=30, max_value=100, value=30, step=1)

    image_path = None
    image = None

    if is_connected and drone_instance:
        st.markdown("---")
        st.markdown("### 🚁 Drone Controls")
        
        # Battery status with color coding
        if battery_level > 80:
            st.success(f"🔋 Battery: {battery_level}%")
        elif battery_level > 20:
            st.warning(f"🔋 Battery: {battery_level}%")
        else:
            st.error(f"🔋 Battery: {battery_level}% - Please charge!")
        
        # Show flight status
        if 'drone_flying' in st.session_state and st.session_state.drone_flying:
            st.info("✈️ Drone is currently flying")
        
        # Distance and height controls
        distance_from_wall = st.slider(
            "📏 Distance from Wall (meters)",
            min_value=0.5, max_value=10.0, value=2.0, step=0.5
        )
        
        height = st.slider(
            "📐 Height (meters)",
            min_value=1, max_value=5, value=2, step=1
        )
        
        # Drone action buttons - centered with padding
        col_pad1, col1, col2, col3, col_pad2 = st.columns([1, 2, 2, 2, 1])
        
        with col1:
            take_off_clicked = st.button("🚁 Take Off", type="primary", use_container_width=True)
        
        with col2:
            capture_clicked = st.button("📸 Capture Image", type="secondary", use_container_width=True)
        
        with col3:
            land_clicked = st.button("🛬 Land", type="secondary", use_container_width=True)
        
        # Handle button actions with full-width messages
        if take_off_clicked:
            with st.spinner("🚁 Taking off drone..."):
                try:
                    if not st.session_state.get('drone_flying', False):
                        drone_instance.streamon()
                        drone_instance.takeoff()
                        st.session_state.drone_flying = True
                        st.success("✅ Drone took off successfully!")
                        st.rerun()  # Refresh to update status
                    else:
                        st.info("✅ Drone is already flying!")
                except Exception as e:
                    st.error(f"❌ Take off error: {str(e)}")
        
        if capture_clicked:
            with st.spinner("📸 Positioning and capturing image..."):
                try:
                    # Ensure drone is flying
                    if not st.session_state.get('drone_flying', False):
                        st.error("❌ Please take off first!")
                    else:
                        # Move to specified height (convert meters to cm for drone)
                        height_cm = int(height * 100)
                        if height_cm > 0:
                            drone_instance.move_up(height_cm)
                        
                        # Move to specified distance (assuming forward movement)
                        distance_cm = int(distance_from_wall * 100)
                        if distance_cm > 0:
                            drone_instance.move_forward(distance_cm)
                        
                        # Wait a moment for stabilization
                        import time
                        time.sleep(2)
                        
                        # Capture image
                        frame = drone_instance.get_frame_read().frame
                        
                        if frame is not None and not np.all(frame == 0):
                            # Convert BGR to RGB
                            frame_rgb = frame[:, :, ::-1]
                            image = Image.fromarray(frame_rgb)

                            session_dir = tempfile.mkdtemp(
                                prefix="drone_", suffix=str(uuid.uuid4()))
                            image_path = os.path.join(
                                session_dir, "drone_capture.jpg")
                            image.save(image_path)

                            st.image(
                                image, caption="📸 Drone Captured Image", use_container_width=True)
                            st.success("✅ Image captured successfully!")
                        else:
                            st.error("❌ Failed to capture valid image. Please try again.")

                except Exception as e:
                    st.error(f"❌ Capture error: {str(e)}")
        
        if land_clicked:
            with st.spinner("🛬 Landing drone..."):
                try:
                    if st.session_state.get('drone_flying', False):
                        drone_instance.land()
                        st.session_state.drone_flying = False
                        st.success("✅ Drone landed safely!")
                        st.rerun()  # Refresh to update status
                    else:
                        st.info("✅ Drone is already on the ground!")
                except Exception as e:
                    st.error(f"❌ Landing error: {str(e)}")
        
        st.markdown("---")
        
    else:
        # Drone not connected - show image upload
        st.markdown("### 📷 Upload Image")
        if not is_connected:
            st.info("🚁 Drone not connected. Please upload an image to proceed.")
        
        uploaded_file = st.file_uploader(
            "📷 Upload an Image", type=["jpg", "jpeg", "png"])

        if uploaded_file:
            session_dir = tempfile.mkdtemp(
                prefix="seg_", suffix=str(uuid.uuid4()))
            image_path = os.path.join(session_dir, uploaded_file.name)
            with open(image_path, "wb") as f:
                f.write(uploaded_file.read())
            image = Image.open(image_path).convert("RGB")
            st.image(image, caption="📥 Uploaded Image",
                     use_container_width=True)

    # Process the image if we have one (from either upload or drone)
    if image_path and image:
        session_dir = os.path.dirname(image_path)

        with st.spinner("🧠 Step 1: Picking the best wall point..."):
            bw_image, pt = pick_wall_point(image)
            bw_path = os.path.join(session_dir, "01_black_and_white.jpg")
            pt_path = os.path.join(session_dir, "02_best_point.jpg")
            save_image(bw_image, bw_path)
            save_image_with_point(image, pt, pt_path)
        st.success("✅ Step 1 Done: Wall point selected.")
        st.image(bw_path, caption="🖼️ Step 1: Black & White Image",
                 use_container_width=True)
        st.image(pt_path, caption="🎯 Step 1: Selected Wall Point",
                 use_container_width=True)

        with st.spinner("📦 Step 2: Running SAM segmentation..."):
            sam = SAM(SAM_WEIGHTS)
            results = sam.predict(source=image_path, points=[
                                  pt], save=False, verbose=False)
            seg_image = draw_result_on_image(image, results)
            seg_path = os.path.join(session_dir, "03_segmentation.jpg")
            save_image(seg_image, seg_path)
        st.success("✅ Step 2 Done: Segmentation complete.")
        st.image(seg_path, caption="📐 Step 2: Wall Segmentation",
                 use_container_width=True)

        with st.spinner(f"🔲 Step 3: Drawing grid points (GAP = {gap})..."):
            img_points, grid = draw_points(results, image_path, gap)
            points_path = os.path.join(session_dir, "04_points.jpg")
            save_image(img_points, points_path)
        st.success("✅ Step 3 Done: Grid points added.")
        st.image(points_path, caption="🧮 Step 3: Grid Points",
                 use_container_width=True)

        with st.spinner("➡️ Step 4: Connecting points to form path..."):
            img_path, _ = connect_points(grid, results, image_path, gap)
            path_img_path = os.path.join(session_dir, "05_path.jpg")
            save_image(img_path, path_img_path)
        st.success("✅ Step 4 Done: Path connected.")
        st.image(path_img_path, caption="🛣️ Step 4: Final Path",
                 use_container_width=True)

        st.balloons()
        st.markdown(
            "🎉 **Pipeline Complete!** Try another image or change the GAP value.")


if __name__ == "__main__":
    main()
