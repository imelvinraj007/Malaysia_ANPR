import streamlit as st
import json
import time
from collections import OrderedDict
import cv2
import csv
import requests
import pandas as pd
import os
import base64
from tqdm import tqdm
from typing import List, Dict
import numpy as np
from PIL import Image
from flask import Flask, render_template, request
import mysql.connector as mysql 

mydb = mysql.connect(
    host="localhost",
    user="root",
    password="",
    database="anpr"
)
cursor = mydb.cursor()

def authenticate(username, password):
    # Add your authentication logic here
    if username == "admin" and password == "password":
        return True
    else:
        return False

def login():
    st.subheader("Login")

    logged_in = st.session_state.get('logged_in', False)

    if not logged_in:
        username = st.text_input("Username")
        password = st.text_input("Password", type="password")

        if st.button("Login"):
            if authenticate(username, password):
                st.session_state.logged_in = True
                st.success("Logged in as admin")
                return True
            else:
                st.error("Invalid username or password")
        return False
    else:
        return True

def display_data():
    # Select all rows from the 'username' table
    query = "SELECT * FROM username"
    cursor.execute(query)
    data = cursor.fetchall()

    if len(data) > 0:
        st.header("Data in 'username' Table")
        for row in data:
            st.write("ID:", row[0])
            st.write("Name:", row[1])
            st.write("---")
    else:
        st.info("No data available in the table.")

def display_data2():
    # Select all rows from the 'registered_vehicle' table
    query = "SELECT * FROM registered_vehicles"
    cursor.execute(query)
    data = cursor.fetchall()

    if len(data) > 0:
        st.header("Data in 'registered_vehicles' Table")
        for row in data:
            st.write("Number Plate:", row[0])
            st.write("Department:", row[1])
            st.write("---")
    else:
        st.info("No data available in the table.")

def add():
    name = request.form.get("name")
    email = request.form.get("email")

    cursor = mydb.cursor()
    query = "INSERT INTO username (name, email) VALUES (%s, %s)"
    values = (name, email)
    cursor.execute(query, values)
    mydb.commit()
    cursor.close()

    return "Information added successfully!"

def perform_ocr(image_path):
    result = []
    with open(image_path, 'rb') as fp:
        response = requests.post(
            'https://api.platerecognizer.com/v1/plate-reader/',
            files=dict(upload=fp),
            data=dict(regions='fr'),
            headers={'Authorization': 'Token ' + '46569c6bbf83ec3257068d20a74113e420598687'}
        )

    result.append(response.json(object_pairs_hook=OrderedDict))
    time.sleep(1)

    resp_dict = json.loads(json.dumps(result, indent=2))
    num = resp_dict[0]['results'][0]['plate']
    characters = resp_dict[0]['results'][0]['candidates'][0]['plate']

    # Check if the extracted number plate exists in the 'registered_vehicles' table
    query = "SELECT * FROM registered_vehicles WHERE NUMBER_PLATE = %s"
    values = (num,)

    cursor.execute(query, values)
    result = cursor.fetchall()

    if result:
        department = result[0][1]
        return department, characters
    else:
        return 'Unknown', characters
    
def open_camera():
    global camera_open  # Update the global variable

    frameWidth = 640    # Frame Width
    frameHeight = 480   # Frame Height

    plateCascade = cv2.CascadeClassifier(r"C:\Users\Hariths Haziq\Downloads\ANPR-System\ANPR-System\haarcascade_russian_plate_number")
    minArea = 500

    cap = cv2.VideoCapture(0)
    cap.set(3, frameWidth)
    cap.set(4, frameHeight)
    cap.set(10, 150)
    count = 0

    # Placeholder to display the camera feed
    camera_feed_placeholder = st.empty()

    # Set camera_open to True
    camera_open = True

    # Add a unique key to the button to prevent re-execution when stopped
    stop_camera_button = st.button("Stop Camera", key="stop_camera")

    while camera_open:
        success, img = cap.read()

        imgGray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

        numberPlates = plateCascade.detectMultiScale(imgGray, 1.1, 4)

        for (x, y, w, h) in numberPlates:
            area = w * h
            if area > minArea:
                cv2.rectangle(img, (x, y), (x + w, y + h), (255, 0, 0), 2)
                cv2.putText(img, "NumberPlate", (x, y - 5), cv2.FONT_HERSHEY_COMPLEX, 1, (0, 0, 255), 2)
                imgRoi = img[y:y + h, x:x + w]
                cv2.imshow("ROI", imgRoi)

        # Display the camera feed within the website
        camera_feed_placeholder.image(img, channels="BGR")

        if cv2.waitKey(1) & 0xFF == ord('s'):
            cv2.imwrite(r"C:\Users\Hariths Haziq\Downloads\ANPR-System\ANPR-System\scan" + str(count) + ".jpg", imgRoi)
            cv2.rectangle(img, (0, 200), (640, 300), (0, 255, 0), cv2.FILLED)
            cv2.putText(img, "Scan Saved", (15, 265), cv2.FONT_HERSHEY_COMPLEX, 2, (0, 0, 255), 2)
            camera_feed_placeholder.image(img, channels="BGR")
            cv2.waitKey(500)
            count += 1

        # Check if the "Stop Camera" button was clicked
        if stop_camera_button:
            break

    cap.release()
    cv2.destroyAllWindows()

def stop_camera():
    global camera_open  # Update the global variable
    camera_open = False

def process_images(folder_path):
    results = []

    # Iterate over each image file in the folder
    image_files = [file for file in os.listdir(folder_path) if file.endswith('.jpg')]
    progress_bar = st.progress(0)

    for i, image_file in enumerate(tqdm(image_files, desc="Processing Images", leave=False)):
        image_path = os.path.join(folder_path, image_file)

        # Perform OCR on the image
        plate_number, extracted_characters = perform_ocr(image_path)

        # Append the results to the list
        results.append({'Image': image_file, 'Department': plate_number, 'Extracted Characters': extracted_characters})

        # Update progress bar
        progress = (i + 1) / len(image_files)
        progress_bar.progress(progress)

    # Create a DataFrame from the results list
    data = pd.DataFrame(results, columns=['Image', 'Department', 'Extracted Characters'])
    return data

def main():
    st.set_page_config(page_title="ANPR PUO", page_icon="✨", layout="wide")

    if not login():
        return
    
    PUO = """
    **Politeknik Ungku Omar**
    """

    team_members = """
    **Team members:**

    MELVIN RAJ A/L EALUMALAI (01DDT21F1066)

    HARITHS HAZIQ BIN NOOR AZIAN (01DDT21F1058)

    MUHAMMAD AIDIL FIKRI BIN MOHD NIZAM (01DDT21F1072)
    """

    supervisor = """
    **Supervisor:**

    MOHD ASSIDIQ B. CHE AHMAD
    """

    st.title("Real-time Number Plate Recognition System 🚘🚙")

    # Upload multiple image files
    uploaded_files = st.file_uploader("Upload multiple image files", accept_multiple_files=True)

    if uploaded_files is not None:
        # Create a temporary folder to store the uploaded images
        temp_folder = os.path.join(os.getcwd(), 'temp_images')
        os.makedirs(temp_folder, exist_ok=True)

        # Save the uploaded images to the temporary folder
        for file in uploaded_files:
            file_path = os.path.join(temp_folder, file.name)
            with open(file_path, "wb") as f:
                f.write(file.getbuffer())

        # Process the images and get the results
        data = process_images(temp_folder)

        # Display the results in a table
        st.subheader("OCR Results")
        st.dataframe(data)

        # Download the results as an Excel file
        st.markdown(get_excel_download_link(data), unsafe_allow_html=True)

        # Remove the temporary folder and its contents
        for file_name in os.listdir(temp_folder):
            file_path = os.path.join(temp_folder, file_name)
            os.remove(file_path)
        os.rmdir(temp_folder)

        # Display team members and supervisor information
        st.sidebar.markdown(PUO)
        st.sidebar.markdown(team_members)
        st.sidebar.markdown(supervisor)

        camera_buttons_container = st.container()
    with camera_buttons_container:
        open_camera_button = st.button("Open Camera")
        stop_camera_button = st.button("Stop Camera")

    if open_camera_button:
        open_camera()

    if stop_camera_button:
        stop_camera()
    st.title("Insert, Display, and Delete Data in 'registered_vehicles' Table")

    # Input fields
    number_plate = st.text_input("Number Plate")
    department = st.text_input("Department")

    # Buttons
    button_col1, button_col2 = st.columns(2)
    insert_button = button_col1.button("Insert")
    delete_button = button_col2.button("Delete")

    if insert_button:
        # Insert data into the 'registered_vehicle' table
        query = "INSERT INTO registered_vehicles (NUMBER_PLATE, DEPARTMENT) VALUES (%s, %s)"
        values = (number_plate, department)

        cursor.execute(query, values)
        mydb.commit()

        st.success("Data inserted successfully!")

    if delete_button:
        # Delete data from the 'registered_vehicle' table
        query = "DELETE FROM registered_vehicles WHERE NUMBER_PLATE = %s"
        values = (number_plate,)

        cursor.execute(query, values)
        mydb.commit()

        st.success("Data deleted successfully!")

    # Display the data from the 'registered_vehicle' table
    display_data2()

    # Close the cursor and connection
    cursor.close()
    mydb.close()

    

def get_excel_download_link(data):
    output_path = 'output.xlsx'
    data.to_excel(output_path, index=False)
    with open(output_path, 'rb') as f:
        contents = f.read()
    encoded_contents = base64.b64encode(contents).decode("utf-8")
    href = f'<a href="data:application/vnd.openxmlformats-officedocument.spreadsheetml.sheet;base64,{encoded_contents}" download="output.xlsx">Download Excel File</a>'
    return href





if __name__ == '__main__':
    main()
