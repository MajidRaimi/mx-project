import os
import tempfile
import uuid
from PIL import Image
import streamlit as st
from ultralytics import SAM
from package import (
    pick_wall_point,
    save_image,
    save_image_with_point,
    draw_result_on_image,
    draw_points,
    connect_points,
)


os.environ["STREAMLIT_DISABLE_FILE_WATCHER"] = "true"

SAM_WEIGHTS = "sam2_t.pt"


def main():
    st.set_page_config(
        page_title="Wall Segmentation Step-by-Step", layout="centered")
    st.title("🧱 Wall Segmentation Pipeline")
    st.markdown(
        "Upload an image and watch each processing step with its visual result.")

    uploaded_file = st.file_uploader(
        "📷 Upload an Image", type=["jpg", "jpeg", "png"])
    gap = st.slider("🔢 Select GAP (grid spacing)",
                    min_value=30, max_value=100, value=30, step=1)

    if uploaded_file:

        session_dir = tempfile.mkdtemp(prefix="seg_", suffix=str(uuid.uuid4()))

        image_path = os.path.join(session_dir, uploaded_file.name)
        with open(image_path, "wb") as f:
            f.write(uploaded_file.read())

        image = Image.open(image_path).convert("RGB")
        st.image(image, caption="📥 Uploaded Image", use_container_width=True)

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
