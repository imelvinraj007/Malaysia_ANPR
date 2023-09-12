import json
import time
from collections import OrderedDict
import cv2
import requests
import pandas as pd
import os

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
    
    if num.lower() == 'jtx1422' or num.lower() == 'hy10233':
        return 'JTMK', characters
    else:
        return 'Unknown', characters

def main():
    folder_path = 'C:/Users/imelv/OneDrive/Desktop/ANPR'  # Folder containing the images
    output_path = 'C:/Users/imelv/OneDrive/Desktop/output.xlsx'  # Output Excel file path
    
    results = []
    
    # Iterate over each image file in the folder
    for image_file in os.listdir(folder_path):
        if image_file.endswith('.jpg'):
            image_path = os.path.join(folder_path, image_file)
            
            # Perform OCR on the image
            plate_number, extracted_characters = perform_ocr(image_path)
            
            # Append the results to the list
            results.append({'Image': image_file, 'Number Plate': plate_number, 'Extracted Characters': extracted_characters})
    
    # Create a DataFrame from the results list
    data = pd.DataFrame(results, columns=['Image', 'Number Plate', 'Extracted Characters'])
    
    # Save the results to an Excel file
    data.to_excel(output_path, index=False)
    
    print("OCR completed. Results saved in", output_path)

if __name__ == '__main__':
    main()
