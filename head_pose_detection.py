import cv2
import dlib
import numpy as np
import time
import requests
import simpleaudio as sa

# Initialize dlib's face detector and facial landmark predictor
detector = dlib.get_frontal_face_detector()
predictor = dlib.shape_predictor("shape_predictor_68_face_landmarks.dat")

alternate_img = cv2.imread('angryCapy.png')
audio_wave_obj = sa.WaveObject.from_wave_file("capcap.wav")

# Initialize counters and tracking variables
left_away_count = 0
right_away_count = 0
look_away_total = 0 
last_direction = "forward"  # Start with "forward" as the initial direction
last_look_away_time = time.time()  # Track the time of the last increment
cooldown_period = 1  # Cooldown period in seconds to prevent duplicate counts
audio_played = False  # Track if audio has been played for the current look_away_total

capybara_x = 2
capybara_y = 2 
capybara_width = 500
capybara_height = 500
capybara_speed = 10

capybara_img = cv2.imread('happyCapy.PNG', cv2.IMREAD_UNCHANGED)
capybara_img = cv2.resize(capybara_img, (capybara_width, capybara_height))

def overlay_image_alpha(background, overlay, x, y):
    """Overlay PNG with alpha channel onto the background."""
    background_width = background.shape[1]
    background_height = background.shape[0]
    
    if overlay.shape[2] == 3:
        overlay = cv2.cvtColor(overlay, cv2.COLOR_BGR2BGRA)
    
    h, w = overlay.shape[0], overlay.shape[1]
    
    # Ensure coordinates are within frame
    if x >= background_width or y >= background_height:
        return background
    
    # Crop if necessary
    if x + w > background_width:
        w = background_width - x
    if y + h > background_height:
        h = background_height - y
    
    # Get ROI
    overlay_roi = overlay[0:h, 0:w]
    background_roi = background[y:y+h, x:x+w]
    
    # Extract alpha channel and create masks
    if overlay_roi.shape[2] == 4:
        alpha = overlay_roi[:, :, 3] / 255.0
        alpha = np.expand_dims(alpha, axis=-1)
        background_roi = background_roi * (1 - alpha) + overlay_roi[:, :, :3] * alpha
        
    background[y:y+h, x:x+w] = background_roi
    return background

def get_head_pose(shape):
    # Define 2D facial landmarks
    image_points = np.array([
        (shape.part(30).x, shape.part(30).y),    # Nose tip
        (shape.part(8).x, shape.part(8).y),      # Chin
        (shape.part(36).x, shape.part(36).y),    # Left eye corner
        (shape.part(45).x, shape.part(45).y),    # Right eye corner
        (shape.part(48).x, shape.part(48).y),    # Left mouth corner
        (shape.part(54).x, shape.part(54).y)     # Right mouth corner
    ], dtype="double")

    # Define 3D model points of the facial landmarks
    model_points = np.array([
        (0.0, 0.0, 0.0),          # Nose tip
        (0.0, -330.0, -65.0),     # Chin
        (-225.0, 170.0, -135.0),  # Left eye corner
        (225.0, 170.0, -135.0),   # Right eye corner
        (-150.0, -150.0, -125.0), # Left mouth corner
        (150.0, -150.0, -125.0)   # Right mouth corner
    ])

    # Camera internals
    focal_length = 640  # Assuming 640x480 resolution
    center = (320, 240)
    camera_matrix = np.array([
        [focal_length, 0, center[0]],
        [0, focal_length, center[1]],
        [0, 0, 1]
    ], dtype="double")

    dist_coeffs = np.zeros((4, 1))  # Assume no lens distortion
    _, rotation_vector, translation_vector = cv2.solvePnP(
        model_points, image_points, camera_matrix, dist_coeffs
    )

    return rotation_vector, translation_vector

def increment_lookaway():
    try:
        # Send a POST request to the Flask app to update lookaway count
        response = requests.post("http://127.0.0.1:5000/update_lookaway")
        if response.status_code == 200:
            print("Look-away count updated.")
        else:
            print("Failed to update look-away count.")
    except Exception as e:
        print("Error:", e)

# Initialize the video capture
cap = cv2.VideoCapture(1)

while True:
    ret, frame = cap.read()
    if not ret:
        break

    # Create an overlay for the mask
    overlay = frame.copy()
    
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    faces = detector(gray)

    # Switch image and play audio every 4 lookaways
    if (look_away_total % 8) < 4:
        image_to_display = capybara_img
    else:
        image_to_display = alternate_img

    # Play audio if look_away_total is a multiple of 4 and audio hasn't been played
    if look_away_total % 4 == 0 and look_away_total > 0 and not audio_played:
        audio_wave_obj.play()  # Play audio alert
        audio_played = True  # Mark audio as played for this look_away_total
    elif look_away_total % 4 != 0:
        audio_played = False  # Reset the flag when look_away_total changes

    # Overlay the capybara image
    frame = overlay_image_alpha(frame, image_to_display, capybara_x, capybara_y)

    for face in faces:
        shape = predictor(gray, face)
        rotation_vector, _ = get_head_pose(shape)

        # Draw a transparent mask over the face
        x, y, w, h = face.left(), face.top(), face.width(), face.height()
        cv2.rectangle(overlay, (x, y), (x + w, y + h), (0, 0, 255), -1)

        # Get the current time
        current_time = time.time()

        # Check head position and update counters based on the direction change with cooldown
        if rotation_vector[1] > 0.2 and last_direction != "right" and (current_time - last_look_away_time) > cooldown_period:
            right_away_count += 1
            increment_lookaway()  # Send update to Flask app
            look_away_total += 1 
            last_direction = "right"  
            last_look_away_time = current_time  
        elif rotation_vector[1] < -0.2 and last_direction != "left" and (current_time - last_look_away_time) > cooldown_period:
            left_away_count += 1
            look_away_total += 1
            increment_lookaway()  
            last_direction = "left"  
            last_look_away_time = current_time  
        elif -0.2 <= rotation_vector[1] <= 0.2:
            last_direction = "forward"  

        # Display the current direction
        if last_direction == "right":
            cv2.putText(frame, "Looking Right", (50, 50), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 2)
        elif last_direction == "left":
            cv2.putText(frame, "Looking Left", (50, 50), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 2)
        else:
            cv2.putText(frame, "Looking Forward", (50, 50), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)

    # Apply the transparent mask
    alpha = 0.4  # Transparency factor (0 = fully transparent, 1 = fully opaque)
    frame = cv2.addWeighted(overlay, alpha, frame, 1 - alpha, 0)

    # Display counters on the frame
    cv2.putText(frame, f"Left Count: {left_away_count}", (50, 100), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 255, 0), 2)
    cv2.putText(frame, f"Right Count: {right_away_count}", (50, 130), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 255, 0), 2)

    cv2.imshow("Head Pose Detection", frame)

    # Press 'q' to exit
    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

cap.release()
cv2.destroyAllWindows()